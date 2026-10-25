-- depends_on: {{ ref('int_delivery_enriched') }}

{{ config(
    materialized='table',
    pre_hook="{{ ensure_single_value_key_map(
        'dw.dim_category_key_map',
        'category_key',
        'category_name',
        'nvarchar(64)',
        'int_delivery_enriched'
    ) }}"
) }}

select
    category_key,
    category_name
from dw.dim_category_key_map
