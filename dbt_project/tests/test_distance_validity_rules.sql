select *
from {{ ref('fact_delivery') }}
where
    (valid_distance_flag = 1 and (delivery_distance_km is null or delivery_distance_km > 50))
    or (valid_distance_flag = 0 and delivery_distance_km is not null)
    or (valid_distance_flag = 0 and distance_band <> 'Unknown')
