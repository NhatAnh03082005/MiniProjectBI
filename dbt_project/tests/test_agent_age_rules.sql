-- No maximum valid age is approved. The test rejects impossible negative ages
-- and verifies approved age-group and underage-flag behavior.
select *
from {{ ref('fact_delivery') }}
where
    agent_age < 0
    or (agent_age is null and (age_group <> 'Unknown' or underage_agent_flag <> 0))
    or (agent_age < 18 and (age_group <> 'Under 18' or underage_agent_flag <> 1))
    or (agent_age >= 18 and agent_age < 25 and age_group <> '18-24')
    or (agent_age >= 25 and agent_age < 35 and age_group <> '25-34')
    or (agent_age >= 35 and agent_age < 45 and age_group <> '35-44')
    or (agent_age >= 45 and age_group <> '45+')
