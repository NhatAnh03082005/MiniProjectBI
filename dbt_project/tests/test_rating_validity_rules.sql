-- Null ratings are allowed. Only values in [1, 5] are analysis-valid.
select *
from {{ ref('fact_delivery') }}
where
    (agent_rating_valid is not null and (agent_rating_valid < 1 or agent_rating_valid > 5))
    or (agent_rating_raw between 1 and 5 and (agent_rating_valid <> agent_rating_raw or valid_rating_flag <> 1))
    or ((agent_rating_raw is null or agent_rating_raw < 1 or agent_rating_raw > 5)
        and (agent_rating_valid is not null or valid_rating_flag <> 0))
