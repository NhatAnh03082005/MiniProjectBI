"""UI lifecycle tests; SQL and Gemini are mocked, analytics/grounding are real."""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.proto.TextInput_pb2 import TextInput as TextInputProto
from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"
FAKE_KEY = "unit-test-key-not-a-real-credential"


def fixture_frame() -> pd.DataFrame:
    rows = []
    vehicles = ["motorcycle", "motorcycle", "scooter", "van"]
    categories = ["Electronics", "Electronics", "Grocery", "Grocery"]
    minutes = [90, 210, 110, 130]
    for i in range(4):
        day = date(2022, 2, 11 + i)
        rows.append({
            "delivery_key": f"delivery-{i}", "order_id": f"fixture-{i}",
            "date_key": int(day.strftime("%Y%m%d")), "delivery_count": 1,
            "full_date": pd.Timestamp(day), "vehicle_type": vehicles[i],
            "category_name": categories[i], "area_name": "Urban" if i != 1 else "Metropolitan",
            "traffic_level": ["Low", "Jam", "High", "Medium"][i],
            "weather_name": ["Sunny", "Cloudy", "Fog", "Sunny"][i],
            "time_period": ["Morning", "Evening", "Afternoon", "Night"][i],
            "delivery_time_minutes": minutes[i], "above_baseline_p90_flag": minutes[i] > 195,
            "pickup_delay_minutes": 5 + i, "delivery_distance_km": 5 + i * 5,
            "valid_distance_flag": True, "agent_rating_valid": 4.5,
            "valid_rating_flag": True, "missing_operational_context_flag": False,
            "distance_band": "0–10 km" if i < 2 else "10–20 km",
        })
    return pd.DataFrame(rows)


def state(app: AppTest, name: str, default=None):
    try:
        return app.session_state[name]
    except KeyError:
        return default


class AppLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.frame = fixture_frame()
        self.source = {"fetched_at": "2026-11-17T01:00:00+00:00", "server": "test-server",
                       "database": "fixture", "snapshot_consistency": "unit-test fixture"}
        self.load = patch("ai.data.load_warehouse", return_value=(self.frame, self.source)).start()
        self.generate = patch("ai.gemini.generate", side_effect=self.response).start()
        self.models = patch("ai.gemini.list_models", return_value=["fixture-model-a", "fixture-model-b"]).start()
        self.addCleanup(patch.stopall)
        self.app = AppTest.from_file(str(APP), default_timeout=25).run()
        self.assert_clean()

    def response(self, **kwargs):
        question = kwargs.get("question", "")
        payload = {
            "summary": [{"text": "Tập đang chọn có {{F001}}.", "evidence_ids": ["F001"]}],
            "explanations": [{"text": "Thời lượng giao trung bình của tập đang chọn là {{F002}}.",
                              "evidence_ids": ["F002"]}],
            "answer": ([{"text": "Trong phạm vi đã chọn, số bản ghi là {{F001}}.", "evidence_ids": ["F001"]}]
                       if question else []),
            "answer_status": "answered" if question else "not_requested",
        }
        return SimpleNamespace(payload=payload, model=kwargs["model"], model_version="fixture-model-version",
                               response_id="fixture-response", usage={"input_tokens": 10, "output_tokens": 20})

    def assert_clean(self):
        self.assertEqual(len(self.app.exception), 0, [e.value for e in self.app.exception])

    def load_data(self):
        self.app.button(key="load_data").click().run()
        self.assert_clean()

    def enter_key(self):
        self.app.text_input(key="gemini_api_key").set_value(FAKE_KEY).run()
        self.assert_clean()

    def generate_summary(self):
        self.app.button(key="generate_summary").click().run()
        self.assert_clean()
        self.assertIsNotNone(state(self.app, "_ai_result"))

    def test_no_network_on_start_or_rerun_and_key_required(self):
        self.load.assert_not_called()
        self.generate.assert_not_called()
        self.models.assert_not_called()
        self.assertTrue(self.app.button(key="generate_summary").disabled)
        self.load_data()
        self.assertTrue(self.app.button(key="generate_summary").disabled)
        self.app.run()
        self.assertEqual(self.load.call_count, 1)
        self.generate.assert_not_called()
        self.models.assert_not_called()

    def test_api_key_is_blank_password_input_and_isolated_between_sessions(self):
        first_key = self.app.text_input(key="gemini_api_key")
        self.assertEqual(first_key.proto.type, TextInputProto.PASSWORD)
        self.assertEqual(first_key.value, "")
        self.assertEqual(state(self.app, "gemini_api_key"), "")
        self.assertTrue(self.app.button(key="generate_summary").disabled)
        self.load_data()
        self.enter_key()
        self.assertFalse(self.app.button(key="generate_summary").disabled)

        second = AppTest.from_file(str(APP), default_timeout=25).run()
        self.assertEqual(len(second.exception), 0, [e.value for e in second.exception])
        second_key = second.text_input(key="gemini_api_key")
        self.assertEqual(second_key.proto.type, TextInputProto.PASSWORD)
        self.assertEqual(second_key.value, "")
        self.assertEqual(state(second, "gemini_api_key"), "")
        self.assertTrue(second.button(key="generate_summary").disabled)
        second.button(key="load_data").click().run()
        self.assertEqual(len(second.exception), 0, [e.value for e in second.exception])
        self.assertEqual(second.text_input(key="gemini_api_key").value, "")
        self.assertTrue(second.button(key="generate_summary").disabled)
        self.assertTrue(second.button(key="list_models").disabled)

        self.app.run()
        self.assert_clean()
        self.assertEqual(self.app.text_input(key="gemini_api_key").value, FAKE_KEY)
        self.assertFalse(self.app.button(key="generate_summary").disabled)
        self.generate.assert_not_called()
        self.models.assert_not_called()

    def test_one_request_per_click_and_read_only_ui_reruns_retain_result(self):
        self.load_data()
        self.enter_key()
        self.generate.assert_not_called()
        self.generate_summary()
        self.assertEqual(self.generate.call_count, 1)
        saved = state(self.app, "_ai_result")
        self.assertEqual(saved["snapshot_id"], state(self.app, "_bundle")["snapshot_id"])
        self.app.selectbox(key="evidence_group").set_value("Thời tiết").run()
        self.app.run()
        self.assert_clean()
        self.assertEqual(self.generate.call_count, 1)
        self.assertEqual(state(self.app, "_ai_result")["snapshot_id"], saved["snapshot_id"])
        self.assertNotIn(FAKE_KEY, json.dumps(saved))
        self.assertNotIn(FAKE_KEY, json.dumps(state(self.app, "_bundle")))

    def test_filters_model_and_question_each_invalidate_without_auto_request(self):
        self.load_data()
        self.enter_key()
        self.generate_summary()
        self.app.multiselect(key="filter_vehicles").set_value(["motorcycle"]).run()
        self.assertIsNone(state(self.app, "_ai_result"))
        self.assertEqual(self.generate.call_count, 1)
        self.generate_summary()
        self.app.text_input(key="gemini_model").set_value("fixture-new-model").run()
        self.assertIsNone(state(self.app, "_ai_result"))
        self.assertEqual(self.generate.call_count, 2)
        self.generate_summary()
        self.app.text_area(key="ai_question").set_value("Có bao nhiêu bản ghi?").run()
        self.assertIsNone(state(self.app, "_ai_result"))
        self.assertEqual(self.generate.call_count, 3)
        self.app.button(key="generate_answer").click().run()
        self.assert_clean()
        saved = state(self.app, "_ai_result")
        self.assertEqual(self.generate.call_count, 4)
        self.assertEqual(saved["validated"]["answer_status"], "answered")

    def test_exact_days_override_range_and_invalidate_snapshot(self):
        self.load_data()
        self.enter_key()
        self.generate_summary()
        old = state(self.app, "_bundle")["snapshot_id"]
        self.app.multiselect(key="filter_dates").set_value(["2022-02-11", "2022-02-14"]).run()
        self.assert_clean()
        bundle = state(self.app, "_bundle")
        self.assertIsNone(state(self.app, "_ai_result"))
        self.assertNotEqual(bundle["snapshot_id"], old)
        self.assertEqual(bundle["filters"]["dates"], ("2022-02-11", "2022-02-14"))
        self.assertIsNone(bundle["filters"]["start_date"])
        self.assertEqual(bundle["kpis"]["total_records"], 2)
        self.assertEqual(self.generate.call_count, 1)

    def test_reload_and_connection_change_cannot_show_previous_result(self):
        self.load_data()
        self.enter_key()
        self.generate_summary()
        self.load_data()
        self.assertEqual(self.load.call_count, 2)
        self.assertEqual(self.generate.call_count, 1)
        self.assertIsNone(state(self.app, "_ai_result"))
        self.generate_summary()
        self.app.text_input(key="database_server").set_value("different-server").run()
        self.assert_clean()
        self.assertIsNone(state(self.app, "_ai_result"))
        self.assertTrue(self.app.button(key="generate_summary").disabled)
        self.assertEqual(self.load.call_count, 2)
        self.assertEqual(self.generate.call_count, 2)

    def test_empty_filter_combination_never_calls_gemini(self):
        self.load_data()
        self.enter_key()
        self.app.multiselect(key="filter_vehicles").set_value(["motorcycle"]).run()
        self.app.multiselect(key="filter_categories").set_value(["Grocery"]).run()
        self.assert_clean()
        self.assertFalse(state(self.app, "_bundle")["kpis"]["total_records"])
        self.assertTrue(self.app.button(key="generate_summary").disabled)
        self.generate.assert_not_called()

    def test_models_only_load_explicitly_and_clear_removes_key_models_result(self):
        self.load_data()
        self.enter_key()
        self.models.assert_not_called()
        self.app.button(key="list_models").click().run()
        self.assert_clean()
        self.assertEqual(self.models.call_count, 1)
        self.app.selectbox(key="model_choice").set_value("fixture-model-b").run()
        self.assertEqual(self.app.text_input(key="gemini_model").value, "fixture-model-b")
        self.generate_summary()
        self.app.button(key="clear_key").click().run()
        self.assert_clean()
        self.assertEqual(self.app.text_input(key="gemini_api_key").value, "")
        self.assertFalse(state(self.app, "_model_choices"))
        self.assertIsNone(state(self.app, "_ai_result"))
        self.assertTrue(self.app.button(key="generate_summary").disabled)
        self.assertEqual(self.generate.call_count, 1)

    def test_failures_do_not_render_raw_exception_or_a_fallback_result(self):
        self.load_data()
        self.enter_key()
        self.generate.side_effect = RuntimeError("upstream raw error " + FAKE_KEY)
        self.app.button(key="generate_summary").click().run()
        self.assert_clean()
        self.assertIsNone(state(self.app, "_ai_result"))
        self.assertTrue(len(self.app.error))
        self.assertFalse(any(FAKE_KEY in error.value or "upstream raw" in error.value for error in self.app.error))
        self.load.side_effect = RuntimeError("ODBC raw connection " + FAKE_KEY)
        self.app.button(key="load_data").click().run()
        self.assert_clean()
        self.assertIsNone(state(self.app, "_warehouse_frame"))
        self.assertFalse(any(FAKE_KEY in error.value or "ODBC raw" in error.value for error in self.app.error))

    def test_ungrounded_model_output_is_rejected_before_render(self):
        self.load_data()
        self.enter_key()
        response = self.response(model="fixture-model")
        response.payload["summary"][0]["text"] = "Có 999999 bản ghi ngoài chứng cứ."
        self.generate.side_effect = None
        self.generate.return_value = response
        self.app.button(key="generate_summary").click().run()
        self.assert_clean()
        self.assertIsNone(state(self.app, "_ai_result"))
        self.assertTrue(len(self.app.error))
        self.assertFalse(any("999999" in text.value for text in self.app.text))


if __name__ == "__main__":
    unittest.main()
