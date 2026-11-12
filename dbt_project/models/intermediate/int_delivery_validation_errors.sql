-- One row per missing, unparseable, or out-of-range required source value.
-- Statistical outliers and underage agents remain warnings.
with staged as (
    select * from {{ ref('stg_amazon_delivery') }}
),
duplicate_orders as (
    select order_id
    from staged
    where order_id is not null
    group by order_id
    having count(*) > 1
),
checked as (
    select
        s.staging_row_id,
        s.order_id,
        s.source_file_name,
        s.source_row_number,
        s.load_batch_id,
        s.loaded_at,
        rules.column_name,
        rules.raw_value,
        validation.error_code,
        rules.expected_rule
    from staged as s
    inner join {{ source('staging', 'raw_amazon_delivery') }} as r
        on s.staging_row_id = r.staging_row_id
    left join duplicate_orders as d
        on s.order_id = d.order_id
    cross apply (values
        ('Order_ID', cast(r.Order_ID as nvarchar(4000)), cast(s.order_id as nvarchar(4000)),
            'required unique order ID after trimming'),
        ('Agent_Age', cast(r.Agent_Age as nvarchar(4000)), cast(s.agent_age as nvarchar(4000)),
            'required nonnegative smallint'),
        ('Agent_Rating', cast(r.Agent_Rating as nvarchar(4000)), cast(s.agent_rating_raw as nvarchar(4000)),
            'required decimal rating between 1 and 5'),
        ('Store_Latitude', cast(r.Store_Latitude as nvarchar(4000)), cast(s.store_latitude as nvarchar(4000)),
            'required latitude between -90 and 90'),
        ('Store_Longitude', cast(r.Store_Longitude as nvarchar(4000)), cast(s.store_longitude as nvarchar(4000)),
            'required longitude between -180 and 180'),
        ('Drop_Latitude', cast(r.Drop_Latitude as nvarchar(4000)), cast(s.drop_latitude as nvarchar(4000)),
            'required latitude between -90 and 90'),
        ('Drop_Longitude', cast(r.Drop_Longitude as nvarchar(4000)), cast(s.drop_longitude as nvarchar(4000)),
            'required longitude between -180 and 180'),
        ('Order_Date', cast(r.Order_Date as nvarchar(4000)), cast(s.order_date as nvarchar(4000)),
            'required date parseable with SQL Server style 23'),
        ('Order_Time', cast(r.Order_Time as nvarchar(4000)), cast(s.order_time as nvarchar(4000)),
            'required valid time'),
        ('Pickup_Time', cast(r.Pickup_Time as nvarchar(4000)), cast(s.pickup_time as nvarchar(4000)),
            'required valid time'),
        ('Vehicle', cast(r.Vehicle as nvarchar(4000)), cast(s.vehicle_type as nvarchar(4000)),
            'required vehicle category'),
        ('Area', cast(r.Area as nvarchar(4000)), cast(s.area_name as nvarchar(4000)),
            'required area category'),
        ('Delivery_Time', cast(r.Delivery_Time as nvarchar(4000)), cast(s.delivery_time_minutes as nvarchar(4000)),
            'required nonnegative decimal minutes'),
        ('Category', cast(r.Category as nvarchar(4000)), cast(s.category_name as nvarchar(4000)),
            'required delivery category')
    ) as rules(column_name, raw_value, normalized_value, expected_rule)
    cross apply (values (
        case
            when rules.raw_value is null
                or upper(ltrim(rtrim(rules.raw_value))) in ('', 'NAN', 'NULL')
                then case when rules.column_name = 'Order_ID' then 'MISSING_ORDER_ID'
                          else 'MISSING_VALUE' end
            when rules.normalized_value is null then 'INVALID_CAST'
            when rules.column_name in ('Vehicle', 'Area', 'Category')
                and upper(rules.normalized_value) = 'UNKNOWN' then 'MISSING_VALUE'
            when rules.column_name = 'Order_ID' and d.order_id is not null then 'DUPLICATE_ORDER_ID'
            when rules.column_name = 'Agent_Age' and s.agent_age < 0 then 'NEGATIVE_VALUE'
            when rules.column_name = 'Agent_Rating'
                and (s.agent_rating_raw < 1 or s.agent_rating_raw > 5) then 'OUT_OF_RANGE'
            when rules.column_name = 'Store_Latitude'
                and (s.store_latitude < -90 or s.store_latitude > 90) then 'OUT_OF_RANGE'
            when rules.column_name = 'Drop_Latitude'
                and (s.drop_latitude < -90 or s.drop_latitude > 90) then 'OUT_OF_RANGE'
            when rules.column_name = 'Store_Longitude'
                and (s.store_longitude < -180 or s.store_longitude > 180) then 'OUT_OF_RANGE'
            when rules.column_name = 'Drop_Longitude'
                and (s.drop_longitude < -180 or s.drop_longitude > 180) then 'OUT_OF_RANGE'
            when rules.column_name = 'Delivery_Time' and s.delivery_time_minutes < 0 then 'NEGATIVE_VALUE'
        end
    )) as validation(error_code)
    where validation.error_code is not null
)
select * from checked
