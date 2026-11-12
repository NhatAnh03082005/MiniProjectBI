-- depends_on: {{ ref('int_delivery_accepted') }}

{{ config(
    materialized='table',
    pre_hook="{{ ensure_single_value_key_map(
        'dw.dim_category_key_map',
        'category_key',
        'category_name',
        'nvarchar(64)',
        'int_delivery_accepted'
    ) }}"
) }}

select
    key_map.category_key,
    key_map.category_name
from dw.dim_category_key_map as key_map
where key_map.category_name = {{ delivery_sql_string(var('delivery_rules').unknown_label) }}
    or exists (
        select 1
        from {{ ref('int_delivery_accepted') }} as accepted
        where accepted.category_name = key_map.category_name
    )
