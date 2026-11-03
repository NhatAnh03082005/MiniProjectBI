import os
import uuid
from datetime import date, datetime, timezone

import pandas as pd
import pyodbc

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


EXPECTED_ROW_COUNT = 43_739
EXPECTED_COLUMN_COUNT = 16
EXPECTED_DATE_FROM = date(2022, 2, 11)
EXPECTED_DATE_TO = date(2022, 4, 6)
BATCH_NAME = 'FULL_DATASET'

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


@data_exporter
def export_full_amazon_delivery(payload, *args, **kwargs):
    source_df = payload['data']
    actual_row_count = len(source_df)
    file_checksum = payload['source_file_checksum']
    source_file_name = payload['source_file_name']
    load_batch_id = str(uuid.uuid4())
    loaded_at = datetime.now(timezone.utc).replace(tzinfo=None)

    connection = pyodbc.connect(get_connection_string(), autocommit=False)
    batch_created = False

    try:
        cursor = connection.cursor()

        # Idempotency: chỉ bỏ qua khi cùng checksum đã SUCCEEDED và batch đó
        # thực sự có đủ 43.739 dòng trong staging.
        cursor.execute(
            """
            SELECT TOP (1)
                b.load_batch_id
            FROM audit.load_batch AS b
            WHERE b.batch_name = ?
              AND b.batch_type = 'FULL_LOAD'
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
            BATCH_NAME,
            file_checksum,
            EXPECTED_DATE_FROM,
            EXPECTED_DATE_TO,
            EXPECTED_ROW_COUNT,
            EXPECTED_ROW_COUNT,
            EXPECTED_ROW_COUNT,
            EXPECTED_ROW_COUNT,
        )
        existing_batch = cursor.fetchone()

        if existing_batch:
            skip_reason = (
                f'Batch đã SUCCEEDED trước đó: {existing_batch[0]}'
            )
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
                    finished_at,
                    status,
                    rows_read,
                    rows_loaded,
                    rows_rejected,
                    error_message
                )
                VALUES
                (
                    ?, ?, 'FULL_LOAD', ?, ?, ?, ?, ?,
                    SYSUTCDATETIME(), 'SKIPPED', ?, 0, 0, ?
                );
                """,
                load_batch_id,
                BATCH_NAME,
                source_file_name,
                file_checksum,
                EXPECTED_DATE_FROM,
                EXPECTED_DATE_TO,
                EXPECTED_ROW_COUNT,
                actual_row_count,
                skip_reason,
            )
            connection.commit()
            return pd.DataFrame(
                [
                    {
                        'status': 'SKIPPED',
                        'reason': skip_reason,
                        'load_batch_id': load_batch_id,
                        'batch_name': BATCH_NAME,
                        'batch_type': 'FULL_LOAD',
                        'source_file_name': source_file_name,
                        'source_file_checksum': file_checksum,
                        'expected_row_count': EXPECTED_ROW_COUNT,
                        'rows_read': actual_row_count,
                        'rows_loaded': 0,
                        'rows_rejected': 0,
                        'start_date': EXPECTED_DATE_FROM.isoformat(),
                        'end_date': EXPECTED_DATE_TO.isoformat(),
                    }
                ]
            )

        # A full load cannot be added after incremental batches have already
        # loaded the same orders into staging.
        normalized_order_ids = source_df['Order_ID'].astype(str).str.strip()
        normalized_order_keys = normalized_order_ids.str.casefold()
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
                f'{BATCH_NAME} có {len(overlapping_keys):,} Order_ID đã tồn tại '
                f'trong staging. Ví dụ: {overlap_examples}'
            )

        # Tạo audit batch theo đúng DDL: ID là VARCHAR nên Python tự tạo UUID.
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
                ?, ?, 'FULL_LOAD', ?, ?, ?, ?, ?,
                'STARTED', ?, 0, 0, NULL
            );
            """,
            load_batch_id,
            BATCH_NAME,
            source_file_name,
            file_checksum,
            EXPECTED_DATE_FROM,
            EXPECTED_DATE_TO,
            EXPECTED_ROW_COUNT,
            actual_row_count,
        )
        connection.commit()
        batch_created = True

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
        for source_row_number, source_values in enumerate(
            source_df.itertuples(index=False, name=None),
            start=1,
        ):
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

        if loaded_row_count != EXPECTED_ROW_COUNT:
            raise RuntimeError(
                f'SQL Server nhận {loaded_row_count:,} dòng, '
                f'cần {EXPECTED_ROW_COUNT:,} dòng.'
            )

        # Staging insert và cập nhật SUCCEEDED nằm trong cùng transaction.
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

        return pd.DataFrame(
            [
                {
                    'status': 'SUCCEEDED',
                    'load_batch_id': load_batch_id,
                    'batch_name': BATCH_NAME,
                    'batch_type': 'FULL_LOAD',
                    'source_file_name': source_file_name,
                    'source_file_checksum': file_checksum,
                    'expected_row_count': EXPECTED_ROW_COUNT,
                    'rows_read': actual_row_count,
                    'rows_loaded': loaded_row_count,
                    'rows_rejected': 0,
                    'start_date': EXPECTED_DATE_FROM.isoformat(),
                    'end_date': EXPECTED_DATE_TO.isoformat(),
                }
            ]
        )

    except Exception as error:
        connection.rollback()

        # Batch STARTED đã commit riêng. Nếu load lỗi, staging được rollback
        # và audit batch được giữ lại với trạng thái FAILED.
        if batch_created:
            try:
                failure_cursor = connection.cursor()
                failure_cursor.execute(
                    """
                    UPDATE audit.load_batch
                    SET
                        finished_at = SYSUTCDATETIME(),
                        status = 'FAILED',
                        rows_loaded = 0,
                        rows_rejected = 0,
                        error_message = ?
                    WHERE load_batch_id = ?;
                    """,
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

    status = str(output.iloc[0]['status']).upper()
    assert status in {'SUCCEEDED', 'SKIPPED'}, f'Status không hợp lệ: {status}'
    assert int(output.iloc[0]['rows_read']) == EXPECTED_ROW_COUNT

    if status == 'SUCCEEDED':
        assert int(output.iloc[0]['rows_loaded']) == EXPECTED_ROW_COUNT
    else:
        assert int(output.iloc[0]['rows_loaded']) == 0
