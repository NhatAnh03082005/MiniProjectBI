{% set rules = var('delivery_rules') %}

with source_data as (

    select *
    from {{ source('staging', 'raw_amazon_delivery') }}

),

trimmed as (

    select
        staging_row_id,
        {{ delivery_normalized_text('Order_ID') }} as order_id_text,
        {{ delivery_normalized_text('Agent_Age') }} as agent_age_text,
        {{ delivery_normalized_text('Agent_Rating') }} as agent_rating_text,
        {{ delivery_normalized_text('Store_Latitude') }} as store_latitude_text,
        {{ delivery_normalized_text('Store_Longitude') }} as store_longitude_text,
        {{ delivery_normalized_text('Drop_Latitude') }} as drop_latitude_text,
        {{ delivery_normalized_text('Drop_Longitude') }} as drop_longitude_text,
        {{ delivery_normalized_text('Order_Date') }} as order_date_text,
        {{ delivery_normalized_text('Order_Time') }} as order_time_text,
        {{ delivery_normalized_text('Pickup_Time') }} as pickup_time_text,
        {{ delivery_normalized_text('Weather') }} as weather_name,
        {{ delivery_normalized_text('Traffic') }} as traffic_level,
        {{ delivery_normalized_text('Vehicle') }} as vehicle_type,
        {{ delivery_normalized_text('Area') }} as area_name_raw,
        {{ delivery_normalized_text('Delivery_Time') }} as delivery_time_text,
        {{ delivery_normalized_text('Category') }} as category_name,
        source_file_name,
        source_row_number,
        load_batch_id,
        loaded_at
    from source_data

)

select
    staging_row_id,
    order_id_text as order_id,
    try_convert(smallint, agent_age_text) as agent_age,
    try_convert(decimal(4, 2), agent_rating_text) as agent_rating_raw,
    try_convert(decimal(12, 8), store_latitude_text) as store_latitude,
    try_convert(decimal(12, 8), store_longitude_text) as store_longitude,
    try_convert(decimal(12, 8), drop_latitude_text) as drop_latitude,
    try_convert(decimal(12, 8), drop_longitude_text) as drop_longitude,
    try_convert(date, order_date_text, {{ rules.date_parse_style }}) as order_date,
    try_convert(time(0), order_time_text) as order_time,
    try_convert(time(0), pickup_time_text) as pickup_time,
    weather_name,
    traffic_level,
    vehicle_type,
    area_name_raw,
    case
        {% for source_name, normalized_name in rules.area_aliases.items() %}
        when area_name_raw = {{ delivery_sql_string(source_name) }} then {{ delivery_sql_string(normalized_name) }}
        {% endfor %}
        else area_name_raw
    end as area_name,
    try_convert(decimal(10, 2), delivery_time_text) as delivery_time_minutes,
    category_name,
    source_file_name,
    source_row_number,
    load_batch_id,
    loaded_at
from trimmed
