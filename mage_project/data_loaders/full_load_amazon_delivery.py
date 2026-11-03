import hashlib
import os
from io import BytesIO
from pathlib import Path

import pandas as pd

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def full_load_amazon_delivery(*args, **kwargs):
    project_root = os.environ.get('BI_PROJECT_ROOT')
    if not project_root:
        raise RuntimeError(
            'Thiếu BI_PROJECT_ROOT. Hãy đặt biến trong PowerShell rồi khởi động lại Mage.'
        )

    source_path = Path(project_root) / 'data' / 'raw' / 'amazon_delivery.csv'
    if not source_path.is_file():
        raise FileNotFoundError(f'Không tìm thấy file: {source_path}')

    # Đọc một snapshot byte duy nhất để checksum và DataFrame luôn khớp nhau.
    source_bytes = source_path.read_bytes()
    source_df = pd.read_csv(
        BytesIO(source_bytes),
        dtype=str,
        encoding='utf-8',
        keep_default_na=False,
        na_filter=False,
    )
    return {
        'source_file_name': source_path.name,
        'source_file_checksum': hashlib.sha256(source_bytes).hexdigest(),
        'data': source_df,
    }
