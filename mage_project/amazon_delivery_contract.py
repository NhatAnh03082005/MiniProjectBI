"""Shared technical contract for the Mage Amazon Delivery pipelines.

Mage keeps the 16 source values unchanged.  This module only validates the
source interface, derives batch metadata, and computes a deterministic hash
used by the current-state upsert.  Business cleaning remains in dbt.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


SOURCE_COLUMNS = [
    'Order_ID',
    'Agent_Age',
    'Agent_Rating',
    'Store_Latitude',
    'Store_Longitude',
    'Drop_Latitude',
    'Drop_Longitude',
    'Order_Date',
    'Order_Time',
    'Pickup_Time',
    'Weather',
    'Traffic',
    'Vehicle',
    'Area',
    'Delivery_Time',
    'Category',
]
HASH_COLUMNS = [column for column in SOURCE_COLUMNS if column != 'Order_ID']
EXPECTED_COLUMN_COUNT = len(SOURCE_COLUMNS)
NULL_LIKE_ORDER_IDS = {'', 'nan', 'null', 'none', 'n/a', 'na', '-'}
MAX_ORDER_ID_LENGTH = 32


def generate_batch_name(batch_type: str, now: datetime | None = None) -> str:
    """Return a unique, human-readable batch name under VARCHAR(50)."""
    current = now or datetime.now(timezone.utc)
    timestamp = current.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    prefix = 'full' if batch_type.upper() == 'FULL_LOAD' else 'inc'
    return f'amazon_delivery_{prefix}_{timestamp}_{uuid.uuid4().hex[:8]}'


def compute_raw_row_hash(values: list[Any] | tuple[Any, ...]) -> str:
    """Hash raw non-key values without trimming or business normalization."""
    serialized = json.dumps(
        [None if value is None else str(value) for value in values],
        ensure_ascii=False,
        separators=(',', ':'),
    )
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def resolve_source_path(project_root: str, source_file_path: str | None) -> Path:
    """Resolve an optional runtime source path, defaulting to the shared CSV."""
    root = Path(project_root).resolve()
    if source_file_path:
        candidate = Path(source_file_path)
        if not candidate.is_absolute():
            candidate = root / candidate
    else:
        candidate = root / 'data' / 'raw' / 'amazon_delivery.csv'
    return candidate.resolve()


def build_validation_result(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        'batch_name': payload['batch_name'],
        'batch_type': payload['batch_type'],
        'source_file_name': payload['source_file_name'],
        'source_file_checksum': payload['source_file_checksum'],
        'data': pd.DataFrame(),
        'rows_read': 0,
        'rows_rejected': 0,
        'rejection_summary': '',
        # Mage 0.9.80 cannot deserialize cached builtins.NoneType values in a
        # complex dictionary. Empty strings keep the block output cache-safe;
        # the repository converts them back to SQL NULL for audit columns.
        'date_from': '',
        'date_to': '',
        'validation_error': '',
    }


def validate_and_prepare(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate technical rules and add source row number plus raw row hash."""
    result = build_validation_result(payload)
    if payload.get('read_error'):
        result['validation_error'] = str(payload['read_error'])
        return result

    source_df = payload['data']
    try:
        if source_df.shape[1] != EXPECTED_COLUMN_COUNT:
            raise ValueError(
                f'Sai số cột: nhận {source_df.shape[1]}, '
                f'cần {EXPECTED_COLUMN_COUNT}.'
            )
        if list(source_df.columns) != SOURCE_COLUMNS:
            raise ValueError(
                'Header CSV không đúng thứ tự/tên cột. '
                f'Nhận {list(source_df.columns)}; cần {SOURCE_COLUMNS}.'
            )

        working = source_df.copy()
        result['rows_read'] = len(working)
        working['_source_row_number'] = range(1, len(working) + 1)

        normalized_ids = working['Order_ID'].astype(str).str.strip()
        order_keys = normalized_ids.str.casefold()
        invalid_id_mask = order_keys.isin(NULL_LIKE_ORDER_IDS) | normalized_ids.str.len().gt(
            MAX_ORDER_ID_LENGTH
        )

        duplicate_mask = order_keys[~invalid_id_mask].duplicated(keep=False)
        if duplicate_mask.any():
            examples = normalized_ids.loc[duplicate_mask.index[duplicate_mask]][:10].tolist()
            raise ValueError(
                'Order_ID lặp trong cùng batch sau trim/case-fold. '
                f'Ví dụ: {examples}'
            )

        parsed_dates = pd.to_datetime(
            working['Order_Date'], format='%Y-%m-%d', errors='coerce'
        )
        invalid_date_mask = parsed_dates.isna()
        rejected_mask = invalid_id_mask | invalid_date_mask
        result['rows_rejected'] = int(rejected_mask.sum())

        reasons = []
        if invalid_id_mask.any():
            reasons.append(f'Order_ID không hợp lệ: {int(invalid_id_mask.sum())}')
        if invalid_date_mask.any():
            reasons.append(f'Order_Date không parse được: {int(invalid_date_mask.sum())}')
        result['rejection_summary'] = '; '.join(reasons)

        valid = working.loc[~rejected_mask].copy()
        valid_dates = parsed_dates.loc[~rejected_mask]
        if not valid.empty:
            result['date_from'] = valid_dates.min().date().isoformat()
            result['date_to'] = valid_dates.max().date().isoformat()
            valid['_row_hash'] = [
                compute_raw_row_hash(row)
                for row in valid[HASH_COLUMNS].itertuples(index=False, name=None)
            ]
        else:
            valid['_row_hash'] = pd.Series(dtype='object')

        result['data'] = valid
    except Exception as error:
        result['validation_error'] = str(error)
    return result

