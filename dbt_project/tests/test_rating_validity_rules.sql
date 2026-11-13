-- Rating range and validity flags follow the configured policy.
{% set rating_range = var('delivery_rules').ranges.agent_rating %}

select *
from {{ ref('fact_delivery') }}
where
    (agent_rating_raw is not null and (agent_rating_raw < {{ rating_range.min }}
        or agent_rating_raw > {{ rating_range.max }}))
    or
    (agent_rating_valid is not null and (agent_rating_valid < {{ rating_range.min }}
        or agent_rating_valid > {{ rating_range.max }}))
    or (agent_rating_raw between {{ rating_range.min }} and {{ rating_range.max }}
        and (agent_rating_valid <> agent_rating_raw or valid_rating_flag <> 1))
    or ((agent_rating_raw is null or agent_rating_raw < {{ rating_range.min }}
        or agent_rating_raw > {{ rating_range.max }})
        and (agent_rating_valid is not null or valid_rating_flag <> 0))
