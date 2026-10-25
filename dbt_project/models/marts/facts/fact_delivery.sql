{{ config(materialized='table') }}

with enriched as (

    select *
    from {{ ref('int_delivery_enriched') }}
    where order_id is not null

),

fact_rows as (

    select
        enriched.delivery_key,
        enriched.order_id,
        coalesce(dim_date.date_key, 0) as date_key,
        coalesce(dim_delivery_condition.delivery_condition_key, 0) as delivery_condition_key,
        coalesce(dim_vehicle.vehicle_key, 0) as vehicle_key,
        coalesce(dim_area.area_key, 0) as area_key,
        coalesce(dim_category.category_key, 0) as category_key,
        enriched.order_time,
        enriched.pickup_time,
        enriched.order_hour,
        enriched.time_period,
        enriched.agent_age,
        enriched.age_group,
        enriched.underage_agent_flag,
        enriched.agent_rating_raw,
        enriched.agent_rating_valid,
        enriched.rating_group,
        enriched.valid_rating_flag,
        enriched.delivery_time_minutes,
        enriched.above_baseline_p90_flag,
        enriched.delivery_time_iqr_outlier_flag,
        enriched.pickup_delay_minutes,
        enriched.pickup_rollover_flag,
        enriched.delivery_distance_km,
        enriched.valid_distance_flag,
        enriched.distance_band,
        enriched.delivery_count,
        enriched.missing_operational_context_flag,
        enriched.source_file_name,
        enriched.load_batch_id,
        enriched.loaded_at
    from enriched
    left join {{ ref('dim_date') }} as dim_date
        on enriched.order_date = dim_date.full_date
    left join {{ ref('dim_delivery_condition') }} as dim_delivery_condition
        on enriched.weather_name = dim_delivery_condition.weather_name
        and enriched.traffic_level = dim_delivery_condition.traffic_level
    left join {{ ref('dim_vehicle') }} as dim_vehicle
        on enriched.vehicle_type = dim_vehicle.vehicle_type
    left join {{ ref('dim_area') }} as dim_area
        on enriched.area_name = dim_area.area_name
    left join {{ ref('dim_category') }} as dim_category
        on enriched.category_name = dim_category.category_name

)

select *
from fact_rows
