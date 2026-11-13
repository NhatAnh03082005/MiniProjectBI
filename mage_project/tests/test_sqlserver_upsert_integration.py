import os
import unittest
import uuid
from pathlib import Path
import sys

import pandas as pd
import pyodbc

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mage_project.amazon_delivery_contract import (
    SOURCE_COLUMNS,
    generate_batch_name,
    validate_and_prepare,
)
from mage_project.amazon_delivery_repository import export_amazon_delivery
from mage_project.custom.verify_amazon_delivery_batch import verify_amazon_delivery_batch


RUN_INTEGRATION = os.environ.get('RUN_SQLSERVER_INTEGRATION') == '1'


@unittest.skipUnless(RUN_INTEGRATION, 'Set RUN_SQLSERVER_INTEGRATION=1 to run SQL Server test.')
class SqlServerUpsertIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_database = os.environ.get('MSSQL_DATABASE')
        cls.database = f'AmazonDeliveryBI_MageTest_{uuid.uuid4().hex[:8]}'
        cls.master_connection = pyodbc.connect(
            cls._connection_string('master'), autocommit=True
        )
        cls.master_connection.execute(f'CREATE DATABASE [{cls.database}];')
        os.environ['MSSQL_DATABASE'] = cls.database
        with pyodbc.connect(cls._connection_string(cls.database), autocommit=True) as connection:
            connection.execute('CREATE SCHEMA audit;')
            connection.execute('CREATE SCHEMA staging;')
            connection.execute(
                """
                CREATE TABLE audit.load_batch
                (
                    load_batch_id VARCHAR(64) NOT NULL PRIMARY KEY,
                    batch_name VARCHAR(50) NOT NULL,
                    batch_type VARCHAR(20) NOT NULL,
                    source_file_name NVARCHAR(260) NOT NULL,
                    source_file_checksum CHAR(64) NOT NULL,
                    expected_date_from DATE NULL,
                    expected_date_to DATE NULL,
                    expected_row_count INT NULL,
                    started_at DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
                    finished_at DATETIME2(3) NULL,
                    status VARCHAR(20) NOT NULL,
                    rows_read INT NOT NULL DEFAULT 0,
                    rows_loaded INT NOT NULL DEFAULT 0,
                    rows_rejected INT NOT NULL DEFAULT 0,
                    rows_inserted INT NOT NULL DEFAULT 0,
                    rows_updated INT NOT NULL DEFAULT 0,
                    rows_unchanged INT NOT NULL DEFAULT 0,
                    error_message NVARCHAR(MAX) NULL
                );
                """
            )
            connection.execute(
                """
                CREATE TABLE staging.raw_amazon_delivery
                (
                    staging_row_id BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                    Order_ID VARCHAR(32) NULL,
                    Agent_Age VARCHAR(16) NULL,
                    Agent_Rating VARCHAR(16) NULL,
                    Store_Latitude VARCHAR(32) NULL,
                    Store_Longitude VARCHAR(32) NULL,
                    Drop_Latitude VARCHAR(32) NULL,
                    Drop_Longitude VARCHAR(32) NULL,
                    Order_Date VARCHAR(16) NULL,
                    Order_Time VARCHAR(16) NULL,
                    Pickup_Time VARCHAR(16) NULL,
                    Weather VARCHAR(32) NULL,
                    Traffic VARCHAR(32) NULL,
                    Vehicle VARCHAR(32) NULL,
                    Area VARCHAR(64) NULL,
                    Delivery_Time VARCHAR(16) NULL,
                    Category VARCHAR(64) NULL,
                    source_file_name NVARCHAR(260) NOT NULL,
                    source_row_number BIGINT NOT NULL,
                    load_batch_id VARCHAR(64) NOT NULL,
                    loaded_at DATETIME2(3) NOT NULL,
                    row_hash CHAR(64) NULL,
                    updated_load_batch_id VARCHAR(64) NULL,
                    updated_at DATETIME2(3) NULL,
                    updated_source_file_name NVARCHAR(260) NULL,
                    updated_source_row_number BIGINT NULL,
                    FOREIGN KEY (load_batch_id) REFERENCES audit.load_batch(load_batch_id),
                    FOREIGN KEY (updated_load_batch_id) REFERENCES audit.load_batch(load_batch_id)
                );
                CREATE UNIQUE INDEX UX_test_order_id
                    ON staging.raw_amazon_delivery(Order_ID)
                    WHERE Order_ID IS NOT NULL;
                """
            )

    @classmethod
    def tearDownClass(cls):
        if cls.original_database:
            os.environ['MSSQL_DATABASE'] = cls.original_database
        else:
            os.environ.pop('MSSQL_DATABASE', None)
        if cls.database.startswith('AmazonDeliveryBI_MageTest_'):
            cls.master_connection.execute(
                f'ALTER DATABASE [{cls.database}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;'
            )
            cls.master_connection.execute(f'DROP DATABASE [{cls.database}];')
        cls.master_connection.close()

    @classmethod
    def _connection_string(cls, database):
        return (
            f"DRIVER={{{os.environ['MSSQL_DRIVER']}}};"
            f"SERVER={os.environ['MSSQL_SERVER']};DATABASE={database};"
            'Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;'
        )

    def _payload(self, rating='4.5'):
        row = [
            'ORDER_TEST_0001', '30', rating, '12.1', '77.1', '12.2', '77.2',
            '2022-04-06', '10:00:00', '10:10:00', 'Sunny', 'Low ',
            'scooter ', 'Metropolitian ', '120', 'Books',
        ]
        raw = {
            'batch_name': generate_batch_name('INCREMENTAL'),
            'batch_type': 'INCREMENTAL',
            'source_file_name': 'integration.csv',
            'source_file_checksum': 'b' * 64,
            'data': pd.DataFrame([row], columns=SOURCE_COLUMNS),
            'read_error': '',
        }
        return validate_and_prepare(raw)

    def test_insert_unchanged_update_and_lineage(self):
        inserted = export_amazon_delivery(self._payload())
        self.assertEqual(int(inserted.iloc[0]['rows_inserted']), 1)
        self.assertTrue(bool(verify_amazon_delivery_batch(inserted).iloc[0]['verified']))
        original_batch = str(inserted.iloc[0]['load_batch_id'])

        unchanged = export_amazon_delivery(self._payload())
        self.assertEqual(int(unchanged.iloc[0]['rows_unchanged']), 1)
        self.assertTrue(bool(verify_amazon_delivery_batch(unchanged).iloc[0]['verified']))

        updated = export_amazon_delivery(self._payload('4.9'))
        self.assertEqual(int(updated.iloc[0]['rows_updated']), 1)
        self.assertTrue(bool(verify_amazon_delivery_batch(updated).iloc[0]['verified']))

        with pyodbc.connect(self._connection_string(self.database)) as connection:
            row = connection.execute(
                """
                SELECT Agent_Rating, load_batch_id, updated_load_batch_id, row_hash
                FROM staging.raw_amazon_delivery
                WHERE Order_ID = 'ORDER_TEST_0001';
                """
            ).fetchone()
        self.assertEqual(row[0], '4.9')
        self.assertEqual(row[1], original_batch)
        self.assertEqual(row[2], str(updated.iloc[0]['load_batch_id']))
        self.assertRegex(row[3], r'^[0-9a-f]{64}$')


if __name__ == '__main__':
    unittest.main()

