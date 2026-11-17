"""Optional read-only integration audit against independent SQL aggregates.

Enable explicitly with RUN_AI_DDS_TESTS=1. No Gemini API key is used here.
The reference implements DAX COUNT's empty/zero-match BLANK convention.
"""
import os
import unittest

from ai.analytics import FilterContext, build_analysis
from ai.data import DatabaseConfig, _connection_string, load_warehouse


@unittest.skipUnless(os.environ.get("RUN_AI_DDS_TESTS") == "1", "Set RUN_AI_DDS_TESTS=1 to check the local DDS")
class LiveDdsParityTests(unittest.TestCase):
    def test_sql_aggregates_match_application_in_multiple_filter_contexts(self):
        import pyodbc
        config = DatabaseConfig(server=os.environ.get("MSSQL_SERVER", r"localhost\SQLEXPRESS"))
        frame, source = load_warehouse(config)
        cases = [
            ("all", FilterContext(), "1=1", []),
            ("grocery", FilterContext(categories=("Grocery",)), "g.category_name = ?", ["Grocery"]),
            ("small_area", FilterContext(areas=("Semi-Urban",)), "a.area_name = ?", ["Semi-Urban"]),
            ("jam", FilterContext(traffic=("Jam",)), "c.traffic_level = ?", ["Jam"]),
            ("vehicle_multiselect", FilterContext(vehicles=("van", "scooter")), "v.vehicle_type IN (?,?)", ["van", "scooter"]),
            ("date_range", FilterContext(start_date="2022-03-01", end_date="2022-03-10"), "d.full_date BETWEEN ? AND ?", ["2022-03-01", "2022-03-10"]),
            ("exact_days", FilterContext(dates=("2022-03-01", "2022-03-03")), "d.full_date IN (?,?)", ["2022-03-01", "2022-03-03"]),
            ("empty_calendar_day", FilterContext(dates=("2022-03-22",)), "d.full_date = ?", ["2022-03-22"]),
            ("combined", FilterContext(vehicles=("motorcycle",), categories=("Grocery",), traffic=("Low",)), "v.vehicle_type=? AND g.category_name=? AND c.traffic_level=?", ["motorcycle", "Grocery", "Low"]),
        ]
        connection = pyodbc.connect(_connection_string(config), autocommit=True, timeout=5)
        connection.timeout = 30
        try:
            for name, filters, predicate, params in cases:
                with self.subTest(context=name):
                    sql = """
WITH selected AS (
    SELECT f.*
    FROM dw.fact_delivery f
    JOIN dw.dim_date d ON d.date_key=f.date_key
    JOIN dw.dim_delivery_condition c ON c.delivery_condition_key=f.delivery_condition_key
    JOIN dw.dim_vehicle v ON v.vehicle_key=f.vehicle_key
    JOIN dw.dim_area a ON a.area_key=f.area_key
    JOIN dw.dim_category g ON g.category_key=f.category_key
    WHERE """ + predicate + """
), basic AS (
 SELECT COUNT_BIG(*) AS row_count, SUM(delivery_count) AS total_records,
 AVG(CAST(delivery_time_minutes AS float)) AS average_minutes,
 COUNT(delivery_time_minutes) AS valid_time_count,
 COUNT(CASE WHEN above_baseline_p90_flag=1 THEN delivery_time_minutes END) AS above_count,
 COUNT(DISTINCT CASE WHEN date_key<>0 THEN date_key END) AS days,
 AVG(CAST(pickup_delay_minutes AS float)) AS average_pickup_delay,
 AVG(CASE WHEN valid_distance_flag=1 THEN CAST(delivery_distance_km AS float) END) AS average_valid_distance,
 AVG(CASE WHEN valid_rating_flag=1 THEN CAST(agent_rating_valid AS float) END) AS average_valid_rating
 FROM selected
)
SELECT b.*, p.median_minutes, p.p90_minutes, p.p95_minutes
FROM basic b
OUTER APPLY (
 SELECT TOP (1)
 PERCENTILE_CONT(.5) WITHIN GROUP (ORDER BY delivery_time_minutes) OVER() AS median_minutes,
 PERCENTILE_CONT(.9) WITHIN GROUP (ORDER BY delivery_time_minutes) OVER() AS p90_minutes,
 PERCENTILE_CONT(.95) WITHIN GROUP (ORDER BY delivery_time_minutes) OVER() AS p95_minutes
 FROM selected WHERE delivery_time_minutes IS NOT NULL
) p
"""
                    cursor = connection.cursor()
                    try:
                        row = cursor.execute(sql, params).fetchone()
                        ref = dict(zip([d[0] for d in cursor.description], row))
                    finally:
                        cursor.close()
                    calculated = build_analysis(frame, filters=filters, source_meta=source)["kpis"]
                    expected = {key: ref[key] for key in ["total_records", "average_minutes", "median_minutes", "p90_minutes", "p95_minutes", "average_pickup_delay", "average_valid_distance", "average_valid_rating"]}
                    expected["above_baseline_count"] = ref["above_count"] or None
                    expected["share_above_baseline"] = (ref["above_count"] / ref["valid_time_count"]) if ref["above_count"] and ref["valid_time_count"] else None
                    expected["active_days"] = ref["days"] or None
                    expected["records_per_active_day"] = ref["total_records"] / ref["days"] if ref["days"] else None
                    for metric, value in expected.items():
                        with self.subTest(metric=metric):
                            if value is None:
                                self.assertIsNone(calculated[metric])
                            else:
                                self.assertAlmostEqual(float(calculated[metric]), float(value), places=7)
        finally:
            connection.close()
        _, after = load_warehouse(config)
        self.assertEqual(source["source_fingerprint"], after["source_fingerprint"], "DDS changed during the parity audit; rerun with ETL stopped")


if __name__ == "__main__":
    unittest.main()
