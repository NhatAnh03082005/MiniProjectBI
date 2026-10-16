# Phạm vi dự án

## In scope

- Amazon Delivery Dataset: 43.739 bản ghi, 16 cột, 44 Active Day từ 2022-02-11 đến 2022-04-06.
- Phân tích BI mô tả/chẩn đoán hiệu suất giao hàng chặng cuối.
- Theo dõi khối lượng, Delivery Time, phân bố, pickup delay, valid distance và valid rating.
- Phân tích theo thời gian, Traffic, Weather, Vehicle, Area, Category, age group và rating group.
- Data quality monitoring cho missing, rollover, rating, age, categorical values và coordinates.
- Thiết kế Dimensional Model, Mapping và Full/Incremental Load ở các task tiếp theo.
- Sau khi thiết kế được duyệt: Mage.ai, SQL Server, dbt, Power BI và AI Summary có thể kiểm chứng.
- Báo cáo, bằng chứng kiểm thử và video demo.

## Out of scope

- Machine Learning và dự báo.
- Phân tích doanh thu, lợi nhuận, chi phí hoặc số lượng sản phẩm.
- Đánh giá hiệu suất cá nhân agent.
- Suy luận quan hệ nhân quả.
- On-time Delivery Rate hoặc kết luận “giao trễ” khi không có SLA.
- Công khai drop coordinate chính xác ở mức dòng.
- Kết luận xu hướng dài hạn hoặc mùa vụ từ 44 ngày dữ liệu.
- Khẳng định dataset là dữ liệu vận hành chính thức của Amazon.

## Pending design decisions

- Grain Data Warehouse, Fact, Dimension, key và relationship.
- Star Schema và Source-to-Target Mapping.
- Watermark, idempotency, rerun và rejected-record handling.
- Kiến trúc và phương án chia sẻ SQL Server.
- Dashboard layout, AI Summary và LLM provider.

Business Baseline đã được duyệt; các quyết định trên thuộc MOD-01 trở đi và chưa được triển khai.
