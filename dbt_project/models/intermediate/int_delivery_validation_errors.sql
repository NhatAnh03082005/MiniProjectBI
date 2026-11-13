-- One row per missing, unparseable, or out-of-range required source value.
-- Statistical outliers and underage agents remain warnings.
{% set rules_config = var('delivery_rules') %}
{% set business_key = (rules_config.fields | selectattr('unique') | list)[0] %}

with staged as (
    select * from {{ ref('stg_amazon_delivery') }}
),
duplicate_orders as (
    select {{ business_key.staged }}
    from staged
    where {{ business_key.staged }} is not null
    group by {{ business_key.staged }}
    having count(*) > 1
),
checked as (
    select
        s.staging_row_id,
        s.order_id,
        s.source_file_name,
        s.source_row_number,
        s.load_batch_id,
        s.loaded_at,
        rules.column_name,
        rules.raw_value,
        validation.error_code,
        rules.expected_rule
    from staged as s
    inner join {{ source('staging', 'raw_amazon_delivery') }} as r
        on s.staging_row_id = r.staging_row_id
    left join duplicate_orders as d
        on s.{{ business_key.staged }} = d.{{ business_key.staged }}
    cross apply (values
        {% for field in rules_config.fields %}
        {% set expected_rule = field.expected if field.required else field.expected | replace('required ', 'optional ') %}
        ({{ delivery_sql_string(field.source) }}, cast(r.{{ field.source }} as nvarchar(4000)),
            cast(s.{{ field.staged }} as nvarchar(4000)), {{ delivery_sql_string(expected_rule) }},
            {{ delivery_sql_string(field.missing_error | default('MISSING_VALUE')) }},
            {{ 1 if field.required else 0 }}){{ "," if not loop.last else "" }}
        {% endfor %}
    ) as rules(column_name, raw_value, normalized_value, expected_rule, missing_error, required_flag)
    cross apply (values (
        case
            when {{ delivery_is_missing('rules.raw_value') }}
                then case when rules.required_flag = 1 then rules.missing_error end
            when rules.normalized_value is null then 'INVALID_CAST'
            {% for field in rules_config.fields %}
            {% if field.required and field.unknown_if_missing | default(false) %}
            when rules.column_name = {{ delivery_sql_string(field.source) }}
                and upper(rules.normalized_value) = upper({{ delivery_sql_string(rules_config.unknown_label) }})
                then 'MISSING_VALUE'
            {% endif %}
            {% if field.unique | default(false) %}
            when rules.column_name = {{ delivery_sql_string(field.source) }}
                and d.{{ business_key.staged }} is not null then 'DUPLICATE_ORDER_ID'
            {% endif %}
            {% if field.range is defined %}
            {% set bounds = rules_config.ranges[field.range] %}
            when rules.column_name = {{ delivery_sql_string(field.source) }} and (
                {% if bounds.min is not none %}s.{{ field.staged }} < {{ bounds.min }}{% endif %}
                {% if bounds.min is not none and bounds.max is not none %}or{% endif %}
                {% if bounds.max is not none %}s.{{ field.staged }} > {{ bounds.max }}{% endif %}
            ) then {{ delivery_sql_string(bounds.error_code) }}
            {% endif %}
            {% endfor %}
        end
    )) as validation(error_code)
    where validation.error_code is not null
)
select * from checked
