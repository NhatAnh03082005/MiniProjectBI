import os

import pandas as pd
import pyodbc

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@custom
def verify_amazon_delivery_batch(export_result, *args, **kwargs):
    if export_result is None or len(export_result) != 1:
        raise ValueError('Exporter phải trả đúng một dòng tóm tắt batch.')
    result = export_result.iloc[0]
    required_variables = ('MSSQL_SERVER', 'MSSQL_DATABASE', 'MSSQL_DRIVER')
    missing = [name for name in required_variables if not os.environ.get(name)]
    if missing:
        raise RuntimeError('Thiếu biến môi trường: ' + ', '.join(missing))
    connection_string = (
        f"DRIVER={{{os.environ['MSSQL_DRIVER']}}};"
        f"SERVER={os.environ['MSSQL_SERVER']};"
        f"DATABASE={os.environ['MSSQL_DATABASE']};"
        'Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;'
    )
    with pyodbc.connect(connection_string) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT b.status, b.rows_read, b.rows_loaded, b.rows_rejected,
                   b.source_file_checksum,
                   (SELECT COUNT_BIG(*) FROM staging.raw_amazon_delivery AS s
                    WHERE s.load_batch_id = b.load_batch_id)
            FROM audit.load_batch AS b
            WHERE b.load_batch_id = ?;
            """,
            str(result['load_batch_id']),
        )
        audit_row = cursor.fetchone()
        if audit_row is None:
            raise ValueError('Không tìm thấy audit batch vừa chạy.')

        status = str(result['status']).upper()
        expected = int(result['expected_row_count'])
        if audit_row[0] != status or int(audit_row[1]) != int(result['rows_read']):
            raise ValueError('Trạng thái hoặc số dòng đọc không khớp audit.')
        if int(audit_row[2]) != int(result['rows_loaded']) or int(audit_row[3]) != 0:
            raise ValueError('Số dòng nạp/từ chối không khớp audit.')
        if str(audit_row[4]).lower() != str(result['source_file_checksum']).lower():
            raise ValueError('Checksum trong audit không khớp kết quả exporter.')

        if status == 'SUCCEEDED':
            if int(audit_row[5]) != expected or int(audit_row[2]) != expected:
                raise ValueError('Số dòng staging của batch không đạt kỳ vọng.')
        elif status == 'SKIPPED':
            if int(audit_row[5]) != 0 or int(audit_row[2]) != 0:
                raise ValueError('Batch SKIPPED không được ghi thêm dòng staging.')
            cursor.execute(
                """
                SELECT TOP (1) b.load_batch_id
                FROM audit.load_batch AS b
                WHERE b.batch_name = ? AND b.batch_type = ?
                  AND b.source_file_checksum = ?
                  AND b.expected_date_from = ? AND b.expected_date_to = ?
                  AND b.expected_row_count = ? AND b.rows_read = ?
                  AND b.rows_loaded = ? AND b.status = 'SUCCEEDED'
                  AND (SELECT COUNT_BIG(*) FROM staging.raw_amazon_delivery AS s
                       WHERE s.load_batch_id = b.load_batch_id) = ?;
                """,
                str(result['batch_name']),
                str(result['batch_type']),
                str(result['source_file_checksum']),
                str(result['start_date']),
                str(result['end_date']),
                expected, expected, expected, expected,
            )
            if cursor.fetchone() is None:
                raise ValueError('Không tìm thấy batch SUCCEEDED đầy đủ cho lần SKIPPED.')
        else:
            raise ValueError(f'Trạng thái batch không hợp lệ: {status}')

    return pd.DataFrame([{
        'load_batch_id': str(result['load_batch_id']),
        'batch_name': str(result['batch_name']),
        'status': status,
        'expected_row_count': expected,
        'rows_read': int(result['rows_read']),
        'rows_loaded': int(result['rows_loaded']),
        'verified': True,
    }])


@test
def test_verification(output, *args):
    assert output is not None and len(output) == 1
    assert bool(output.iloc[0]['verified'])
