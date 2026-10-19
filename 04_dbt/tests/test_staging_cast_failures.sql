-- A non-null-like raw value that becomes null after TRY_CONVERT is a parse error.
with raw as (

    select *
    from {{ source('staging', 'raw_amazon_delivery') }}

),

staged as (

    select *
    from {{ ref('stg_amazon_delivery') }}

)

select
    raw.staging_row_id,
    'agent_age' as failing_column
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Agent_Age))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Agent_Age)) end is not null
  and staged.agent_age is null

union all

select raw.staging_row_id, 'agent_rating'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Agent_Rating))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Agent_Rating)) end is not null
  and staged.agent_rating_raw is null

union all

select raw.staging_row_id, 'store_latitude'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Store_Latitude))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Store_Latitude)) end is not null
  and staged.store_latitude is null

union all

select raw.staging_row_id, 'store_longitude'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Store_Longitude))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Store_Longitude)) end is not null
  and staged.store_longitude is null

union all

select raw.staging_row_id, 'drop_latitude'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Drop_Latitude))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Drop_Latitude)) end is not null
  and staged.drop_latitude is null

union all

select raw.staging_row_id, 'drop_longitude'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Drop_Longitude))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Drop_Longitude)) end is not null
  and staged.drop_longitude is null

union all

select raw.staging_row_id, 'order_date'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Order_Date))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Order_Date)) end is not null
  and staged.order_date is null

union all

select raw.staging_row_id, 'order_time'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Order_Time))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Order_Time)) end is not null
  and staged.order_time is null

union all

select raw.staging_row_id, 'pickup_time'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Pickup_Time))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Pickup_Time)) end is not null
  and staged.pickup_time is null

union all

select raw.staging_row_id, 'delivery_time'
from raw
inner join staged on raw.staging_row_id = staged.staging_row_id
where case when upper(ltrim(rtrim(raw.Delivery_Time))) in ('', 'NAN', 'NULL') then null else ltrim(rtrim(raw.Delivery_Time)) end is not null
  and staged.delivery_time_minutes is null
