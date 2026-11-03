import pandas as pd

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


EXPECTED_COLUMN_COUNT = 16
SOURCE_COLUMNS = [
    'Order_ID', 'Agent_Age', 'Agent_Rating', 'Store_Latitude',
    'Store_Longitude', 'Drop_Latitude', 'Drop_Longitude', 'Order_Date',
    'Order_Time', 'Pickup_Time', 'Weather', 'Traffic', 'Vehicle',
    'Area', 'Delivery_Time', 'Category',
]
BATCH_CONFIG = {
    'INITIAL_FULL': ('2022-02-11', '2022-02-18', 6_982),
    'INCREMENTAL_01': ('2022-03-01', '2022-03-31', 30_658),
    'INCREMENTAL_02': ('2022-04-01', '2022-04-06', 6_099),
}


@transformer
def validate_incremental_amazon_delivery(payload, *args, **kwargs):
    batch_name = payload['batch_name']
    result = {
        'batch_name': batch_name,
        'source_file_name': payload['source_file_name'],
        'source_file_checksum': payload['source_file_checksum'],
        'data': pd.DataFrame(),
        'rows_read': 0,
        'validation_error': '',
    }
    if payload.get('read_error'):
        result['validation_error'] = payload['read_error']
        return result

    source_df = payload['data']
    try:
        actual_column_count = source_df.shape[1]
        if actual_column_count != EXPECTED_COLUMN_COUNT:
            raise ValueError(
                f'Sai số cột: nhận {actual_column_count}, cần {EXPECTED_COLUMN_COUNT}.'
            )
        if list(source_df.columns) != SOURCE_COLUMNS:
            raise ValueError(
                'Header CSV không đúng thứ tự/tên cột.\n'
                f'Nhận được: {list(source_df.columns)}\n'
                f'Mong đợi: {SOURCE_COLUMNS}'
            )

        source_df = source_df.copy()
        source_df['_source_row_number'] = range(1, len(source_df) + 1)
        parsed_order_dates = pd.to_datetime(
            source_df['Order_Date'], format='%Y-%m-%d', errors='raise'
        )
        start_date, end_date, expected_row_count = BATCH_CONFIG[batch_name]
        batch_mask = parsed_order_dates.between(
            pd.Timestamp(start_date), pd.Timestamp(end_date), inclusive='both'
        )
        batch_df = source_df.loc[batch_mask].copy()
        result['rows_read'] = len(batch_df)
        if len(batch_df) != expected_row_count:
            raise ValueError(
                f'{batch_name} có {len(batch_df):,} dòng sau khi lọc; '
                f'cần {expected_row_count:,} dòng.'
            )

        normalized_order_ids = batch_df['Order_ID'].astype(str).str.strip()
        blank_order_ids = normalized_order_ids.eq('')
        if blank_order_ids.any():
            raise ValueError(
                f'{batch_name} có {int(blank_order_ids.sum()):,} Order_ID NULL/rỗng.'
            )
        normalized_order_keys = normalized_order_ids.str.casefold()
        duplicate_mask = normalized_order_keys.duplicated(keep=False)
        if duplicate_mask.any():
            examples = normalized_order_ids.loc[duplicate_mask].head(10).tolist()
            raise ValueError(
                f'{batch_name} có Order_ID lặp trong batch. Ví dụ: {examples}'
            )
        result['data'] = batch_df
    except Exception as error:
        # Exporter cập nhật audit FAILED; không bỏ qua lỗi kiểm tra.
        result['validation_error'] = str(error)
    return result
