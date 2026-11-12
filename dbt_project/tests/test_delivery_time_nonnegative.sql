-- The accepted delivery time must satisfy its configured range.
{% set bounds = var('delivery_rules').ranges.delivery_time %}

select *
from {{ ref('fact_delivery') }}
where delivery_time_minutes < {{ bounds.min }}
{% if bounds.max is not none %}
    or delivery_time_minutes > {{ bounds.max }}
{% endif %}
