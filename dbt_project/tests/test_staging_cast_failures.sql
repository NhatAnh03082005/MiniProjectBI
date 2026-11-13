-- Every conversion failure in a required source field must be quarantined.
{% set rule_set = var('delivery_rules') %}
{% set cast_fields = rule_set.fields | selectattr('cast_check') | list %}

with cast_failures as (
    select
        raw.staging_row_id,
        checks.column_name
    from {{ source('staging', 'raw_amazon_delivery') }} as raw
    inner join {{ ref('stg_amazon_delivery') }} as staged
        on raw.staging_row_id = staged.staging_row_id
    cross apply (values
        {% for field in cast_fields %}
        ({{ delivery_sql_string(field.source) }}, cast(raw.{{ field.source }} as nvarchar(4000)),
            cast(staged.{{ field.staged }} as nvarchar(4000))){{ "," if not loop.last else "" }}
        {% endfor %}
    ) as checks(column_name, raw_value, staged_value)
    where not {{ delivery_is_missing('checks.raw_value') }}
        and checks.staged_value is null
)

select failures.*
from cast_failures as failures
left join {{ ref('delivery_rejections') }} as rejected
    on failures.staging_row_id = rejected.staging_row_id
    and failures.column_name = rejected.column_name
    and rejected.error_code = 'INVALID_CAST'
where rejected.staging_row_id is null
