-- Verify approved flags without excluding missing values or statistical outliers.
{% set rule_set = var('delivery_rules') %}

with fact_with_condition as (

    select
        fact_delivery.*,
        dim_delivery_condition.weather_name,
        dim_delivery_condition.traffic_level
    from {{ ref('fact_delivery') }} as fact_delivery
    inner join {{ ref('dim_delivery_condition') }} as dim_delivery_condition
        on fact_delivery.delivery_condition_key = dim_delivery_condition.delivery_condition_key

)

select *
from fact_with_condition
where
    (delivery_time_minutes is null and above_baseline_p90_flag is not null)
    or (delivery_time_minutes > {{ rule_set.baseline_p90_minutes }} and above_baseline_p90_flag <> 1)
    or (delivery_time_minutes <= {{ rule_set.baseline_p90_minutes }} and above_baseline_p90_flag <> 0)
    or (order_time is null and (order_hour is not null or pickup_delay_minutes is not null or pickup_rollover_flag is not null))
    or (missing_operational_context_flag <> case
        when
            {% for context_field in rule_set.operational_context_fields %}
            {{ context_field.staged }} is null
            {% if context_field.unknown_is_missing %}
            or upper({{ context_field.staged }}) = upper({{ delivery_sql_string(rule_set.unknown_label) }})
            {% endif %}
            {{ "or" if not loop.last else "" }}
            {% endfor %}
        then 1
        else 0
    end)
