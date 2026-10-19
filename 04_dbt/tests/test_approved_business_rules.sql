-- Verify approved flags without excluding missing values or statistical outliers.
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
    or (delivery_time_minutes > 195 and above_baseline_p90_flag <> 1)
    or (delivery_time_minutes <= 195 and above_baseline_p90_flag <> 0)
    or (order_time is null and (order_hour is not null or pickup_delay_minutes is not null or pickup_rollover_flag is not null))
    or (missing_operational_context_flag <> case
        when order_time is null or weather_name = 'Unknown' or traffic_level = 'Unknown' then 1
        else 0
    end)
