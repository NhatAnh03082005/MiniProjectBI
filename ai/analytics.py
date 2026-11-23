"""Deterministic, local aggregates matching the checked-in Power BI measures."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, timezone
import hashlib
import json
import math

import pandas as pd

from .data import fingerprint_frame

BASELINE_MINUTES = 195
SMALL_SAMPLE = 200
ANALYSIS_VERSION = "1.2"
KPI_DEFINITIONS = {
    "total_records": ("Số bản ghi giao hàng trong bộ lọc", "bản ghi"),
    "average_minutes": ("Thời lượng giao trung bình", "phút"),
    "median_minutes": ("Trung vị thời lượng giao", "phút"),
    "p90_minutes": ("P90 thời lượng giao theo bộ lọc", "phút"),
    "p95_minutes": ("P95 thời lượng giao theo bộ lọc", "phút"),
    "above_baseline_count": ("Số bản ghi vượt baseline cố định", "bản ghi"),
    "share_above_baseline": ("Tỷ trọng vượt baseline cố định", "%"),
    "active_days": ("Số ngày thực sự có bản ghi", "ngày"),
    "records_per_active_day": ("Số bản ghi bình quân trên ngày có dữ liệu", "bản ghi/ngày"),
    "average_pickup_delay": ("Thời gian chờ pickup trung bình", "phút"),
    "average_valid_distance": ("Khoảng cách hợp lệ trung bình", "km"),
    "average_valid_rating": ("Rating hợp lệ trung bình", "điểm"),
    "valid_distance_count": ("Số bản ghi có khoảng cách hợp lệ", "bản ghi"),
    "valid_distance_coverage": ("Tỷ trọng khoảng cách hợp lệ (Operational Drivers)", "%"),
    "report_valid_distance_coverage": ("Tỷ lệ khoảng cách hợp lệ (Area & Category)", "%"),
    "valid_rating_coverage": ("Tỷ trọng rating hợp lệ trong Fact", "%"),
    "pickup_delay_coverage": ("Tỷ trọng có pickup delay trong Fact", "%"),
    "operational_context_coverage": ("Tỷ trọng đủ context vận hành trong Fact", "%"),
}
DIMENSIONS = {
    "traffic": ("traffic_level", "Traffic"),
    "weather": ("weather_name", "Weather"),
    "vehicle": ("vehicle_type", "Vehicle"),
    "area": ("area_name", "Area"),
    "category": ("category_name", "Category"),
    "time_period": ("time_period", "Time period"),
}
FILTER_COLUMNS = {
    "vehicles": "vehicle_type", "categories": "category_name", "areas": "area_name",
    "traffic": "traffic_level", "weather": "weather_name", "time_periods": "time_period",
}
REQUIRED_COLUMNS = {
    "delivery_key", "order_id", "date_key", "delivery_count", "full_date",
    "delivery_time_minutes", "above_baseline_p90_flag", "pickup_delay_minutes",
    "delivery_distance_km", "valid_distance_flag", "agent_rating_valid", "valid_rating_flag",
    "missing_operational_context_flag", "distance_band", *FILTER_COLUMNS.values(),
}


class AnalyticsError(ValueError):
    """The frame or requested context cannot be compared safely with the model."""


def _date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise AnalyticsError("Ngày phải có dạng YYYY-MM-DD.") from None


@dataclass(frozen=True)
class FilterContext:
    start_date: str | date | None = None
    end_date: str | date | None = None
    dates: tuple[str, ...] = ()
    vehicles: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    areas: tuple[str, ...] = ()
    traffic: tuple[str, ...] = ()
    weather: tuple[str, ...] = ()
    time_periods: tuple[str, ...] = ()

    def __post_init__(self):
        start, end = _date(self.start_date), _date(self.end_date)
        if start and end and start > end:
            raise AnalyticsError("Ngày bắt đầu phải không sau ngày kết thúc.")
        object.__setattr__(self, "start_date", start.isoformat() if start else None)
        object.__setattr__(self, "end_date", end.isoformat() if end else None)
        if isinstance(self.dates, str):
            raise AnalyticsError("Danh sách ngày không hợp lệ.")
        parsed_dates = [_date(v) for v in self.dates]
        if any(v is None for v in parsed_dates):
            raise AnalyticsError("Danh sách ngày không hợp lệ.")
        object.__setattr__(self, "dates", tuple(sorted({v.isoformat() for v in parsed_dates})))
        for name in FILTER_COLUMNS:
            values = getattr(self, name)
            if isinstance(values, str) or any(not isinstance(v, str) or not v for v in values):
                raise AnalyticsError("Danh sách giá trị bộ lọc không hợp lệ.")
            object.__setattr__(self, name, tuple(sorted(set(values))))


def _number(series: pd.Series) -> float | None:
    return float(series.mean()) if series.notna().any() else None


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    result = pd.to_numeric(frame[column], errors="coerce")
    if (frame[column].notna() & result.isna()).any() or result.dropna().map(lambda v: not math.isfinite(v)).any():
        raise AnalyticsError(f"Cột {column} có giá trị số không hợp lệ.")
    return result.astype(float)


def _flag(frame: pd.DataFrame, column: str) -> pd.Series:
    values = frame[column]
    if not values.dropna().isin([0, 1, False, True]).all():
        raise AnalyticsError(f"Cờ {column} không phải 0/1.")
    return values.astype("boolean")


def _prepare(frame: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise AnalyticsError("DDS thiếu các cột cần thiết cho phân tích.")
    result = frame.copy(deep=True)
    for column in ("order_id", "delivery_key"):
        values = result[column].astype("string").str.strip()
        if values.isna().any() or values.eq("").any() or values.str.casefold().duplicated().any():
            raise AnalyticsError("DDS sai grain: mỗi Order_ID và delivery_key phải duy nhất, không rỗng.")
        result[column] = values
    for column in ("date_key", "delivery_count", "delivery_time_minutes", "pickup_delay_minutes",
                   "delivery_distance_km", "agent_rating_valid"):
        result[column] = _numeric(result, column)
    if result["delivery_count"].isna().any() or not result["delivery_count"].eq(1).all():
        raise AnalyticsError("DDS sai grain: delivery_count phải bằng 1 ở mỗi dòng.")
    if result["date_key"].isna().any() or result["date_key"].mod(1).ne(0).any():
        raise AnalyticsError("date_key không hợp lệ.")
    result["date_key"] = result["date_key"].astype("int64")
    original_dates = result["full_date"]
    result["full_date"] = pd.to_datetime(original_dates, errors="coerce").dt.normalize()
    if result.loc[result["date_key"].ne(0), "full_date"].isna().any():
        raise AnalyticsError("DDS có ngày chưa tra được vào Dimension Date.")
    result.loc[result["date_key"].eq(0), "full_date"] = pd.NaT
    for column in ("above_baseline_p90_flag", "valid_distance_flag", "valid_rating_flag",
                   "missing_operational_context_flag"):
        result[column] = _flag(result, column)
    times = result["delivery_time_minutes"]
    flags = result["above_baseline_p90_flag"]
    if times.dropna().lt(0).any() or (times.notna() & (flags.isna() | flags.ne(times.gt(BASELINE_MINUTES)))).any() \
            or (times.isna() & flags.notna()).any():
        raise AnalyticsError("Cờ baseline trong DDS không khớp quy tắc Delivery Time > 195 phút.")
    distances = result["delivery_distance_km"]
    valid = result["valid_distance_flag"].fillna(False)
    if distances.dropna().lt(0).any() or valid.ne(distances.notna() & distances.le(50)).any():
        raise AnalyticsError("Cờ khoảng cách hợp lệ trong DDS không khớp ngưỡng 50 km.")
    ratings = result["agent_rating_valid"]
    if (result["valid_rating_flag"].fillna(False) & ~ratings.between(1, 5)).any():
        raise AnalyticsError("Rating hợp lệ nằm ngoài miền 1–5.")
    for column in (*FILTER_COLUMNS.values(), "distance_band"):
        result[column] = result[column].fillna("Unknown").astype(str)
    return result


def _metrics(frame: pd.DataFrame) -> dict:
    count = len(frame)
    times = frame["delivery_time_minutes"].dropna()
    above = int((frame["above_baseline_p90_flag"].fillna(False) & frame["delivery_time_minutes"].notna()).sum())
    days = int(frame.loc[frame["date_key"].ne(0), "date_key"].nunique())
    distance = frame.loc[frame["valid_distance_flag"].fillna(False)]
    rating = frame.loc[frame["valid_rating_flag"].fillna(False), "agent_rating_valid"]
    # COUNT(empty) and SUM(empty) are BLANK in the checked-in DAX. In particular
    # Above Baseline Count has no COALESCE, so zero qualifying rows stays None.
    return {
        "total_records": count if count else None,
        "valid_time_count": len(times) if len(times) else None,
        "average_minutes": _number(times),
        "median_minutes": float(times.median()) if len(times) else None,
        "p90_minutes": float(times.quantile(.90, interpolation="linear")) if len(times) else None,
        "p95_minutes": float(times.quantile(.95, interpolation="linear")) if len(times) else None,
        "above_baseline_count": above if above else None,
        "share_above_baseline": above / len(times) if above and len(times) else None,
        "active_days": days if days else None,
        "records_per_active_day": count / days if count and days else None,
        "average_pickup_delay": _number(frame["pickup_delay_minutes"]),
        "valid_pickup_delay_count": int(frame["pickup_delay_minutes"].notna().sum()) or None,
        "average_valid_distance": _number(distance["delivery_distance_km"]),
        "average_valid_rating": _number(rating),
        "valid_rating_count": int(rating.notna().sum()) or None,
        "valid_distance_count": len(distance) if len(distance) else None,
        "valid_distance_coverage": len(distance) / count if len(distance) and count else None,
        # Report-level quality measures explicitly COALESCE the numerator to 0.
        "report_valid_distance_coverage": len(distance) / count if count else None,
        "valid_rating_coverage": int(frame["valid_rating_flag"].fillna(False).sum()) / count if count else None,
        "pickup_delay_coverage": int(frame["pickup_delay_minutes"].notna().sum()) / count if count else None,
        "operational_context_coverage": int(frame["missing_operational_context_flag"].eq(False).fillna(False).sum()) / count if count else None,
    }


def _group_record(label: str, frame: pd.DataFrame) -> dict:
    m = _metrics(frame)
    valid_time_count = m["valid_time_count"] or 0
    return {"label": label, "n": len(frame), "valid_time_count": valid_time_count,
            "average_minutes": m["average_minutes"],
            "median_minutes": m["median_minutes"], "p90_minutes": m["p90_minutes"],
            "above_baseline_count": m["above_baseline_count"], "share_above_baseline": m["share_above_baseline"],
            "small_n": 0 < len(frame) < SMALL_SAMPLE,
            "small_time_n": 0 < valid_time_count < SMALL_SAMPLE}


def format_fact(value, unit: str) -> str:
    if value is None:
        return "Không có dữ liệu"
    if isinstance(value, str):
        return value
    if unit == "%":
        return f"{value * 100:.2f}".replace(".", ",") + "%"
    if unit in ("bản ghi", "ngày"):
        text = f"{value:,.0f}".replace(",", ".")
    else:
        text = f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{text} {unit}".strip()


def _facts(kpis: dict, tables: dict, scope: dict) -> tuple[list[dict], bool]:
    facts = []
    evidence_truncated = False

    def add(label, value, unit, n=None, source="kpi", context=None):
        nonlocal evidence_truncated
        if len(facts) >= 160:
            evidence_truncated = True
            return
        fact = {"id": f"F{len(facts) + 1:03d}", "label": label, "value": value, "unit": unit,
                "display": format_fact(value, unit), "n": n, "source": source}
        if context:
            fact["context"] = context
        facts.append(fact)

    for key, (label, unit) in KPI_DEFINITIONS.items():
        sample_n = scope["selected_records"]
        if key in {"average_minutes", "median_minutes", "p90_minutes", "p95_minutes", "above_baseline_count", "share_above_baseline"}:
            sample_n = kpis["valid_time_count"] or 0
        elif key == "average_valid_distance":
            sample_n = kpis["valid_distance_count"] or 0
        elif key == "average_valid_rating":
            sample_n = kpis["valid_rating_count"] or 0
        elif key == "average_pickup_delay":
            sample_n = kpis["valid_pickup_delay_count"] or 0
        add(label, kpis[key], unit, sample_n, f"kpi/{key}")

    # Reserve the bounded evidence budget for rules, scope and comparisons
    # before optional group detail. A large category list must not hide them.
    add("Ngưỡng baseline P90 cố định, không phải SLA", BASELINE_MINUTES, "phút", source="rule/baseline")
    add("Ngưỡng gắn nhãn cỡ mẫu nhỏ", SMALL_SAMPLE, "bản ghi", source="rule/small_sample")
    add("Giới hạn khoảng cách hợp lệ", 50, "km", source="rule/distance")
    gap_days = sum(r["total_records"] == 0 for r in tables["daily"])
    add("Số ngày lịch không có bản ghi trong phạm vi đã lọc", gap_days, "ngày", source="calendar/gaps")
    if scope["selected_min_date"]:
        add("Ngày có dữ liệu đầu tiên trong bộ lọc", scope["selected_min_date"], "ngày lịch", source="scope/min_date")
        add("Ngày có dữ liệu cuối cùng trong bộ lọc", scope["selected_max_date"], "ngày lịch", source="scope/max_date")

    priority_groups = set()
    for key in (*DIMENSIONS, "distance_band"):
        eligible = [r for r in tables[key] if r["valid_time_count"] >= SMALL_SAMPLE and r["average_minutes"] is not None
                    and r["label"].strip().casefold() != "unknown"]
        if len(eligible) < 2:
            continue
        ordered = sorted(eligible, key=lambda r: (r["average_minutes"], r["label"]))
        low, high = ordered[0], ordered[-1]
        priority_groups.update(((key, high["label"]), (key, low["label"])))
        add(f"{key}: chênh lệch trung bình giữa {high['label']} (cao nhất) và {low['label']} (thấp nhất), các nhóm đủ mẫu",
            high["average_minutes"] - low["average_minutes"], "phút", source=f"comparison/{key}",
            context={"high": high["label"], "low": low["label"],
                     "high_n": high["valid_time_count"], "low_n": low["valid_time_count"],
                     "high_average_minutes": high["average_minutes"], "low_average_minutes": low["average_minutes"],
                     "minimum_n": SMALL_SAMPLE})

    # Compare adjacent calendar dates only, with enough nonblank durations on
    # BOTH days; total record count is not the sample size of an average.
    changes = []
    for previous, current in zip(tables["daily"], tables["daily"][1:]):
        if (_date(current["date"]) - _date(previous["date"])).days != 1:
            continue
        if (previous["valid_time_count"] < SMALL_SAMPLE or current["valid_time_count"] < SMALL_SAMPLE
                or previous["average_minutes"] is None or current["average_minutes"] is None):
            continue
        changes.append((current["average_minutes"] - previous["average_minutes"], previous, current))
    for direction, candidates in (("tăng", [r for r in changes if r[0] > 0]), ("giảm", [r for r in changes if r[0] < 0])):
        if not candidates:
            continue
        change, previous, current = max(candidates, key=lambda r: abs(r[0]))
        context = {"from_date": previous["date"], "to_date": current["date"],
                   "from_n": previous["valid_time_count"], "to_n": current["valid_time_count"],
                   "from_average_minutes": previous["average_minutes"], "to_average_minutes": current["average_minutes"],
                   "direction": direction}
        add(f"Mức {direction} trung bình lớn nhất giữa hai ngày lịch liền nhau đủ mẫu",
            abs(change), "phút", source="comparison/daily_average", context=context)
        # These values need their own fact tokens so the local claim renderer
        # can bind every date, mean and sample size to explicit evidence.
        for field, label, unit in (
            ("from_date", "Ngày trước trong cặp", "ngày lịch"),
            ("to_date", "Ngày sau trong cặp", "ngày lịch"),
            ("from_average_minutes", "Thời lượng giao trung bình ngày trước", "phút"),
            ("to_average_minutes", "Thời lượng giao trung bình ngày sau", "phút"),
            ("from_n", "Số thời lượng hợp lệ ngày trước", "bản ghi"),
            ("to_n", "Số thời lượng hợp lệ ngày sau", "bản ghi"),
        ):
            source_suffix = {"from_average_minutes": "from_average", "to_average_minutes": "to_average"}.get(field, field)
            sample_n = context["from_n"] if field.startswith("from_") else context["to_n"]
            add(f"{label} có mức {direction} lớn nhất", context[field], unit, sample_n,
                source=f"comparison/daily_average/{source_suffix}", context=context)

    def group_details(key, title, row):
        count_context = {"dimension": key, "group": row["label"], "small_n": row["small_n"]}
        mean_context = {**count_context, "small_n": row["small_time_n"]}
        if key == "distance_band":
            count_context["valid_distance_only"] = True
            mean_context["valid_distance_only"] = True
        suffix = " (mẫu nhỏ)" if row["small_n"] else ""
        add(f"{title} = {row['label']}: cỡ mẫu{suffix}", row["n"], "bản ghi", row["n"],
            f"group/{key}/n", count_context)
        add(f"{title} = {row['label']}: thời lượng giao trung bình", row["average_minutes"], "phút",
            row["valid_time_count"], f"group/{key}/average", mean_context)
        if row["valid_time_count"] != row["n"]:
            add(f"{title} = {row['label']}: số thời lượng hợp lệ", row["valid_time_count"], "bản ghi",
                row["valid_time_count"], f"group/{key}/valid_time_count", mean_context)
        if key == "distance_band":
            add(f"Khoảng cách {row['label']}: Haversine trung bình", row["average_distance"], "km",
                row["n"], "group/distance_band/distance", count_context)

    # Keep both groups behind a comparison available for verification even
    # when lower-priority category details must be omitted at the fact limit.
    for prioritized in (True, False):
        for key, (_, title) in DIMENSIONS.items():
            for row in tables[key]:
                if ((key, row["label"]) in priority_groups) == prioritized:
                    group_details(key, title, row)
        for row in tables["distance_band"]:
            if (("distance_band", row["label"]) in priority_groups) == prioritized:
                group_details("distance_band", "Khoảng cách", row)
    return facts, evidence_truncated


def build_analysis(frame: pd.DataFrame, filters: FilterContext = FilterContext(), source_meta: dict | None = None) -> dict:
    """Return only aggregates/facts; no identifiers or per-delivery records."""
    if not isinstance(filters, FilterContext):
        raise AnalyticsError("Bộ lọc phải là FilterContext.")
    full = _prepare(frame)
    selected = full
    if filters.start_date:
        selected = selected.loc[selected["full_date"].ge(pd.Timestamp(filters.start_date))]
    if filters.end_date:
        selected = selected.loc[selected["full_date"].le(pd.Timestamp(filters.end_date))]
    if filters.dates:
        selected = selected.loc[selected["full_date"].isin(pd.to_datetime(list(filters.dates)))]
    for name, column in FILTER_COLUMNS.items():
        if getattr(filters, name):
            selected = selected.loc[selected[column].isin(getattr(filters, name))]
    global_dates = full.loc[full["date_key"].ne(0), "full_date"].dropna()
    global_min = global_dates.min().date() if len(global_dates) else None
    global_max = global_dates.max().date() if len(global_dates) else None
    kpis = _metrics(selected)
    tables = {}
    for key, (column, _) in DIMENSIONS.items():
        rows = [_group_record(str(label), part) for label, part in selected.groupby(column, sort=True, observed=True)]
        rows.sort(key=lambda r: (-(r["average_minutes"] if r["average_minutes"] is not None else -math.inf), r["label"]))
        if key == "time_period":
            order = {"Morning": 0, "Afternoon": 1, "Evening": 2, "Night": 3, "Unknown": 4}
            rows.sort(key=lambda r: (order.get(r["label"], 5), r["label"]))
        tables[key] = rows
    distance = selected.loc[selected["valid_distance_flag"].fillna(False)]
    tables["distance_band"] = []
    for label, part in distance.groupby("distance_band", sort=True, observed=True):
        row = _group_record(str(label), part)
        row["average_distance"] = _number(part["delivery_distance_km"])
        tables["distance_band"].append(row)
    tables["distance_band"].sort(key=lambda r: r["average_distance"])
    if filters.dates:
        calendar = [pd.Timestamp(v) for v in filters.dates
                    if (not filters.start_date or v >= filters.start_date) and (not filters.end_date or v <= filters.end_date)]
    else:
        start, end = _date(filters.start_date) or global_min, _date(filters.end_date) or global_max
        if start and end and (end - start).days > 10000:
            raise AnalyticsError("Khoảng ngày vượt quá phạm vi phân tích hỗ trợ.")
        calendar = list(pd.date_range(start, end, freq="D")) if start and end and start <= end else []
    daily_groups = {label: part for label, part in selected.groupby("full_date", observed=True)}
    tables["daily"] = []
    for day in calendar:
        part = daily_groups.get(day, selected.iloc[:0])
        row = _group_record(day.date().isoformat(), part)
        inside = bool(global_min and global_min <= day.date() <= global_max)
        row.update(date=day.date().isoformat(), total_records=len(part) if inside else None)
        tables["daily"].append(row)
    tables["day_period"] = []
    dated = selected.loc[selected["full_date"].notna()].copy()
    dated["_weekday"] = dated["full_date"].dt.dayofweek
    for (weekday, period), part in dated.groupby(["_weekday", "time_period"], sort=True, observed=True):
        row = _group_record(str(period), part)
        row.update(day_of_week_number=int(weekday) + 1, day_name=("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[int(weekday)], time_period=str(period))
        tables["day_period"].append(row)
    observed_dates = selected["full_date"].dropna()
    scope = {
        "global_records": len(full), "selected_records": len(selected),
        "selected_min_date": observed_dates.min().date().isoformat() if len(observed_dates) else None,
        "selected_max_date": observed_dates.max().date().isoformat() if len(observed_dates) else None,
        "global_min_date": global_min.isoformat() if global_min else None,
        "global_max_date": global_max.isoformat() if global_max else None,
        "selected_calendar_days": len(calendar), "active_days": kpis["active_days"],
        "baseline_minutes": BASELINE_MINUTES, "small_sample_threshold": SMALL_SAMPLE,
        "grain": "Một dòng Fact cho một Order_ID nguồn được chấp nhận",
    }
    metadata = source_meta or {}
    source = {key: metadata[key] for key in ("fetched_at", "server", "database", "snapshot_consistency") if isinstance(metadata.get(key), str)}
    source.update(source_fingerprint=fingerprint_frame(frame), global_min_date=scope["global_min_date"], global_max_date=scope["global_max_date"])
    identity = json.dumps({"version": ANALYSIS_VERSION, "rules": {"baseline_minutes": 195, "max_distance_km": 50, "small_sample": 200},
                           "fingerprint": source["source_fingerprint"], "filters": asdict(filters)}, sort_keys=True, ensure_ascii=False)
    facts, evidence_truncated = _facts(kpis, tables, scope)
    return {
        "schema_version": "1", "snapshot_id": hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24],
        "generated_at": metadata.get("fetched_at") or datetime.now(timezone.utc).isoformat(), "filters": asdict(filters),
        "source": source, "scope": scope, "kpis": kpis, "tables": tables,
        "facts": facts,
        "limitations": [
            "Phân tích trên tập Fact được chấp nhận; không thay thế kiểm tra chất lượng dữ liệu raw.",
            "Chênh lệch giữa các nhóm chỉ mang tính mô tả, không chứng minh quan hệ nhân quả.",
            "Baseline cố định là ngưỡng thống kê của dự án, không phải SLA hoặc tỷ lệ giao trễ.",
            "Đơn vị phút là giả định của dự án; dữ liệu không có doanh thu, chi phí hay Agent_ID.",
            "Ngày không có bản ghi không chứng minh hoạt động giao hàng đã dừng.",
            "Các tháng có thể chỉ có một phần thời gian; cần xem phạm vi ngày và active days khi so sánh.",
            "Bộ lọc ứng dụng độc lập với Power BI Desktop; cần chọn cùng ngữ cảnh để đối soát.",
            "Power BI dùng Import; dữ liệu trên báo cáo có thể khác DDS nếu chưa refresh.",
            "Nhóm nhỏ cần thận trọng; nhóm Unknown vẫn xuất hiện trong bảng nhưng không dùng xếp hạng chênh lệch.",
        ] + (["Danh sách chứng cứ gửi AI đã rút gọn; một số nhóm chi tiết không có trong chứng cứ. "
              "Các KPI, quy tắc, phạm vi và so sánh chính vẫn được giữ; xem bảng nhóm đầy đủ để đối chiếu."]
             if evidence_truncated else []),
    }
