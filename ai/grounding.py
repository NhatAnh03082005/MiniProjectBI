"""Validate citations and fill quantitative placeholders from calculated facts.

This is a numeric/citation guard, not a proof that arbitrary natural language
is semantically correct. The UI retains the cited evidence for human review.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Mapping
from typing import Any

STATEMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string", "description": "Vietnamese prose. Every numeric value must use an exact {{F001}} evidence placeholder."},
        "evidence_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 10},
    },
    "required": ["text", "evidence_ids"],
    "additionalProperties": False,
}
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "array", "items": STATEMENT_SCHEMA, "minItems": 1, "maxItems": 4},
        "explanations": {"type": "array", "items": STATEMENT_SCHEMA, "minItems": 1, "maxItems": 5},
        "answer": {"type": "array", "items": STATEMENT_SCHEMA, "maxItems": 3},
        "answer_status": {"type": "string", "enum": ["not_requested", "answered", "insufficient_data"]},
    },
    "required": ["summary", "explanations", "answer", "answer_status"],
    "additionalProperties": False,
}
TOKEN = re.compile(r"\{\{(F[0-9]{3,5})\}\}")
FACT_ID = re.compile(r"F[0-9]{3,5}\Z")
DISPLAY_UNITS = frozenset({"ngày", "bản ghi", "phút", "km", "%", "điểm", "bản ghi/ngày"})


class GroundingError(ValueError):
    """The response cannot be shown as an evidence-backed AI result."""


def _normal(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Cf")


def _check_policy(text: str) -> None:
    normalized = _normal(text).casefold()
    # These are direct claims the available observational data cannot support.
    # The system prompt also disallows more subtle unsupported interpretations.
    bad_claims = (
        r"giao\s+trễ", r"giao\s+đúng\s+hạn", r"late\s+(?:rate|deliver)",
        r"on[- ]time\s+(?:rate|deliver)", r"nguyên\s+nhân\s+(?:là|chính)",
        r"gây\s+ra", r"dẫn\s+đến", r"caused?\s+by", r"\bcauses?\b",
        r"will\s+(?:increase|decrease|rise|fall)",
        r"(?:dự\s+báo|dự\s+đoán)\s+(?:rằng|sẽ|tháng|quý|năm|ngày)",
    )
    if any(re.search(pattern, normalized) for pattern in bad_claims):
        raise GroundingError("Nhận xét chứa kết luận vượt phạm vi dữ liệu; hãy tạo lại hoặc đối chiếu chứng cứ.")
    if re.search(r"https?://|www\.|javascript:|<[^>]*>|!\[|\]\(", normalized):
        raise GroundingError("Kết quả AI chứa liên kết hoặc nội dung định dạng không được hỗ trợ.")


def _fact_map(bundle: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = bundle.get("facts")
    if not isinstance(rows, list):
        raise GroundingError("Thiếu danh sách số liệu để kiểm chứng.")
    facts: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise GroundingError("Định dạng chứng cứ không hợp lệ.")
        fid = row.get("id")
        if not isinstance(fid, str) or not FACT_ID.fullmatch(fid) or fid in facts:
            raise GroundingError("Mã chứng cứ thiếu, trùng hoặc không hợp lệ.")
        if not isinstance(row.get("display"), str) or len(row["display"]) > 500:
            raise GroundingError("Chứng cứ chưa có giá trị hiển thị hợp lệ.")
        value = row.get("value")
        if isinstance(value, float) and not math.isfinite(value):
            raise GroundingError("Chứng cứ chứa số không hữu hạn.")
        facts[fid] = row
    return facts


def _render(text: str, facts: Mapping[str, dict[str, Any]]) -> str:
    """Fill known values, removing only an adjacent duplicate of their unit."""
    pieces: list[str] = []
    cursor = 0
    for match in TOKEN.finditer(text):
        fact = facts[match.group(1)]
        display, unit = fact["display"], fact.get("unit")
        pieces.extend((text[cursor:match.start()], display))
        cursor = match.end()
        if not isinstance(unit, str) or unit not in DISPLAY_UNITS \
                or not display.endswith("%" if unit == "%" else " " + unit):
            continue
        # Word units require separation; percentages may directly follow the
        # token. Do not consume a prefix of another unit, such as bản ghi/ngày
        # after a fact measured in bản ghi, including a spaced slash.
        separator = r"[ \t]*" if unit == "%" else r"[ \t]+"
        duplicate = re.match(separator + re.escape(unit) + r"(?![\w/]|[ \t]*/)", text[cursor:])
        if duplicate:
            cursor += duplicate.end()
    pieces.append(text[cursor:])
    return "".join(pieces).strip()


def _statement(raw: Any, facts: Mapping[str, dict[str, Any]], allowed_terms: list[str]) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {"text", "evidence_ids"}:
        raise GroundingError("Mỗi nhận xét cần có nội dung và mã chứng cứ.")
    text, refs = raw["text"], raw["evidence_ids"]
    if not isinstance(text, str) or not 8 <= len(text.strip()) <= 1200:
        raise GroundingError("Độ dài nhận xét AI không hợp lệ.")
    if not isinstance(refs, list) or not 1 <= len(refs) <= 10:
        raise GroundingError("Mỗi nhận xét cần dẫn các chứng cứ tương ứng.")
    if any(not isinstance(r, str) or r not in facts for r in refs):
        raise GroundingError("AI dẫn một mã chứng cứ không có trong phạm vi đã chọn.")
    if any(facts[r].get("value") is None for r in refs):
        raise GroundingError("AI dẫn một chứng cứ chưa có giá trị; hãy tạo lại hoặc kiểm tra phạm vi dữ liệu.")
    if len(refs) != len(set(refs)):
        raise GroundingError("AI dẫn trùng mã chứng cứ.")
    tokens = TOKEN.findall(text)
    if any(token not in facts or facts[token].get("value") is None for token in tokens):
        raise GroundingError("AI đang dùng giá trị thiếu hoặc không có trong dữ liệu.")
    # The numeric placeholders are already exact evidence IDs. Derive missing
    # citations from them instead of trusting a redundant list copied by the
    # model. Unknown IDs and null values above remain hard errors.
    refs = list(dict.fromkeys([*refs, *tokens]))
    if len(refs) > 10:
        raise GroundingError("Nhận xét dẫn quá nhiều chứng cứ; hãy tạo lại thành các ý ngắn hơn.")
    remainder = TOKEN.sub("", text)
    if any(c in remainder for c in "{}"):
        raise GroundingError("Kết quả chứa mã thay thế không hợp lệ.")
    # Metric names and actual category labels are allowed; numbers in prose
    # themselves must be rendered from a known fact, never copied by the LLM.
    remainder = _normal(remainder)
    for term in sorted(set(["P90", "P95", *allowed_terms]), key=len, reverse=True):
        if term and any(ch.isdigit() for ch in term):
            remainder = re.sub(re.escape(_normal(term)), "", remainder, flags=re.I)
    if any(ch.isnumeric() for ch in remainder):
        raise GroundingError("AI tự ghi số ngoài chứng cứ; hãy tạo lại để đối chiếu được từng giá trị.")
    _check_policy(text)

    rendered = _render(text, facts)
    # Keep raw templates too: downloaded results can be recomputed and audited.
    return {"text": rendered, "template": text, "evidence_ids": list(refs)}


def validate_response(payload: Any, bundle: Mapping[str, Any], question: str = "") -> dict[str, Any]:
    """Reject schema/number/citation violations before any AI text is displayed."""
    required = {"summary", "explanations", "answer", "answer_status"}
    if not isinstance(payload, dict) or set(payload) != required:
        raise GroundingError("Gemini chưa trả đủ các phần tóm tắt, giải thích và trạng thái câu hỏi.")
    facts = _fact_map(bundle)
    terms = bundle.get("allowed_terms", [])
    if not isinstance(terms, list) or any(not isinstance(t, str) for t in terms):
        raise GroundingError("Nhãn nhóm trong chứng cứ không hợp lệ.")
    result: dict[str, Any] = {"snapshot_id": bundle.get("snapshot_id")}
    for section, low, high in [("summary", 1, 4), ("explanations", 1, 5), ("answer", 0, 3)]:
        rows = payload[section]
        if not isinstance(rows, list) or not low <= len(rows) <= high:
            raise GroundingError("Số nhận xét Gemini trả về không hợp lệ.")
        result[section] = [_statement(row, facts, terms) for row in rows]
    status = payload["answer_status"]
    if not isinstance(status, str) or status not in {"not_requested", "answered", "insufficient_data"}:
        raise GroundingError("Trạng thái trả lời câu hỏi không hợp lệ.")
    if not question.strip():
        if status != "not_requested" or result["answer"]:
            raise GroundingError("AI trả lời một câu hỏi chưa được yêu cầu.")
    elif status == "not_requested" or (status == "answered") != bool(result["answer"]):
        raise GroundingError("Trạng thái và nội dung trả lời không khớp.")
    result["answer_status"] = status
    result["validation"] = "schema_numbers_evidence_ids_checked"
    return result
