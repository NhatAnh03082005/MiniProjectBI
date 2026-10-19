{{ config(
    materialized='table',
    pre_hook=ensure_single_value_key_map(
        'dw.dim_area_key_map',
        'area_key',
        'area_name',
        'nvarchar(64)',
        ref('int_delivery_enriched')
    )
) }}

select
    area_key,
    area_name
from dw.dim_area_key_map
