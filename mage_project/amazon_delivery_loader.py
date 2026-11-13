"""Shared source reader for full and incremental Mage pipelines."""

from __future__ import annotations

import hashlib
import os
from io import BytesIO
from typing import Any

import pandas as pd

from mage_project.amazon_delivery_contract import generate_batch_name, resolve_source_path


def load_amazon_delivery(batch_type: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    project_root = os.environ.get('BI_PROJECT_ROOT')
    if not project_root:
        raise RuntimeError(
            'Thiếu BI_PROJECT_ROOT. Hãy đặt biến môi trường rồi khởi động lại Mage.'
        )

    variables = kwargs.get('variables') if isinstance(kwargs.get('variables'), dict) else {}
    source_file_path = kwargs.get('source_file_path') or variables.get('source_file_path')
    source_path = resolve_source_path(project_root, source_file_path)
    if not source_path.is_file():
        raise FileNotFoundError(f'Không tìm thấy file: {source_path}')

    source_bytes = source_path.read_bytes()
    checksum = hashlib.sha256(source_bytes).hexdigest()
    batch_name = generate_batch_name(batch_type)
    try:
        source_df = pd.read_csv(
            BytesIO(source_bytes),
            dtype=str,
            encoding='utf-8',
            keep_default_na=False,
            na_filter=False,
        )
        read_error = ''
    except Exception as error:
        source_df = pd.DataFrame()
        read_error = str(error)

    return {
        'batch_name': batch_name,
        'batch_type': batch_type,
        'source_file_name': source_path.name,
        'source_file_checksum': checksum,
        'data': source_df,
        'read_error': read_error,
    }
