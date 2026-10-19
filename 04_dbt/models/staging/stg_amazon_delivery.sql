with source_data as (

    select *
    from {{ source('staging', 'raw_amazon_delivery') }}

),

trimmed as (

    select
        staging_row_id,
        case when upper(ltrim(rtrim(Order_ID))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(Order_ID)) end as order_id_text,
        case when upper(ltrim(rtrim(Agent_Age))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(Agent_Age)) end as agent_age_text,
        case when upper(ltrim(rtrim(Agent_Rating))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(Agent_Rating)) end as agent_rating_text,
        case when upper(ltrim(rtrim(Store_Latitude))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(Store_Latitude)) end as store_latitude_text,
        case when upper(ltrim(rtrim(Store_Longitude))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(Store_Longitude)) end as store_longitude_text,
        case when upper(ltrim(rtrim(Drop_Latitude))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(Drop_Latitude)) end as drop_latitude_text,
        case when upper(ltrim(rtrim(Drop_Longitude))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(Drop_Longitude)) end as drop_longitude_text,
        case when upper(ltrim(rtrim(Order_Date))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(Order_Date)) end as order_date_text,
        case when upper(ltrim(rtrim(Order_Time))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(Order_Time)) end as order_time_text,
        case when upper(ltrim(rtrim(Pickup_Time))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(Pickup_Time)) end as pickup_time_text,
        case when upper(ltrim(rtrim(Weather))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(Weather)) end as weather_name,
        case when upper(ltrim(rtrim(Traffic))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(Traffic)) end as traffic_level,
        case when upper(ltrim(rtrim(Vehicle))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(Vehicle)) end as vehicle_type,
        case when upper(ltrim(rtrim(Area))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(Area)) end as area_name_raw,
        case when upper(ltrim(rtrim(Delivery_Time))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(Delivery_Time)) end as delivery_time_text,
        case when upper(ltrim(rtrim(Category))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(Category)) end as category_name,
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
    try_convert(date, order_date_text, 23) as order_date,
    try_convert(time(0), order_time_text) as order_time,
    try_convert(time(0), pickup_time_text) as pickup_time,
    weather_name,
    traffic_level,
    vehicle_type,
    area_name_raw,
    case
        when area_name_raw = 'Metropolitian' then 'Metropolitan'
        else area_name_raw
    end as area_name,
    try_convert(decimal(10, 2), delivery_time_text) as delivery_time_minutes,
    category_name,
    source_file_name,
    source_row_number,
    load_batch_id,
    loaded_at
from trimmed
