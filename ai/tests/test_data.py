import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from ai import data
from ai.data import DatabaseConfig, WarehouseError, fingerprint_frame, load_warehouse


class WarehouseTests(unittest.TestCase):
    def connection(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        columns = ["delivery_key", "order_id", "date_key", "full_date", "weather_name",
                   "traffic_level", "vehicle_type", "area_name", "category_name"]
        cursor.description = [(name,) for name in columns]
        cursor.fetchall.return_value = [("local-key", "local-order", 20220301, "2022-03-01",
                                        "Sunny", "Low", "van", "Urban", "Grocery")]
        return connection, cursor

    def test_success_is_one_fixed_select_in_serializable_transaction(self):
        connection, cursor = self.connection()
        with patch.object(data, "pyodbc") as driver:
            driver.connect.return_value = connection
            frame, meta = load_warehouse(DatabaseConfig())
        commands = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertEqual(len(commands), 2)
        self.assertIn("SERIALIZABLE", commands[0])
        self.assertIn("LOCK_TIMEOUT 5000", commands[0])
        self.assertEqual(commands[1], data.WAREHOUSE_SELECT)
        self.assertEqual(commands[1].count("LEFT JOIN"), 5)
        for forbidden in ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "CREATE ", "Store_Latitude", "Drop_Longitude"):
            self.assertNotIn(forbidden.lower(), commands[1].lower())
        self.assertFalse(driver.connect.call_args.kwargs["autocommit"])
        self.assertEqual(connection.timeout, 30)
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()
        cursor.close.assert_called_once()
        connection.close.assert_called_once()
        self.assertEqual(meta["global_min_date"], "2022-03-01")
        self.assertEqual(meta["global_max_date"], "2022-03-01")
        self.assertEqual(meta["source_fingerprint"], fingerprint_frame(frame))
        self.assertNotIn("rows", meta)
        self.assertNotIn("local-order", str(meta))

    def test_failed_read_rolls_back_closes_and_sanitizes_error(self):
        for stage in ("execute", "fetchall", "commit"):
            connection, cursor = self.connection()
            target = connection if stage == "commit" else cursor
            getattr(target, stage).side_effect = RuntimeError("secret-password and internal connection string")
            with patch.object(data, "pyodbc") as driver:
                driver.connect.return_value = connection
                with self.subTest(stage=stage), self.assertRaises(WarehouseError) as caught:
                    load_warehouse(DatabaseConfig())
            self.assertNotIn("secret-password", str(caught.exception))
            connection.rollback.assert_called_once()
            cursor.close.assert_called_once()
            connection.close.assert_called_once()

    def test_unordered_sql_read_preserves_the_same_rows_and_fingerprint(self):
        connection, cursor = self.connection()
        first_row = cursor.fetchall.return_value[0]
        second_row = ("another-key", "another-order", *first_row[2:])
        fingerprints = []
        orders = []
        for records in ([first_row, second_row], [second_row, first_row]):
            connection, cursor = self.connection()
            cursor.fetchall.return_value = records
            with patch.object(data, "pyodbc") as driver:
                driver.connect.return_value = connection
                frame, meta = load_warehouse(DatabaseConfig())
            fingerprints.append(meta["source_fingerprint"])
            orders.append(frame["delivery_key"].tolist())
            query = cursor.execute.call_args_list[1].args[0].upper()
            self.assertNotIn("ORDER BY", query)
            self.assertNotIn("WHERE", query)
            self.assertEqual(query.count("LEFT JOIN"), 5)
            self.assertEqual(set(frame["order_id"]), {"local-order", "another-order"})
        self.assertNotEqual(orders[0], orders[1])
        self.assertEqual(fingerprints[0], fingerprints[1])

    def test_missing_driver_and_invalid_config_fail_before_connection(self):
        with patch.object(data, "pyodbc", None), self.assertRaises(WarehouseError):
            load_warehouse(DatabaseConfig())
        for config in (DatabaseConfig(server="localhost;UID=x"), DatabaseConfig(database=""),
                       DatabaseConfig(driver="bad\nname"), DatabaseConfig(trust_certificate="yes")):
            with patch.object(data, "pyodbc") as driver:
                with self.subTest(config=config), self.assertRaises(WarehouseError):
                    load_warehouse(config)
                driver.connect.assert_not_called()

    def test_missing_dimension_is_not_silently_dropped(self):
        connection, cursor = self.connection()
        cursor.fetchall.return_value = [("key", "order", 20220301, "2022-03-01", None,
                                        "Low", "van", "Urban", "Grocery")]
        with patch.object(data, "pyodbc") as driver:
            driver.connect.return_value = connection
            with self.assertRaises(WarehouseError):
                load_warehouse(DatabaseConfig())
        connection.close.assert_called_once()

    def test_fingerprint_is_row_and_column_order_independent(self):
        frame = pd.DataFrame({"delivery_key": ["b", "a"], "delivery_count": [1, 1]})
        self.assertEqual(fingerprint_frame(frame), fingerprint_frame(frame.iloc[::-1, ::-1]))
        changed = frame.copy()
        changed.loc[0, "delivery_count"] = 2
        self.assertNotEqual(fingerprint_frame(frame), fingerprint_frame(changed))


if __name__ == "__main__":
    unittest.main()
