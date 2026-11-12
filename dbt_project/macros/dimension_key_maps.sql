{% macro ensure_single_value_key_map(
    map_table,
    key_column,
    natural_column,
    natural_type,
    source_model
) %}
    if object_id(N'{{ map_table }}', N'U') is null
    begin
        create table {{ map_table }} (
            {{ key_column }} int identity(1,1) not null primary key,
            {{ natural_column }} {{ natural_type }} not null unique
        );
        set identity_insert {{ map_table }} on;
        insert into {{ map_table }} ({{ key_column }}, {{ natural_column }})
        values (0, {{ delivery_sql_string(var('delivery_rules').unknown_label) }});
        set identity_insert {{ map_table }} off;
    end;

    if exists (
        select 1 from {{ map_table }}
        where {{ key_column }} = 0
            and {{ natural_column }} <> {{ delivery_sql_string(var('delivery_rules').unknown_label) }}
    )
    begin
        if exists (
            select 1 from {{ map_table }}
            where {{ natural_column }} = {{ delivery_sql_string(var('delivery_rules').unknown_label) }}
                and {{ key_column }} <> 0
        )
            throw 50001, 'Configured Unknown label already has a different key', 1;
        update {{ map_table }}
        set {{ natural_column }} = {{ delivery_sql_string(var('delivery_rules').unknown_label) }}
        where {{ key_column }} = 0;
    end;

    merge {{ map_table }} as target
    using (
        select distinct coalesce({{ natural_column }}, {{ delivery_sql_string(var('delivery_rules').unknown_label) }}) as {{ natural_column }}
        from {{ ref(source_model) }}
    ) as source
        on target.{{ natural_column }} = source.{{ natural_column }}
    when not matched by target then
        insert ({{ natural_column }}) values (source.{{ natural_column }});
{% endmacro %}

{% macro ensure_delivery_condition_key_map(source_model) %}
    if object_id(N'dw.dim_delivery_condition_key_map', N'U') is null
    begin
        create table dw.dim_delivery_condition_key_map (
            delivery_condition_key int identity(1,1) not null primary key,
            weather_name nvarchar(32) not null,
            traffic_level nvarchar(32) not null,
            constraint uq_dim_delivery_condition_key_map unique (weather_name, traffic_level)
        );
        set identity_insert dw.dim_delivery_condition_key_map on;
        insert into dw.dim_delivery_condition_key_map (delivery_condition_key, weather_name, traffic_level)
        values (0, {{ delivery_sql_string(var('delivery_rules').unknown_label) }},
            {{ delivery_sql_string(var('delivery_rules').unknown_label) }});
        set identity_insert dw.dim_delivery_condition_key_map off;
    end;

    if exists (
        select 1 from dw.dim_delivery_condition_key_map
        where delivery_condition_key = 0
            and (weather_name <> {{ delivery_sql_string(var('delivery_rules').unknown_label) }}
                or traffic_level <> {{ delivery_sql_string(var('delivery_rules').unknown_label) }})
    )
    begin
        if exists (
            select 1 from dw.dim_delivery_condition_key_map
            where weather_name = {{ delivery_sql_string(var('delivery_rules').unknown_label) }}
                and traffic_level = {{ delivery_sql_string(var('delivery_rules').unknown_label) }}
                and delivery_condition_key <> 0
        )
            throw 50002, 'Configured Unknown combination already has a different key', 1;
        update dw.dim_delivery_condition_key_map
        set weather_name = {{ delivery_sql_string(var('delivery_rules').unknown_label) }},
            traffic_level = {{ delivery_sql_string(var('delivery_rules').unknown_label) }}
        where delivery_condition_key = 0;
    end;

    merge dw.dim_delivery_condition_key_map as target
    using (
        select distinct
            coalesce(weather_name, {{ delivery_sql_string(var('delivery_rules').unknown_label) }}) as weather_name,
            coalesce(traffic_level, {{ delivery_sql_string(var('delivery_rules').unknown_label) }}) as traffic_level
        from {{ ref(source_model) }}
    ) as source
        on target.weather_name = source.weather_name
        and target.traffic_level = source.traffic_level
    when not matched by target then
        insert (weather_name, traffic_level) values (source.weather_name, source.traffic_level);
{% endmacro %}
