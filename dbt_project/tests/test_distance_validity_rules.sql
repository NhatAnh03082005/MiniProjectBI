select *
from {{ ref('fact_delivery') }}
where
    (valid_distance_flag = 1 and (delivery_distance_km is null or delivery_distance_km > 50))
    or (valid_distance_flag = 0 and delivery_distance_km is not null and delivery_distance_km <= 50)
    or (delivery_distance_km > 50 and (distance_outlier_flag <> 1
        or distance_status <> 'Outlier >50 km' or distance_band <> '>50 km'))
    or (delivery_distance_km is null and (distance_outlier_flag <> 0
        or valid_distance_flag <> 0 or distance_status <> 'Store coordinates (0,0)'
        or distance_band <> 'Not calculable (Store 0,0)'))
    or (delivery_distance_km <= 50 and (distance_outlier_flag <> 0
        or distance_status <> 'Valid'))
