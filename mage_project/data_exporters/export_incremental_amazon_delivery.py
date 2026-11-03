import os
import uuid
from datetime import datetime, timezone

import pandas as pd
import pyodbc

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


EXPECTED_COLUMN_COUNT = 16

SOURCE_COLUMNS = [
    'Order_ID',
    'Agent_Age',
    'Agent_Rating',
    'Store_Latitude',
    'Store_Longitude',
    'Drop_Latitude',
    'Drop_Longitude',
    'Order_Date',
    'Order_Time',
    'Pickup_Time',
    'Weather',
    'Traffic',
    'Vehicle',
    'Area',
    'Delivery_Time',
    'Category',
]

BATCH_CONFIG = {
    'INITIAL_FULL': {
        'batch_type': 'FULL_LOAD',
        'start_date': '2022-02-11',
        'end_date': '2022-02-18',
        'expected_row_count': 6_982,
    },
    'INCREMENTAL_01': {
        'batch_type': 'INCREMENTAL',
        'start_date': '2022-03-01',
        'end_date': '2022-03-31',
        'expected_row_count': 30_658,
    },
    'INCREMENTAL_02': {
        'batch_type': 'INCREMENTAL',
        'start_date': '2022-04-01',
        'end_date': '2022-04-06',
        'expected_row_count': 6_099,
    },
}


def get_connection_string():
    required_variables = ('MSSQL_SERVER', 'MSSQL_DATABASE', 'MSSQL_DRIVER')
    missing = [name for name in required_variables if not os.environ.get(name)]

    if missing:
        raise RuntimeError(
            'Thiếu biến môi trường: '
            + ', '.join(missing)
            + '. Hãy dừng Mage, đặt biến trong PowerShell và khởi động lại.'
        )

    return (
        f"DRIVER={{{os.environ['MSSQL_DRIVER']}}};"
        f"SERVER={os.environ['MSSQL_SERVER']};"
        f"DATABASE={os.environ['MSSQL_DATABASE']};"
        'Trusted_Connection=yes;'
        'Encrypt=yes;'
        'TrustServerCertificate=yes;'
    )


def to_database_value(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, 'item'):
        try:
            return value.item()
        except (AttributeError, ValueError):
            pass
    return value


def get_batch_name(kwargs):
    batch_name = kwargs.get('batch_name')

    if not batch_name and isinstance(kwargs.get('variables'), dict):
        batch_name = kwargs['variables'].get('batch_name')

    if not isinstance(batch_name, str) or not batch_name.strip():
        raise ValueError(
            'Thiếu runtime variable batch_name. Giá trị hợp lệ: '
            + ', '.join(BATCH_CONFIG)
        )

    batch_name = batch_name.strip().upper()
    if batch_name not in BATCH_CONFIG:
        raise ValueError(
            f'batch_name không hợp lệ: {batch_name!r}. Giá trị hợp lệ: '
            + ', '.join(BATCH_CONFIG)
        )

    return batch_name


def build_output(
    load_batch_id,
    batch_name,
    config,
    status,
    source_file_name,
    source_file_checksum,
    rows_read,
    rows_loaded,
    reason=None,
):
    return pd.DataFrame(
        [
            {
                'load_batch_id': load_batch_id,
                'batch_name': batch_name,
                'batch_type': config['batch_type'],
                'status': status,
                'source_file_name': source_file_name,
                'source_file_checksum': source_file_checksum,
                'expected_row_count': config['expected_row_count'],
                'rows_read': rows_read,
                'rows_loaded': rows_loaded,
                'rows_rejected': 0,
                'start_date': config['start_date'],
                'end_date': config['end_date'],
                'reason': reason,
            }
        ]
    )


@data_exporter
def export_incremental_amazon_delivery(payload, *args, **kwargs):
    batch_name = get_batch_name({'batch_name': payload['batch_name']})
    config = BATCH_CONFIG[batch_name]

    file_checksum = payload['source_file_checksum']
    source_file_name = payload['source_file_name']
    load_batch_id = str(uuid.uuid4())
    loaded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    rows_read = 0

    connection = pyodbc.connect(get_connection_string(), autocommit=False)
    batch_created = False

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO audit.load_batch
            (
                load_batch_id,
                batch_name,
                batch_type,
                source_file_name,
                source_file_checksum,
                expected_date_from,
                expected_date_to,
                expected_row_count,
                status,
                rows_read,
                rows_loaded,
                rows_rejected,
                error_message
            )
            VALUES
            (
                ?, ?, ?, ?, ?, ?, ?, ?,
                'STARTED', ?, 0, 0, NULL
            );
            """,
            load_batch_id,
            batch_name,
            config['batch_type'],
            source_file_name,
            file_checksum,
            config['start_date'],
            config['end_date'],
            config['expected_row_count'],
            0,
        )
        connection.commit()
        batch_created = True

        rows_read = int(payload['rows_read'])

        cursor.execute(
            """
            UPDATE audit.load_batch
            SET rows_read = ?
            WHERE load_batch_id = ?;
            """,
            rows_read,
            load_batch_id,
        )

        if payload.get('validation_error'):
            raise ValueError(payload['validation_error'])

        batch_df = payload['data']
        normalized_order_ids = batch_df['Order_ID'].astype(str).str.strip()
        normalized_order_keys = normalized_order_ids.str.casefold()

        cursor.execute(
            """
            SELECT TOP (1)
                b.load_batch_id
            FROM audit.load_batch AS b
            WHERE b.load_batch_id <> ?
              AND b.batch_name = ?
              AND b.batch_type = ?
              AND b.source_file_checksum = ?
              AND b.expected_date_from = ?
              AND b.expected_date_to = ?
              AND b.expected_row_count = ?
              AND b.rows_read = ?
              AND b.rows_loaded = ?
              AND b.status = 'SUCCEEDED'
              AND (
                    SELECT COUNT_BIG(*)
                    FROM staging.raw_amazon_delivery AS s
                    WHERE s.load_batch_id = b.load_batch_id
                  ) = ?
            ORDER BY b.finished_at DESC, b.started_at DESC;
            """,
            load_batch_id,
            batch_name,
            config['batch_type'],
            file_checksum,
            config['start_date'],
            config['end_date'],
            config['expected_row_count'],
            rows_read,
            config['expected_row_count'],
            config['expected_row_count'],
        )
        existing_successful_batch = cursor.fetchone()

        if existing_successful_batch:
            skip_reason = (
                f'Batch đã SUCCEEDED trước đó: {existing_successful_batch[0]}'
            )
            cursor.execute(
                """
                UPDATE audit.load_batch
                SET
                    finished_at = SYSUTCDATETIME(),
                    status = 'SKIPPED',
                    rows_read = ?,
                    rows_loaded = 0,
                    rows_rejected = 0,
                    error_message = ?
                WHERE load_batch_id = ?;
                """,
                rows_read,
                skip_reason,
                load_batch_id,
            )
            connection.commit()
            return build_output(
                load_batch_id,
                batch_name,
                config,
                'SKIPPED',
                source_file_name,
                file_checksum,
                rows_read,
                0,
                skip_reason,
            )

        cursor.execute(
            """
            SELECT Order_ID
            FROM staging.raw_amazon_delivery
            WHERE Order_ID IS NOT NULL;
            """
        )
        existing_order_keys = {
            str(row[0]).strip().casefold()
            for row in cursor.fetchall()
            if str(row[0]).strip()
        }
        overlapping_keys = set(normalized_order_keys).intersection(
            existing_order_keys
        )
        if overlapping_keys:
            overlap_examples = normalized_order_ids[
                normalized_order_keys.isin(overlapping_keys)
            ].head(10).tolist()
            raise ValueError(
                f'{batch_name} có {len(overlapping_keys):,} Order_ID đã tồn tại '
                f'trong staging. Ví dụ: {overlap_examples}'
            )

        insert_sql = """
            INSERT INTO staging.raw_amazon_delivery
            (
                Order_ID,
                Agent_Age,
                Agent_Rating,
                Store_Latitude,
                Store_Longitude,
                Drop_Latitude,
                Drop_Longitude,
                Order_Date,
                Order_Time,
                Pickup_Time,
                Weather,
                Traffic,
                Vehicle,
                Area,
                Delivery_Time,
                Category,
                source_file_name,
                source_row_number,
                load_batch_id,
                loaded_at
            )
            VALUES
            (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            );
        """

        rows_to_insert = []
        for row in batch_df.itertuples(index=False, name=None):
            source_values = row[:EXPECTED_COLUMN_COUNT]
            source_row_number = row[EXPECTED_COLUMN_COUNT]
            rows_to_insert.append(
                tuple(to_database_value(value) for value in source_values)
                + (
                    source_file_name,
                    source_row_number,
                    load_batch_id,
                    loaded_at,
                )
            )

        cursor.fast_executemany = True
        cursor.executemany(insert_sql, rows_to_insert)

        cursor.execute(
            """
            SELECT COUNT_BIG(*)
            FROM staging.raw_amazon_delivery
            WHERE load_batch_id = ?;
            """,
            load_batch_id,
        )
        loaded_row_count = int(cursor.fetchone()[0])
        if loaded_row_count != config['expected_row_count']:
            raise RuntimeError(
                f'SQL Server nhận {loaded_row_count:,} dòng cho {batch_name}; '
                f'cần {config["expected_row_count"]:,} dòng.'
            )

        cursor.execute(
            """
            UPDATE audit.load_batch
            SET
                finished_at = SYSUTCDATETIME(),
                status = 'SUCCEEDED',
                rows_loaded = ?,
                rows_rejected = 0,
                error_message = NULL
            WHERE load_batch_id = ?;
            """,
            loaded_row_count,
            load_batch_id,
        )
        connection.commit()

        return build_output(
            load_batch_id,
            batch_name,
            config,
            'SUCCEEDED',
            source_file_name,
            file_checksum,
            rows_read,
            loaded_row_count,
        )

    except Exception as error:
        connection.rollback()

        if batch_created:
            try:
                failure_cursor = connection.cursor()
                failure_cursor.execute(
                    """
                    UPDATE audit.load_batch
                    SET
                        finished_at = SYSUTCDATETIME(),
                        status = 'FAILED',
                        rows_read = ?,
                        rows_loaded = 0,
                        rows_rejected = 0,
                        error_message = ?
                    WHERE load_batch_id = ?;
                    """,
                    rows_read,
                    str(error)[:4000],
                    load_batch_id,
                )
                connection.commit()
            except Exception:
                connection.rollback()
        raise

    finally:
        connection.close()


@test
def test_output(output, *args):
    assert output is not None, 'Block không trả kết quả.'
    assert len(output) == 1, 'Kết quả phải có đúng một dòng tóm tắt.'

    batch_name = str(output.iloc[0]['batch_name']).upper()
    assert batch_name in BATCH_CONFIG, f'batch_name không hợp lệ: {batch_name}'

    config = BATCH_CONFIG[batch_name]
    status = str(output.iloc[0]['status']).upper()
    assert status in {'SUCCEEDED', 'SKIPPED'}, f'Status không hợp lệ: {status}'
    assert int(output.iloc[0]['rows_read']) == config['expected_row_count']
    assert int(output.iloc[0]['expected_row_count']) == config['expected_row_count']

    if status == 'SUCCEEDED':
        assert int(output.iloc[0]['rows_loaded']) == config['expected_row_count']
    else:
        assert int(output.iloc[0]['rows_loaded']) == 0
