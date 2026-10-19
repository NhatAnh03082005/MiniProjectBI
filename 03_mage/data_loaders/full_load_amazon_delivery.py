import hashlib
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pyodbc

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


EXPECTED_ROW_COUNT = 43_739
EXPECTED_COLUMN_COUNT = 16
EXPECTED_DATE_FROM = date(2022, 2, 11)
EXPECTED_DATE_TO = date(2022, 4, 6)

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


def calculate_sha256(file_path):
    digest = hashlib.sha256()
    with file_path.open('rb') as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


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


@data_loader
def full_load_amazon_delivery(*args, **kwargs):
    project_root = os.environ.get('BI_PROJECT_ROOT')
    if not project_root:
        raise RuntimeError(
            'Thiếu BI_PROJECT_ROOT. Hãy đặt biến trong PowerShell rồi khởi động lại Mage.'
        )

    source_path = (
        Path(project_root) / '01_data' / 'raw' / 'amazon_delivery.csv'
    )
    if not source_path.is_file():
        raise FileNotFoundError(f'Không tìm thấy file: {source_path}')

    # Giữ nguyên chuỗi nguồn tại raw, gồm cả chuỗi "NaN" và ô trống.
    # Chuẩn hóa missing và ép kiểu chỉ diễn ra ở lớp dbt staging.
    source_df = pd.read_csv(
        source_path,
        dtype=str,
        encoding='utf-8',
        keep_default_na=False,
        na_filter=False,
    )
    actual_row_count, actual_column_count = source_df.shape

    if actual_row_count != EXPECTED_ROW_COUNT:
        raise ValueError(
            f'Sai số dòng: nhận {actual_row_count:,}, '
            f'cần {EXPECTED_ROW_COUNT:,}.'
        )

    if actual_column_count != EXPECTED_COLUMN_COUNT:
        raise ValueError(
            f'Sai số cột: nhận {actual_column_count}, '
            f'cần {EXPECTED_COLUMN_COUNT}.'
        )

    if list(source_df.columns) != SOURCE_COLUMNS:
        raise ValueError(
            'Header CSV không đúng thứ tự/tên cột.\n'
            f'Nhận được: {list(source_df.columns)}\n'
            f'Mong đợi: {SOURCE_COLUMNS}'
        )

    file_checksum = calculate_sha256(source_path)
    source_file_name = source_path.name
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
            WHERE b.batch_type = 'FULL_LOAD'
              AND b.source_file_checksum = ?
              AND b.status = 'SUCCEEDED'
              AND (
                    SELECT COUNT_BIG(*)
                    FROM staging.raw_amazon_delivery AS s
                    WHERE s.load_batch_id = b.load_batch_id
                  ) = ?
            ORDER BY b.finished_at DESC, b.started_at DESC;
            """,
            file_checksum,
            EXPECTED_ROW_COUNT,
        )
        existing_batch = cursor.fetchone()

        if existing_batch:
            connection.rollback()
            return pd.DataFrame(
                [
                    {
                        'status': 'SKIPPED',
                        'reason': 'Checksum đã được nạp thành công trước đó',
                        'load_batch_id': existing_batch[0],
                        'source_file_name': source_file_name,
                        'source_file_checksum': file_checksum,
                        'rows_read': actual_row_count,
                        'rows_loaded': 0,
                    }
                ]
            )

        # Tạo audit batch theo đúng DDL: ID là VARCHAR nên Python tự tạo UUID.
        cursor.execute(
            """
            INSERT INTO audit.load_batch
            (
                load_batch_id,
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
                ?, 'FULL_LOAD', ?, ?, ?, ?, ?,
                'STARTED', ?, 0, 0, NULL
            );
            """,
            load_batch_id,
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
                    'source_file_name': source_file_name,
                    'source_file_checksum': file_checksum,
                    'rows_read': actual_row_count,
                    'rows_loaded': loaded_row_count,
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
