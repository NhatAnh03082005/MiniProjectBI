{% set rule_set = var('delivery_rules') %}
{% set rating_range = rule_set.ranges.agent_rating %}
{% set distance_rule = rule_set.distance %}

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
        {% for field in rule_set.fields %}
        {% if field.unknown_if_missing | default(false) %}
        coalesce({{ field.staged }}, {{ delivery_sql_string(rule_set.unknown_label) }}) as {{ field.normalized }},
        {% endif %}
        {% endfor %}
        case
            when order_time is null then {{ delivery_sql_string(rule_set.unknown_label) }}
            {% for period in rule_set.time_periods %}
            when datepart(hour, order_time) < {{ period.upper_exclusive_hour }} then {{ delivery_sql_string(period.label) }}
            {% endfor %}
            else {{ delivery_sql_string(rule_set.time_period_else) }}
        end as time_period,
        case
            when agent_age is null then {{ delivery_sql_string(rule_set.unknown_label) }}
            {% for age_group in rule_set.age_groups %}
            when agent_age < {{ age_group.upper_exclusive }} then {{ delivery_sql_string(age_group.label) }}
            {% endfor %}
            else {{ delivery_sql_string(rule_set.age_group_else) }}
        end as age_group,
        case
            when agent_rating_raw is null then {{ delivery_sql_string(rule_set.unknown_label) }}
            when agent_rating_raw < {{ rating_range.min }} or agent_rating_raw > {{ rating_range.max }}
                then {{ delivery_sql_string(rule_set.invalid_rating_label) }}
            {% for rating_group in rule_set.rating_groups %}
            when agent_rating_raw < {{ rating_group.upper_exclusive }} then {{ delivery_sql_string(rating_group.label) }}
            {% endfor %}
            else {{ delivery_sql_string(rule_set.rating_group_else) }}
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
            when store_latitude between {{ rule_set.ranges.latitude.min }} and {{ rule_set.ranges.latitude.max }}
                and drop_latitude between {{ rule_set.ranges.latitude.min }} and {{ rule_set.ranges.latitude.max }}
                and store_longitude between {{ rule_set.ranges.longitude.min }} and {{ rule_set.ranges.longitude.max }}
                and drop_longitude between {{ rule_set.ranges.longitude.min }} and {{ rule_set.ranges.longitude.max }}
                and not (store_latitude = {{ distance_rule.invalid_store_latitude }}
                    and store_longitude = {{ distance_rule.invalid_store_longitude }})
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
            when haversine_a_clamped is not null then 2.0 * {{ distance_rule.earth_radius_km }} * asin(sqrt(haversine_a_clamped))
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
    cast(case when agent_age < {{ rule_set.age_groups[0].upper_exclusive }} then 1 else 0 end as bit) as underage_agent_flag,
    agent_rating_raw,
    cast(case when agent_rating_raw between {{ rating_range.min }} and {{ rating_range.max }} then agent_rating_raw end as decimal(4, 2)) as agent_rating_valid,
    rating_group,
    cast(case when agent_rating_raw between {{ rating_range.min }} and {{ rating_range.max }} then 1 else 0 end as bit) as valid_rating_flag,
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
            when delivery_time_minutes > {{ rule_set.baseline_p90_minutes }} then 1
            else 0
        end as bit
    ) as above_baseline_p90_flag,
    cast(
        case
            when delivery_time_minutes is null then null
            when delivery_time_minutes < {{ rule_set.delivery_time_iqr.lower_minutes }}
                or delivery_time_minutes > {{ rule_set.delivery_time_iqr.upper_minutes }} then 1
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
    cast(delivery_distance_km_raw as float) as delivery_distance_km,
    cast(case when delivery_distance_km_raw <= {{ distance_rule.max_valid_km }} then 1 else 0 end as bit) as valid_distance_flag,
    cast(case when delivery_distance_km_raw > {{ distance_rule.max_valid_km }} then 1 else 0 end as bit) as distance_outlier_flag,
    case
        when store_latitude = {{ distance_rule.invalid_store_latitude }}
            and store_longitude = {{ distance_rule.invalid_store_longitude }}
            then {{ delivery_sql_string(distance_rule.status_invalid_store) }}
        when delivery_distance_km_raw is null then {{ delivery_sql_string(distance_rule.status_not_calculable) }}
        when delivery_distance_km_raw > {{ distance_rule.max_valid_km }} then {{ delivery_distance_label(distance_rule.status_outlier, distance_rule) }}
        else {{ delivery_sql_string(distance_rule.status_valid) }}
    end as distance_status,
    case
        when store_latitude = {{ distance_rule.invalid_store_latitude }}
            and store_longitude = {{ distance_rule.invalid_store_longitude }}
            then {{ delivery_sql_string(distance_rule.band_invalid_store) }}
        when delivery_distance_km_raw is null then {{ delivery_sql_string(distance_rule.band_not_calculable) }}
        when delivery_distance_km_raw > {{ distance_rule.max_valid_km }} then {{ delivery_distance_label(distance_rule.band_outlier, distance_rule) }}
        {% for band in distance_rule.bands %}
        when delivery_distance_km_raw < {{ band.upper_exclusive_km }} then {{ delivery_sql_string(band.label) }}
        {% endfor %}
        else {{ delivery_distance_label(distance_rule.band_else, distance_rule) }}
    end as distance_band,
    cast(1 as tinyint) as delivery_count,
    cast(
        case
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
        end as bit
    ) as missing_operational_context_flag,
    source_file_name,
    source_row_number,
    load_batch_id,
    loaded_at
from distance_enriched
