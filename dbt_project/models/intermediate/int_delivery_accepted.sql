-- The Fact and categorical Dimensions consume exactly the same accepted rows.
with rejected_rows as (
    select distinct staging_row_id
    from {{ ref('int_delivery_validation_errors') }}
)
select
    enriched.delivery_key,
    enriched.staging_row_id,
    enriched.order_id,
    enriched.order_date,
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
    enriched.weather_name,
    enriched.traffic_level,
    enriched.vehicle_type,
    enriched.area_name_raw,
    enriched.area_name,
    enriched.category_name,
    enriched.delivery_time_minutes,
    enriched.above_baseline_p90_flag,
    enriched.delivery_time_iqr_outlier_flag,
    enriched.pickup_delay_minutes,
    enriched.pickup_rollover_flag,
    enriched.delivery_distance_km,
    enriched.valid_distance_flag,
    enriched.distance_outlier_flag,
    enriched.distance_status,
    enriched.distance_band,
    enriched.delivery_count,
    enriched.missing_operational_context_flag,
    enriched.source_file_name,
    enriched.source_row_number,
    enriched.load_batch_id,
    enriched.loaded_at
from {{ ref('int_delivery_enriched') }} as enriched
left join rejected_rows as rejected
    on enriched.staging_row_id = rejected.staging_row_id
where rejected.staging_row_id is null
