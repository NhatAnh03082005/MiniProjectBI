-- Every raw row must appear once in the accepted Fact or in rejection state.
with raw_count as (
    select count_big(*) as row_count
    from {{ source('staging', 'raw_amazon_delivery') }}
),
accepted_count as (
    select count_big(*) as row_count
    from {{ ref('fact_delivery') }}
),
rejected_count as (
    select count_big(distinct staging_row_id) as row_count
    from {{ ref('delivery_rejections') }}
)
select
    raw_count.row_count as raw_rows,
    accepted_count.row_count as accepted_rows,
    rejected_count.row_count as rejected_rows
from raw_count
cross join accepted_count
cross join rejected_count
where raw_count.row_count <> accepted_count.row_count + rejected_count.row_count
