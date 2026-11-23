"""Local, explicit-action UI for evidence-backed delivery analysis."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from typing import Any

import pandas as pd
import streamlit as st

from ai import analytics, credentials, data, gemini as Gemini, grounding
from ai.grounding import GroundingError, validate_response


ORANGE = "#FF9900"
BLUE = "#146EB4"
QUESTION_SUGGESTIONS = (
    "P90 là gì và hiện tại bằng bao nhiêu?",
    "Tổng số giao hàng và thời gian giao trung bình hiện tại là bao nhiêu?",
    "Tóm tắt các KPI trong phạm vi đang chọn.",
    "Mức giao thông nào có thời gian giao trung bình cao nhất và thấp nhất? Chênh lệch đã tính là bao nhiêu?",
    "Phân tích thời tiết trong phạm vi đang chọn.",
    "Ngày nào có mức tăng thời gian giao trung bình lớn nhất?",
    "Khoảng cách giao hàng hợp lệ trung bình là bao nhiêu?",
)
DATA_MODE = "Phân tích dữ liệu"
GENERAL_MODE = "Hỏi Gemini chung"
CSS = """
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
  font-family: 'Segoe UI', Arial, sans-serif; color: #232F3E;
}
[data-testid="stAppViewContainer"] { background: #F4F6F8; }
[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E2E7ED; }
.block-container { padding-top: 2rem; padding-bottom: 2.5rem; max-width: 1500px; }
h1 { font-size: 2rem !important; letter-spacing: -.025em; }
h2 { font-size: 1.35rem !important; }
h3 { font-size: 1.08rem !important; }
[data-testid="stMetric"] {
  background: white; border: 1px solid #E2E7ED; border-top: 3px solid #FF9900;
  border-radius: 10px; padding: 12px 14px; min-height: 108px;
}
[data-testid="stMetricLabel"] p { font-size: .85rem; white-space: normal; }
[data-testid="stMetricValue"] { font-size: 1.5rem; white-space: normal; }
[data-testid="stMetricValue"] > div {
  white-space: normal; overflow: visible; overflow-wrap: anywhere; text-overflow: clip;
}
[data-testid="stText"] { font-family: 'Segoe UI', Arial, sans-serif; font-size: 1rem; line-height: 1.65; }
button[kind="primary"] { background: #FF9900; color: #232F3E; border-color: #FF9900; }
[data-testid="stForm"] .st-key-ai_question [data-testid="InputInstructions"] { display: none; }
.st-key-ai_request_form .st-key-generate_summary button,
.st-key-ai_request_form .st-key-generate_answer button {
  min-height: 2.75rem;
  transition: background-color 220ms ease, border-color 220ms ease, color 220ms ease,
              box-shadow 220ms ease, opacity 220ms ease;
}
.st-key-ai_request_form .st-key-generate_answer button:not(:disabled) {
  background: #FFFFFF; color: #657180; border-color: #D5DBE3; box-shadow: none; opacity: .72;
}
.st-key-ai_request_form:has(.st-key-ai_question textarea:not(:placeholder-shown))
  .st-key-generate_summary button:not(:disabled) {
  background: #FFFFFF; color: #232F3E; border-color: #D5DBE3; box-shadow: none;
}
.st-key-ai_request_form:has(.st-key-ai_question textarea:not(:placeholder-shown))
  .st-key-generate_answer button:not(:disabled) {
  background: #FF9900; color: #232F3E; border-color: #FF9900;
  box-shadow: 0 4px 12px rgba(255, 153, 0, .22); opacity: 1;
}
.st-key-ai_request_form:has(.st-key-ai_question textarea:not(:placeholder-shown))
  .st-key-generate_answer button:not(:disabled):hover {
  background: #FFAD33; border-color: #FFAD33;
}
[data-testid="stTabs"] { margin-top: 1.2rem; }
.st-key-kpi_grid { container-type: inline-size; container-name: kpis; }
.st-key-kpi_grid [data-testid="stHorizontalBlock"] {
  display: grid !important; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem;
}
.st-key-kpi_grid [data-testid="stColumn"] { width: auto !important; min-width: 0 !important; }
@container kpis (min-width: 1100px) {
  .st-key-kpi_grid [data-testid="stHorizontalBlock"] { grid-template-columns: repeat(6, minmax(0, 1fr)); }
}
@container kpis (max-width: 560px) {
  .st-key-kpi_grid [data-testid="stHorizontalBlock"] { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@container kpis (max-width: 360px) {
  .st-key-kpi_grid [data-testid="stHorizontalBlock"] { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 1100px) {
  .st-key-filter_grid [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
  .st-key-filter_grid [data-testid="stColumn"] {
    flex: 1 1 180px !important; min-width: 180px !important;
  }
  .st-key-filter_grid [data-testid="stColumn"]:first-child {
    flex-basis: 100% !important; min-width: 100% !important;
  }
}
</style>
"""


def _invalidate_ai() -> None:
    if st.session_state.pop("_ai_result", None) is not None:
        st.session_state["_ai_stale"] = True


def _use_question_suggestion() -> None:
    suggestion = st.session_state.get("ai_question_suggestion")
    if suggestion:
        st.session_state["ai_question"] = suggestion
        _invalidate_ai()


def _clear_key() -> None:
    # Keep the key initialized so a later rerun does not immediately reload it
    # from this user's optional Windows credential store.
    st.session_state["gemini_api_key"] = ""
    st.session_state.pop("_model_choices", None)
    st.session_state.pop("model_choice", None)
    st.session_state["gemini_model"] = Gemini.DEFAULT_MODEL
    _invalidate_ai()


def _load_saved_key_once() -> None:
    if "gemini_api_key" in st.session_state:
        return
    try:
        st.session_state["gemini_api_key"] = credentials.load_key() or ""
    except credentials.CredentialStoreError as error:
        st.session_state["gemini_api_key"] = ""
        st.session_state["_credential_notice"] = ("warning", str(error))
    except Exception:
        st.session_state["gemini_api_key"] = ""
        st.session_state["_credential_notice"] = ("warning", "Chưa đọc được key đã lưu; hãy nhập key cho phiên này.")


def _save_key_on_machine() -> None:
    try:
        credentials.save_key(st.session_state.get("gemini_api_key", "").strip())
        st.session_state["_credential_notice"] = (
            "success", "Đã lưu key trong Windows Credential Manager của tài khoản hiện tại.")
    except credentials.CredentialStoreError as error:
        st.session_state["_credential_notice"] = ("error", str(error))
    except Exception:
        st.session_state["_credential_notice"] = ("error", "Chưa lưu được key; key vẫn dùng được trong phiên này.")


def _delete_saved_key() -> None:
    try:
        credentials.delete_key()
        _clear_key()
        st.session_state["_credential_notice"] = ("success", "Đã xóa key lưu trên máy và key của phiên hiện tại.")
    except credentials.CredentialStoreError as error:
        st.session_state["_credential_notice"] = ("error", str(error))
    except Exception:
        st.session_state["_credential_notice"] = ("error", "Chưa xóa được key đã lưu trên máy.")


def _key_changed() -> None:
    st.session_state.pop("_model_choices", None)
    st.session_state.pop("model_choice", None)
    _invalidate_ai()


def _use_listed_model() -> None:
    chosen = st.session_state.get("model_choice")
    if chosen:
        st.session_state["gemini_model"] = chosen
        _invalidate_ai()


def _clear_data() -> None:
    for key in ("_warehouse_frame", "_source_meta", "_loaded_connection", "_bundle", "_bundle_signature"):
        st.session_state.pop(key, None)
    for key in list(st.session_state):
        if key.startswith("filter_"):
            st.session_state.pop(key, None)
    _invalidate_ai()


def _connection_signature(server: str, database: str, driver: str, trust: bool) -> tuple:
    return server.strip(), database.strip(), driver.strip(), bool(trust)


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _fmt(value: Any, decimals: int = 0, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "—"
    rendered = f"{float(value):,.{decimals}f}".translate(str.maketrans(",.", ".,"))
    return rendered + suffix


def _local_time(value: Any) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone(timedelta(hours=7))).strftime("%d/%m/%Y %H:%M (UTC+7)")
    except (ValueError, TypeError):
        return "chưa xác định"


def _sidebar() -> tuple:
    with st.sidebar:
        st.header("Amazon Delivery BI")
        st.caption("Dữ liệu đã kiểm tra · Phân tích có đối chiếu")
        with st.expander("Kết nối dữ liệu", expanded=True):
            server = st.text_input("SQL Server", value=os.environ.get("MSSQL_SERVER", r"localhost\SQLEXPRESS"),
                                   key="database_server", on_change=_invalidate_ai)
            database = st.text_input("Database", value="AmazonDeliveryBI", key="database_name", on_change=_invalidate_ai)
            driver = st.text_input("ODBC Driver", value="ODBC Driver 18 for SQL Server", key="database_driver",
                                   on_change=_invalidate_ai)
            trust = st.checkbox("Tin cậy chứng chỉ SQL Server cục bộ", value=True, key="database_trust",
                                on_change=_invalidate_ai)
            st.caption("Dùng tài khoản Windows đang đăng nhập.")
            connection = _connection_signature(server, database, driver, trust)
            if st.button("Kết nối và tải dữ liệu", key="load_data", width="stretch", disabled=not all(connection[:3])):
                _clear_data()
                try:
                    config = data.DatabaseConfig(server=connection[0], database=connection[1],
                                                 driver=connection[2], trust_certificate=connection[3])
                    with st.spinner("Đang tải dữ liệu giao hàng…"):
                        frame, source = data.load_warehouse(config)
                    st.session_state["_warehouse_frame"] = frame
                    st.session_state["_source_meta"] = source
                    st.session_state["_loaded_connection"] = connection
                    st.session_state["_data_version"] = st.session_state.get("_data_version", 0) + 1
                except data.WarehouseError as error:
                    st.error(str(error))
                except Exception:
                    st.error("Chưa tải được dữ liệu. Kiểm tra tên SQL Server, database, ODBC Driver và quyền tài khoản Windows rồi thử lại.")

        st.subheader("Gemini")
        _load_saved_key_once()
        st.text_input("Gemini API key", type="password", key="gemini_api_key", on_change=_key_changed,
                      help="Key được che trên giao diện. Chỉ ghi nhớ trên máy khi bấm nút lưu; không ghi vào source hoặc file tải xuống.")
        if "gemini_model" not in st.session_state:
            st.session_state["gemini_model"] = Gemini.DEFAULT_MODEL
        st.text_input("Mô hình Gemini", key="gemini_model", on_change=_invalidate_ai)
        key = st.session_state.get("gemini_api_key", "").strip()
        if st.button("Xem mô hình khả dụng", key="list_models", width="stretch", disabled=not key):
            try:
                with st.spinner("Đang lấy danh sách mô hình…"):
                    st.session_state["_model_choices"] = list(Gemini.list_models(api_key=key))
                st.session_state.pop("model_choice", None)
            except Gemini.GeminiError as error:
                st.error(str(error))
            except Exception:
                st.error("Chưa lấy được danh sách mô hình. Kiểm tra khóa và kết nối Internet rồi thử lại.")
        choices = st.session_state.get("_model_choices", [])
        if choices:
            st.selectbox("Chọn từ danh sách", choices, index=None, placeholder="Chọn để điền tên mô hình",
                         key="model_choice", on_change=_use_listed_model)
        st.button("Xóa khóa phiên", key="clear_key", width="stretch", on_click=_clear_key)
        store_supported = credentials.is_supported()
        st.button("Lưu key trên máy", key="save_key", width="stretch", on_click=_save_key_on_machine,
                  disabled=not (store_supported and key))
        st.button("Xóa key đã lưu", key="delete_saved_key", width="stretch", on_click=_delete_saved_key,
                  disabled=not store_supported,
                  help="Xóa key khỏi Windows Credential Manager và xóa key của phiên hiện tại.")
        st.caption("Lưu key là tùy chọn, chỉ áp dụng cho tài khoản Windows trên máy này. “Xóa khóa phiên” vẫn giữ key đã lưu trên máy.")
        if not store_supported:
            st.caption("Máy này không hỗ trợ Windows Credential Manager; vẫn có thể dùng key trong phiên.")
        notice = st.session_state.pop("_credential_notice", None)
        if notice:
            getattr(st, notice[0])(notice[1])
        st.caption("Mỗi lần bấm tạo phân tích có thể gọi Gemini tối đa 3 lần khi cần thử lại. Chi phí và hạn mức tùy tài khoản, mô hình đang dùng.")
    return connection


def _options(frame: pd.DataFrame, column: str) -> list[str]:
    if column not in frame:
        return []
    return sorted({str(value) for value in frame[column].dropna() if str(value).strip()}, key=str.casefold)


def _filters(frame: pd.DataFrame) -> analytics.FilterContext | None:
    st.subheader("Phạm vi phân tích")
    st.caption("Để trống lựa chọn để xem tất cả. Bộ lọc này độc lập với Power BI; chọn cùng phạm vi và bỏ lựa chọn trên biểu đồ trước khi đối chiếu.")
    values = pd.to_datetime(frame["full_date"], errors="coerce").dropna()
    if values.empty:
        st.info("Không có ngày hợp lệ để phân tích.")
        return None
    first, last = values.min().date(), values.max().date()
    selected_values = {}
    with st.container(key="filter_grid"):
        columns = st.columns([1.3, 1, 1, 1])
        with columns[0]:
            selected = st.date_input("Khoảng ngày", value=(first, last), min_value=first, max_value=last,
                                     key="filter_range", on_change=_invalidate_ai, format="DD/MM/YYYY")
        for container, label, column, name in zip(columns[1:], ("Phương tiện", "Danh mục", "Khu vực"),
                                                 ("vehicle_type", "category_name", "area_name"),
                                                 ("vehicles", "categories", "areas")):
            with container:
                selected_values[name] = tuple(st.multiselect(label, _options(frame, column), placeholder="Tất cả",
                                                             key="filter_" + name, on_change=_invalidate_ai))
    with st.expander("Bộ lọc bổ sung", expanded=False):
        columns = st.columns(3)
        for container, label, column, name in zip(columns, ("Giao thông", "Thời tiết", "Khung giờ"),
                                                 ("traffic_level", "weather_name", "time_period"),
                                                 ("traffic", "weather", "time_periods")):
            with container:
                selected_values[name] = tuple(st.multiselect(label, _options(frame, column), placeholder="Tất cả",
                                                             key="filter_" + name, on_change=_invalidate_ai))
        days = [day.date().isoformat() for day in pd.date_range(first, last)]
        exact_days = tuple(st.multiselect("Chọn ngày riêng lẻ khi đối chiếu Power BI", days,
                                          format_func=lambda day: date.fromisoformat(day).strftime("%d/%m/%Y"),
                                          key="filter_dates", on_change=_invalidate_ai,
                                          help="Khi chọn ngày riêng lẻ, khoảng ngày phía trên không áp dụng."))
    if exact_days:
        st.caption("Phạm vi ngày đang dùng là các ngày được chọn riêng lẻ.")
        return analytics.FilterContext(dates=exact_days, **selected_values)
    if isinstance(selected, date):
        selected = (selected, selected)
    if len(selected) == 1:
        st.info("Chọn thêm ngày kết thúc để hoàn tất khoảng ngày.")
        return None
    start, end = selected if len(selected) == 2 else (None, None)
    return analytics.FilterContext(start_date=start, end_date=end, **selected_values)


def _metrics(bundle: dict) -> None:
    values = bundle.get("kpis", {})
    share = values.get("share_above_baseline")
    cards = (
        ("Số bản ghi", _fmt(values.get("total_records"))),
        ("Thời gian trung bình", _fmt(values.get("average_minutes"), 2, " phút")),
        ("Trung vị", _fmt(values.get("median_minutes"), 0, " phút")),
        ("P90 thời gian giao", _fmt(values.get("p90_minutes"), 0, " phút")),
        ("Tỷ lệ vượt mốc 195 phút", _fmt(None if share is None else share * 100, 2, "%")),
        ("Bản ghi / ngày có dữ liệu", _fmt(values.get("records_per_active_day"), 2)),
    )
    with st.container(key="kpi_grid"):
        for column, (label, value) in zip(st.columns(6), cards):
            column.metric(label, value)
    st.caption("P90 được tính lại trong phạm vi đang chọn. Mốc 195 phút là tham chiếu thống kê cố định, không phải cam kết giao hàng.")


def _facts_frame(bundle: dict, ids: list[str] | None = None) -> pd.DataFrame:
    rows = []
    for fact in bundle.get("facts", []):
        if ids is not None and fact.get("id") not in ids:
            continue
        source = fact.get("source", "")
        rows.append({"Mã": fact.get("id"), "Chỉ số": fact.get("label", ""),
                     "Giá trị": fact.get("display", "—"), "Cỡ mẫu": fact.get("n"),
                     "Nguồn": source if isinstance(source, str) else json.dumps(source, ensure_ascii=False),
                     "Ngữ cảnh": json.dumps(fact["context"], ensure_ascii=False, sort_keys=True)
                     if fact.get("context") else ""})
    return pd.DataFrame(rows, columns=["Mã", "Chỉ số", "Giá trị", "Cỡ mẫu", "Nguồn", "Ngữ cảnh"])


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False, default=str).encode("utf-8")


def _show_statements(title: str, statements: list[dict], bundle: dict) -> None:
    if not statements:
        return
    st.subheader(title)
    for number, statement in enumerate(statements, 1):
        # Only validated catalog text is rendered, always as plain text.
        st.text(statement["text"])
        ids = statement.get("evidence_ids", [])
        with st.expander("Số liệu cho nhận xét " + str(number) + " · " + ", ".join(ids)):
            st.dataframe(_facts_frame(bundle, ids), hide_index=True, width="stretch")


def _generate(bundle: dict, context: str, question: str = "") -> None:
    _invalidate_ai()
    # A failed explicit retry is an API failure, not a change of filter context.
    st.session_state["_ai_stale"] = False
    progress = st.empty()

    def show_retry(next_attempt: int, max_attempts: int, safe_reason: str) -> None:
        # Do not render upstream error bodies or arbitrary callback text.
        if type(next_attempt) is int and type(max_attempts) is int and 1 < next_attempt <= max_attempts <= 3:
            progress.info(f"Gemini chưa trả về kết quả hợp lệ. Đang thử lại lần {next_attempt}/{max_attempts}…")

    try:
        with st.spinner("Gemini đang đọc các số liệu đã tính…"):
            response = Gemini.generate(api_key=st.session_state["gemini_api_key"].strip(),
                                       model=st.session_state["gemini_model"].strip(), bundle=bundle,
                                       question=question, on_retry=show_retry)
            validated = validate_response(response.payload, bundle, question=question)
        if type(response.attempts) is not int or not 1 <= response.attempts <= 3:
            raise GroundingError("Số lần gọi Gemini không hợp lệ; hãy tạo lại phân tích.")
        st.session_state["_ai_result"] = {
            "mode": "data", "snapshot_id": bundle["snapshot_id"], "context": context, "question": question,
            "validated": validated, "model": response.model, "model_version": response.model_version,
            "response_id": response.response_id, "usage": response.usage, "attempts": response.attempts,
            "usage_scope": getattr(response, "usage_scope", "final_attempt_only"),
            "validation": validated["validation"], "narrative_version": grounding.NARRATIVE_VERSION,
        }
        if response.attempts > 1:
            progress.success(f"Đã nhận phản hồi Gemini sau {response.attempts} lần gọi.")
        else:
            progress.empty()
    except (GroundingError, Gemini.GeminiError) as error:
        progress.empty()
        st.error(str(error))
    except Exception:
        progress.empty()
        st.error("Chưa tạo được phân tích. Kiểm tra khóa Gemini, mô hình, kết nối Internet hoặc hạn mức rồi thử lại.")


def _generate_general(context: str, question: str) -> None:
    _invalidate_ai()
    st.session_state["_ai_stale"] = False
    progress = st.empty()

    def show_retry(next_attempt: int, max_attempts: int, safe_reason: str) -> None:
        if type(next_attempt) is int and type(max_attempts) is int and 1 < next_attempt <= max_attempts <= 3:
            progress.info(f"Gemini chưa trả về câu trả lời hợp lệ. Đang thử lại lần {next_attempt}/{max_attempts}…")

    try:
        with st.spinner("Gemini đang trả lời…"):
            response = Gemini.generate_general(
                api_key=st.session_state["gemini_api_key"].strip(),
                model=st.session_state["gemini_model"].strip(),
                question=question,
                on_retry=show_retry,
            )
        answer = response.payload.get("answer") if isinstance(response.payload, dict) else None
        if set(response.payload) != {"answer"} or not isinstance(answer, str) \
                or not answer.strip() or len(answer) > 12000:
            raise Gemini.GeminiError("Gemini chưa trả về câu trả lời chung hợp lệ.")
        if type(response.attempts) is not int or not 1 <= response.attempts <= 3:
            raise Gemini.GeminiError("Số lần gọi Gemini không hợp lệ; hãy thử lại.")
        st.session_state["_ai_result"] = {
            "mode": "general", "snapshot_id": None, "context": context, "question": question,
            "answer": answer.strip(), "model": response.model,
            "model_version": response.model_version, "response_id": response.response_id,
            "usage": response.usage, "attempts": response.attempts,
            "usage_scope": getattr(response, "usage_scope", "final_attempt_only"),
            "validation": "general_text_v1",
        }
        if response.attempts > 1:
            progress.success(f"Đã nhận phản hồi Gemini sau {response.attempts} lần gọi.")
        else:
            progress.empty()
    except Gemini.GeminiError as error:
        progress.empty()
        st.error(str(error))
    except Exception:
        progress.empty()
        st.error("Chưa nhận được câu trả lời. Kiểm tra khóa Gemini, mô hình, kết nối Internet hoặc hạn mức rồi thử lại.")


def _ai_tab(bundle: dict | None, context: str) -> None:
    if "ai_question" not in st.session_state:
        st.session_state["ai_question"] = ""
    mode = st.radio(
        "Chế độ trả lời", (DATA_MODE, GENERAL_MODE), horizontal=True,
        key="ai_answer_mode", on_change=_invalidate_ai,
    )
    data_mode = mode == DATA_MODE
    if data_mode:
        with st.expander("Gợi ý câu hỏi và phạm vi hỗ trợ", expanded=False):
            st.markdown(
                "**Bạn không cần nhớ câu lệnh cố định.** Hãy viết câu hỏi như khi trao đổi với một người phân tích dữ liệu."
            )
            st.selectbox(
                "Câu hỏi gợi ý",
                QUESTION_SUGGESTIONS,
                index=None,
                placeholder="Chọn một câu hỏi mẫu",
                key="ai_question_suggestion",
                on_change=_use_question_suggestion,
            )
            st.caption(
                "Có thể hỏi về tổng quan; ý nghĩa hoặc giá trị KPI; xu hướng theo ngày; nhóm cao nhất, thấp nhất "
                "hoặc hai nhóm cụ thể theo giao thông, thời tiết, phương tiện, khu vực, danh mục, khung giờ và "
                "khoảng cách. Muốn đổi ngày hoặc phạm vi, hãy dùng bộ lọc trước rồi đặt câu hỏi. Ứng dụng không "
                "dự báo tài chính, suy luận nguyên nhân, tạo SQL hay liệt kê từng đơn hàng."
            )
    else:
        st.caption(
            "Chế độ này trả lời kiến thức chung bằng Gemini. Câu trả lời không dùng dữ liệu DDS, "
            "không đại diện cho dashboard và không có số liệu đối chiếu."
        )
    key_ready = bool(st.session_state.get("gemini_api_key", "").strip())
    model_ready = bool(st.session_state.get("gemini_model", "").strip())
    data_ready = bundle is not None and (bundle.get("kpis", {}).get("total_records") or 0) > 0
    common_ready = key_ready and model_ready
    summary_ready = common_ready and data_ready and data_mode
    answer_ready = common_ready and (data_ready if data_mode else True)
    with st.form("ai_request_form", clear_on_submit=False, enter_to_submit=False, border=False):
        question = st.text_area(
            "Câu hỏi về dữ liệu đang chọn (không bắt buộc)" if data_mode else "Câu hỏi cho Gemini",
            key="ai_question", height=90,
            placeholder=("Ví dụ: P90 là gì và hiện tại bằng bao nhiêu?" if data_mode
                         else "Bạn có thể hỏi một câu hỏi kiến thức chung…"),
        )
        st.caption(
            ("Bạn có thể hỏi bằng tiếng Việt tự nhiên; lỗi gõ rõ nghĩa cũng được nhận diện mà không cần khớp câu mẫu. "
             "Kết quả luôn dùng phạm vi đang chọn và ứng dụng sẽ nói rõ khi dữ liệu chưa đủ hoặc câu hỏi nằm ngoài "
             "thông tin hiện có. " if data_mode else
             "Gemini trả lời tự do nhưng không nhận dữ liệu dashboard trong chế độ này. ")
            + "Không nhập mật khẩu hay API key vào ô này."
        )
        left, right = st.columns(2)
        with left:
            summarize = st.form_submit_button(
                "Tạo tóm tắt và phân tích", key="generate_summary",
                type="primary", width="stretch", disabled=not summary_ready,
            )
        with right:
            ask = st.form_submit_button(
                "Giải thích câu hỏi", key="generate_answer",
                type="secondary", width="stretch", disabled=not answer_ready,
            )
    if summarize and summary_ready and bundle is not None:
        _generate(bundle, context)
    elif ask and answer_ready:
        submitted_question = question.strip()
        if submitted_question:
            if data_mode and bundle is not None:
                _generate(bundle, context, submitted_question)
            else:
                _generate_general(context, submitted_question)
        else:
            st.info("Nhập câu hỏi trước khi yêu cầu giải thích.")
    if data_mode and not data_ready:
        st.info("Kết nối dữ liệu và chọn phạm vi có bản ghi để tạo phân tích.")
    elif not key_ready:
        st.info("Nhập Gemini API key ở thanh bên để sử dụng chức năng AI.")
    elif st.session_state.get("_ai_stale"):
        st.info("Câu hỏi, phạm vi hoặc thiết lập đã thay đổi. Hãy tạo lại phân tích cho lựa chọn hiện tại.")
    saved = st.session_state.get("_ai_result")
    if saved is None or saved["context"] != context:
        return
    if saved.get("mode", "data") == "general":
        st.subheader("Câu hỏi đã gửi")
        st.text(saved["question"])
        st.subheader("Trả lời của Gemini")
        st.write(saved["answer"])
        st.caption("Câu trả lời kiến thức chung này không dựa trên DDS hoặc dashboard và không có số liệu đối chiếu.")
        export = {key: value for key, value in saved.items() if key != "context"}
        with st.expander("Thông tin kết quả và tải xuống"):
            st.write("Mô hình:", saved.get("model_version") or saved.get("model"))
            st.write("Số lần gọi Gemini:", saved["attempts"])
            st.download_button("Tải câu trả lời Gemini (JSON)", _json_bytes(export),
                               file_name="gemini_general_answer.json", mime="application/json",
                               key="download_ai_general")
        return
    if bundle is None or saved["snapshot_id"] != bundle["snapshot_id"]:
        return
    result = saved["validated"]
    if saved.get("question"):
        st.subheader("Câu hỏi đã gửi")
        st.text(saved["question"])
        if result.get("answer_status") == "unsupported_question":
            st.info(
                "Câu hỏi này nằm ngoài phạm vi dữ liệu hoặc phép tính hiện có. Hãy nêu rõ KPI, hỏi xu hướng "
                "theo ngày, hoặc nêu chiều phân tích và nhóm cần so sánh. Nếu muốn đổi ngày, khu vực hay danh "
                "mục, hãy chọn bộ lọc trước; bạn cũng có thể dùng một câu gợi ý phía trên."
            )
        elif result.get("answer_status") == "insufficient_data":
            st.info(
                "Câu hỏi phù hợp, nhưng phạm vi đang chọn chưa có đủ dữ liệu để trả lời. "
                "Hãy nới bộ lọc hoặc chọn phạm vi khác."
            )
        _show_statements("Trả lời câu hỏi", result.get("answer", []), bundle)
    else:
        st.caption("Gemini lựa chọn và sắp xếp các nhận xét trong danh mục đã tính. Ứng dụng dựng câu và điền số từ chứng cứ; hãy mở dẫn chứng để đối chiếu.")
        _show_statements("Tóm tắt KPI", result.get("summary", []), bundle)
        _show_statements("Xu hướng và khác biệt cần chú ý", result.get("explanations", []), bundle)
    export = {key: value for key, value in saved.items() if key != "context"}
    with st.expander("Thông tin kết quả và tải xuống"):
        st.write("Mô hình:", saved.get("model_version") or saved.get("model"))
        st.write("Mã phạm vi dữ liệu:", saved["snapshot_id"])
        st.write("Số lần gọi Gemini:", saved["attempts"])
        st.download_button("Tải kết quả AI (JSON)", _json_bytes(export),
                           file_name="amazon_delivery_ai_" + bundle["snapshot_id"][:12] + ".json",
                           mime="application/json", key="download_ai")


def _evidence_tab(bundle: dict | None) -> None:
    if bundle is None:
        st.info("Sau khi tải dữ liệu, các KPI và bảng đối chiếu sẽ hiển thị tại đây.")
        return
    st.subheader("Số liệu dùng để tạo phân tích")
    st.caption("Giá trị được tính trước khi gọi Gemini. Mã chỉ số giúp đối chiếu từng nhận xét với cùng phạm vi dữ liệu.")
    st.dataframe(_facts_frame(bundle), hide_index=True, width="stretch")
    tables = bundle.get("tables", {})
    with st.expander("Theo ngày và theo nhóm", expanded=False):
        daily = pd.DataFrame(tables.get("daily", []))
        if not daily.empty and "date" in daily:
            count_column, average_column = st.columns(2)
            with count_column:
                st.write("Số bản ghi theo ngày")
                st.line_chart(daily, x="date", y="total_records", color=BLUE, height=230)
            with average_column:
                st.write("Thời gian giao trung bình theo ngày (phút)")
                if "average_minutes" in daily and pd.to_numeric(daily["average_minutes"], errors="coerce").notna().any():
                    st.line_chart(daily, x="date", y="average_minutes", color=ORANGE, height=230)
                else:
                    st.info("Chưa có giá trị thời gian trung bình trong phạm vi này.")
            daily_columns = [name for name in ("date", "n", "average_minutes") if name in daily]
            st.dataframe(daily[daily_columns].rename(columns={"date": "Ngày", "n": "Số bản ghi",
                                                              "average_minutes": "Trung bình (phút)"}),
                         hide_index=True, width="stretch")
        groups = {"Giao thông": "traffic", "Thời tiết": "weather", "Phương tiện": "vehicle",
                  "Khu vực": "area", "Danh mục": "category", "Khung giờ": "time_period",
                  "Nhóm khoảng cách": "distance_band", "Ngày × khung giờ": "day_period"}
        choice = st.selectbox("Bảng so sánh", list(groups), key="evidence_group")
        group = pd.DataFrame(tables.get(groups[choice], []))
        if not group.empty:
            day_period = groups[choice] == "day_period"
            if day_period:
                ordered = group.sort_values("day_of_week_number")
                days = ordered["day_name"].drop_duplicates().tolist()
                observed_periods = set(group["time_period"])
                preferred = ("Morning", "Afternoon", "Evening", "Night", "Unknown")
                periods = [p for p in preferred if p in observed_periods]
                periods += sorted(observed_periods.difference(preferred))
                means = group.pivot(index="day_name", columns="time_period", values="average_minutes").reindex(index=days, columns=periods)
                counts = group.pivot(index="day_name", columns="time_period", values="valid_time_count").reindex(index=days, columns=periods)
                mean_tab, count_tab = st.tabs(["Trung bình (phút)", "Cỡ mẫu thời lượng"])
                with mean_tab:
                    st.dataframe(means.rename_axis(index="Ngày", columns="Khung giờ").round(2), width="stretch")
                with count_tab:
                    st.dataframe(counts.rename_axis(index="Ngày", columns="Khung giờ").astype("Int64"), width="stretch")
                st.caption("Mỗi ô là một ngày trong tuần × khung giờ. Đọc thời gian trung bình cùng cỡ mẫu thời lượng hợp lệ; ô trống không có giá trị để so sánh.")
            elif {"label", "average_minutes"}.issubset(group.columns):
                # Explicit Vega-Lite fields avoid Streamlit-version differences
                # in how horizontal st.bar_chart swaps axis labels.
                st.vega_lite_chart(
                    group,
                    {
                        "mark": {"type": "bar", "color": BLUE},
                        "encoding": {
                            "x": {"field": "average_minutes", "type": "quantitative",
                                  "title": "Thời gian trung bình (phút)"},
                            "y": {"field": "label", "type": "nominal", "title": "Nhóm", "sort": "-x"},
                            "tooltip": [
                                {"field": "label", "type": "nominal", "title": "Nhóm"},
                                {"field": "average_minutes", "type": "quantitative",
                                 "title": "Trung bình (phút)", "format": ".2f"},
                            ],
                        },
                        "height": 300,
                    },
                    width="stretch",
                )
            display = group.drop(columns="label") if day_period else group.copy()
            if "share_above_baseline" in display:
                display["share_above_baseline"] = display["share_above_baseline"].map(
                    lambda value: _fmt(None if pd.isna(value) else value * 100, 2, "%"))
            display = display.rename(columns={"label": "Nhóm", "n": "Số bản ghi", "average_minutes": "Trung bình (phút)",
                                              "median_minutes": "Trung vị (phút)", "p90_minutes": "P90 (phút)",
                                              "share_above_baseline": "Tỷ lệ vượt mốc", "small_n": "Mẫu nhỏ",
                                              "valid_time_count": "Số thời lượng hợp lệ", "small_time_n": "Mẫu thời lượng nhỏ",
                                              "day_name": "Ngày", "day_of_week_number": "Thứ tự ngày", "time_period": "Khung giờ",
                                              "average_distance": "Khoảng cách TB (km)"})
            if day_period:
                with st.expander("Chi tiết từng ngày và khung giờ"):
                    st.dataframe(display, hide_index=True, width="stretch")
            else:
                st.dataframe(display, hide_index=True, width="stretch")
        else:
            st.info("Không có bản ghi cho bảng so sánh này.")
    with st.expander("Phạm vi, nguồn và cách đối chiếu"):
        st.json({key: bundle.get(key) for key in ("snapshot_id", "generated_at", "filters", "source", "scope")})
        for limitation in bundle.get("limitations", []):
            st.write(limitation)
        st.caption("Power BI dùng dữ liệu Import. Sau khi DDS thay đổi, cần Refresh Power BI; ứng dụng này không tự đồng bộ slicer hoặc lựa chọn trên biểu đồ.")
        st.download_button("Tải số liệu đối chiếu (JSON)", _json_bytes(bundle),
                           file_name="amazon_delivery_evidence_" + bundle["snapshot_id"][:12] + ".json",
                           mime="application/json", key="download_bundle")


def main() -> None:
    st.set_page_config(page_title="Amazon Delivery · Phân tích AI", layout="wide", initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)  # Constant CSS only; never model/user content.
    connection = _sidebar()
    st.title("Phân tích giao hàng với AI")
    st.caption("Amazon Delivery BI · Tóm tắt KPI và giải thích từ số liệu có thể đối chiếu")
    frame = st.session_state.get("_warehouse_frame")
    current = frame is not None and st.session_state.get("_loaded_connection") == connection
    bundle = None
    if frame is not None and not current:
        _invalidate_ai()
        st.info("Thông tin kết nối đã thay đổi. Bấm “Kết nối và tải dữ liệu” để dùng nguồn mới.")
    elif frame is None:
        st.info(
            "Kết nối dữ liệu ở thanh bên để phân tích dashboard, hoặc chọn Hỏi Gemini chung "
            "để đặt câu hỏi kiến thức chung mà không cần tải DDS."
        )
    elif frame.empty:
        _invalidate_ai()
        st.info("Nguồn dữ liệu chưa có bản ghi. Kiểm tra bước nạp DDS trước khi phân tích.")
    else:
        source = st.session_state.get("_source_meta", {})
        st.caption("Đã lấy dữ liệu lúc " + _local_time(source.get("fetched_at")))
        filters = _filters(frame)
        if filters is not None:
            signature = _fingerprint({"filters": asdict(filters), "data_version": st.session_state.get("_data_version", 0),
                                      "analysis_version": analytics.ANALYSIS_VERSION})
            if signature != st.session_state.get("_bundle_signature"):
                _invalidate_ai()
                try:
                    st.session_state["_bundle"] = analytics.build_analysis(frame, filters, source)
                    st.session_state["_bundle_signature"] = signature
                except Exception:
                    st.session_state.pop("_bundle", None)
                    st.error("Chưa tính được số liệu cho phạm vi này. Tải lại dữ liệu và chọn lại bộ lọc.")
            bundle = st.session_state.get("_bundle")
            if bundle:
                _metrics(bundle)
                if not bundle.get("kpis", {}).get("total_records"):
                    st.info("Phạm vi đang chọn không có bản ghi. Hãy thay đổi bộ lọc để tiếp tục.")
    context = _fingerprint({"snapshot_id": bundle.get("snapshot_id") if bundle else None,
                            "connection": connection, "data_version": st.session_state.get("_data_version", 0),
                            "model": st.session_state.get("gemini_model", ""),
                            "question": st.session_state.get("ai_question", ""),
                            "narrative_version": grounding.NARRATIVE_VERSION})
    if context != st.session_state.get("_ai_context"):
        _invalidate_ai()
        st.session_state["_ai_context"] = context
    ai_tab, evidence_tab = st.tabs(["AI phân tích", "Số liệu đối chiếu"])
    with ai_tab:
        _ai_tab(bundle, context)
    with evidence_tab:
        _evidence_tab(bundle)


if __name__ == "__main__":
    main()
