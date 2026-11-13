{% macro validate_delivery_rules() %}
    {% set rules = var('delivery_rules') %}
    {% set unique_fields = rules.fields | selectattr('unique') | list %}
    {% if unique_fields | length != 1 or not unique_fields[0].required %}
        {{ exceptions.raise_compiler_error('delivery_rules must have exactly one required business key') }}
    {% endif %}
    {% if '' not in rules.missing_tokens or not rules.unknown_label %}
        {{ exceptions.raise_compiler_error('delivery_rules needs an empty missing token and an Unknown label') }}
    {% endif %}
    {% if rules.reject_warning_severity not in ['warn', 'error'] %}
        {{ exceptions.raise_compiler_error('reject_warning_severity must be warn or error') }}
    {% endif %}
    {% for field in rules.fields %}
        {% if field.range is defined and field.range not in rules.ranges %}
            {{ exceptions.raise_compiler_error('Unknown range for ' ~ field.source) }}
        {% endif %}
    {% endfor %}
    {% for name, bounds in rules.ranges.items() %}
        {% if bounds.min is not none and bounds.max is not none and bounds.min > bounds.max %}
            {{ exceptions.raise_compiler_error('Invalid min/max for ' ~ name) }}
        {% endif %}
    {% endfor %}
    {% for groups, limit_key in [(rules.age_groups, 'upper_exclusive'),
                                 (rules.rating_groups, 'upper_exclusive'),
                                 (rules.time_periods, 'upper_exclusive_hour'),
                                 (rules.distance.bands, 'upper_exclusive_km')] %}
        {% if groups | length == 0 %}
            {{ exceptions.raise_compiler_error('Configured groups cannot be empty') }}
        {% endif %}
        {% for group in groups %}
            {% if not loop.first and group[limit_key] <= groups[loop.index0 - 1][limit_key] %}
                {{ exceptions.raise_compiler_error('Configured group boundaries must increase') }}
            {% endif %}
        {% endfor %}
    {% endfor %}
    {% if rules.distance.max_valid_km <= rules.distance.bands[-1].upper_exclusive_km
          or rules.distance.earth_radius_km <= 0 %}
        {{ exceptions.raise_compiler_error('Distance limit must exceed band boundaries; Earth radius must be positive') }}
    {% endif %}
    {% if rules.time_periods[-1].upper_exclusive_hour >= 24 %}
        {{ exceptions.raise_compiler_error('Time period boundaries must be before 24:00') }}
    {% endif %}
    {% if rules.date_calendar.start > rules.date_calendar.end %}
        {{ exceptions.raise_compiler_error('Calendar start must not follow calendar end') }}
    {% endif %}
    {% set calendar_start = modules.datetime.datetime.strptime(rules.date_calendar.start, '%Y-%m-%d') %}
    {% set calendar_end = modules.datetime.datetime.strptime(rules.date_calendar.end, '%Y-%m-%d') %}
    {% if (calendar_end - calendar_start).days > 9999 %}
        {{ exceptions.raise_compiler_error('Configured calendar exceeds the 10,000-day generator') }}
    {% endif %}
    {{ return('select 1') }}
{% endmacro %}
