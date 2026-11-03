import hashlib
import os
from io import BytesIO
from pathlib import Path

import pandas as pd

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


VALID_BATCH_NAMES = ('INITIAL_FULL', 'INCREMENTAL_01', 'INCREMENTAL_02')


@data_loader
def incremental_load_amazon_delivery(*args, **kwargs):
    batch_name = kwargs.get('batch_name')
    if not batch_name and isinstance(kwargs.get('variables'), dict):
        batch_name = kwargs['variables'].get('batch_name')
    if not isinstance(batch_name, str) or not batch_name.strip():
        raise ValueError(
            'Thiếu runtime variable batch_name. Giá trị hợp lệ: '
            + ', '.join(VALID_BATCH_NAMES)
        )
    batch_name = batch_name.strip().upper()
    if batch_name not in VALID_BATCH_NAMES:
        raise ValueError(
            f'batch_name không hợp lệ: {batch_name!r}. Giá trị hợp lệ: '
            + ', '.join(VALID_BATCH_NAMES)
        )

    project_root = os.environ.get('BI_PROJECT_ROOT')
    if not project_root:
        raise RuntimeError(
            'Thiếu BI_PROJECT_ROOT. Hãy đặt biến trong PowerShell rồi khởi động lại Mage.'
        )
    source_path = Path(project_root) / 'data' / 'raw' / 'amazon_delivery.csv'
    if not source_path.is_file():
        raise FileNotFoundError(f'Không tìm thấy file: {source_path}')

    source_bytes = source_path.read_bytes()
    file_checksum = hashlib.sha256(source_bytes).hexdigest()
    try:
        source_df = pd.read_csv(
            BytesIO(source_bytes),
            dtype=str,
            encoding='utf-8',
            keep_default_na=False,
            na_filter=False,
        )
        return {
            'batch_name': batch_name,
            'source_file_name': source_path.name,
            'source_file_checksum': file_checksum,
            'data': source_df,
            'read_error': '',
        }
    except Exception as error:
        # Để exporter ghi FAILED vào audit như luồng incremental gốc.
        return {
            'batch_name': batch_name,
            'source_file_name': source_path.name,
            'source_file_checksum': file_checksum,
            'data': pd.DataFrame(),
            'read_error': str(error),
        }
