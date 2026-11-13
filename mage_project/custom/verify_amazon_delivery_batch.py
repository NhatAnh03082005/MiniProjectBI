import os

import pandas as pd
import pyodbc

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


def get_connection_string():
    required = ('MSSQL_SERVER', 'MSSQL_DATABASE', 'MSSQL_DRIVER')
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError('Thiếu biến môi trường: ' + ', '.join(missing))
    return (
        f"DRIVER={{{os.environ['MSSQL_DRIVER']}}};"
        f"SERVER={os.environ['MSSQL_SERVER']};"
        f"DATABASE={os.environ['MSSQL_DATABASE']};"
        'Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;'
    )


@custom
def verify_amazon_delivery_batch(export_result, *args, **kwargs):
    if export_result is None or len(export_result) != 1:
        raise ValueError('Exporter phải trả đúng một dòng tóm tắt batch.')
    result = export_result.iloc[0]
    load_batch_id = str(result['load_batch_id'])

    with pyodbc.connect(get_connection_string()) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT status, rows_read, rows_loaded, rows_rejected,
                   rows_inserted, rows_updated, rows_unchanged,
                   source_file_checksum
            FROM audit.load_batch
            WHERE load_batch_id = ?;
            """,
            load_batch_id,
        )
        audit = cursor.fetchone()
        if audit is None:
            raise ValueError('Không tìm thấy audit batch vừa chạy.')

        status = str(result['status']).upper()
        if status != 'SUCCEEDED' or str(audit[0]).upper() != status:
            raise ValueError(f'Batch không SUCCEEDED: result={status}, audit={audit[0]}')

        expected_values = (
            int(result['rows_read']),
            int(result['rows_loaded']),
            int(result['rows_rejected']),
            int(result['rows_inserted']),
            int(result['rows_updated']),
            int(result['rows_unchanged']),
        )
        audit_values = tuple(int(value) for value in audit[1:7])
        if audit_values != expected_values:
            raise ValueError(
                f'Action counter không khớp: audit={audit_values}, result={expected_values}'
            )
        if expected_values[0] != sum(expected_values[2:6]):
            raise ValueError('rows_read không bằng insert + update + unchanged + rejected.')
        if expected_values[1] != expected_values[3] + expected_values[4]:
            raise ValueError('rows_loaded không bằng insert + update.')
        if str(audit[7]).lower() != str(result['source_file_checksum']).lower():
            raise ValueError('Checksum trong audit không khớp kết quả exporter.')

        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN load_batch_id = ? THEN 1 ELSE 0 END),
                SUM(CASE WHEN updated_load_batch_id = ? AND load_batch_id <> ?
                         THEN 1 ELSE 0 END),
                SUM(CASE WHEN (load_batch_id = ? OR updated_load_batch_id = ?)
                              AND row_hash IS NULL THEN 1 ELSE 0 END)
            FROM staging.raw_amazon_delivery;
            """,
            load_batch_id,
            load_batch_id,
            load_batch_id,
            load_batch_id,
            load_batch_id,
        )
        staging = cursor.fetchone()
        inserted = int(staging[0] or 0)
        updated = int(staging[1] or 0)
        null_hashes = int(staging[2] or 0)
        if inserted != expected_values[3] or updated != expected_values[4]:
            raise ValueError(
                f'Lineage staging không khớp: insert={inserted}, update={updated}.'
            )
        if null_hashes:
            raise ValueError(f'Có {null_hashes} dòng được chạm nhưng thiếu row_hash.')

    return pd.DataFrame([{
        'load_batch_id': load_batch_id,
        'batch_name': str(result['batch_name']),
        'status': status,
        'rows_read': expected_values[0],
        'rows_inserted': expected_values[3],
        'rows_updated': expected_values[4],
        'rows_unchanged': expected_values[5],
        'rows_rejected': expected_values[2],
        'verified': True,
    }])


@test
def test_verification(output, *args):
    assert output is not None and len(output) == 1
    assert bool(output.iloc[0]['verified'])
