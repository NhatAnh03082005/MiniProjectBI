-- depends_on: {{ ref('int_delivery_enriched') }}

{{ config(
    materialized='table',
    pre_hook="{{ ensure_delivery_condition_key_map('int_delivery_enriched') }}"
) }}

select
    delivery_condition_key,
    weather_name,
    traffic_level
from dw.dim_delivery_condition_key_map
