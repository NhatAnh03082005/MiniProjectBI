{{ config(severity=var('delivery_rules').reject_warning_severity) }}

-- One warning count per rejected source row, even if that row has several errors.
select distinct staging_row_id
from {{ ref('delivery_rejections') }}
