import copy
import unittest

from ai.grounding import GroundingError, validate_response


class GroundingTests(unittest.TestCase):
    def setUp(self):
        self.bundle = {
            "snapshot_id": "test-snapshot",
            "facts": [
                {"id": "F001", "label": "Số bản ghi", "value": 120, "display": "120 bản ghi", "n": 120},
                {"id": "F002", "label": "Trung bình", "value": 125.5, "display": "125,50 phút", "n": 120},
                {"id": "F003", "label": "Khoảng cách", "value": None, "display": "—", "n": 0},
            ],
            "allowed_terms": ["Under 18"],
        }
        self.response = {
            "summary": [{"text": "Phạm vi đang chọn có {{F001}}, thời gian trung bình là {{F002}}.", "evidence_ids": ["F001", "F002"]}],
            "explanations": [{"text": "Cần đọc thời gian giao cùng cỡ mẫu của nhóm trước khi so sánh.", "evidence_ids": ["F001", "F002"]}],
            "answer": [], "answer_status": "not_requested",
        }

    def assertRejected(self, payload):
        with self.assertRaises(GroundingError):
            validate_response(payload, self.bundle)

    def test_values_are_rendered_from_evidence(self):
        out = validate_response(self.response, self.bundle)
        self.assertEqual(out["summary"][0]["text"], "Phạm vi đang chọn có 120 bản ghi, thời gian trung bình là 125,50 phút.")
        self.assertEqual(out["snapshot_id"], "test-snapshot")

    def test_adjacent_duplicate_units_are_removed_but_template_and_values_are_preserved(self):
        cases = [
            ("ngày", 44, "44 ngày", " ngày"),
            ("bản ghi", 120, "120 bản ghi", " bản ghi"),
            ("phút", 125.5, "125,50 phút", " phút"),
            ("km", 9.72, "9,72 km", " km"),
            ("%", .1, "10,00%", "%"),
            ("%", .1, "10,00%", " %"),
            ("điểm", 4.64, "4,64 điểm", " điểm"),
            ("bản ghi/ngày", 120.5, "120,50 bản ghi/ngày", " bản ghi/ngày"),
        ]
        for unit, value, display, duplicate in cases:
            with self.subTest(unit=unit, duplicate=duplicate):
                bundle = copy.deepcopy(self.bundle)
                fact = {"id": "F004", "value": value, "unit": unit, "display": display}
                bundle["facts"].append(fact)
                payload = copy.deepcopy(self.response)
                template = "Chỉ số trong phạm vi là {{F004}}" + duplicate + " đang được đối chiếu."
                payload["summary"][0] = {"text": template, "evidence_ids": ["F004"]}
                out = validate_response(payload, bundle)["summary"][0]
                self.assertEqual(out["text"], "Chỉ số trong phạm vi là " + display + " đang được đối chiếu.")
                self.assertEqual(out["template"], template)
                self.assertEqual(out["evidence_ids"], ["F004"])
                self.assertEqual(bundle["facts"][-1], fact)

    def test_unit_cleanup_preserves_other_units_composite_units_and_nonadjacent_prose(self):
        self.bundle["facts"][0]["unit"] = "bản ghi"
        for suffix in (" ngày", " bản ghi/ngày", " bản ghi / ngày", " bản ghi_mới",
                       "\nbản ghi", " trong phạm vi bản ghi"):
            with self.subTest(suffix=suffix):
                template = "Tập đang chọn có {{F001}}" + suffix + "."
                self.response["summary"][0] = {"text": template, "evidence_ids": ["F001"]}
                out = validate_response(self.response, self.bundle)["summary"][0]
                self.assertEqual(out["text"], template.replace("{{F001}}", "120 bản ghi"))

    def test_unit_cleanup_requires_a_whitelisted_unit_already_present_in_display(self):
        for unit, display in ((None, "120 bản ghi"), ("bản ghi", "120"), ("đơn vị", "120 đơn vị")):
            with self.subTest(unit=unit, display=display):
                self.bundle["facts"][0].update(unit=unit, display=display)
                template = "Tập đang chọn có {{F001}} " + (unit or "bản ghi") + "."
                self.response["summary"][0] = {"text": template, "evidence_ids": ["F001"]}
                out = validate_response(self.response, self.bundle)["summary"][0]
                self.assertEqual(out["text"], template.replace("{{F001}}", display))

    def test_fabricated_number_is_blocked_even_with_a_real_citation(self):
        self.response["summary"][0]["text"] = "Phạm vi đang chọn có 99999 bản ghi."
        self.assertRejected(self.response)

    def test_missing_or_stale_evidence_is_blocked(self):
        self.response["summary"][0]["evidence_ids"] = ["F999"]
        self.assertRejected(self.response)

    def test_known_placeholder_supplies_its_missing_citation(self):
        self.response["summary"][0]["evidence_ids"] = ["F001"]
        out = validate_response(self.response, self.bundle)
        self.assertEqual(out["summary"][0]["evidence_ids"], ["F001", "F002"])
        self.assertIn("125,50 phút", out["summary"][0]["text"])

    def test_unknown_numeric_placeholder_is_rejected_even_when_not_listed(self):
        self.response["summary"][0]["text"] = "Thời lượng trung bình là {{F999}}."
        self.response["summary"][0]["evidence_ids"] = ["F001"]
        self.assertRejected(self.response)

    def test_derived_citations_still_have_a_bounded_unique_list(self):
        for i in range(4, 12):
            self.bundle["facts"].append({"id": f"F{i:03d}", "value": i, "display": f"{i} bản ghi"})
        self.response["summary"][0] = {
            "text": "Tổng số bản ghi đang được đối chiếu là {{F011}}.",
            "evidence_ids": [f"F{i:03d}" for i in range(1, 11)],
        }
        self.assertRejected(self.response)

    def test_null_fact_cannot_become_a_numeric_statement(self):
        self.response["summary"][0] = {"text": "Khoảng cách trung bình là {{F003}}.", "evidence_ids": ["F003"]}
        self.assertRejected(self.response)

    def test_unknown_placeholder_and_extra_fields_are_blocked(self):
        bad = copy.deepcopy(self.response)
        bad["summary"][0]["text"] = "Số lượng là {{FAKE}}."
        self.assertRejected(bad)
        bad = copy.deepcopy(self.response)
        bad["sql"] = "DROP TABLE dw.fact_delivery"
        self.assertRejected(bad)

    def test_causal_sla_and_external_content_are_blocked(self):
        for text in ["Tắc đường gây ra thời gian giao cao.", "Tỷ lệ giao trễ đang ở mức cao.",
                     "Xem https://example.com để biết thông tin.", "<script>alert('x')</script>",
                     "Xem ![hình](https://example.com/x)."]:
            with self.subTest(text=text):
                bad = copy.deepcopy(self.response); bad["summary"][0]["text"] = text
                self.assertRejected(bad)

    def test_metric_names_and_actual_group_labels_are_allowed(self):
        self.response["summary"][0] = {"text": "Đọc P90 và nhóm Under 18 cùng cỡ mẫu để hiểu phạm vi phân tích.", "evidence_ids": ["F001"]}
        validate_response(self.response, self.bundle)

    def test_unicode_digits_do_not_bypass_numeric_guard(self):
        for value in ["９９９", "۹۹۹", "¹²³"]:
            bad = copy.deepcopy(self.response); bad["summary"][0]["text"] = f"Có {value} lượt ghi nhận trong dữ liệu."
            self.assertRejected(bad)

    def test_numeric_distance_label_is_allowed_only_when_present_in_scope(self):
        self.bundle["allowed_terms"].append("[20,50] km")
        self.response["summary"][0] = {"text": "Nhóm [20,50] km cần đọc cùng số lượng bản ghi của nhóm.", "evidence_ids": ["F001"]}
        validate_response(self.response, self.bundle)
        self.response["summary"][0]["text"] = "Nhóm [50,999] km cần đọc cùng số lượng bản ghi của nhóm."
        self.assertRejected(self.response)

    def test_answer_status_is_bound_to_actual_question(self):
        self.response["answer_status"] = "answered"
        self.response["answer"] = [copy.deepcopy(self.response["summary"][0])]
        self.assertRejected(self.response)
        self.assertEqual(validate_response(self.response, self.bundle, "Bao nhiêu bản ghi?")["answer_status"], "answered")
        self.response["answer"] = []; self.response["answer_status"] = "insufficient_data"
        self.assertEqual(validate_response(self.response, self.bundle, "Doanh thu là bao nhiêu?")["answer_status"], "insufficient_data")

    def test_duplicate_evidence_ids_and_nonfinite_values_are_rejected(self):
        self.bundle["facts"].append(copy.deepcopy(self.bundle["facts"][0]))
        self.assertRejected(self.response)
        self.bundle["facts"].pop(); self.bundle["facts"][0]["value"] = float("nan")
        self.assertRejected(self.response)


if __name__ == "__main__":
    unittest.main()
