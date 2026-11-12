-- depends_on: {{ ref('int_delivery_accepted') }}

{{ config(
    materialized='table',
    pre_hook="{{ ensure_delivery_condition_key_map('int_delivery_accepted') }}"
) }}

select
    key_map.delivery_condition_key,
    key_map.weather_name,
    key_map.traffic_level
from dw.dim_delivery_condition_key_map as key_map
where (key_map.weather_name = {{ delivery_sql_string(var('delivery_rules').unknown_label) }}
    and key_map.traffic_level = {{ delivery_sql_string(var('delivery_rules').unknown_label) }})
    or exists (
        select 1
        from {{ ref('int_delivery_accepted') }} as accepted
        where accepted.weather_name = key_map.weather_name
          and accepted.traffic_level = key_map.traffic_level
    )
