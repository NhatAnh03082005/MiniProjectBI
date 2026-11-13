import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mage_project.amazon_delivery_contract import (
    HASH_COLUMNS,
    SOURCE_COLUMNS,
    compute_raw_row_hash,
    generate_batch_name,
    validate_and_prepare,
)
from mage_project.amazon_delivery_repository import assert_export_output, build_output


def make_payload(rows):
    return {
        'batch_name': 'amazon_delivery_incremental_test',
        'batch_type': 'INCREMENTAL',
        'source_file_name': 'test.csv',
        'source_file_checksum': 'a' * 64,
        'data': pd.DataFrame(rows, columns=SOURCE_COLUMNS),
        'read_error': '',
    }


def valid_row(order_id='ORDER0000001', order_date='2022-04-06'):
    return [
        order_id, '30', '4.5', '12.1', '77.1', '12.2', '77.2',
        order_date, '10:00:00', '10:10:00', 'Sunny', 'Low ',
        'scooter ', 'Metropolitian ', '120', 'Books',
    ]


class ContractTests(unittest.TestCase):
    def test_dynamic_batch_name_is_unique_and_fits_sql_column(self):
        now = datetime(2026, 11, 12, 7, 30, tzinfo=timezone.utc)
        first = generate_batch_name('INCREMENTAL', now)
        second = generate_batch_name('INCREMENTAL', now)
        self.assertRegex(
            first,
            r'^amazon_delivery_inc_20261112T073000Z_[0-9a-f]{8}$',
        )
        self.assertNotEqual(first, second)
        self.assertLessEqual(len(first), 50)

    def test_raw_hash_is_stable_and_whitespace_sensitive(self):
        values = valid_row()[1:]
        self.assertEqual(compute_raw_row_hash(values), compute_raw_row_hash(values))
        changed = values.copy()
        changed[10] = 'Low'
        self.assertNotEqual(compute_raw_row_hash(values), compute_raw_row_hash(changed))

    def test_validation_computes_dynamic_range_and_hash(self):
        result = validate_and_prepare(make_payload([
            valid_row('ORDER0000001', '2022-04-01'),
            valid_row('ORDER0000002', '2022-04-06'),
        ]))
        self.assertEqual(result['validation_error'], '')
        self.assertEqual(result['rows_read'], 2)
        self.assertEqual(result['rows_rejected'], 0)
        self.assertEqual(result['date_from'], '2022-04-01')
        self.assertEqual(result['date_to'], '2022-04-06')
        self.assertEqual(len(result['data']), 2)
        self.assertTrue(result['data']['_row_hash'].str.fullmatch(r'[0-9a-f]{64}').all())
        expected = compute_raw_row_hash(
            [result['data'].iloc[0][column] for column in HASH_COLUMNS]
        )
        self.assertEqual(result['data'].iloc[0]['_row_hash'], expected)

    def test_invalid_key_and_date_are_rejected_not_silently_loaded(self):
        result = validate_and_prepare(make_payload([
            valid_row('', '2022-04-01'),
            valid_row('ORDER0000002', 'not-a-date'),
            valid_row('ORDER0000003', '2022-04-06'),
        ]))
        self.assertEqual(result['validation_error'], '')
        self.assertEqual(result['rows_read'], 3)
        self.assertEqual(result['rows_rejected'], 2)
        self.assertEqual(len(result['data']), 1)

    def test_all_rejected_batch_has_cache_safe_empty_date_range(self):
        result = validate_and_prepare(make_payload([
            valid_row('ORDER0000001', '2022-02-30'),
            valid_row('', 'not-a-date'),
        ]))
        self.assertEqual(result['validation_error'], '')
        self.assertEqual(result['rows_read'], 2)
        self.assertEqual(result['rows_rejected'], 2)
        self.assertEqual(len(result['data']), 0)
        self.assertEqual(result['date_from'], '')
        self.assertEqual(result['date_to'], '')
        self.assertTrue(all(value is not None for value in result.values()))

    def test_duplicate_order_id_in_batch_is_fatal(self):
        result = validate_and_prepare(make_payload([
            valid_row(' Order0000001 '),
            valid_row('order0000001'),
        ]))
        self.assertIn('Order_ID lặp', result['validation_error'])

    def test_export_summary_reconciles(self):
        payload = validate_and_prepare(make_payload([valid_row()]))
        output = build_output(payload, 'batch-id', 'SUCCEEDED', 1, 0, 0)
        assert_export_output(output)


if __name__ == '__main__':
    unittest.main()

