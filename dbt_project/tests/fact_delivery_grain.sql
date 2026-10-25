-- The Fact contract permits exactly one row for each valid order_id.
select
    order_id
from {{ ref('fact_delivery') }}
group by order_id
having count(*) <> 1
