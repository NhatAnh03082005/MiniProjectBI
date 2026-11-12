-- Accepted rows must satisfy configured required fields and optional labels.
{% set rule_set = var('delivery_rules') %}
{% set required_fields = rule_set.fields | selectattr('required') | list %}
{% set optional_categories = rule_set.fields | selectattr('unknown_if_missing') | list %}

select accepted.staging_row_id
from {{ ref('int_delivery_accepted') }} as accepted
inner join {{ ref('stg_amazon_delivery') }} as staged
    on accepted.staging_row_id = staged.staging_row_id
where
    {% for field in required_fields %}
    staged.{{ field.staged }} is null or
    {% endfor %}
    {% for field in optional_categories %}
    accepted.{{ field.staged }} is null
    or (staged.{{ field.staged }} is null
        and accepted.{{ field.staged }} <> {{ delivery_sql_string(rule_set.unknown_label) }})
    {{ "or" if not loop.last else "" }}
    {% endfor %}
