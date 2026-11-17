"""Read the current DDS once; identifiers stay in the local validation frame."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib

import pandas as pd

try:
    import pyodbc
except ImportError:  # Let the UI show a useful, credential-free message.
    pyodbc = None


class WarehouseError(RuntimeError):
    """A safe message suitable for display; never contains an ODBC exception."""


@dataclass(frozen=True)
class DatabaseConfig:
    server: str = r"localhost\SQLEXPRESS"
    database: str = "AmazonDeliveryBI"
    driver: str = "ODBC Driver 18 for SQL Server"
    trust_certificate: bool = True


# No user text is interpolated into SQL. LEFT JOIN preserves any orphan for
# validation instead of silently dropping it. No coordinates are selected.
WAREHOUSE_SELECT = """
SELECT
    f.delivery_key, f.order_id, f.date_key, f.delivery_count,
    d.full_date, d.day_name, d.day_of_week_number, d.month_number,
    d.month_name, d.quarter_number, d.year,
    c.weather_name, c.traffic_level, v.vehicle_type, a.area_name,
    g.category_name, f.time_period, f.order_hour, f.age_group,
    f.rating_group, f.agent_age, f.agent_rating_raw, f.agent_rating_valid,
    f.valid_rating_flag, f.delivery_time_minutes, f.above_baseline_p90_flag,
    f.delivery_time_iqr_outlier_flag, f.pickup_delay_minutes,
    f.pickup_rollover_flag, f.delivery_distance_km, f.valid_distance_flag,
    f.distance_outlier_flag, f.distance_status, f.distance_band,
    f.missing_operational_context_flag, f.underage_agent_flag
FROM dw.fact_delivery AS f
LEFT JOIN dw.dim_date AS d ON d.date_key = f.date_key
LEFT JOIN dw.dim_delivery_condition AS c
    ON c.delivery_condition_key = f.delivery_condition_key
LEFT JOIN dw.dim_vehicle AS v ON v.vehicle_key = f.vehicle_key
LEFT JOIN dw.dim_area AS a ON a.area_key = f.area_key
LEFT JOIN dw.dim_category AS g ON g.category_key = f.category_key
ORDER BY f.delivery_key
""".strip()


def _connection_string(config: DatabaseConfig) -> str:
    values = (config.server, config.database, config.driver)
    if any(not isinstance(v, str) or not v.strip() or len(v) > 256
           or any(ch in v for ch in ";\r\n\x00") for v in values):
        raise WarehouseError("Tên máy chủ, cơ sở dữ liệu hoặc driver không hợp lệ.")
    if not isinstance(config.trust_certificate, bool):
        raise WarehouseError("Thiết lập chứng chỉ không hợp lệ.")

    def quoted(value: str) -> str:
        return "{" + value.replace("}", "}}") + "}"

    return (
        f"DRIVER={quoted(config.driver)};SERVER={quoted(config.server)};"
        f"DATABASE={quoted(config.database)};Trusted_Connection=yes;Encrypt=yes;"
        f"TrustServerCertificate={'yes' if config.trust_certificate else 'no'};"
        "APP={AmazonDeliveryBI AI};"
    )


def fingerprint_frame(frame: pd.DataFrame) -> str:
    """A content fingerprint, independent of row order and fetch timestamp."""
    ordered = frame.reindex(sorted(frame.columns), axis=1)
    if "delivery_key" in ordered:
        ordered = ordered.sort_values("delivery_key", kind="stable")
    payload = ordered.to_json(orient="records", date_format="iso", double_precision=15)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_warehouse(config: DatabaseConfig = DatabaseConfig()) -> tuple[pd.DataFrame, dict]:
    """Fetch within one SERIALIZABLE read transaction, then release all locks.

    A lock/query timeout fails the request rather than returning a partial frame.
    SQL Server may block a concurrent warehouse rebuild during this short read.
    The caller must not send the returned per-record frame to an LLM.
    """
    connection_string = _connection_string(config)
    if pyodbc is None:
        raise WarehouseError("Thiếu pyodbc. Hãy cài các thư viện của ứng dụng AI.")
    connection = None
    cursor = None
    try:
        connection = pyodbc.connect(connection_string, autocommit=False, timeout=5)
        connection.timeout = 30
        cursor = connection.cursor()
        cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE; SET LOCK_TIMEOUT 5000;")
        cursor.execute(WAREHOUSE_SELECT)
        columns = [item[0] for item in cursor.description]
        records = [tuple(row) for row in cursor.fetchall()]
        connection.commit()
    except Exception:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        raise WarehouseError(
            "Không đọc được DDS. Kiểm tra SQL Server, quyền Windows, driver và trạng thái nạp dữ liệu; "
            "sau đó thử lại."
        ) from None
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
    try:
        frame = pd.DataFrame.from_records(records, columns=columns)
        for name in ("weather_name", "traffic_level", "vehicle_type", "area_name", "category_name"):
            if name not in frame or frame[name].isna().any():
                raise ValueError("Missing dimension member")
        if "full_date" not in frame or "date_key" not in frame:
            raise ValueError("Missing date fields")
        frame["full_date"] = pd.to_datetime(frame["full_date"], errors="coerce").dt.normalize()
        if frame.loc[frame["date_key"].ne(0), "full_date"].isna().any():
            raise ValueError("Missing date member")
        dates = frame.loc[frame["date_key"].ne(0), "full_date"].dropna()
        metadata = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "server": config.server,
            "database": config.database,
            "source_fingerprint": fingerprint_frame(frame),
            "global_min_date": dates.min().date().isoformat() if len(dates) else None,
            "global_max_date": dates.max().date().isoformat() if len(dates) else None,
            "snapshot_consistency": "SERIALIZABLE read transaction; all rows fetched before commit",
        }
        return frame, metadata
    except Exception:
        raise WarehouseError("DDS thiếu cột hoặc thành viên Dimension cần thiết. Hãy kiểm tra lại mô hình dữ liệu.") from None
