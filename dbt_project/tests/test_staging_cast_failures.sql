-- Parsing failures are expected to be quarantined, never silently lost.
with raw as (

    select *
    from {{ source('staging', 'raw_amazon_delivery') }}

),

staged as (

    select *
    from {{ ref('stg_amazon_delivery') }}

),
cast_failures as (

select
    raw.staging_row_id,
    'Agent_Age' as failing_column
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Agent_Age))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Agent_Age)) end is not null
  and staged.agent_age is null

union all

select raw.staging_row_id, 'Agent_Rating'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Agent_Rating))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Agent_Rating)) end is not null
  and staged.agent_rating_raw is null

union all

select raw.staging_row_id, 'Store_Latitude'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Store_Latitude))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Store_Latitude)) end is not null
  and staged.store_latitude is null

union all

select raw.staging_row_id, 'Store_Longitude'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Store_Longitude))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Store_Longitude)) end is not null
  and staged.store_longitude is null

union all

select raw.staging_row_id, 'Drop_Latitude'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Drop_Latitude))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Drop_Latitude)) end is not null
  and staged.drop_latitude is null

union all

select raw.staging_row_id, 'Drop_Longitude'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Drop_Longitude))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Drop_Longitude)) end is not null
  and staged.drop_longitude is null

union all

select raw.staging_row_id, 'Order_Date'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Order_Date))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Order_Date)) end is not null
  and staged.order_date is null

union all

select raw.staging_row_id, 'Order_Time'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Order_Time))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Order_Time)) end is not null
  and staged.order_time is null

union all

select raw.staging_row_id, 'Pickup_Time'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Pickup_Time))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Pickup_Time)) end is not null
  and staged.pickup_time is null

union all

select raw.staging_row_id, 'Delivery_Time'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Delivery_Time))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Delivery_Time)) end is not null
  and staged.delivery_time_minutes is null
)

select failures.*
from cast_failures as failures
left join {{ ref('delivery_rejections') }} as rejected
    on failures.staging_row_id = rejected.staging_row_id
    and failures.failing_column = rejected.column_name
    and rejected.error_code = 'INVALID_CAST'
where rejected.staging_row_id is null
