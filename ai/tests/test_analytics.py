import json
import unittest

import pandas as pd

from ai.analytics import AnalyticsError, FilterContext, build_analysis


def frame_for(times, dates=None, **overrides):
    dates = dates or ["2022-03-01"] * len(times)
    rows = []
    for i, (minutes, day) in enumerate(zip(times, dates)):
        row = {
            "delivery_key": f"key-{i}", "order_id": f"private-order-{i}",
            "date_key": int(day.replace("-", "")), "full_date": pd.Timestamp(day),
            "delivery_count": 1, "delivery_time_minutes": minutes,
            "above_baseline_p90_flag": minutes > 195 if minutes is not None else None,
            "pickup_delay_minutes": 10, "delivery_distance_km": 5,
            "valid_distance_flag": True, "agent_rating_valid": 4.5,
            "valid_rating_flag": True, "missing_operational_context_flag": False,
            "distance_band": "[5,10) km", "vehicle_type": "motorcycle",
            "category_name": "Grocery", "area_name": "Urban", "traffic_level": "Low",
            "weather_name": "Sunny", "time_period": "Morning",
        }
        row.update({key: values[i] for key, values in overrides.items()})
        rows.append(row)
    if not rows:
        return frame_for([10]).iloc[:0].copy()
    return pd.DataFrame(rows)


class AnalyticsTests(unittest.TestCase):
    def test_grain_rejects_duplicate_orders_keys_and_nonunit_counts(self):
        for column, values in (("order_id", ["x", "X"]), ("delivery_key", ["x", "x"]),
                               ("delivery_count", [1, 2])):
            with self.subTest(column=column), self.assertRaises(AnalyticsError):
                build_analysis(frame_for([10, 20], **{column: values}))

    def test_empty_context_preserves_dax_blank_and_json_null(self):
        result = build_analysis(frame_for([10, 200]), FilterContext(vehicles=("absent",)))
        self.assertEqual(result["scope"]["selected_records"], 0)
        self.assertTrue(all(value is None for value in result["kpis"].values()))
        self.assertEqual(result["tables"]["daily"][0]["total_records"], 0)
        json.dumps(result, allow_nan=False)
        empty_source = build_analysis(frame_for([]))
        self.assertEqual(empty_source["tables"]["daily"], [])

    def test_zero_above_is_blank_not_zero(self):
        kpis = build_analysis(frame_for([10, 195, 40]))["kpis"]
        self.assertIsNone(kpis["above_baseline_count"])
        self.assertIsNone(kpis["share_above_baseline"])
        self.assertEqual(kpis["total_records"], 3)

    def test_percentiles_use_linear_inclusive_interpolation(self):
        kpis = build_analysis(frame_for([0, 10]))["kpis"]
        self.assertEqual(kpis["median_minutes"], 5)
        self.assertEqual(kpis["p90_minutes"], 9)
        self.assertEqual(kpis["p95_minutes"], 9.5)

    def test_filter_multiselect_intersection_and_exact_dates(self):
        frame = frame_for([10, 20, 30, 200], ["2022-03-01", "2022-03-02", "2022-03-03", "2022-03-04"],
                          vehicle_type=["van", "scooter", "van", "motorcycle"],
                          category_name=["A", "B", "B", "A"])
        filters = FilterContext(start_date="2022-03-02", end_date="2022-03-04",
                                dates=("2022-03-01", "2022-03-03", "2022-03-04"),
                                vehicles=("van", "scooter"), categories=("B",))
        result = build_analysis(frame, filters)
        self.assertEqual(result["kpis"]["total_records"], 1)
        self.assertEqual(result["kpis"]["average_minutes"], 30)
        self.assertEqual([r["date"] for r in result["tables"]["daily"]], ["2022-03-03", "2022-03-04"])

    def test_calendar_gap_zero_inside_source_extent_blank_outside(self):
        result = build_analysis(frame_for([10, 20], ["2022-03-02", "2022-03-04"]),
                                FilterContext(start_date="2022-03-01", end_date="2022-03-05"))
        daily = result["tables"]["daily"]
        self.assertEqual([r["total_records"] for r in daily], [None, 1, 0, 1, None])
        self.assertIsNone(daily[2]["average_minutes"])
        self.assertEqual(result["kpis"]["active_days"], 2)
        self.assertEqual(result["kpis"]["records_per_active_day"], 1)

    def test_unknown_date_not_active_but_retained_in_grand_total(self):
        frame = frame_for([10, 20])
        frame.loc[1, "date_key"] = 0
        frame.loc[1, "full_date"] = pd.NaT
        result = build_analysis(frame)
        self.assertEqual(result["kpis"]["total_records"], 2)
        self.assertEqual(result["kpis"]["active_days"], 1)
        self.assertEqual(result["kpis"]["records_per_active_day"], 2)

    def test_distance_diagnostics_use_only_valid_rows_and_correct_denominator(self):
        frame = frame_for([10, 200, 270], delivery_distance_km=[5, 80, None],
                          valid_distance_flag=[True, False, False],
                          distance_band=["[5,10) km", ">50 km", "Not calculable"],
                          vehicle_type=["van", "scooter", "scooter"])
        result = build_analysis(frame)
        self.assertEqual(result["kpis"]["average_valid_distance"], 5)
        distance_fact = next(f for f in result["facts"] if f["source"] == "kpi/average_valid_distance")
        self.assertEqual(distance_fact["n"], 1)
        self.assertIn("[5,10) km", result["allowed_terms"])
        self.assertEqual(result["kpis"]["valid_distance_count"], 1)
        self.assertAlmostEqual(result["kpis"]["valid_distance_coverage"], 1/3)
        self.assertEqual(len(result["tables"]["distance_band"]), 1)
        self.assertEqual(result["tables"]["distance_band"][0]["average_minutes"], 10)
        filtered = build_analysis(frame, FilterContext(vehicles=("scooter",)))
        self.assertIsNone(filtered["kpis"]["valid_distance_count"])
        self.assertIsNone(filtered["kpis"]["valid_distance_coverage"])
        self.assertEqual(filtered["kpis"]["report_valid_distance_coverage"], 0)
        report_fact = next(f for f in filtered["facts"] if f["source"] == "kpi/report_valid_distance_coverage")
        self.assertEqual(report_fact["display"], "0,00%")

    def test_aggregation_uses_rows_instead_of_average_of_group_averages(self):
        result = build_analysis(frame_for([10, 10, 10, 210], traffic_level=["Low", "Low", "Low", "Jam"]))
        self.assertEqual(result["kpis"]["average_minutes"], 60)
        self.assertEqual(result["kpis"]["total_records"], 4)
        self.assertEqual(result["kpis"]["above_baseline_count"], 1)
        self.assertEqual(result["kpis"]["share_above_baseline"], .25)

    def test_baseline_flag_parity_is_validated_and_195_is_not_above(self):
        good = frame_for([195, 196])
        self.assertEqual(build_analysis(good)["kpis"]["above_baseline_count"], 1)
        good.loc[0, "above_baseline_p90_flag"] = True
        with self.assertRaises(AnalyticsError):
            build_analysis(good)

    def test_invalid_distance_numeric_and_filter_inputs_fail(self):
        for kwargs in ({"delivery_distance_km": [80], "valid_distance_flag": [True]},
                       {"delivery_time_minutes": [float("inf")]}, {"delivery_count": [None]}):
            with self.subTest(kwargs=kwargs), self.assertRaises(AnalyticsError):
                build_analysis(frame_for([10], **kwargs))
        for kwargs in ({"start_date": "03/01/2022"}, {"start_date": "2022-03-02", "end_date": "2022-03-01"},
                       {"vehicles": "van"}, {"dates": (None,)}):
            with self.subTest(kwargs=kwargs), self.assertRaises(AnalyticsError):
                FilterContext(**kwargs)

    def test_ranking_excludes_unknown_and_small_groups_but_tables_keep_them(self):
        labels = ["Low"] * 200 + ["Jam"] * 200 + ["Tiny"] + ["Unknown"] * 200
        result = build_analysis(frame_for([10] * 200 + [210] * 200 + [270] + [270] * 200, traffic_level=labels))
        comparison = next(f for f in result["facts"] if f["source"] == "comparison/traffic")
        self.assertEqual(comparison["context"]["high"], "Jam")
        self.assertEqual(comparison["value"], 200)
        self.assertEqual(len(result["tables"]["traffic"]), 4)
        tiny = next(r for r in result["tables"]["traffic"] if r["label"] == "Tiny")
        self.assertTrue(tiny["small_n"])

    def test_daily_changes_compare_adjacent_calendar_dates_only(self):
        frame = frame_for([10] * 200 + [210] * 200, ["2022-03-01"] * 200 + ["2022-03-03"] * 200)
        result = build_analysis(frame, FilterContext(dates=("2022-03-01", "2022-03-03")))
        self.assertFalse(any(f["source"] == "comparison/daily_average" for f in result["facts"]))
        frame = frame_for([10] * 200 + [20] * 200 + [5] * 200,
                          ["2022-03-01"] * 200 + ["2022-03-02"] * 200 + ["2022-03-03"] * 200)
        changes = [f for f in build_analysis(frame)["facts"] if f["source"] == "comparison/daily_average"]
        self.assertEqual([f["value"] for f in changes], [10, 15])
        self.assertEqual([f["context"]["direction"] for f in changes], ["tăng", "giảm"])

    def test_snapshot_is_stable_and_contains_no_delivery_rows_or_host_in_facts(self):
        frame = frame_for([10, 210])
        before = frame.copy(deep=True)
        meta = {"fetched_at": "2026-11-17T00:00:00+00:00", "server": "private-host", "rows": [{"secret": "x"}]}
        first = build_analysis(frame, source_meta=meta)
        second = build_analysis(frame.iloc[::-1], source_meta=meta)
        self.assertEqual(first["snapshot_id"], second["snapshot_id"])
        self.assertEqual(first["generated_at"], meta["fetched_at"])
        pd.testing.assert_frame_equal(frame, before)
        serialized = json.dumps(first, ensure_ascii=False, allow_nan=False)
        self.assertNotIn("private-order-", serialized)
        self.assertNotIn("delivery_key", serialized)
        self.assertNotIn("rows", first["source"])
        self.assertNotIn("private-host", json.dumps(first["facts"]))
        self.assertLessEqual(len(first["facts"]), 160)
        self.assertEqual(len({f["id"] for f in first["facts"]}), len(first["facts"]))
        share = next(f for f in first["facts"] if f["source"] == "kpi/share_above_baseline")
        self.assertEqual(share["value"], .5)
        self.assertEqual(share["display"], "50,00%")


if __name__ == "__main__":
    unittest.main()
