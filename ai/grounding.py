"""Render vetted claims selected by Gemini; never display model-written prose."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
import copy
from itertools import combinations
import math
import re
import unicodedata
from typing import Any

from .analytics import BASELINE_MINUTES, KPI_DEFINITIONS, format_fact

NARRATIVE_VERSION = "5"
FACT_ID = re.compile(r"F[0-9]{3,5}\Z")
TOKEN = re.compile(r"\{\{(F[0-9]{3,5})\}\}")
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "snapshot_id": {"type": "string"},
        "summary": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 4},
        "explanations": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5},
        "answer": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        "answer_status": {"type": "string", "enum": [
            "not_requested", "answered", "insufficient_data", "unsupported_question",
        ]},
    },
    "required": ["snapshot_id", "summary", "explanations", "answer", "answer_status"],
    "additionalProperties": False,
}
_TOPICS = {
    "traffic": ("giao thông", ("giao thong", "traffic", "tac duong")),
    "weather": ("thời tiết", ("thoi tiet", "weather")),
    "vehicle": ("phương tiện", ("phuong tien", "vehicle", "vehicles", "loai xe")),
    "area": ("khu vực", ("khu vuc", "area", "areas")),
    "category": ("danh mục", ("danh muc", "category", "categories", "loai hang")),
    "time_period": ("khung giờ", ("khung gio", "time period", "time periods", "buoi")),
    "distance_band": ("khoảng cách", ("khoang cach", "distance")),
}


class GroundingError(ValueError):
    """A selection or its underlying evidence cannot be displayed safely."""


def _normal(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold().replace("đ", "d")
    return "".join(c for c in unicodedata.normalize("NFKD", text)
                   if unicodedata.category(c) not in {"Mn", "Cf"})


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _same(a: Any, b: Any) -> bool:
    return _number(a) and _number(b) and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def _label(value: Any) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 160 \
            or any(c in value for c in "{}\r\n"):
        raise GroundingError("Nhãn nhóm trong chứng cứ không hợp lệ.")
    return value


def _fact_map(bundle: Mapping[str, Any]) -> dict[str, dict]:
    rows = bundle.get("facts")
    if not isinstance(rows, list) or not rows:
        raise GroundingError("Thiếu danh sách số liệu để kiểm chứng.")
    facts = {}
    for row in rows:
        if not isinstance(row, dict):
            raise GroundingError("Định dạng chứng cứ không hợp lệ.")
        fid, value, unit, source = (row.get(k) for k in ("id", "value", "unit", "source"))
        if not isinstance(fid, str) or not FACT_ID.fullmatch(fid) or fid in facts:
            raise GroundingError("Mã chứng cứ thiếu, trùng hoặc không hợp lệ.")
        if value is not None and not (isinstance(value, str) or _number(value)):
            raise GroundingError("Giá trị chứng cứ không hợp lệ.")
        if not isinstance(unit, str) or not isinstance(source, str):
            raise GroundingError("Chứng cứ thiếu đơn vị hoặc nguồn.")
        expected = None
        if source.startswith("kpi/"):
            definition = KPI_DEFINITIONS.get(source[4:])
            expected = definition[1] if definition else None
        elif source.startswith("comparison/"):
            expected = ("ngày lịch" if source.endswith(("/from_date", "/to_date")) else
                        "bản ghi" if source.endswith(("/from_n", "/to_n")) else "phút")
        elif source.startswith("group/"):
            expected = ("bản ghi" if source.endswith(("/n", "/valid_time_count")) else
                        "km" if source.endswith("/distance") else "phút")
        elif source == "calendar/gaps":
            expected = "ngày"
        elif source in {"scope/min_date", "scope/max_date"}:
            expected = "ngày lịch"
        elif source.startswith("rule/"):
            expected = {"rule/baseline": "phút", "rule/small_sample": "bản ghi", "rule/distance": "km"}.get(source)
        if expected is not None and unit != expected:
            raise GroundingError("Đơn vị chứng cứ không khớp loại chỉ số.")
        if value is not None:
            if unit == "ngày lịch":
                try:
                    date.fromisoformat(value)
                except (TypeError, ValueError):
                    raise GroundingError("Ngày trong chứng cứ không hợp lệ.") from None
            elif not _number(value) or value < 0:
                raise GroundingError("Chỉ số định lượng phải là số hữu hạn không âm.")
            if unit == "%" and value > 1:
                raise GroundingError("Tỷ lệ trong chứng cứ nằm ngoài miền hợp lệ.")
            if unit == "điểm" and not 1 <= value <= 5:
                raise GroundingError("Rating trong chứng cứ nằm ngoài miền hợp lệ.")
        if row.get("display") != format_fact(value, unit):
            raise GroundingError("Giá trị hiển thị không khớp số liệu đã tính.")
        if unit in {"bản ghi", "ngày"} and value is not None \
                and (not _number(value) or value < 0 or int(value) != value):
            raise GroundingError("Số đếm trong chứng cứ không hợp lệ.")
        sample = row.get("n")
        if sample is not None and (not _number(sample) or sample < 0 or int(sample) != sample):
            raise GroundingError("Cỡ mẫu trong chứng cứ không hợp lệ.")
        if "context" in row and not isinstance(row["context"], dict):
            raise GroundingError("Ngữ cảnh chứng cứ không hợp lệ.")
        if source.startswith("group/") and row.get("context", {}).get("dimension") != source.split("/")[1]:
            raise GroundingError("Chiều phân tích không khớp nguồn chứng cứ của nhóm.")
        facts[fid] = row
    return facts


def build_claim_catalog(bundle: Mapping[str, Any]) -> dict[str, dict]:
    """Build all permitted wording locally from typed, current-snapshot facts."""
    facts = _fact_map(bundle)
    claims = {}

    def one(source, group=None, direction=None):
        rows = [f for f in facts.values() if f["source"] == source
                and (group is None or f.get("context", {}).get("group") == group)
                and (direction is None or f.get("context", {}).get("direction") == direction)]
        if len(rows) > 1:
            raise GroundingError("Nguồn chứng cứ bị trùng trong cùng ngữ cảnh.")
        return rows[0] if rows else None

    def token(fact):
        return "{{" + fact["id"] + "}}"

    def add(cid, template, rows, kind, topic="overview", sections=None, groups=(), metrics=()):
        refs = list(dict.fromkeys(f["id"] for f in rows))
        if not refs or len(refs) > 10 or cid in claims:
            raise GroundingError("Nhận xét có cấu trúc chứng cứ không hợp lệ.")
        tokens = TOKEN.findall(template)
        if any(t not in refs or facts[t]["value"] is None for t in tokens):
            raise GroundingError("Nhận xét đang dùng giá trị thiếu hoặc sai chứng cứ.")
        claims[cid] = {"id": cid, "text": TOKEN.sub(lambda m: facts[m[1]]["display"], template),
                       "template": template, "evidence_ids": refs, "kind": kind, "topic": topic,
                       "sections": sections or ["summary", "explanations", "answer"],
                       "groups": list(groups), "metrics": list(metrics)}

    total = one("kpi/total_records")
    if total is None or not _number(total["value"]) or total["value"] <= 0:
        raise GroundingError("Phạm vi chưa có bản ghi để tạo phân tích AI.")
    rows = [total]
    overview = f"Phạm vi đang chọn có {token(total)} giao hàng."
    overview_metrics = ["total_records"]
    for key in ("average_minutes", "median_minutes"):
        f = one("kpi/" + key)
        if f and f["value"] is not None:
            rows.append(f)
            overview_metrics.append(key)
            overview += f" {KPI_DEFINITIONS[key][0]} là {token(f)}."
    add("overview", overview, rows, "overview", sections=["summary", "answer"], metrics=overview_metrics)

    for key, (label, _) in KPI_DEFINITIONS.items():
        f = one("kpi/" + key)
        if not f:
            continue
        missing = f["value"] is None
        text = f"Chỉ số {label.lower()} hiện trả BLANK trong bộ lọc này." if missing else f"{label}: {token(f)}."
        add("kpi/" + key, text, [f], "blank" if missing else "metric", topic="kpi",
            sections=["answer"] if key in overview_metrics else None, metrics=[key])

    def define_metric(key: str, present: str, missing: str) -> None:
        fact = one("kpi/" + key)
        if fact is None:
            return
        text = missing if fact["value"] is None else present.format(value=token(fact))
        add("definition/" + key, text, [fact], "definition", topic="kpi",
            sections=["answer"], metrics=[key])

    define_metric(
        "average_minutes",
        "Thời gian giao trung bình là tổng các thời lượng giao hợp lệ chia cho số thời lượng hợp lệ; "
        "trong phạm vi đang chọn, chỉ số này là {value}. Chỉ số trung bình có thể bị ảnh hưởng bởi các giá trị rất lớn hoặc rất nhỏ.",
        "Thời gian giao trung bình là tổng các thời lượng giao hợp lệ chia cho số thời lượng hợp lệ; "
        "phạm vi đang chọn chưa có thời lượng hợp lệ để tính chỉ số này.",
    )
    define_metric(
        "median_minutes",
        "Trung vị thời lượng giao là giá trị ở giữa khi sắp xếp các thời lượng hợp lệ; khoảng một nửa số quan sát "
        "không vượt quá giá trị này và một nửa không thấp hơn giá trị này. Trung vị hiện tại là {value}.",
        "Trung vị là giá trị ở giữa khi sắp xếp các thời lượng giao hợp lệ; phạm vi đang chọn chưa có "
        "thời lượng hợp lệ để tính trung vị.",
    )
    define_metric(
        "p90_minutes",
        "P90 là phân vị thứ 90: khoảng 90% thời lượng giao hợp lệ trong phạm vi đang chọn không vượt quá {value}, "
        "còn khoảng 10% cao hơn. Đây là chỉ số thống kê, không phải SLA hay kết luận giao hàng trễ.",
        "P90 là phân vị thứ 90; phạm vi đang chọn chưa có thời lượng hợp lệ để tính P90. "
        "Đây là chỉ số thống kê, không phải SLA hay kết luận giao hàng trễ.",
    )
    define_metric(
        "p95_minutes",
        "P95 là phân vị thứ 95: khoảng 95% thời lượng giao hợp lệ trong phạm vi đang chọn không vượt quá {value}, "
        "còn khoảng 5% cao hơn. Đây là chỉ số thống kê, không phải SLA hay kết luận giao hàng trễ.",
        "P95 là phân vị thứ 95; phạm vi đang chọn chưa có thời lượng hợp lệ để tính P95. "
        "Đây là chỉ số thống kê, không phải SLA hay kết luận giao hàng trễ.",
    )
    define_metric(
        "records_per_active_day",
        "Bản ghi trên mỗi ngày có dữ liệu được tính bằng tổng số bản ghi chia cho số ngày có ít nhất một bản ghi; "
        "giá trị trong phạm vi đang chọn là {value}.",
        "Bản ghi trên mỗi ngày có dữ liệu được tính bằng tổng số bản ghi chia cho số ngày có ít nhất một bản ghi; "
        "phạm vi đang chọn chưa có đủ dữ liệu để tính chỉ số này.",
    )

    baseline_rule = one("rule/baseline")
    if baseline_rule is not None:
        add(
            "definition/baseline",
            f"Mốc {token(baseline_rule)} là tham chiếu thống kê cố định dùng để đếm và tính tỷ lệ thời lượng vượt mốc. "
            "Mốc này không phải SLA, cam kết giao hàng hay kết luận giao hàng trễ.",
            [baseline_rule], "definition", topic="kpi", sections=["answer"],
        )

    p90, p95 = one("kpi/p90_minutes"), one("kpi/p95_minutes")
    if p90 and p95 and p90["value"] is not None and p95["value"] is not None:
        add("distribution", f"P90 thời lượng giao theo bộ lọc là {token(p90)}; P95 là {token(p95)}.",
            [p90, p95], "distribution", metrics=["p90_minutes", "p95_minutes"])

    above, share, baseline = one("kpi/above_baseline_count"), one("kpi/share_above_baseline"), one("rule/baseline")
    if above and share and baseline:
        if (above["value"] is None) != (share["value"] is None):
            raise GroundingError("Số bản ghi và tỷ lệ vượt mốc không cùng trạng thái dữ liệu.")
        missing = above["value"] is None
        if not missing and (not _same(above.get("n"), share.get("n")) or not above["n"]
                            or not _same(share["value"], above["value"] / above["n"])):
            raise GroundingError("Mẫu số của tỷ lệ vượt mốc không khớp chứng cứ.")
        text = (f"Measure số bản ghi và tỷ lệ vượt mốc tham chiếu {token(baseline)} hiện trả BLANK trong bộ lọc này."
                if missing else f"Có {token(above)} vượt mốc tham chiếu {token(baseline)}; tỷ lệ trên các thời lượng hợp lệ là {token(share)}.")
        add("baseline", text, [above, share, baseline], "blank" if missing else "baseline",
            metrics=["above_baseline_count", "share_above_baseline"])

    active, gaps = one("kpi/active_days"), one("calendar/gaps")
    if active and gaps and active["value"] is not None:
        add("calendar", f"Có {token(active)} có bản ghi. Số ngày lịch không có bản ghi trong phạm vi được thống kê là {token(gaps)}.",
            [active, gaps], "calendar", "calendar", metrics=["active_days", "calendar_gaps"])
    first, last = one("scope/min_date"), one("scope/max_date")
    if first and last and first["value"] is not None and last["value"] is not None:
        try:
            assert date.fromisoformat(first["value"]) <= date.fromisoformat(last["value"])
        except (TypeError, ValueError, AssertionError):
            raise GroundingError("Ngày trong phạm vi chứng cứ không hợp lệ.") from None
        add("calendar_range", f"Ngày đầu tiên có bản ghi là {token(first)}; ngày cuối cùng có bản ghi là {token(last)}.",
            [first, last], "calendar", "calendar")

    threshold = one("rule/small_sample")

    def group_parts(topic, label):
        mean, count = one(f"group/{topic}/average", label), one(f"group/{topic}/n", label)
        if not mean or not count or mean["value"] is None:
            return None
        n = mean.get("n")
        if not _number(n) or n <= 0 or not _number(count["value"]) or n > count["value"]:
            raise GroundingError("Cỡ mẫu thời lượng không khớp tổng số bản ghi của nhóm.")
        effective = count if _same(n, count["value"]) else one(f"group/{topic}/valid_time_count", label)
        if not effective:
            return None  # A lower-priority fact may have been omitted at the evidence cap.
        if not _same(effective["value"], n):
            raise GroundingError("Cỡ mẫu thời lượng không khớp chứng cứ của nhóm.")
        return mean, effective, count

    for topic, (name, _) in _TOPICS.items():
        for mean in [f for f in facts.values() if f["source"] == f"group/{topic}/average"]:
            label = _label(mean.get("context", {}).get("group"))
            parts = group_parts(topic, label)
            if not parts:
                continue
            mean, effective, count = parts
            rows = [mean, effective]
            text = f"Nhóm {name} {label} có thời lượng giao trung bình {token(mean)} trên {token(effective)} có thời lượng hợp lệ."
            if effective["id"] != count["id"]:
                text += f" Tổng số bản ghi của nhóm là {token(count)}."
                rows.append(count)
            if threshold and 0 < mean["n"] < threshold["value"]:
                text += " Cỡ mẫu thời lượng nhỏ; cần thận trọng khi so sánh."
                rows.append(threshold)
            add("group/" + mean["id"], text, rows, "group", topic,
                sections=["explanations", "answer"], groups=[label], metrics=["average_minutes", "valid_time_count", "total_records"])

        comparison = one("comparison/" + topic)
        if comparison is None:
            continue
        c = comparison.get("context", {})
        high, low = _label(c.get("high")), _label(c.get("low"))
        high_parts, low_parts = group_parts(topic, high), group_parts(topic, low)
        if not high_parts or not low_parts or not threshold:
            continue
        hm, hn, _ = high_parts
        lm, ln, _ = low_parts
        if high == low or any(_normal(v) == "unknown" for v in (high, low)) \
                or not _same(c.get("minimum_n"), threshold["value"]) \
                or min(hn["value"], ln["value"]) < threshold["value"] \
                or not all((_same(c.get("high_n"), hn["value"]), _same(c.get("low_n"), ln["value"]),
                            _same(c.get("high_average_minutes"), hm["value"]), _same(c.get("low_average_minutes"), lm["value"]),
                            _same(comparison["value"], hm["value"] - lm["value"]))) or comparison["value"] < 0:
            raise GroundingError("So sánh nhóm không khớp giá trị, cỡ mẫu hoặc ngữ cảnh.")
        text = (f"Trong các nhóm {name} có nhãn xác định và đủ mẫu thời lượng, {high} có trung bình cao nhất là {token(hm)} "
                f"với cỡ mẫu {token(hn)}; {low} có trung bình thấp nhất là {token(lm)} với cỡ mẫu {token(ln)}. "
                f"Chênh lệch giữa hai nhóm là {token(comparison)}.")
        add("comparison/" + topic, text, [comparison, hm, hn, lm, ln, threshold], "comparison", topic,
            sections=["explanations", "answer"], groups=[high, low], metrics=["average_minutes", "valid_time_count", "difference"])

    for direction, suffix in (("tăng", "increase"), ("giảm", "decrease")):
        delta = one("comparison/daily_average", direction=direction)
        if not delta or not threshold:
            continue
        fields = {key: one("comparison/daily_average/" + key, direction=direction)
                  for key in ("from_date", "to_date", "from_average", "to_average", "from_n", "to_n")}
        if not all(fields.values()):
            continue
        fd, td, fm, tm, fn, tn = fields.values()
        try:
            adjacent = (date.fromisoformat(td["value"]) - date.fromisoformat(fd["value"])).days == 1
        except (ValueError, TypeError):
            adjacent = False
        sign = 1 if direction == "tăng" else -1
        c = delta.get("context", {})
        if not adjacent or min(fn["value"], tn["value"]) < threshold["value"] \
                or not _same(delta["value"], sign * (tm["value"] - fm["value"])) or delta["value"] <= 0 \
                or c.get("from_date") != fd["value"] or c.get("to_date") != td["value"] \
                or not all((_same(c.get("from_n"), fn["value"]), _same(c.get("to_n"), tn["value"]),
                            _same(c.get("from_average_minutes"), fm["value"]), _same(c.get("to_average_minutes"), tm["value"]))) \
                or any(f.get("context") != c for f in fields.values()):
            raise GroundingError("Biến động ngày không khớp ngày, thời lượng hoặc cỡ mẫu.")
        text = (f"Trong các cặp ngày lịch liền nhau đủ mẫu thời lượng, mức {direction} trung bình lớn nhất là {token(delta)}. "
                f"Ngày {token(fd)} có trung bình {token(fm)} với cỡ mẫu {token(fn)}; "
                f"ngày {token(td)} có trung bình {token(tm)} với cỡ mẫu {token(tn)}.")
        add("daily/" + suffix, text, [delta, fd, td, fm, tm, fn, tn, threshold], "daily", "daily",
            sections=["explanations", "answer"], metrics=["average_minutes", "valid_time_count", "difference"])

    add("scope_note", "Các kết quả mô tả phạm vi bộ lọc hiện tại; cần đọc cùng cỡ mẫu và không suy ra quan hệ nhân quả.",
        [total], "scope_note", sections=["explanations"])
    return claims


def _question_policy(catalog: dict, question: str) -> dict:
    if not isinstance(question, str) or len(question) > 1000:
        raise GroundingError("Câu hỏi phải là văn bản không quá một nghìn ký tự.")

    answer_ids = [cid for cid, claim in catalog.items() if "answer" in claim["sections"]]

    def policy(mode: str, statuses: tuple[str, ...], *, ids=(), metrics=(), groups=(), required=(),
               required_status: str | None = None) -> dict:
        return {
            "mode": mode,
            "allowed_statuses": list(statuses),
            "allowed_answer_ids": list(dict.fromkeys(ids)),
            "required_status": required_status,
            "metrics": set(metrics),
            "groups": set(groups),
            "required_claim_ids": set(required),
        }

    def unsupported() -> dict:
        return policy("explicit_unsupported", ("unsupported_question",),
                      required_status="unsupported_question")

    def insufficient() -> dict:
        return policy("deterministic", ("insufficient_data",), required_status="insufficient_data")

    def semantic(*, ids=None, metrics=(), groups=()) -> dict:
        eligible = answer_ids if ids is None else list(ids)
        if not eligible:
            return insufficient()
        return policy("semantic_fallback", ("answered", "insufficient_data", "unsupported_question"),
                      ids=eligible, metrics=metrics, groups=groups)

    if not question.strip():
        return policy("not_requested", ("not_requested",), required_status="not_requested")

    original_question = unicodedata.normalize("NFKC", question)
    q = _normal(question)
    q = re.sub(r"(?<!\w)what(?:'|’)s(?!\w)", "what is", q)
    q = re.sub(r"(?<!\w)p\s*[-_]?\s*(50|90|95)(?!\w)", r"p\1", q)
    q = re.sub(r"(?<!\w)(50|90|95)(?:st|nd|rd|th)\s+percentile(?!\w)", r"p\1", q)
    q = re.sub(r"(?<!\w)(?:phan vi(?: thu)?|percentile)\s*(50|90|95)(?!\w)", r"p\1", q)
    definition_requested = any(term in q for term in (
        "la gi", "y nghia", "nghia la", "giai thich", "dinh nghia", "hieu nhu the nao", "hieu the nao",
        "noi len dieu gi", "phan anh", "the hien", "noi gi", "mo ta", "noi ro", "lam ro", "dung ra sao",
        "co phai", "tac dung", "dung de lam gi", "dung lam gi", "de lam gi",
        "duoc dung nhu the nao", "dung nhu the nao", "what is", "what exactly is", "what does", "how is it used",
        "meaning", " means", "explain", "explanation", "define", "definition", "describe", "clarify",
        "represent", "indicate", "used for", "purpose",
    ))
    baseline_intent = any(term in q for term in (
        "baseline", "moc tham chieu", f"moc {BASELINE_MINUTES}", f"nguong {BASELINE_MINUTES}",
    ))
    exceed_intent = any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", q) for term in (
        "vuot", "tren", "lon hon", "cao hon", "tro len", "khong duoi", "it nhat", "tu muc",
        "above", "exceed", "exceeds", "greater than", "beyond", "at least", "no less than",
        "over", "past", "after",
    )) or ">=" in q or bool(re.search(r"\bp(?:90|95)\s*\+", q)) \
        or bool(re.search(r"(?<!thong )\bqua\b", q))
    if exceed_intent and ("p90" in q or "p95" in q) and not baseline_intent:
        # The application has a fixed >195-minute baseline metric, but it does
        # not calculate a dynamic share/count above the filtered P90 or P95.
        return unsupported()
    contract_terms = ("sla", "dung han", "giao tre", "cam ket")
    safe_contract_question = definition_requested and any(term in q for term in contract_terms) \
        and (baseline_intent or "p90" in q or "p95" in q)
    unsupported_terms = (
        "doanh thu", "chi phi", "loi nhuan", "thu nhap", "revenue", "profit", "sales", "income",
        "du bao", "du doan", "forecast", "predict", "thang sau", "tuan sau", "ngay mai", "hom nay",
        "hom qua", "sau nay", "will", "future", "tomorrow", "nguyen nhan", "gay ra", "vi sao",
        "tai sao", "anh huong", "tac dong", "caused", "causes", "affect", "impact", "why",
        "api key", "mat khau", "password", "secret",
        "system prompt", "bo qua", "bo huong dan", "bo quy tac", "ignore", "sql", "order_id",
        "toa do", "coordinates", "tung don", "danh sach", "liet ke tat ca",
        "tuan nay", "thang nay", "nam nay", "quy nay", "tuan truoc", "thang truoc", "nam truoc",
        "this week", "this month", "this year", "current week", "current month", "current year",
        "this quarter", "current quarter", "last week", "last month", "last quarter", "last year",
        "today", "yesterday", "co on khong", "on chu", "tot hay xau", "tot khong", "xau khong",
        "chap nhan duoc", "binh thuong khong", "qua cao", "qua thap", "hop ly khong",
        "co cao khong", "co thap khong", "cao hay thap", "dat yeu cau", "dat target",
        "dang lo", "co dang lo", "on khong", "on chua",
        "good or bad", "is it good", "is it bad", "acceptable", "okay or not", "normal",
        "reasonable", "too high", "too low", "meet target", "meet the target", "meets target",
        "within target", "concerning", "worry", "worried",
        "khach hang", "customer", "vip", "xe o to", "o to", "automobile", "car", "truck",
    )
    if any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", q) for term in unsupported_terms):
        return unsupported()
    if not safe_contract_question and any(
            re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", q) for term in contract_terms):
        return unsupported()

    topics = {topic for topic, (_, aliases) in _TOPICS.items()
              if any(re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", q) for alias in aliases)}
    groups = set()
    scalar_high_low = bool(re.search(
        r"\bhow\s+(?:high|low)\s+is\s+(?:the\s+)?(?:p90|p95|p50|median|average|mean|avg)\b",
        q,
    ))
    labels = sorted({group for claim in catalog.values() for group in claim["groups"]}, key=len, reverse=True)
    remaining = q
    raw_remaining = original_question.casefold()
    for label in labels:
        if scalar_high_low and _normal(label) in {"high", "low"}:
            continue
        pattern = r"(?<!\w)" + re.escape(_normal(label)) + r"(?!\w)"
        raw_pattern = r"(?<!\w)" + re.escape(unicodedata.normalize("NFKC", label).casefold()) + r"(?!\w)"
        if re.search(raw_pattern, raw_remaining):
            groups.add(label)
            remaining = re.sub(pattern, " ", remaining)
            raw_remaining = re.sub(raw_pattern, " ", raw_remaining)
    if groups and not topics:
        topics = {claim["topic"] for claim in catalog.values() if groups.intersection(claim["groups"])}
    current_value_phrase = "ngay bay gio" in q
    daily = ("ngay" in q or "daily" in q) and not current_value_phrase and any(term in q for term in (
        "tang", "giam", "bien dong", "lien nhau", "increase", "decrease",
    ))
    if daily:
        topics.add("daily")
    elif ("ngay" in q or "calendar" in q) and not current_value_phrase \
            and not topics and "ban ghi/ngay" not in q:
        topics.add("calendar")
    if len(topics) > 1:
        return unsupported()

    numeric = re.sub(r"p(?:50|90|95)", "", remaining)
    if baseline_intent:
        numeric = re.sub(r"(?<!\d)" + str(BASELINE_MINUTES) + r"(?!\d)", "", numeric)
    if any(character.isnumeric() for character in numeric):
        return unsupported()
    if any(character.isalpha() and not ("a" <= character <= "z") for character in numeric):
        return unsupported()

    metric_terms = {
        "p90_minutes": ("p90", "phan vi 90", "percentile 90"),
        "p95_minutes": ("p95", "phan vi 95", "percentile 95"),
        "median_minutes": ("trung vi", "median", "p50"),
        "average_pickup_delay": ("pickup", "cho lay hang"),
        "records_per_active_day": (
            "ban ghi/ngay", "ban ghi moi ngay", "ban ghi binh quan moi ngay",
            "binh quan ban ghi moi ngay", "records per active day", "records/day",
            "active-day record average", "active day record average",
        ),
        "average_valid_distance": ("khoang cach hop le trung binh", "khoang cach trung binh", "average distance", "mean distance"),
        "valid_distance_coverage": ("ty le khoang cach hop le", "ty trong khoang cach hop le", "valid distance coverage"),
        "valid_rating_coverage": ("ty le rating hop le", "ty trong rating hop le", "rating coverage"),
        "pickup_delay_coverage": ("ty le co pickup", "pickup coverage"),
        "operational_context_coverage": ("ty le du context", "operational context coverage"),
        "valid_distance_count": ("so ban ghi co khoang cach hop le", "valid distance count"),
    }
    wanted = {key for key, aliases in metric_terms.items() if any(term in q for term in aliases)}
    duration_requested = any(term in q for term in (
        "thoi gian giao", "thoi luong giao", "giao lau", "giao nhanh", "delivery time", "delivery duration",
        "average delivery", "mean delivery",
    ))
    mean_as_verb = "meaning" in q or bool(re.search(r"\bwhat (?:does|do)\b.*\bmean\b", q))
    mean_requested = any(term in q for term in ("trung binh", "binh quan", "average")) \
        or bool(re.search(r"(?<!\w)avg(?!\w)", q)) \
        or (bool(re.search(r"(?<!\w)mean(?!\w)", q)) and not mean_as_verb)
    distance_requested = "khoang cach" in q or "distance" in q
    rating_requested = "rating" in q or "diem danh gia" in q or "danh gia hop le" in q
    ratio_requested = any(term in q for term in ("ty le", "ty trong", "percent", "share", "rate"))
    if mean_requested and distance_requested and not duration_requested:
        wanted.add("average_valid_distance")
    if rating_requested and not ratio_requested:
        wanted.add("average_valid_rating")
    specialized = wanted.intersection({
        "average_pickup_delay", "average_valid_rating", "average_valid_distance", "records_per_active_day",
    })
    if (duration_requested and mean_requested and "average_pickup_delay" not in wanted) \
            or (mean_requested and not specialized):
        wanted.add("average_minutes")
    count_intent = re.search(
        r"(?:bao nhieu ban ghi|bao nhieu don|bao nhieu chuyen(?: giao)?|bao nhieu giao hang|"
        r"so ban ghi|so luong ban ghi|so chuyen(?: giao)?|so luong don|so luong giao hang|so luong chuyen(?: giao)?|"
        r"so don|so giao hang|tong so giao hang|nhieu ban ghi|it ban ghi|"
        r"total records|record count|how many (?:deliveries|delivery records|delivery rows|records|orders|shipments)|"
        r"number of (?:deliveries|delivery records|delivery rows|records|orders|shipments)|total deliveries|total delivery records|"
        r"total orders|delivery volume|delivery count|deliveries count|order count)"
        r"(?!\s+(?:vuot|tren|co khoang cach|binh quan|trung binh|moi ngay)|\s*/\s*ngay)", q)
    if count_intent:
        wanted.add("total_records")
    percentile_metrics = wanted.intersection({"p90_minutes", "p95_minutes"})
    explicit_metric_list = bool(
        re.search(
            r"(?:p90|p95).{0,24}(?:\b(?:va|and)\b|,).{0,12}"
            r"(?:tong\s+)?(?:so ban ghi|so luong ban ghi|so chuyen giao|so luong don|so luong giao hang|so don|ban ghi|"
            r"chuyen giao|giao hang|total records|record count|number of deliveries|total deliveries|"
            r"total delivery records|total orders|delivery volume|delivery count)",
            q,
        )
        or re.search(
            r"(?:tong\s+)?(?:so ban ghi|so luong ban ghi|so chuyen giao|so luong don|so luong giao hang|so don|ban ghi|"
            r"chuyen giao|giao hang|total records|record count|number of deliveries|total deliveries|"
            r"total delivery records|total orders|delivery volume|delivery count).{0,24}"
            r"(?:\b(?:va|and)\b|,).{0,12}(?:p90|p95)",
            q,
        )
    )
    if "total_records" in wanted and percentile_metrics and not explicit_metric_list:
        return unsupported()
    broad_record_count_question = bool(re.search(
        r"(?:bao nhieu\s+(?:ban ghi|don|chuyen|giao hang)|"
        r"(?:so|so luong|tong so)\s+(?:ban ghi|don|chuyen(?: giao)?|giao hang)|"
        r"how many\s+(?:deliveries|delivery records|delivery rows|records|orders|shipments)|"
        r"number of\s+(?:deliveries|delivery records|delivery rows|records|orders|shipments)|"
        r"total deliveries|total delivery records|delivery volume|(?:deliveries|delivery|record|order) count)",
        q,
    ))
    if broad_record_count_question and percentile_metrics and not explicit_metric_list:
        return unsupported()
    unsupported_arithmetic = bool(
        re.search(r"\b(?:p90|p95|p50)\b\s*[/×*]\s*\b(?:p90|p95|p50)\b", q)
        or (len(groups) == 2 and re.search(r"\s[/×*]\s", q))
    )
    if unsupported_arithmetic:
        return unsupported()
    subtraction_requested = bool(
        re.search(r"\b(?:p90|p95|p50)\b\s*[-–−]\s*\b(?:p90|p95|p50)\b", q)
        or (len(groups) == 2 and re.search(r"\s[-–−]\s", q))
    )
    difference_requested = subtraction_requested or any(term in q for term in (
        "chenh lech", "do lech", "lech bao nhieu", "hieu giua", "gap", "difference", "minus", "numeric difference",
    ))
    ranked = difference_requested or any(term in q for term in (
        "cao nhat", "thap nhat", "lon nhat", "nho nhat", "nhieu nhat", "it nhat", "lau nhat",
        "nhieu ban ghi nhat", "it ban ghi nhat", "nhieu don nhat", "it don nhat",
        "nhanh nhat", "cham nhat", "cham hon", "nhanh hon", "chenh lech", "khac biet", "khac gi", "so sanh", "lech",
        "cao hon", "thap hon", "lau hon", "highest", "lowest", "maximum", "minimum",
        "slowest", "fastest", "quickest", "best", "worst", "most delayed",
        "slower", "faster", "higher", "lower", "longest", "shortest",
        "takes longest", "taking the most time", "most time", "least time", "least average",
        "compare", "compared", "comparison", " vs ", "versus",
        "most records", "fewest records", "gap",
    ))
    if topics and ranked and not wanted:
        wanted.add("average_minutes")
    # The catalog has duration rankings by group, but it does not calculate a
    # ranking by record volume.  Treat that as an unsupported capability
    # instead of implying that the current filter merely lacks data.
    if topics and ranked and "total_records" in wanted:
        return unsupported()
    all_groups_requested = any(term in q for term in (
        "theo nhom", "tung nhom", "cac nhom", "tat ca nhom", "by group", "each group", "all groups",
        "group averages", "groups", "breakdown",
    )) or bool(re.search(r"\b(?:traffic|weather|vehicle|area|category|time period) averages\b", q))
    if topics and all_groups_requested and not groups:
        return unsupported()

    general_overview = any(term in q for term in (
        "tong quan", "tom tat", "tinh hinh giao hang", "hieu suat giao hang",
        "chi so chinh", "phan tich du lieu", "du lieu dang noi len dieu gi",
        "overview", "summary", "overall performance", "what does the data show",
        "tell me about the data", "show me the data overview", "du lieu the nao", "what are the kpis", "show kpis",
        "key metrics", "summarize current data", "analyze the data", "delivery performance",
        "tinh hinh hien tai", "cac kpi hien tai", "describe the current data",
        "what can the data tell me", "deliveries performing",
    ))

    vocabulary = set((
        "cho toi minh biet hay vui long ban co the giup xin xem lieu nay hien tai dang chon trong tap pham vi du lieu cac chi so kpi nguoi "
        "gi giai thich ro that ro thong so y nghia dinh nghia hieu nhu the nao noi len dieu phan anh the hien mo ta noi lam ro ra sao tac dung de lam duoc nhe a co phai khong sla cam ket "
        "o tai thanh pho tinh quan huyen "
        "so luong ban ghi don giao hang thoi gian phut luong trung binh quan vi phan percentile moc tham chieu co dinh vuot ty le trong bao nhieu la nao nhung tri bay gio "
        "ngay lich cap lien nhau dau tien cuoi cung tu den du mau hop le lon nhat nho cao thap lau nhanh cham muc tang giam bien dong thay doi chenh lech khac biet lech da tinh "
        "cua voi va ve con giua hon sanh theo nhom thong tiet phuong loai xe khu vuc danh khung gio buoi khoang cach do dai km diem gia xay ra vs "
        "rating pickup cho lay nguong tren moi tong tat ca thong ke ket qua phan tich thuc su bang truoc sau van chuyen nam "
        "what which does is are has can could should i me we you give define describe clarify summarize the current selected data scope total records deliveries orders shipments rows number count average avg mean median delivery duration time minutes minute volume right now high low like there used purpose "
        "meaning means explain explanation definition percentile percent share rate above fixed baseline threshold traffic weather vehicle vehicles area areas category categories period periods distance day days daily simple simply terms plain language beginner "
        "largest smallest highest lowest higher lower maximum minimum slowest fastest quickest slower faster longest shortest best worst most delayed takes taking most least increase decrease gap difference minus different exact exactly compare compared comparison versus between and or than from to of in at with by per valid sample size group groups each breakdown "
        "samples observed active calendar missing recorded record for all many how show please tell about clearly overall value values summary overview analysis analyze insight insights statistics stats currently moment level p90 p95 p50 context coverage performing"
    ).split())
    words = set(re.findall(r"[a-z]+[0-9]*", numeric))
    unknown_words = words.difference(vocabulary)

    # Unknown locations must not disappear when Gemini interprets the rest of
    # a natural sentence. Exclusions keep ordinary time/scope phrases such as
    # "hiện tại" and "ở phạm vi này" usable.
    unaccented_admin_scope = False
    for marker in ("tinh", "quan", "huyen"):
        match = re.search(r"(?i)\b" + marker + r"\s+([^\W\d_]+)", original_question)
        if match and match.group(1)[0].isupper():
            unaccented_admin_scope = True
            break
    location_scope = bool(
        re.search(r"\bo\s+(?!pham vi\b|du lieu\b|day\b|dau\b|vi tri\b|muc\b|nguong\b|khoang\b|hien tai\b)\w+", q)
        or re.search(r"(?<!hien )\btai\s+(?!thoi\b|luc\b|ngay\b|pham vi\b|du lieu\b)\w+", q)
        or re.search(r"\bở\s+(?!phạm vi\b|dữ liệu\b|đây\b|đâu\b|vị trí\b|mức\b|ngưỡng\b|khoảng\b|hiện tại\b)[^\W\d_]+", raw_remaining)
        or re.search(r"(?<!hiện )\btại\s+(?!thời\b|lúc\b|ngày\b|phạm vi\b|dữ liệu\b)[^\W\d_]+", raw_remaining)
        or re.search(r"\bthành phố\b|\btỉnh\s+[^\W\d_]+|\bquận\s+[^\W\d_]+|\bhuyện\s+[^\W\d_]+", raw_remaining)
        or re.search(r"\bthanh pho\b", q)
        or unaccented_admin_scope
        or (not groups and bool(re.search(r"\b(?:in|for|at)\s+([A-Z][A-Za-z-]*)", original_question)))
    )
    relative_time_scope = bool(
        re.search(r"\b(?:tuần|tháng|năm|quý|hôm)\b", raw_remaining)
        or re.search(r"\bthứ\s+(?:hai|ba|tư|năm|sáu|bảy|chủ nhật)\b", raw_remaining)
        or re.search(r"\bMay\b", original_question)
        or re.search(
            r"\b(?:tuan|thang|nam|quy)\s+(?:nay|truoc|sau|hien tai|vua roi|gan day)\b|"
            r"\bhom(?:\s+(?:nay|qua|truoc|sau)|\s+thu\s+(?:hai|ba|tu|nam|sau|bay|chu nhat))\b|"
            r"\bthu\s+(?:hai|ba|tu|nam|sau|bay|chu nhat)\b|"
            r"\b(?:on\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b|"
            r"\b(?:january|february|march|april|june|july|august|september|october|november|december|quarter)\b",
            q,
        )
    )
    unresolved_entity_scope = bool(
        re.search(r"\b(?:cua\s+)?phan khuc\s+\w+", remaining)
        or re.search(r"\b(?:cua|cho|theo)\s+doi tac\s+\w+", remaining)
        or re.search(r"\bcua\s+nhom\s+\w+", remaining)
        or re.search(
            r"\bnhom\s+(?!nao\b|giao thong\b|thoi tiet\b|phuong tien\b|khu vuc\b|danh muc\b|khung gio\b)\w+",
            remaining,
        )
        or re.search(r"\bcua\s+(?:loai\s+)?xe\s+\w+", remaining)
        or re.search(
            r"\b(?:(?:cua|cho|tai|ben|theo)\s+)?(?:cua hang|kho|mien|vung|chi nhanh)\s+\w+",
            remaining,
        )
        or re.search(r"\b(?:store|warehouse|region|branch)\s+\w+", remaining)
        or re.search(
            r"\b(?:hub|depot|segment|partner|product|pickup point|delivery point|shop|site|location|outlet)\s+\w+",
            remaining,
        )
        or re.search(r"\bca\s+(?:sang|chieu|toi|dem)\b|\b(?:morning|afternoon|evening|night)\s+shift\b", remaining)
    )
    unresolved_preposition_scope = bool(unknown_words) and bool(
        re.search(
            r"(?<!hien )\b(?:cua|cho|ben|tai|theo|trong|tu)\s+"
            r"(?!(?:p90|p95|chi so|thong so|du lieu|pham vi|bo loc|phan tich|"
            r"toi|minh|ban|nguoi|muc dich|thoi diem|ngay dang chon)\b)\w+",
            remaining,
        )
        or re.search(
            r"\b(?:in|for|at|from|during|by)\s+"
            r"(?!(?:the|this|current|selected|data|scope|analysis|filter|minutes|me|us)\b)\w+",
            remaining,
        )
    )
    if location_scope or relative_time_scope or unresolved_entity_scope or unresolved_preposition_scope:
        return unsupported()
    if general_overview and not (topics or groups or wanted or baseline_intent):
        ids = [cid for cid in ("overview", "distribution", "baseline", "calendar") if cid in catalog]
        return policy("deterministic", ("answered",), ids=ids, required=("overview",),
                      required_status="answered")

    if definition_requested and not unknown_words and not topics and not groups:
        definition_ids = []
        if baseline_intent and "definition/baseline" in catalog:
            definition_ids.append("definition/baseline")
        for key in sorted(wanted):
            claim_id = "definition/" + key
            if claim_id in catalog:
                definition_ids.append(claim_id)
        if definition_ids:
            if len(definition_ids) > RESPONSE_SCHEMA["properties"]["answer"]["maxItems"]:
                return unsupported()
            covered = {metric for cid in definition_ids for metric in catalog[cid]["metrics"]}
            required_metrics = wanted.intersection(covered)
            return policy("deterministic", ("answered",), ids=definition_ids,
                          metrics=required_metrics, required=definition_ids, required_status="answered")

    if unknown_words:
        safe_definition_unknown_words = {"duoi", "tail", "upper"}
        if location_scope or relative_time_scope or unresolved_entity_scope \
                or (ranked and len(groups) == 1) \
                or not (wanted or topics or groups or baseline_intent) \
                or (topics and not groups) \
                or (wanted and not topics and not groups and (
                    not definition_requested or not unknown_words.issubset(safe_definition_unknown_words)
                )):
            return unsupported()
        candidates = answer_ids
        if definition_requested and wanted:
            candidates = [cid for cid in candidates if catalog[cid]["kind"] == "definition"
                          and wanted.intersection(catalog[cid]["metrics"])]
        elif wanted:
            candidates = [cid for cid in candidates if wanted.intersection(catalog[cid]["metrics"])]
            if not topics and not groups:
                candidates = [cid for cid in candidates if catalog[cid]["topic"] in {"overview", "kpi"}]
        if topics:
            candidates = [cid for cid in candidates if catalog[cid]["topic"] in topics]
        if groups:
            candidates = [cid for cid in candidates if groups.issubset(catalog[cid]["groups"])]
        return semantic(ids=candidates, metrics=wanted, groups=groups)
    if baseline_intent and not definition_requested:
        wanted.add("share_above_baseline" if ratio_requested else "above_baseline_count")
    if ratio_requested and not any(KPI_DEFINITIONS[key][1] == "%" for key in wanted):
        return unsupported()
    if topics == {"distance_band"} and not groups and not ranked \
            and wanted.intersection({"average_valid_distance", "valid_distance_coverage", "valid_distance_count"}):
        topics.clear()
    if topics == {"calendar"} and wanted == {"records_per_active_day"}:
        topics.clear()

    topic = next(iter(topics), None)
    required_claim_ids = set()
    if topic == "daily":
        if wanted != {"average_minutes"}:
            return unsupported()
        ids = [cid for cid, claim in catalog.items() if claim["kind"] == "daily"]
        up = "tang" in q or "increase" in q
        down = "giam" in q or "decrease" in q
        if up != down:
            ids = [cid for cid in ids if cid.endswith("increase" if up else "decrease")]
        elif up and down:
            required_claim_ids = {"daily/increase", "daily/decrease"}
            if not required_claim_ids.issubset(ids):
                return insufficient()
    elif topic == "calendar":
        if ranked:
            return unsupported()
        if any(term in q for term in ("dau tien", "cuoi cung", "tu ngay", "den ngay", "date range")):
            ids = [cid for cid in ("calendar_range",) if cid in catalog]
        elif any(term in q for term in ("bao nhieu ngay", "so ngay", "how many", "count")):
            ids = [cid for cid in ("calendar",) if cid in catalog]
        else:
            return unsupported()
    elif topic:
        if not wanted:
            if groups:
                if len(groups) > 2:
                    return unsupported()
                ids = [cid for cid, claim in catalog.items()
                       if claim["topic"] == topic and claim["kind"] == "group"
                       and set(claim["groups"]).issubset(groups)]
                if not ids:
                    return insufficient()
                return policy("deterministic", ("answered",), ids=ids,
                              groups=groups, required=ids, required_status="answered")
            claim_id = "comparison/" + topic
            if claim_id not in catalog:
                return insufficient()
            return policy("deterministic", ("answered",), ids=(claim_id,),
                          metrics=("average_minutes",), required=(claim_id,), required_status="answered")
        if wanted.difference({"average_minutes", "total_records"}) or len(groups) > 2 \
                or (ranked and len(groups) == 1):
            return unsupported()
        if len(groups) == 2:
            comparisons = [cid for cid, claim in catalog.items()
                           if claim["topic"] == topic and claim["kind"] == "comparison"
                           and set(claim["groups"]) == groups]
            if difference_requested:
                if not comparisons:
                    return unsupported()
                return policy("deterministic", ("answered",), ids=comparisons,
                              metrics=wanted, groups=groups, required=comparisons,
                              required_status="answered")
            group_claims = [cid for cid, claim in catalog.items()
                            if claim["topic"] == topic and claim["kind"] == "group"
                            and set(claim["groups"]).issubset(groups)]
            ids = comparisons + group_claims
        elif not groups:
            if not ranked:
                return unsupported()
            ids = [cid for cid, claim in catalog.items()
                   if claim["topic"] == topic and claim["kind"] == "comparison"]
        else:
            ids = [cid for cid, claim in catalog.items()
                   if claim["topic"] == topic and claim["kind"] == "group"
                   and set(claim["groups"]) == groups]
    elif wanted:
        if difference_requested:
            return unsupported()
        ids = [cid for cid, claim in catalog.items()
               if claim["topic"] in {"overview", "kpi"} and wanted.intersection(claim["metrics"])]
    else:
        simple = " ".join(re.sub(r"[^a-z ]", " ", q).split())
        if simple in {"tom tat du lieu", "tom tat du lieu dang chon", "tom tat cac kpi", "tong quan du lieu", "summary", "overview"}:
            ids = [cid for cid in ("overview", "distribution", "baseline", "calendar") if cid in catalog]
        elif any(term in q for term in ("chi so nay", "thong so nay", "con no", "what about it")):
            return unsupported()
        else:
            return unsupported()

    ids = [cid for cid in ids if "answer" in catalog[cid]["sections"]]
    covered = {metric for cid in ids for metric in catalog[cid]["metrics"]}
    if not ids or (wanted and not wanted.issubset(covered)):
        return insufficient()
    return policy("deterministic", ("answered",), ids=ids, metrics=wanted, groups=groups,
                  required=required_claim_ids, required_status="answered")


def question_constraints(bundle: Mapping[str, Any], question: str = "") -> dict:
    policy = _question_policy(build_claim_catalog(bundle), question)
    return {
        "mode": policy["mode"],
        "allowed_statuses": policy["allowed_statuses"],
        "allowed_answer_ids": policy["allowed_answer_ids"],
        "required_status": policy["required_status"],
        "required_metric_keys": sorted(policy["metrics"]),
        "required_claim_ids": sorted(policy["required_claim_ids"]),
    }


def response_schema(bundle: Mapping[str, Any], question: str = "") -> dict:
    catalog = build_claim_catalog(bundle)
    policy = _question_policy(catalog, question)
    result = copy.deepcopy(RESPONSE_SCHEMA)
    result["properties"]["snapshot_id"]["enum"] = [bundle.get("snapshot_id")]

    summary = result["properties"]["summary"]
    summary_ids = [cid for cid in ("overview", "distribution", "baseline", "calendar")
                   if cid in catalog and "summary" in catalog[cid]["sections"]]
    if "overview" in summary_ids:
        summary["prefixItems"] = [{"type": "string", "enum": ["overview"]}]
        tail = [cid for cid in summary_ids if cid != "overview"]
        if tail:
            summary["items"]["enum"] = tail
            summary["maxItems"] = min(summary["maxItems"], 1 + len(tail))
        else:
            summary["maxItems"] = 1
    else:
        summary["maxItems"] = 0

    explanations = result["properties"]["explanations"]
    diagnostic_ids = [cid for cid, claim in catalog.items()
                      if "explanations" in claim["sections"]
                      and claim["kind"] in {"comparison", "daily"}]
    if not diagnostic_ids:
        diagnostic_ids = [cid for cid, claim in catalog.items()
                          if "explanations" in claim["sections"]
                          and claim["kind"] == "scope_note"]
    if not diagnostic_ids:
        diagnostic_ids = [cid for cid, claim in catalog.items()
                          if "explanations" in claim["sections"]]
    if diagnostic_ids:
        explanations["items"]["enum"] = diagnostic_ids
        explanations["minItems"] = 1
        explanations["maxItems"] = 1
    else:
        explanations["maxItems"] = 0

    answer = result["properties"]["answer"]
    allowed_ids = list(policy["allowed_answer_ids"])
    required_ids = sorted(policy["required_claim_ids"])
    if policy["required_status"] == "answered":
        covered_metrics = {metric for cid in required_ids for metric in catalog[cid]["metrics"]}
        covered_groups = {group for cid in required_ids for group in catalog[cid]["groups"]}
        missing_metrics = policy["metrics"] - covered_metrics
        missing_groups = policy["groups"] - covered_groups
        candidates = [cid for cid in allowed_ids if cid not in required_ids]
        capacity = RESPONSE_SCHEMA["properties"]["answer"]["maxItems"] - len(required_ids)
        if missing_metrics or missing_groups:
            for size in range(1, min(capacity, len(candidates)) + 1):
                cover = next((combo for combo in combinations(candidates, size)
                              if missing_metrics.issubset({metric for cid in combo
                                                           for metric in catalog[cid]["metrics"]})
                              and missing_groups.issubset({group for cid in combo
                                                          for group in catalog[cid]["groups"]})), None)
                if cover is not None:
                    required_ids.extend(cover)
                    break
    if allowed_ids:
        optional_ids = [cid for cid in allowed_ids if cid not in required_ids]
        if required_ids:
            answer["prefixItems"] = [
                {"type": "string", "enum": [cid]} for cid in required_ids
            ]
            answer["minItems"] = len(required_ids)
            if optional_ids:
                answer["items"]["enum"] = optional_ids
            answer["maxItems"] = min(answer["maxItems"], len(required_ids) + len(optional_ids))
        else:
            answer["items"]["enum"] = allowed_ids
            if policy["required_status"] == "answered":
                answer["minItems"] = 1
            answer["maxItems"] = min(answer["maxItems"], len(allowed_ids))
    else:
        answer["maxItems"] = 0
    result["properties"]["answer_status"]["enum"] = policy["allowed_statuses"]
    return result


def validate_response(payload: Any, bundle: Mapping[str, Any], question: str = "") -> dict:
    """Accept only eligible claim IDs, then render their locally-owned wording."""
    if not isinstance(payload, dict) or set(payload) != set(RESPONSE_SCHEMA["required"]):
        raise GroundingError("Gemini chưa trả đúng cấu trúc lựa chọn nhận xét.")
    if not isinstance(bundle.get("snapshot_id"), str) or payload["snapshot_id"] != bundle["snapshot_id"]:
        raise GroundingError("Kết quả AI không thuộc phạm vi dữ liệu hiện tại.")
    catalog = build_claim_catalog(bundle)
    policy = _question_policy(catalog, question)
    status = payload["answer_status"]
    if not isinstance(status, str) or status not in policy["allowed_statuses"] \
            or (policy["required_status"] is not None and status != policy["required_status"]):
        raise GroundingError("Trạng thái trả lời không khớp phạm vi câu hỏi được hỗ trợ.")
    result = {"snapshot_id": bundle["snapshot_id"]}
    for section, low, high in (("summary", 1, 4), ("explanations", 1, 5), ("answer", 0, 3)):
        ids = payload[section]
        if not isinstance(ids, list) or not low <= len(ids) <= high \
                or any(not isinstance(cid, str) or cid not in catalog for cid in ids):
            raise GroundingError("AI chọn nhận xét không tồn tại hoặc sai số lượng.")
        if len(ids) != len(set(ids)) or any(section not in catalog[cid]["sections"] for cid in ids):
            raise GroundingError("AI chọn trùng nhận xét hoặc dùng sai phần phân tích.")
        if section == "answer" and any(cid not in policy["allowed_answer_ids"] for cid in ids):
            raise GroundingError("Nhận xét được chọn không trả lời đúng phạm vi câu hỏi.")
        result[section] = [{k: copy.deepcopy(c[k]) for k in ("text", "template", "evidence_ids", "kind", "topic")}
                           | {"claim_id": cid} for cid in ids for c in (catalog[cid],)]
    if "overview" not in payload["summary"]:
        raise GroundingError("Tóm tắt thiếu tổng quan của phạm vi dữ liệu.")
    comparative = {cid for cid, c in catalog.items() if c["kind"] in {"comparison", "daily"}}
    if comparative and not comparative.intersection(payload["explanations"]):
        raise GroundingError("Phần giải thích chưa chọn khác biệt hoặc biến động đã tính.")
    if status == "answered":
        if not payload["answer"]:
            raise GroundingError("Câu hỏi có chứng cứ nhưng kết quả chưa chọn nhận xét trả lời.")
        covered_metrics = {m for cid in payload["answer"] for m in catalog[cid]["metrics"]}
        covered_groups = {g for cid in payload["answer"] for g in catalog[cid]["groups"]}
        if not policy["metrics"].issubset(covered_metrics) or not policy["groups"].issubset(covered_groups) \
                or not policy["required_claim_ids"].issubset(payload["answer"]):
            raise GroundingError("Câu trả lời chưa đủ chỉ số hoặc nhóm được hỏi.")
    elif payload["answer"]:
        raise GroundingError("Không được tạo câu trả lời khi câu hỏi chưa có chứng cứ phù hợp.")
    result.update(answer_status=status, validation="claim_catalog_v2", narrative_version=NARRATIVE_VERSION)
    return result
