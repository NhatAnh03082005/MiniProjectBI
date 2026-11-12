{{ config(materialized='table') }}

-- Current rejection state, rebuilt with the Fact. Raw values remain in staging.
select
    staging_row_id,
    order_id,
    source_file_name,
    source_row_number,
    load_batch_id,
    loaded_at,
    column_name,
    raw_value,
    error_code,
    expected_rule
from {{ ref('int_delivery_validation_errors') }}
