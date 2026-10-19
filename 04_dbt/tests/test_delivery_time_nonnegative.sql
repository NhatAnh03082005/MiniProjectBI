-- Missing delivery time is allowed; a populated value cannot be negative.
select *
from {{ ref('fact_delivery') }}
where delivery_time_minutes < 0
