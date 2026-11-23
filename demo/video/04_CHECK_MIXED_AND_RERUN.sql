/* Read-only. Use after mixed and again after the next scheduled rerun. */
USE AmazonDeliveryBI;
GO
SELECT Order_ID, Delivery_Time, Order_Date,
       load_batch_id AS inserted_by_batch,
       updated_load_batch_id AS last_written_by_batch,
       loaded_at, updated_at
FROM staging.raw_amazon_delivery
WHERE Order_ID IN (
    'seminar3_new_001', 'seminar3_new_002',
    'abwe493376570', 'acnn902187983'
)
ORDER BY Order_ID;

SELECT order_id, delivery_time_minutes, date_key, delivery_count
FROM dw.fact_delivery
WHERE order_id IN (
    'seminar3_new_001', 'seminar3_new_002',
    'abwe493376570', 'acnn902187983'
)
ORDER BY order_id;

SELECT COUNT_BIG(*) AS synthetic_orders_in_staging
FROM staging.raw_amazon_delivery
WHERE Order_ID IN ('seminar3_new_001', 'seminar3_new_002');

SELECT COUNT_BIG(*) AS synthetic_orders_in_fact
FROM dw.fact_delivery
WHERE order_id IN ('seminar3_new_001', 'seminar3_new_002');

SELECT Order_ID, COUNT_BIG(*) AS copies
FROM staging.raw_amazon_delivery
WHERE Order_ID IN ('seminar3_new_001', 'seminar3_new_002')
GROUP BY Order_ID;
/* Both synthetic IDs must occur once, not twice after the rerun. */
