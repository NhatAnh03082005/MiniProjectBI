import os

import pandas as pd
import pyodbc


if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader

if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@data_loader
def test_connection(*args, **kwargs):
    server = os.environ['MSSQL_SERVER']
    database = os.environ['MSSQL_DATABASE']
    driver = os.environ['MSSQL_DRIVER']

    connection_string = (
        f'DRIVER={{{driver}}};'
        f'SERVER={server};'
        f'DATABASE={database};'
        'Trusted_Connection=yes;'
        'Encrypt=yes;'
        'TrustServerCertificate=yes;'
    )

    query = """
    SELECT
        DB_NAME() AS database_name,
        SUSER_SNAME() AS login_name,
        SCHEMA_ID('audit') AS audit_schema_id,
        SCHEMA_ID('staging') AS staging_schema_id,
        OBJECT_ID('audit.load_batch') AS audit_table_id,
        OBJECT_ID('staging.raw_amazon_delivery') AS staging_table_id;
    """

    with pyodbc.connect(connection_string, timeout=10) as connection:
        cursor = connection.cursor()
        cursor.execute(query)

        columns = [
            column[0]
            for column in cursor.description
        ]

        rows = [
            tuple(row)
            for row in cursor.fetchall()
        ]

    return pd.DataFrame(rows, columns=columns)


@test
def validate_connection(output, *args):
    assert output is not None
    assert len(output) == 1

    row = output.iloc[0]

    assert row['database_name'] == 'AmazonDeliveryBI'
    assert pd.notna(row['audit_schema_id'])
    assert pd.notna(row['staging_schema_id'])
    assert pd.notna(row['audit_table_id'])
    assert pd.notna(row['staging_table_id'])