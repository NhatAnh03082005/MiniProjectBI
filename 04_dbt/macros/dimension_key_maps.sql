{% macro ensure_single_value_key_map(map_table, key_column, natural_column, natural_type, source_relation) %}
    if object_id(N'{{ map_table }}', N'U') is null
    begin
        create table {{ map_table }} (
            {{ key_column }} int identity(1,1) not null primary key,
            {{ natural_column }} {{ natural_type }} not null unique
        );
        set identity_insert {{ map_table }} on;
        insert into {{ map_table }} ({{ key_column }}, {{ natural_column }}) values (0, N'Unknown');
        set identity_insert {{ map_table }} off;
    end;

    merge {{ map_table }} as target
    using (
        select distinct coalesce({{ natural_column }}, N'Unknown') as {{ natural_column }}
        from {{ source_relation }}
    ) as source
        on target.{{ natural_column }} = source.{{ natural_column }}
    when not matched by target then
        insert ({{ natural_column }}) values (source.{{ natural_column }});
{% endmacro %}

{% macro ensure_delivery_condition_key_map(source_relation) %}
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
        values (0, N'Unknown', N'Unknown');
        set identity_insert dw.dim_delivery_condition_key_map off;
    end;

    merge dw.dim_delivery_condition_key_map as target
    using (
        select distinct
            coalesce(weather_name, N'Unknown') as weather_name,
            coalesce(traffic_level, N'Unknown') as traffic_level
        from {{ source_relation }}
    ) as source
        on target.weather_name = source.weather_name
        and target.traffic_level = source.traffic_level
    when not matched by target then
        insert (weather_name, traffic_level) values (source.weather_name, source.traffic_level);
{% endmacro %}
