-- No business key with a hard validation error may be present in the Fact.
select distinct fact.order_id
from {{ ref('fact_delivery') }} as fact
inner join {{ ref('delivery_rejections') }} as rejected
    on fact.order_id = rejected.order_id
