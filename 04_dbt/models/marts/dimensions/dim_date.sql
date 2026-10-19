{{ config(materialized='table') }}

with calendar as (

    select cast('2022-01-01' as date) as full_date

    union all

    select dateadd(day, 1, full_date)
    from calendar
    where full_date < cast('2022-12-31' as date)

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
    'Unknown' as day_name,
    cast(null as tinyint) as day_of_week_number,
    cast(null as tinyint) as week_of_year,
    cast(null as tinyint) as month_number,
    'Unknown' as month_name,
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

option (maxrecursion 366)
