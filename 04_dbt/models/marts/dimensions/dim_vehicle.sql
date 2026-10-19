{{ config(
    materialized='table',
    pre_hook=ensure_single_value_key_map(
        'dw.dim_vehicle_key_map',
        'vehicle_key',
        'vehicle_type',
        'nvarchar(32)',
        ref('int_delivery_enriched')
    )
) }}

select
    vehicle_key,
    vehicle_type
from dw.dim_vehicle_key_map
