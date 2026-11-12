-- Descriptive categories may be Unknown; numerical and time inputs remain required.
select accepted.staging_row_id
from {{ ref('int_delivery_accepted') }} as accepted
inner join {{ ref('stg_amazon_delivery') }} as staged
    on accepted.staging_row_id = staged.staging_row_id
where accepted.order_id is null
   or accepted.agent_age is null
   or accepted.agent_rating_raw is null
   or staged.store_latitude is null
   or staged.store_longitude is null
   or staged.drop_latitude is null
   or staged.drop_longitude is null
   or accepted.order_date is null
   or accepted.order_time is null
   or accepted.pickup_time is null
   or accepted.delivery_time_minutes is null
   or accepted.vehicle_type is null
   or accepted.area_name is null
   or accepted.category_name is null
   or (staged.vehicle_type is null and accepted.vehicle_type <> 'Unknown')
   or (staged.area_name is null and accepted.area_name <> 'Unknown')
   or (staged.category_name is null and accepted.category_name <> 'Unknown')
