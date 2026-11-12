-- depends_on: {{ ref('int_delivery_accepted') }}

{{ config(
    materialized='table',
    pre_hook="{{ ensure_single_value_key_map(
        'dw.dim_vehicle_key_map',
        'vehicle_key',
        'vehicle_type',
        'nvarchar(32)',
        'int_delivery_accepted'
    ) }}"
) }}

select
    key_map.vehicle_key,
    key_map.vehicle_type
from dw.dim_vehicle_key_map as key_map
where key_map.vehicle_type = N'Unknown'
    or exists (
        select 1
        from {{ ref('int_delivery_accepted') }} as accepted
        where accepted.vehicle_type = key_map.vehicle_type
    )
