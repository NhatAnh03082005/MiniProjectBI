"""Transactional SQL Server upsert shared by Mage full and incremental loads."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import pyodbc

from mage_project.amazon_delivery_contract import EXPECTED_COLUMN_COUNT


def get_connection_string() -> str:
    required = ('MSSQL_SERVER', 'MSSQL_DATABASE', 'MSSQL_DRIVER')
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError('Thiếu biến môi trường: ' + ', '.join(missing))
    return (
        f"DRIVER={{{os.environ['MSSQL_DRIVER']}}};"
        f"SERVER={os.environ['MSSQL_SERVER']};"
        f"DATABASE={os.environ['MSSQL_DATABASE']};"
        'Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;'
    )


def to_database_value(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, 'item'):
        try:
            return value.item()
        except (AttributeError, ValueError):
            pass
    return value


def build_output(
    payload: dict[str, Any],
    load_batch_id: str,
    status: str,
    rows_inserted: int,
    rows_updated: int,
    rows_unchanged: int,
    reason: str | None = None,
) -> pd.DataFrame:
    rows_rejected = int(payload.get('rows_rejected', 0))
    return pd.DataFrame([{
        'load_batch_id': load_batch_id,
        'batch_name': payload['batch_name'],
        'batch_type': payload['batch_type'],
        'status': status,
        'source_file_name': payload['source_file_name'],
        'source_file_checksum': payload['source_file_checksum'],
        'rows_read': int(payload.get('rows_read', 0)),
        'rows_inserted': rows_inserted,
        'rows_updated': rows_updated,
        'rows_unchanged': rows_unchanged,
        'rows_loaded': rows_inserted + rows_updated,
        'rows_rejected': rows_rejected,
        'date_from': payload.get('date_from'),
        'date_to': payload.get('date_to'),
        'reason': reason,
    }])


def _insert_started_audit(cursor, payload: dict[str, Any], load_batch_id: str) -> None:
    cursor.execute(
        """
        INSERT INTO audit.load_batch
        (
            load_batch_id, batch_name, batch_type,
            source_file_name, source_file_checksum,
            expected_date_from, expected_date_to, expected_row_count,
            status, rows_read, rows_loaded, rows_rejected,
            rows_inserted, rows_updated, rows_unchanged, error_message
        )
        VALUES
        (
            ?, ?, ?, ?, ?, ?, ?, ?,
            'STARTED', ?, 0, ?, 0, 0, 0, NULL
        );
        """,
        load_batch_id,
        payload['batch_name'],
        payload['batch_type'],
        payload['source_file_name'],
        payload['source_file_checksum'],
        payload.get('date_from') or None,
        payload.get('date_to') or None,
        int(payload.get('rows_read', 0)),
        int(payload.get('rows_read', 0)),
        int(payload.get('rows_rejected', 0)),
    )


def _create_incoming_table(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE #incoming_amazon_delivery
        (
            order_key VARCHAR(32) NOT NULL PRIMARY KEY,
            Order_ID VARCHAR(32) NOT NULL,
            Agent_Age VARCHAR(16) NULL,
            Agent_Rating VARCHAR(16) NULL,
            Store_Latitude VARCHAR(32) NULL,
            Store_Longitude VARCHAR(32) NULL,
            Drop_Latitude VARCHAR(32) NULL,
            Drop_Longitude VARCHAR(32) NULL,
            Order_Date VARCHAR(16) NULL,
            Order_Time VARCHAR(16) NULL,
            Pickup_Time VARCHAR(16) NULL,
            Weather VARCHAR(32) NULL,
            Traffic VARCHAR(32) NULL,
            Vehicle VARCHAR(32) NULL,
            Area VARCHAR(64) NULL,
            Delivery_Time VARCHAR(16) NULL,
            Category VARCHAR(64) NULL,
            source_row_number BIGINT NOT NULL,
            row_hash CHAR(64) NOT NULL
        );
        """
    )


def _load_incoming(cursor, batch_df: pd.DataFrame) -> None:
    if batch_df.empty:
        return

    insert_sql = """
        INSERT INTO #incoming_amazon_delivery
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    chunk_size = 500
    cursor.fast_executemany = True

    for start in range(0, len(batch_df), chunk_size):
        chunk_df = batch_df.iloc[start:start + chunk_size]
        rows = []

        for row in chunk_df.itertuples(index=False, name=None):
            source_values = row[:EXPECTED_COLUMN_COUNT]
            source_row_number = row[EXPECTED_COLUMN_COUNT]
            row_hash = row[EXPECTED_COLUMN_COUNT + 1]
            order_key = str(source_values[0]).strip().casefold()

            rows.append(
                (order_key,)
                + tuple(to_database_value(value) for value in source_values)
                + (int(source_row_number), str(row_hash))
            )

        cursor.executemany(insert_sql, rows)


def _count_change_types(cursor) -> tuple[int, int, int]:
    cursor.execute(
        """
        SELECT
            SUM(CASE WHEN target.staging_row_id IS NULL THEN 1 ELSE 0 END),
            SUM(CASE WHEN target.staging_row_id IS NOT NULL
                          AND (target.row_hash IS NULL OR target.row_hash <> source.row_hash)
                     THEN 1 ELSE 0 END),
            SUM(CASE WHEN target.staging_row_id IS NOT NULL
                          AND target.row_hash = source.row_hash
                     THEN 1 ELSE 0 END)
        FROM #incoming_amazon_delivery AS source
        LEFT JOIN staging.raw_amazon_delivery AS target
          ON LOWER(LTRIM(RTRIM(target.Order_ID))) = source.order_key;
        """
    )
    row = cursor.fetchone()
    return tuple(int(value or 0) for value in row)


def _apply_updates(cursor, load_batch_id: str, source_file_name: str) -> None:
    cursor.execute(
        """
        UPDATE target
        SET
            Agent_Age = source.Agent_Age,
            Agent_Rating = source.Agent_Rating,
            Store_Latitude = source.Store_Latitude,
            Store_Longitude = source.Store_Longitude,
            Drop_Latitude = source.Drop_Latitude,
            Drop_Longitude = source.Drop_Longitude,
            Order_Date = source.Order_Date,
            Order_Time = source.Order_Time,
            Pickup_Time = source.Pickup_Time,
            Weather = source.Weather,
            Traffic = source.Traffic,
            Vehicle = source.Vehicle,
            Area = source.Area,
            Delivery_Time = source.Delivery_Time,
            Category = source.Category,
            row_hash = source.row_hash,
            updated_load_batch_id = ?,
            updated_at = SYSUTCDATETIME(),
            updated_source_file_name = ?,
            updated_source_row_number = source.source_row_number
        FROM staging.raw_amazon_delivery AS target
        INNER JOIN #incoming_amazon_delivery AS source
          ON LOWER(LTRIM(RTRIM(target.Order_ID))) = source.order_key
        WHERE target.row_hash IS NULL OR target.row_hash <> source.row_hash;
        """,
        load_batch_id,
        source_file_name,
    )


def _apply_inserts(
    cursor,
    load_batch_id: str,
    source_file_name: str,
    loaded_at: datetime,
) -> None:
    cursor.execute(
        """
        INSERT INTO staging.raw_amazon_delivery
        (
            Order_ID, Agent_Age, Agent_Rating,
            Store_Latitude, Store_Longitude, Drop_Latitude, Drop_Longitude,
            Order_Date, Order_Time, Pickup_Time,
            Weather, Traffic, Vehicle, Area, Delivery_Time, Category,
            source_file_name, source_row_number, load_batch_id, loaded_at,
            row_hash, updated_load_batch_id, updated_at,
            updated_source_file_name, updated_source_row_number
        )
        SELECT
            source.Order_ID, source.Agent_Age, source.Agent_Rating,
            source.Store_Latitude, source.Store_Longitude,
            source.Drop_Latitude, source.Drop_Longitude,
            source.Order_Date, source.Order_Time, source.Pickup_Time,
            source.Weather, source.Traffic, source.Vehicle, source.Area,
            source.Delivery_Time, source.Category,
            ?, source.source_row_number, ?, ?,
            source.row_hash, ?, ?, ?, source.source_row_number
        FROM #incoming_amazon_delivery AS source
        WHERE NOT EXISTS
        (
            SELECT 1
            FROM staging.raw_amazon_delivery AS target
            WHERE LOWER(LTRIM(RTRIM(target.Order_ID))) = source.order_key
        );
        """,
        source_file_name,
        load_batch_id,
        loaded_at,
        load_batch_id,
        loaded_at,
        source_file_name,
    )


def export_amazon_delivery(payload: dict[str, Any]) -> pd.DataFrame:
    load_batch_id = str(uuid.uuid4())
    loaded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    connection = pyodbc.connect(get_connection_string(), autocommit=False)
    audit_created = False
    try:
        cursor = connection.cursor()
        _insert_started_audit(cursor, payload, load_batch_id)
        connection.commit()
        audit_created = True

        if payload.get('validation_error'):
            raise ValueError(str(payload['validation_error']))

        cursor.execute(
            """
            SELECT TOP (1) LOWER(LTRIM(RTRIM(Order_ID)))
            FROM staging.raw_amazon_delivery
            WHERE Order_ID IS NOT NULL
            GROUP BY LOWER(LTRIM(RTRIM(Order_ID)))
            HAVING COUNT_BIG(*) > 1;
            """
        )
        duplicate_target = cursor.fetchone()
        if duplicate_target:
            raise ValueError(
                f'Staging có Order_ID trùng sau trim/case-fold: {duplicate_target[0]}'
            )

        _create_incoming_table(cursor)
        _load_incoming(cursor, payload['data'])
        rows_inserted, rows_updated, rows_unchanged = _count_change_types(cursor)
        _apply_updates(cursor, load_batch_id, payload['source_file_name'])
        _apply_inserts(cursor, load_batch_id, payload['source_file_name'], loaded_at)

        cursor.execute(
            """
            SELECT COUNT_BIG(*)
            FROM #incoming_amazon_delivery AS source
            INNER JOIN staging.raw_amazon_delivery AS target
              ON LOWER(LTRIM(RTRIM(target.Order_ID))) = source.order_key
             AND target.row_hash = source.row_hash;
            """
        )
        verified_rows = int(cursor.fetchone()[0])
        valid_rows = len(payload['data'])
        if verified_rows != valid_rows:
            raise RuntimeError(
                f'Đối soát hash sau upsert sai: {verified_rows:,}/{valid_rows:,} dòng.'
            )

        rows_read = int(payload.get('rows_read', 0))
        rows_rejected = int(payload.get('rows_rejected', 0))
        if rows_read != rows_inserted + rows_updated + rows_unchanged + rows_rejected:
            raise RuntimeError('Đối soát rows_read không khớp các action counter.')

        rows_loaded = rows_inserted + rows_updated
        warning = payload.get('rejection_summary') or None
        cursor.execute(
            """
            UPDATE audit.load_batch
            SET finished_at = SYSUTCDATETIME(),
                status = 'SUCCEEDED',
                rows_loaded = ?, rows_rejected = ?,
                rows_inserted = ?, rows_updated = ?, rows_unchanged = ?,
                error_message = ?
            WHERE load_batch_id = ?;
            """,
            rows_loaded,
            rows_rejected,
            rows_inserted,
            rows_updated,
            rows_unchanged,
            warning,
            load_batch_id,
        )
        connection.commit()
        return build_output(
            payload,
            load_batch_id,
            'SUCCEEDED',
            rows_inserted,
            rows_updated,
            rows_unchanged,
            warning,
        )
    except Exception as error:
        connection.rollback()
        if audit_created:
            try:
                failure_cursor = connection.cursor()
                failure_cursor.execute(
                    """
                    UPDATE audit.load_batch
                    SET finished_at = SYSUTCDATETIME(), status = 'FAILED',
                        rows_loaded = 0, rows_inserted = 0,
                        rows_updated = 0, rows_unchanged = 0,
                        error_message = ?
                    WHERE load_batch_id = ?;
                    """,
                    str(error)[:4000],
                    load_batch_id,
                )
                connection.commit()
            except Exception:
                connection.rollback()
        raise
    finally:
        connection.close()


def assert_export_output(output: pd.DataFrame) -> None:
    assert output is not None and len(output) == 1
    row = output.iloc[0]
    assert str(row['status']).upper() == 'SUCCEEDED'
    assert int(row['rows_read']) == (
        int(row['rows_inserted'])
        + int(row['rows_updated'])
        + int(row['rows_unchanged'])
        + int(row['rows_rejected'])
    )
    assert int(row['rows_loaded']) == int(row['rows_inserted']) + int(row['rows_updated'])

