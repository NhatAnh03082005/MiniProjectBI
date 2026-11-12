{% macro delivery_sql_string(value) -%}
N'{{ value | string | replace("'", "''") }}'
{%- endmacro %}

{% macro delivery_is_missing(expression) -%}
{%- set rules = var('delivery_rules') -%}
(
    {{ expression }} is null
    or upper(ltrim(rtrim(cast({{ expression }} as nvarchar(4000))))) in (
        {%- for token in rules.missing_tokens -%}
        {{ delivery_sql_string(token | upper) }}{{ ", " if not loop.last else "" }}
        {%- endfor -%}
    )
)
{%- endmacro %}

{% macro delivery_normalized_text(expression) -%}
case when {{ delivery_is_missing(expression) }} then null else ltrim(rtrim({{ expression }})) end
{%- endmacro %}

{% macro delivery_distance_label(value, distance_rule) -%}
{{ delivery_sql_string(
    value
    | replace('{max_valid_km}', distance_rule.max_valid_km | string)
    | replace('{last_band_start_km}', distance_rule.bands[-1].upper_exclusive_km | string)
) }}
{%- endmacro %}
