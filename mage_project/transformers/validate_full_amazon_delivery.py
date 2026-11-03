if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


EXPECTED_ROW_COUNT = 43_739
EXPECTED_COLUMN_COUNT = 16
SOURCE_COLUMNS = [
    'Order_ID', 'Agent_Age', 'Agent_Rating', 'Store_Latitude',
    'Store_Longitude', 'Drop_Latitude', 'Drop_Longitude', 'Order_Date',
    'Order_Time', 'Pickup_Time', 'Weather', 'Traffic', 'Vehicle',
    'Area', 'Delivery_Time', 'Category',
]


@transformer
def validate_full_amazon_delivery(payload, *args, **kwargs):
    source_df = payload['data']
    actual_row_count, actual_column_count = source_df.shape
    if actual_row_count != EXPECTED_ROW_COUNT:
        raise ValueError(
            f'Sai số dòng: nhận {actual_row_count:,}, cần {EXPECTED_ROW_COUNT:,}.'
        )
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
    return payload
