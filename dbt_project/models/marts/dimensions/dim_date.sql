{{ config(materialized='table') }}
{% set rule_set = var('delivery_rules') %}

with digits as (

    select digit
    from (
        values
            (0), (1), (2), (3), (4),
            (5), (6), (7), (8), (9)
    ) as values_table(digit)

),

numbers as (

    select
        ones.digit
        + tens.digit * 10
        + hundreds.digit * 100
        + thousands.digit * 1000 as day_number
    from digits as ones
    cross join digits as tens
    cross join digits as hundreds
    cross join digits as thousands

),

calendar as (

    select
        dateadd(
            day,
            day_number,
            cast({{ delivery_sql_string(rule_set.date_calendar.start) }} as date)
        ) as full_date
    from numbers
    where day_number <= datediff(
        day,
        cast({{ delivery_sql_string(rule_set.date_calendar.start) }} as date),
        cast({{ delivery_sql_string(rule_set.date_calendar.end) }} as date)
    )

),

calendar_attributes as (

    select
        convert(int, convert(char(8), full_date, 112)) as date_key,
        full_date,
        datepart(day, full_date) as day_of_month,
        case ((datediff(day, cast('19000101' as date), full_date) % 7) + 7) % 7
            when 0 then 'Monday'
            when 1 then 'Tuesday'
            when 2 then 'Wednesday'
            when 3 then 'Thursday'
            when 4 then 'Friday'
            when 5 then 'Saturday'
            when 6 then 'Sunday'
        end as day_name,
        (((datediff(day, cast('19000101' as date), full_date) % 7) + 7) % 7) + 1 as day_of_week_number,
        datepart(iso_week, full_date) as week_of_year,
        datepart(month, full_date) as month_number,
        concat(N'Tháng ', datepart(month, full_date)) as month_name,
        datepart(quarter, full_date) as quarter_number,
        datepart(year, full_date) as year
    from calendar

)

select
    cast(0 as int) as date_key,
    cast(null as date) as full_date,
    cast(null as tinyint) as day_of_month,
    {{ delivery_sql_string(rule_set.unknown_label) }} as day_name,
    cast(null as tinyint) as day_of_week_number,
    cast(null as tinyint) as week_of_year,
    cast(null as tinyint) as month_number,
    {{ delivery_sql_string(rule_set.unknown_label) }} as month_name,
    cast(null as tinyint) as quarter_number,
    cast(null as smallint) as year

union all

select
    date_key,
    full_date,
    day_of_month,
    day_name,
    day_of_week_number,
    week_of_year,
    month_number,
    month_name,
    quarter_number,
    year
from calendar_attributes
