with staged as (

    select *
    from {{ ref('stg_amazon_delivery') }}

),

-- TODO(LOAD-01): Define the idempotency and duplicate-resolution policy for an
-- order_id that recurs across batches. The baseline source has one row per
-- order_id, so no arbitrary row is dropped here.
deduplication_pending as (

    select *
    from staged

),

categorized as (

    select
        *,
        coalesce(weather_name, 'Unknown') as weather_name_normalized,
        coalesce(traffic_level, 'Unknown') as traffic_level_normalized,
        coalesce(vehicle_type, 'Unknown') as vehicle_type_normalized,
        coalesce(area_name, 'Unknown') as area_name_normalized,
        coalesce(category_name, 'Unknown') as category_name_normalized,
        case
            when order_time is null then 'Unknown'
            when datepart(hour, order_time) < 6 then 'Night'
            when datepart(hour, order_time) < 12 then 'Morning'
            when datepart(hour, order_time) < 18 then 'Afternoon'
            else 'Evening'
        end as time_period,
        case
            when agent_age is null then 'Unknown'
            when agent_age < 18 then 'Under 18'
            when agent_age < 25 then '18-24'
            when agent_age < 35 then '25-34'
            when agent_age < 45 then '35-44'
            else '45+'
        end as age_group,
        case
            when agent_rating_raw is null then 'Unknown'
            when agent_rating_raw < 1 or agent_rating_raw > 5 then 'Invalid'
            when agent_rating_raw < 3 then '[1,3)'
            when agent_rating_raw < 4 then '[3,4)'
            when agent_rating_raw < 4.5 then '[4,4.5)'
            else '[4.5,5]'
        end as rating_group,
        case
            when order_date is not null and order_time is not null then
                dateadd(second, datediff(second, cast('00:00:00' as time), order_time), cast(order_date as datetime2))
        end as order_timestamp,
        case
            when order_date is not null and pickup_time is not null then
                dateadd(second, datediff(second, cast('00:00:00' as time), pickup_time), cast(order_date as datetime2))
        end as pickup_timestamp_same_day
    from deduplication_pending

),

pickup_enriched as (

    select
        *,
        case
            when order_timestamp is null or pickup_timestamp_same_day is null then null
            when pickup_time < order_time then dateadd(day, 1, pickup_timestamp_same_day)
            else pickup_timestamp_same_day
        end as pickup_timestamp,
        case
            when order_time is null or pickup_time is null then cast(null as bit)
            when pickup_time < order_time then cast(1 as bit)
            else cast(0 as bit)
        end as pickup_rollover_flag
    from categorized

),

distance_input as (

    select
        *,
        case
            when store_latitude between -90 and 90
                and drop_latitude between -90 and 90
                and store_longitude between -180 and 180
                and drop_longitude between -180 and 180
                and not (store_latitude = 0 and store_longitude = 0)
            then
                power(sin(radians(drop_latitude - store_latitude) / 2.0), 2)
                + cos(radians(store_latitude)) * cos(radians(drop_latitude))
                * power(sin(radians(drop_longitude - store_longitude) / 2.0), 2)
        end as haversine_a
    from pickup_enriched

),

distance_calculated as (

    select
        *,
        case
            when haversine_a is null then null
            when haversine_a < 0 then cast(0.0 as float)
            when haversine_a > 1 then cast(1.0 as float)
            else haversine_a
        end as haversine_a_clamped
    from distance_input

),

distance_enriched as (

    select
        *,
        case
            when haversine_a_clamped is not null then 2.0 * 6371.0 * asin(sqrt(haversine_a_clamped))
        end as delivery_distance_km_raw
    from distance_calculated

)

select
    convert(char(64), hashbytes('SHA2_256', order_id), 2) as delivery_key,
    staging_row_id,
    order_id,
    order_date,
    order_time,
    pickup_time,
    datepart(hour, order_time) as order_hour,
    time_period,
    agent_age,
    age_group,
    cast(case when agent_age < 18 then 1 else 0 end as bit) as underage_agent_flag,
    agent_rating_raw,
    cast(case when agent_rating_raw between 1 and 5 then agent_rating_raw end as decimal(4, 2)) as agent_rating_valid,
    rating_group,
    cast(case when agent_rating_raw between 1 and 5 then 1 else 0 end as bit) as valid_rating_flag,
    weather_name_normalized as weather_name,
    traffic_level_normalized as traffic_level,
    vehicle_type_normalized as vehicle_type,
    area_name_raw,
    area_name_normalized as area_name,
    category_name_normalized as category_name,
    delivery_time_minutes,
    cast(
        case
            when delivery_time_minutes is null then null
            when delivery_time_minutes > 195 then 1
            else 0
        end as bit
    ) as above_baseline_p90_flag,
    cast(
        case
            when delivery_time_minutes is null then null
            when delivery_time_minutes < -15 or delivery_time_minutes > 265 then 1
            else 0
        end as bit
    ) as delivery_time_iqr_outlier_flag,
    cast(
        case
            when order_timestamp is not null and pickup_timestamp is not null then
                datediff_big(second, order_timestamp, pickup_timestamp) / 60.0
        end as decimal(10, 2)
    ) as pickup_delay_minutes,
    pickup_rollover_flag,
    cast(case when delivery_distance_km_raw <= 50 then delivery_distance_km_raw end as float) as delivery_distance_km,
    cast(case when delivery_distance_km_raw <= 50 then 1 else 0 end as bit) as valid_distance_flag,
    case
        when delivery_distance_km_raw is null or delivery_distance_km_raw > 50 then 'Unknown'
        when delivery_distance_km_raw < 5 then '[0,5) km'
        when delivery_distance_km_raw < 10 then '[5,10) km'
        when delivery_distance_km_raw < 15 then '[10,15) km'
        when delivery_distance_km_raw < 20 then '[15,20) km'
        else '[20,50] km'
    end as distance_band,
    cast(1 as tinyint) as delivery_count,
    cast(
        case
            when order_time is null or weather_name is null or traffic_level is null then 1
            else 0
        end as bit
    ) as missing_operational_context_flag,
    source_file_name,
    source_row_number,
    load_batch_id,
    loaded_at
from distance_enriched
