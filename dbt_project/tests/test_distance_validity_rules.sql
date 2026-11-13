{% set distance_rule = var('delivery_rules').distance %}

select *
from {{ ref('fact_delivery') }}
where
    (valid_distance_flag = 1 and (delivery_distance_km is null
        or delivery_distance_km > {{ distance_rule.max_valid_km }}))
    or (valid_distance_flag = 0 and delivery_distance_km is not null
        and delivery_distance_km <= {{ distance_rule.max_valid_km }})
    or (delivery_distance_km > {{ distance_rule.max_valid_km }} and (distance_outlier_flag <> 1
        or distance_status <> {{ delivery_distance_label(distance_rule.status_outlier, distance_rule) }}
        or distance_band <> {{ delivery_distance_label(distance_rule.band_outlier, distance_rule) }}))
    or (delivery_distance_km is null and (distance_outlier_flag <> 0
        or valid_distance_flag <> 0 or distance_status is null or distance_band is null
        or not (
            (distance_status = {{ delivery_sql_string(distance_rule.status_invalid_store) }}
                and distance_band = {{ delivery_sql_string(distance_rule.band_invalid_store) }})
            or (distance_status = {{ delivery_sql_string(distance_rule.status_not_calculable) }}
                and distance_band = {{ delivery_sql_string(distance_rule.band_not_calculable) }})
        )))
    or (delivery_distance_km <= {{ distance_rule.max_valid_km }} and (distance_outlier_flag <> 0
        or distance_status <> {{ delivery_sql_string(distance_rule.status_valid) }}))
