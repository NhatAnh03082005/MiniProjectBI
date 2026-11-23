"""UI lifecycle tests; SQL and Gemini are mocked, analytics/grounding are real."""
from __future__ import annotations

from datetime import date
from itertools import combinations
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.proto.TextInput_pb2 import TextInput as TextInputProto
from streamlit.testing.v1 import AppTest

from ai import grounding


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
        # UI tests never touch the current Windows user's actual credentials.
        self.credential_load = patch("ai.credentials.load_key", return_value=None).start()
        self.credential_save = patch("ai.credentials.save_key").start()
        self.credential_delete = patch("ai.credentials.delete_key").start()
        self.credential_supported = patch("ai.credentials.is_supported", return_value=True).start()
        self.addCleanup(patch.stopall)
        self.app = AppTest.from_file(str(APP), default_timeout=25).run()
        self.assert_clean()

    def response(self, **kwargs):
        bundle = kwargs["bundle"]
        question = kwargs.get("question", "")
        catalog = grounding.build_claim_catalog(bundle)
        summary = [cid for cid, claim in catalog.items() if "summary" in claim["sections"]]
        explanations = [cid for cid, claim in catalog.items() if "explanations" in claim["sections"]]
        descriptive = [cid for cid in explanations
                       if catalog[cid]["kind"] in {"comparison", "daily"}]
        scope_notes = [cid for cid in explanations if catalog[cid]["kind"] == "scope_note"]
        constraints = grounding.question_constraints(bundle, question)
        status = constraints["required_status"]
        if status is None:
            status = "answered" if constraints["allowed_answer_ids"] else "insufficient_data"
        payload = {
            "snapshot_id": bundle["snapshot_id"],
            "summary": summary[:1],
            "explanations": (descriptive or scope_notes or explanations)[:1],
            "answer": [],
            "answer_status": status,
        }
        if status == "answered":
            allowed = list(constraints["allowed_answer_ids"])
            for size in range(1, min(3, len(allowed)) + 1):
                for selected in combinations(allowed, size):
                    candidate = payload | {"answer": list(selected)}
                    try:
                        grounding.validate_response(candidate, bundle, question)
                    except grounding.GroundingError:
                        continue
                    payload = candidate
                    break
                if payload["answer"]:
                    break
            if not payload["answer"]:
                raise AssertionError("Fixture response cannot cover the question constraints")
        return SimpleNamespace(payload=payload, model=kwargs["model"], model_version="fixture-model-version",
                               response_id="fixture-response", usage={"input_tokens": 10, "output_tokens": 20}, attempts=1)

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

    def test_question_text_makes_the_answer_action_primary_and_only_that_action_sends_it(self):
        self.assertEqual(self.app.button(key="generate_summary").proto.type, "primary")
        self.assertEqual(self.app.button(key="generate_answer").proto.type, "secondary")
        self.load_data()
        self.enter_key()
        question = "  P90 là gì và giải thích rõ thông số này giúp tôi  "
        self.app.text_area(key="ai_question").set_value(question).run()
        self.assert_clean()
        self.assertEqual(self.app.button(key="generate_summary").proto.type, "secondary")
        self.assertEqual(self.app.button(key="generate_answer").proto.type, "primary")
        self.assertFalse(self.app.button(key="generate_answer").disabled)
        self.assertTrue(any("Hãy bấm **Giải thích câu hỏi**" in caption.value
                            for caption in self.app.caption))

        self.app.button(key="generate_summary").click().run()
        self.assert_clean()
        self.assertEqual(self.generate.call_args.kwargs["question"], "")
        self.app.button(key="generate_answer").click().run()
        self.assert_clean()
        self.assertEqual(self.generate.call_args.kwargs["question"], question.strip())

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

    def test_saved_key_loads_masked_once_and_session_clear_does_not_reload(self):
        self.credential_load.return_value = FAKE_KEY
        saved = AppTest.from_file(str(APP), default_timeout=25).run()
        self.assertEqual(len(saved.exception), 0)
        self.assertEqual(saved.text_input(key="gemini_api_key").proto.type, TextInputProto.PASSWORD)
        self.assertEqual(saved.text_input(key="gemini_api_key").value, FAKE_KEY)
        reads = self.credential_load.call_count
        saved.button(key="clear_key").click().run()
        saved.run()
        self.assertEqual(saved.text_input(key="gemini_api_key").value, "")
        self.assertEqual(self.credential_load.call_count, reads)
        self.assertTrue(saved.button(key="save_key").disabled)
        self.credential_save.assert_not_called()
        self.credential_delete.assert_not_called()

    def test_save_is_explicit_and_delete_clears_saved_key_and_current_session(self):
        store = {"key": None}
        self.credential_load.side_effect = lambda: store["key"]
        self.credential_save.side_effect = lambda value: store.update(key=value)
        self.credential_delete.side_effect = lambda: store.update(key=None)
        self.enter_key()
        self.credential_save.assert_not_called()
        self.app.button(key="save_key").click().run()
        self.assert_clean()
        self.credential_save.assert_called_once_with(FAKE_KEY)
        self.assertEqual(store["key"], FAKE_KEY)

        second = AppTest.from_file(str(APP), default_timeout=25).run()
        self.assertEqual(second.text_input(key="gemini_api_key").value, FAKE_KEY)
        second.button(key="delete_saved_key").click().run()
        self.assertEqual(len(second.exception), 0)
        self.assertIsNone(store["key"])
        self.assertEqual(second.text_input(key="gemini_api_key").value, "")
        self.assertTrue(second.button(key="generate_summary").disabled)
        third = AppTest.from_file(str(APP), default_timeout=25).run()
        self.assertEqual(third.text_input(key="gemini_api_key").value, "")
        self.generate.assert_not_called()
        self.models.assert_not_called()

    def test_credential_failures_are_safe_and_keep_the_entered_session_key(self):
        self.credential_load.side_effect = RuntimeError("private store error " + FAKE_KEY)
        fresh = AppTest.from_file(str(APP), default_timeout=25).run()
        self.assertEqual(len(fresh.exception), 0)
        self.assertEqual(fresh.text_input(key="gemini_api_key").value, "")
        self.assertTrue(len(fresh.warning))
        self.assertFalse(any(FAKE_KEY in warning.value for warning in fresh.warning))
        self.enter_key()
        self.credential_save.side_effect = RuntimeError("private store error " + FAKE_KEY)
        self.app.button(key="save_key").click().run()
        self.assert_clean()
        self.assertEqual(self.app.text_input(key="gemini_api_key").value, FAKE_KEY)
        self.assertTrue(len(self.app.error))
        self.assertFalse(any(FAKE_KEY in error.value for error in self.app.error))
        self.credential_delete.side_effect = RuntimeError("private store error " + FAKE_KEY)
        self.app.button(key="delete_saved_key").click().run()
        self.assert_clean()
        self.assertEqual(self.app.text_input(key="gemini_api_key").value, FAKE_KEY)
        self.assertFalse(any(FAKE_KEY in error.value for error in self.app.error))

    def test_group_bar_chart_axes_match_their_actual_fields(self):
        self.load_data()
        specs = [json.loads(chart.proto.spec) for chart in self.app.get("vega_lite_chart")]
        bar = next(spec for spec in specs
                   if spec.get("mark", {}).get("type") == "bar"
                   and spec.get("encoding", {}).get("x", {}).get("field") == "average_minutes")
        self.assertEqual(bar["encoding"]["x"]["field"], "average_minutes")
        self.assertEqual(bar["encoding"]["x"]["title"], "Thời gian trung bình (phút)")
        self.assertEqual(bar["encoding"]["y"]["field"], "label")
        self.assertEqual(bar["encoding"]["y"]["title"], "Nhóm")

    def test_day_period_matrix_preserves_each_weekday_and_its_sample_size(self):
        self.frame.loc[3, "time_period"] = "Morning"
        self.load_data()
        self.app.selectbox(key="evidence_group").set_value("Ngày × khung giờ").run()
        self.assert_clean()
        matrices = [table.value for table in self.app.dataframe if table.value.index.name == "Ngày"]
        self.assertEqual(len(matrices), 2)
        means, counts = matrices
        self.assertEqual(means.loc["Monday", "Morning"], 130)
        self.assertEqual(means.loc["Friday", "Morning"], 90)
        self.assertEqual(counts.loc["Monday", "Morning"], 1)
        self.assertEqual(counts.loc["Friday", "Morning"], 1)
        self.assertTrue(pd.isna(means.loc["Monday", "Evening"]))
        self.assertTrue(pd.isna(counts.loc["Monday", "Evening"]))
        specs = [json.loads(chart.proto.spec) for chart in self.app.get("vega_lite_chart")]
        self.assertFalse(any(spec.get("mark", {}).get("type") == "bar" for spec in specs))

    def test_failed_explicit_retry_does_not_claim_the_filter_changed(self):
        self.load_data()
        self.enter_key()
        self.generate_summary()
        self.generate.side_effect = RuntimeError("synthetic service failure")
        self.app.button(key="generate_summary").click().run()
        self.assert_clean()
        self.assertTrue(len(self.app.error))
        self.assertIsNone(state(self.app, "_ai_result"))
        self.assertFalse(state(self.app, "_ai_stale"))
        self.assertFalse(any("Câu hỏi, phạm vi hoặc thiết lập đã thay đổi" in info.value for info in self.app.info))

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

    def test_model_prose_unknown_claim_and_old_payload_cannot_be_rendered(self):
        self.load_data()
        self.enter_key()
        bad_values = [
            "Có 44 ngày có dữ liệu và 11 ngày không có bản ghi.",
            "CLAIM_DOES_NOT_EXIST",
            {"text": "Có 44 ngày có dữ liệu và 11 ngày không có bản ghi.", "evidence_ids": ["F001"]},
        ]
        for bad in bad_values:
            with self.subTest(bad=type(bad).__name__):
                def malicious(**kwargs):
                    result = self.response(**kwargs)
                    result.payload["summary"] = [bad]
                    return result

                self.generate.side_effect = malicious
                self.app.button(key="generate_summary").click().run()
                self.assert_clean()
                self.assertIsNone(state(self.app, "_ai_result"))
                self.assertTrue(len(self.app.error))
                self.assertFalse(any("44 ngày" in text.value or "11 ngày" in text.value for text in self.app.text))

    def test_retry_progress_then_success_keeps_only_valid_catalog_claims(self):
        self.load_data()
        self.enter_key()

        def after_retry(**kwargs):
            kwargs["on_retry"](2, 3, "private upstream body " + FAKE_KEY)
            result = self.response(**kwargs)
            result.attempts = 2
            return result

        self.generate.side_effect = after_retry
        self.generate_summary()
        saved = state(self.app, "_ai_result")
        self.assertEqual(saved["attempts"], 2)
        self.assertEqual(saved["usage_scope"], "final_attempt_only")
        self.assertEqual(saved["validation"], "claim_catalog_v2")
        self.assertEqual(saved["narrative_version"], grounding.NARRATIVE_VERSION)
        self.assertFalse(state(self.app, "_ai_stale"))
        self.assertTrue(any("sau 2 lần gọi" in message.value for message in self.app.success))
        self.assertFalse(any(FAKE_KEY in message.value for message in [*self.app.info, *self.app.success]))
        self.assertTrue(any("Gemini lựa chọn và sắp xếp" in caption.value for caption in self.app.caption))
        catalog = grounding.build_claim_catalog(state(self.app, "_bundle"))
        for statement in saved["validated"]["summary"] + saved["validated"]["explanations"]:
            self.assertEqual(statement["text"], catalog[statement["claim_id"]]["text"])

    def test_final_retry_failure_keeps_data_without_fabricating_ai_result(self):
        self.load_data()
        self.enter_key()
        self.generate_summary()
        snapshot = state(self.app, "_bundle")["snapshot_id"]

        def exhausted(**kwargs):
            kwargs["on_retry"](2, 3, "temporary failure")
            kwargs["on_retry"](3, 3, "temporary failure")
            raise RuntimeError("private final failure " + FAKE_KEY)

        self.generate.side_effect = exhausted
        self.app.button(key="generate_summary").click().run()
        self.assert_clean()
        self.assertIsNone(state(self.app, "_ai_result"))
        self.assertEqual(state(self.app, "_bundle")["snapshot_id"], snapshot)
        self.assertEqual(len(self.app.metric), 6)
        self.assertTrue(len(self.app.dataframe))
        self.assertTrue(len(self.app.error))
        self.assertFalse(state(self.app, "_ai_stale"))
        self.assertFalse(any(FAKE_KEY in error.value for error in self.app.error))
        self.assertFalse(any("Gemini lựa chọn và sắp xếp" in caption.value for caption in self.app.caption))
        self.assertFalse(any("Đang thử lại" in info.value for info in self.app.info))

    def test_unsupported_financial_question_cannot_display_a_malicious_answer(self):
        self.load_data()
        self.enter_key()
        self.app.text_area(key="ai_question").set_value("Dự báo doanh thu tháng sau là bao nhiêu?").run()
        self.app.button(key="generate_answer").click().run()
        self.assert_clean()
        self.assertEqual(state(self.app, "_ai_result")["validated"]["answer_status"], "unsupported_question")
        self.assertTrue(any("nằm ngoài phạm vi dữ liệu" in info.value for info in self.app.info))

        def malicious(**kwargs):
            result = self.response(**kwargs)
            catalog = grounding.build_claim_catalog(kwargs["bundle"])
            answer_id = next(cid for cid, claim in catalog.items() if "answer" in claim["sections"])
            result.payload["answer_status"] = "answered"
            result.payload["answer"] = [answer_id]
            return result

        self.generate.side_effect = malicious
        self.app.button(key="generate_answer").click().run()
        self.assert_clean()
        self.assertIsNone(state(self.app, "_ai_result"))
        self.assertTrue(len(self.app.error))
        self.assertFalse(any(header.value == "Trả lời câu hỏi" for header in self.app.subheader))

    def test_question_suggestion_fills_the_editor_without_calling_gemini(self):
        self.load_data()
        self.enter_key()
        self.generate_summary()
        calls = self.generate.call_count
        suggestion = "P90 là gì và hiện tại bằng bao nhiêu?"
        self.app.selectbox(key="ai_question_suggestion").set_value(suggestion).run()
        self.assert_clean()
        self.assertEqual(self.app.text_area(key="ai_question").value, suggestion)
        self.assertIsNone(state(self.app, "_ai_result"))
        self.assertEqual(self.generate.call_count, calls)
        self.assertFalse(self.app.button(key="generate_answer").disabled)

    def test_natural_p90_definition_question_returns_controlled_explanation(self):
        self.load_data()
        self.enter_key()
        question = "P90 là gì và giải thích rõ thông số này giúp tôi"
        self.app.text_area(key="ai_question").set_value(question).run()
        self.app.button(key="generate_answer").click().run()
        self.assert_clean()
        saved = state(self.app, "_ai_result")
        self.assertEqual(saved["validated"]["answer_status"], "answered")
        answers = saved["validated"]["answer"]
        self.assertEqual([row["claim_id"] for row in answers], ["definition/p90_minutes"])
        self.assertIn("phân vị thứ 90", answers[0]["text"])
        self.assertIn("không phải SLA", answers[0]["text"])
        self.assertTrue(any(header.value == "Trả lời câu hỏi" for header in self.app.subheader))

    def test_supported_question_without_filtered_evidence_has_a_distinct_message(self):
        self.load_data()
        self.enter_key()
        question = "P90 mô tả phần đuôi ra sao?"

        def insufficient(**kwargs):
            result = self.response(**kwargs)
            result.payload["answer_status"] = "insufficient_data"
            result.payload["answer"] = []
            return result

        self.generate.side_effect = insufficient
        self.app.text_area(key="ai_question").set_value(question).run()
        self.app.button(key="generate_answer").click().run()
        self.assert_clean()
        saved = state(self.app, "_ai_result")
        self.assertEqual(saved["validated"]["answer_status"], "insufficient_data")
        self.assertTrue(any("phạm vi đang chọn chưa có đủ dữ liệu" in info.value for info in self.app.info))

    def test_narrative_version_change_invalidates_previous_ai_without_network(self):
        self.load_data()
        self.enter_key()
        self.generate_summary()
        with patch.object(grounding, "NARRATIVE_VERSION", "new-test-version"):
            self.app.run()
            self.assert_clean()
            self.assertIsNone(state(self.app, "_ai_result"))
            self.assertTrue(any("Câu hỏi, phạm vi hoặc thiết lập đã thay đổi" in info.value for info in self.app.info))
        self.assertEqual(self.generate.call_count, 1)


if __name__ == "__main__":
    unittest.main()
