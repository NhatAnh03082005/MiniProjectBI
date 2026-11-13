-- Verify the configured age range, groups, and underage flag.
{% set rule_set = var('delivery_rules') %}
{% set age_range = rule_set.ranges.agent_age %}
{% set adult_age = rule_set.age_groups[0].upper_exclusive %}

select *
from {{ ref('fact_delivery') }}
where
    agent_age < {{ age_range.min }}
    {% if age_range.max is not none %}
    or agent_age > {{ age_range.max }}
    {% endif %}
    or (agent_age is null and (age_group <> {{ delivery_sql_string(rule_set.unknown_label) }}
        or underage_agent_flag <> 0))
    or (agent_age < {{ adult_age }} and underage_agent_flag <> 1)
    or (agent_age >= {{ adult_age }} and underage_agent_flag <> 0)
    {% for group in rule_set.age_groups %}
    or ({% if not loop.first %}agent_age >= {{ rule_set.age_groups[loop.index0 - 1].upper_exclusive }} and{% endif %}
        agent_age < {{ group.upper_exclusive }} and age_group <> {{ delivery_sql_string(group.label) }})
    {% endfor %}
    or (agent_age >= {{ rule_set.age_groups[-1].upper_exclusive }}
        and age_group <> {{ delivery_sql_string(rule_set.age_group_else) }})
