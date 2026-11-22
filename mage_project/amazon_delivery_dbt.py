"""Run dbt after verified ingestion, against the exact same SQL target.

Ingestion has already committed. A failed build must fail the Mage block; rerun
the whole pipeline to upsert idempotently and rebuild DDS. No ingestion counters
are overwritten and no partial dbt build is described as rolled back.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from contextlib import closing
from datetime import datetime, timezone

import pandas as pd
import pyodbc
import yaml

from mage_project.amazon_delivery_repository import get_connection_string


def _write_json(path: Path, value: dict) -> None:
    pending = path.with_suffix('.pending')
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    pending.replace(path)


def _dbt_python(root: Path) -> Path:
    configured = os.environ.get('DBT_PYTHON_EXECUTABLE')
    if configured:
        candidate = Path(configured).expanduser().resolve()
    else:
        candidate = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if not candidate.is_file():
            candidate = Path(sys.executable)
    if not candidate.is_file():
        raise RuntimeError('Không tìm thấy Python dbt. Cấu hình DBT_PYTHON_EXECUTABLE.')
    return candidate


def _profile() -> dict:
    # Do not read the developer's profiles.yml: it can point at another database.
    # port=None prevents silently adding ,1433 to a named/local instance.
    return {'amazon_delivery_bi': {'target': 'mage', 'outputs': {'mage': {
        'type': 'sqlserver',
        'driver': os.environ['MSSQL_DRIVER'],
        'server': os.environ['MSSQL_SERVER'],
        'port': None,
        'database': os.environ['MSSQL_DATABASE'],
        'schema': 'dw',
        'windows_login': os.environ.get('MSSQL_AUTHENTICATION', 'windows').lower() == 'windows',
        **({'authentication': 'sql',
            'user': "{{ env_var('MSSQL_USER') }}",
            'password': "{{ env_var('MSSQL_PASSWORD') }}"}
           if os.environ.get('MSSQL_AUTHENTICATION', 'windows').lower() == 'sql' else {}),
        'encrypt': True,
        'trust_cert': True,
        'threads': 1,
        'login_timeout': 30,
        'query_timeout': 600,
    }}}}


def _read_results(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError('dbt không sinh run_results.json; xem dbt_stdout.log.')
    artifact = json.loads(path.read_text(encoding='utf-8'))
    results = artifact.get('results', [])
    if not results:
        raise RuntimeError('dbt không chạy model/test nào; không đánh dấu thành công.')
    tests = [row for row in results if row['unique_id'].startswith('test.')]
    counts = {state: sum(row['status'] == state for row in tests)
              for state in ('pass', 'warn', 'fail', 'error', 'skipped')}
    return {
        'invocation_id': artifact.get('metadata', {}).get('invocation_id', ''),
        'nodes_total': len(results),
        'nodes_failed': sum(row['status'] in ('fail', 'error') for row in results),
        'tests_total': len(tests),
        **{f'tests_{key}': count for key, count in counts.items()},
    }


def run_dbt_after_verification(verified: pd.DataFrame) -> pd.DataFrame:
    if verified is None or len(verified) != 1:
        raise ValueError('Cần đúng một kết quả Verify trước khi chạy dbt.')
    row = verified.iloc[0]
    if not bool(row['verified']) or str(row['status']) != 'SUCCEEDED':
        raise ValueError('Ingestion chưa Verify thành công; không chạy dbt.')
    batch_id = str(uuid.UUID(str(row['load_batch_id'])))
    root = Path(os.environ['BI_PROJECT_ROOT']).resolve()
    attempt_id = str(uuid.uuid4())
    work = root / 'logs' / 'etl' / batch_id / attempt_id
    work.mkdir(parents=True, exist_ok=False)
    summary = {
        'load_batch_id': batch_id, 'dbt_attempt_id': attempt_id,
        'server': os.environ.get('MSSQL_SERVER', ''),
        'database': os.environ.get('MSSQL_DATABASE', ''),
        'ingestion_status': 'SUCCEEDED', 'dbt_status': 'STARTED',
        'etl_status': 'STARTED', 'started_at': datetime.now(timezone.utc).isoformat(),
        'log_directory': str(work),
    }
    _write_json(work / 'summary.json', summary)
    # One connection owns the lock for the entire build/reconciliation. The
    # exporter uses this same lock for its upsert transaction.
    try:
        with closing(pyodbc.connect(get_connection_string(), autocommit=True, timeout=30)) as connection:
            connection.timeout = 60
            cursor = connection.cursor()
            cursor.execute((root / 'sql/audit/02_create_dbt_run.sql').read_text('utf-8-sig'))
            cursor.execute('''
                INSERT INTO audit.dbt_run
                    (dbt_attempt_id, load_batch_id, status, log_directory)
                VALUES (?, ?, 'STARTED', ?);
            ''', attempt_id, batch_id, str(work))
            exit_code = None
            try:
                cursor.execute('''
                    SET NOCOUNT ON;
                    DECLARE @result INT;
                    EXEC @result = sys.sp_getapplock
                        @Resource = N'amazon_delivery_staging_dds',
                        @LockMode = 'Exclusive', @LockOwner = 'Session', @LockTimeout = 0;
                    SELECT @result;
                ''')
                if cursor.fetchone()[0] < 0:
                    raise RuntimeError('Một ingestion/dbt khác đang ghi dữ liệu; chạy lại sau.')
                # Recheck that the upstream result refers to a real committed batch.
                cursor.execute('SELECT status FROM audit.load_batch WHERE load_batch_id = ?;', batch_id)
                audit = cursor.fetchone()
                if audit is None or audit[0] != 'SUCCEEDED':
                    raise RuntimeError('Audit ingestion không SUCCEEDED; dừng dbt.')
                profile_dir = work / 'profile'
                profile_dir.mkdir()
                (profile_dir / 'profiles.yml').write_text(
                    yaml.safe_dump(_profile(), sort_keys=False), encoding='utf-8')
                env = os.environ.copy()
                # sources.yml reads this variable independently of the dbt profile.
                env.update({
                    'DBT_SQLSERVER_DATABASE': os.environ['MSSQL_DATABASE'],
                    'DBT_SQLSERVER_SERVER': os.environ['MSSQL_SERVER'],
                    'DBT_SQLSERVER_DRIVER': os.environ['MSSQL_DRIVER'],
                    'DBT_SEND_ANONYMOUS_USAGE_STATS': 'false',
                    'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8',
                    'DBT_WARN_ERROR': 'false',
                })
                # Do not inherit a user's warning-to-error policy: the project's
                # intentional rejection WARN must remain a WARN for this pipeline.
                env.pop('DBT_WARN_ERROR_OPTIONS', None)
                command = [str(_dbt_python(root)), '-m', 'dbt.cli.main',
                           '--no-use-colors', '--no-partial-parse',
                           '--log-path', str(work / 'dbt_logs'),
                           'build', '--project-dir', str(root / 'dbt_project'),
                           '--profiles-dir', str(profile_dir), '--target', 'mage',
                           '--target-path', str(work / 'target')]
                timeout = int(os.environ.get('DBT_BUILD_TIMEOUT_SECONDS', '1800'))
                if timeout <= 0:
                    raise ValueError('DBT_BUILD_TIMEOUT_SECONDS phải lớn hơn 0.')
                print(f'Chạy dbt build: database={summary["database"]}; log={work}')
                with (work / 'dbt_stdout.log').open('w', encoding='utf-8') as output:
                    process = subprocess.run(command, cwd=root / 'dbt_project', env=env,
                                             stdout=output, stderr=subprocess.STDOUT,
                                             timeout=timeout, check=False)
                exit_code = process.returncode
                summary['exit_code'] = exit_code
                # Artifacts live in a unique attempt directory: never read an old run.
                if exit_code != 0:
                    # A failing build can still have useful test counts.
                    if (work / 'target/run_results.json').is_file():
                        summary.update(_read_results(work / 'target/run_results.json'))
                    raise RuntimeError(f'dbt build exit_code={exit_code}; xem {work / "dbt_stdout.log"}')
                summary.update(_read_results(work / 'target/run_results.json'))
                if summary['nodes_failed']:
                    raise RuntimeError('dbt artifact có node thất bại dù exit code bằng 0.')
                cursor.execute('''
                    SELECT
                        (SELECT COUNT_BIG(*) FROM staging.raw_amazon_delivery),
                        (SELECT COUNT_BIG(*) FROM dw.fact_delivery),
                        (SELECT COUNT_BIG(DISTINCT staging_row_id) FROM dw.delivery_rejections);
                ''')
                raw, fact, rejected = map(int, cursor.fetchone())
                summary.update({'staging_rows': raw, 'fact_rows': fact,
                                'dbt_rejected_distinct_rows': rejected})
                if raw != fact + rejected:
                    raise RuntimeError('Đối soát DDS sai: staging != fact + dbt rejected distinct rows.')
                summary.update({'dbt_status': 'SUCCEEDED', 'etl_status': 'SUCCEEDED',
                                'reconciliation_status': 'PASS'})
                summary['finished_at'] = datetime.now(timezone.utc).isoformat()
                _write_json(work / 'summary.json', summary)
                cursor.execute('''
                    UPDATE audit.dbt_run SET status = 'SUCCEEDED', finished_at = SYSUTCDATETIME(),
                        exit_code = ?, result_summary = ? WHERE dbt_attempt_id = ?;
                ''', exit_code, json.dumps(summary, ensure_ascii=False), attempt_id)
            except BaseException as error:
                # Keyboard interruption/timeout must never leave a successful status.
                message = (str(error) if isinstance(error, (RuntimeError, ValueError))
                           else f'{type(error).__name__}: xem log lần chạy hoặc cấu hình môi trường.')
                summary.update({'dbt_status': 'FAILED', 'etl_status': 'FAILED',
                                'exit_code': exit_code, 'error_message': message[:2000],
                                'finished_at': datetime.now(timezone.utc).isoformat()})
                _write_json(work / 'summary.json', summary)
                try:
                    cursor.execute('''
                        UPDATE audit.dbt_run SET status = 'FAILED', finished_at = SYSUTCDATETIME(),
                            exit_code = ?, result_summary = ?, error_message = ?
                        WHERE dbt_attempt_id = ?;
                    ''', exit_code, json.dumps(summary, ensure_ascii=False), message[:2000], attempt_id)
                except Exception:
                    print(f'Không cập nhật được audit.dbt_run; xem {work / "summary.json"}')
                raise RuntimeError(f'ETL thất bại ở dbt/đối soát. {message}') from error
    except BaseException as error:
        # Also cover connection/schema/initial audit failures before dbt starts.
        if summary['etl_status'] != 'FAILED':
            summary.update({
                'dbt_status': 'FAILED', 'etl_status': 'FAILED',
                'error_message': f'{type(error).__name__}: dbt setup/connection/audit failed; see Mage logs.',
                'finished_at': datetime.now(timezone.utc).isoformat(),
            })
            _write_json(work / 'summary.json', summary)
        raise
    result = verified.copy()
    result['ingestion_status'] = 'SUCCEEDED'
    result['dbt_status'] = 'SUCCEEDED'
    result['etl_status'] = 'SUCCEEDED'
    result['dbt_attempt_id'] = attempt_id
    result['dbt_log_directory'] = str(work)
    for field in ('tests_total', 'tests_pass', 'tests_warn', 'tests_fail', 'tests_error',
                  'tests_skipped', 'staging_rows', 'fact_rows', 'dbt_rejected_distinct_rows'):
        result[field] = summary[field]
    print(f'ETL SUCCEEDED: batch={batch_id}; fact={summary["fact_rows"]}; log={work}')
    return result
