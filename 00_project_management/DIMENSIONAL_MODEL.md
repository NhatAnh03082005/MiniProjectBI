# MOD-01 — Dimensional Model Design

## 1. Document control

| Thuộc tính | Giá trị |
|---|---|
| Project | Amazon Delivery BI |
| Task | `MOD-01` — Chốt grain DW, Fact, Dimension, keys và relationships |
| Trạng thái | Approved |
| Ngày thiết kế | 2026-10-17 |
| Ngày phê duyệt | 2026-10-17 |
| Phạm vi | Logical dimensional model; chưa phải physical SQL/dbt implementation |

> Dataset được sử dụng theo tên do người đăng Kaggle cung cấp. Project không khẳng định đây là dữ liệu vận hành chính thức của Amazon.

## 2. Quyết định mô hình

Mô hình sử dụng **Star Schema** với một Fact trung tâm và năm Dimension:

- `dw.fact_delivery`
- `dw.dim_date`
- `dw.dim_delivery_condition`
- `dw.dim_vehicle`
- `dw.dim_area`
- `dw.dim_category`

Không tạo `dim_agent` vì nguồn không có `Agent_ID`. Không tạo `dim_time` vì yêu cầu hiện tại chỉ cần giờ đặt hàng và khung giờ; các thuộc tính này được lưu trực tiếp trong Fact. Không tạo Dimension riêng cho Weather và Traffic; hai thuộc tính ít giá trị được kết hợp trong một junk dimension là `dim_delivery_condition`.

## 3. Business process và grain Data Warehouse

### 3.1. Business process

Quy trình được mô hình hóa là ghi nhận và phân tích một bản ghi giao hàng nguồn trong snapshot, từ thời điểm order đến pickup và thời lượng giao hàng được nguồn cung cấp.

### 3.2. Grain chính thức

> Một dòng trong `dw.fact_delivery` đại diện cho một bản ghi giao hàng nguồn duy nhất, được nhận diện bởi một `Order_ID` hợp lệ và duy nhất trong snapshot.

Hệ quả:

- Baseline dự kiến có 43.739 dòng Fact.
- `Order_ID` phải duy nhất và không null trong Fact.
- Không gọi chắc chắn mỗi dòng là một completed delivery vì nguồn không có delivery status.
- Không hạ grain xuống delivery attempt, agent, sản phẩm/SKU hoặc event vì nguồn không có khóa và lịch sử tương ứng.

## 4. Thiết kế Fact

### 4.1. `dw.fact_delivery`

| Nhóm | Cột logic | Vai trò | Quy tắc chính |
|---|---|---|---|
| Row identifier | `delivery_key` | Surrogate row key | Khóa kỹ thuật ổn định, sinh xác định từ `order_id`; không thay thế business key nguồn |
| Degenerate key | `order_id` | Business key nguồn | Giữ trực tiếp trong Fact; unique, not null |
| Foreign key | `date_key` | FK đến `dim_date` | Từ `Order_Date` |
| Foreign key | `delivery_condition_key` | FK đến `dim_delivery_condition` | Từ Weather và Traffic đã chuẩn hóa |
| Foreign key | `vehicle_key` | FK đến `dim_vehicle` | Từ Vehicle đã trim |
| Foreign key | `area_key` | FK đến `dim_area` | Từ Area đã trim và chuẩn hóa |
| Foreign key | `category_key` | FK đến `dim_category` | Từ Category đã trim |
| Time attribute | `order_time` | Thuộc tính Fact | Null khi nguồn thiếu |
| Time attribute | `pickup_time` | Thuộc tính Fact | Giữ thời gian đã parse; không tự đặt giá trị khi thiếu |
| Derived time | `order_hour` | Thuộc tính phân tích | 0–23; null khi `order_time` null |
| Derived time | `time_period` | Thuộc tính phân tích | Nhãn khung giờ theo rule được chốt ở MAP-01 |
| Agent attribute | `agent_age` | Thuộc tính Fact | Giữ tuổi nguồn đã parse |
| Agent attribute | `age_group` | Thuộc tính phân tích | Nhóm tuổi; boundary chốt ở MAP-01 |
| Quality flag | `underage_agent_flag` | Cờ chất lượng | True khi tuổi dưới 18 |
| Agent measure | `agent_rating_raw` | Giá trị nguồn đã parse | Giữ 1,0–6,0 và null để truy vết |
| Agent measure | `agent_rating_valid` | Giá trị dùng phân tích | Chỉ 1,0–5,0; ngoài miền hoặc thiếu thì null |
| Derived attribute | `rating_group` | Thuộc tính phân tích | Dựa trên rating hợp lệ; boundary chốt ở MAP-01 |
| Quality flag | `valid_rating_flag` | Cờ chất lượng | True khi rating nằm trong 1,0–5,0 |
| Base measure | `delivery_time_minutes` | Thời lượng nguồn | Numeric; giữ toàn bộ 10–270 và IQR outlier |
| Derived flag | `above_baseline_p90_flag` | Cờ KPI | True khi `delivery_time_minutes > 195` |
| Diagnostic flag | `delivery_time_iqr_outlier_flag` | Cờ chẩn đoán | Không dùng để loại record |
| Base measure | `pickup_delay_minutes` | Measure dẫn xuất | Null khi thiếu Order Time; áp dụng rollover đã khóa |
| Quality flag | `pickup_rollover_flag` | Cờ truy vết | True khi Pickup Time nhỏ hơn Order Time và cộng một ngày |
| Base measure | `delivery_distance_km` | Measure dẫn xuất | Haversine; chỉ có giá trị khi đạt valid-distance rule |
| Quality flag | `valid_distance_flag` | Cờ chất lượng | Đủ tọa độ, store khác `(0,0)`, distance không quá 50 km |
| Derived attribute | `distance_band` | Thuộc tính phân tích | Chỉ áp dụng cho valid distance; boundary chốt ở MAP-01 |
| Additive measure | `delivery_count` | Measure đếm | Luôn bằng 1 cho mỗi dòng Fact hợp lệ |
| Quality flag | `missing_operational_context_flag` | Cờ chất lượng | Thiếu Order Time, Weather hoặc Traffic sau chuẩn hóa |
| Audit | `source_file_name` | Lineage | Tên file nguồn |
| Audit | `load_batch_id` | Lineage | Tham chiếu batch/audit; thiết kế chi tiết ở LOAD-01 |
| Audit | `loaded_at` | Lineage | Timestamp nạp vào DW |

### 4.2. Tọa độ

- Bốn tọa độ raw phải được giữ bất biến tại raw/staging để đối soát.
- `dw.fact_delivery` không lưu exact drop coordinates phục vụ semantic model.
- Fact chỉ công bố `delivery_distance_km`, `valid_distance_flag` và `distance_band`.
- Nếu nhóm cần lưu tọa độ trong lớp kỹ thuật để kiểm thử, chúng phải nằm ngoài semantic/public model và tuân thủ privacy rule.

### 4.3. Không lưu KPI tổng hợp trong Fact

Average, Median, P90, P95, Average per Active Day và Share Above Baseline P90 phải được tính lại theo filter context. Không tạo các cột Fact chứa sẵn average, percentile hoặc percentage.

## 5. Thiết kế Dimension

### 5.1. `dw.dim_date`

| Thuộc tính | Thiết kế |
|---|---|
| Grain | Một ngày lịch |
| Surrogate key | `date_key` kiểu số nguyên dạng `YYYYMMDD` |
| Natural key | `full_date` |
| Thuộc tính chính | `full_date`, `day_of_month`, `day_name`, `day_of_week_number`, `week_of_year`, `month_number`, `month_name`, `quarter_number`, `year` |
| Phạm vi tối thiểu | Bao phủ 2022-02-11 đến 2022-04-06; có thể sinh đủ năm 2022 để dùng Power BI |
| SCD | Không áp dụng; calendar dimension tĩnh |
| Unknown Member | `date_key = 0`, chỉ dùng khi ngày nguồn thiếu/không parse được trong các lần nạp tương lai |

Active Day không phải thuộc tính cố định của Date Dimension. KPI-09 phải đếm ngày có Fact trong filter context bằng distinct count của `date_key` hoặc `order_date`, không đếm toàn bộ calendar days.

### 5.2. `dw.dim_delivery_condition`

| Thuộc tính | Thiết kế |
|---|---|
| Grain | Một tổ hợp Weather và Traffic đã chuẩn hóa |
| Surrogate key | `delivery_condition_key` |
| Natural key | Tổ hợp chuẩn hóa `weather_name` + `traffic_level` |
| Thuộc tính chính | `weather_name`, `traffic_level` |
| SCD | Type 1 |
| Unknown handling | Missing từng thuộc tính được chuẩn hóa thành `Unknown`; key 0 dành cho lookup failure |

Việc dùng junk dimension giúp phân tích riêng hoặc kết hợp Weather/Traffic mà không tạo hai Dimension rất nhỏ.

### 5.3. `dw.dim_vehicle`

| Thuộc tính | Thiết kế |
|---|---|
| Grain | Một loại phương tiện đã chuẩn hóa |
| Surrogate key | `vehicle_key` |
| Natural key | `vehicle_type` đã trim |
| Thuộc tính chính | `vehicle_type` |
| SCD | Type 1 |
| Unknown Member | Key 0, nhãn `Unknown` |

### 5.4. `dw.dim_area`

| Thuộc tính | Thiết kế |
|---|---|
| Grain | Một Area đã chuẩn hóa |
| Surrogate key | `area_key` |
| Natural key | `area_name` đã chuẩn hóa |
| Thuộc tính chính | `area_name`, `area_name_raw` nếu cần lineage nội bộ |
| Chuẩn hóa | `Metropolitian` thành `Metropolitan`; không sửa raw |
| SCD | Type 1 |
| Unknown Member | Key 0, nhãn `Unknown` |

### 5.5. `dw.dim_category`

| Thuộc tính | Thiết kế |
|---|---|
| Grain | Một Category nguồn đã trim |
| Surrogate key | `category_key` |
| Natural key | `category_name` |
| Thuộc tính chính | `category_name` |
| SCD | Type 1 |
| Unknown Member | Key 0, nhãn `Unknown` |

Category `Grocery` được giữ nguyên. Không sửa Delivery Time hoặc loại Grocery chỉ vì phân bố khác các nhóm còn lại.

## 6. Key strategy

### 6.1. Fact key

- `delivery_key` là surrogate row key sinh xác định từ `order_id` để hỗ trợ idempotency và rerun.
- Kiểu vật lý và thuật toán hash cụ thể được chốt ở MAP-01/physical design; không dùng hash rút gọn có nguy cơ collision mà không kiểm tra.
- `order_id` vẫn được giữ nguyên như degenerate business key và phải có unique test.

### 6.2. Dimension keys

- Mỗi Dimension dùng surrogate key số nguyên.
- Giá trị `0` được dành cho Unknown Member.
- Giá trị chuẩn hóa từ nguồn được giữ như natural key để lookup và đối soát.
- Vì nguồn chỉ là snapshot và các Dimension không có business identifier/historical attributes, dùng SCD Type 1; không triển khai SCD Type 2 trong phạm vi hiện tại.

### 6.3. Unknown Member

- Mọi Dimension phải có key 0 và nhãn dễ hiểu như `Unknown`.
- Categorical missing không làm rơi bản ghi Fact.
- Lookup failure dùng key 0 và phải được ghi audit.
- Unknown Member không được dùng để che lỗi parse hoặc lookup; số lượng phải được kiểm tra và báo cáo.

## 7. Relationships

| Dimension | Fact foreign key | Cardinality | Filter direction |
|---|---|---|---|
| `dim_date` | `fact_delivery.date_key` | 1 → nhiều | Dimension → Fact |
| `dim_delivery_condition` | `fact_delivery.delivery_condition_key` | 1 → nhiều | Dimension → Fact |
| `dim_vehicle` | `fact_delivery.vehicle_key` | 1 → nhiều | Dimension → Fact |
| `dim_area` | `fact_delivery.area_key` | 1 → nhiều | Dimension → Fact |
| `dim_category` | `fact_delivery.category_key` | 1 → nhiều | Dimension → Fact |

Yêu cầu:

- Không tạo relationship Dimension-to-Dimension.
- Không dùng many-to-many hoặc bidirectional filter trong baseline.
- Fact foreign key phải not null sau khi áp dụng Unknown Member.
- Dimension surrogate key phải unique và not null.

## 8. Aggregation behavior

| Loại | Trường/KPI | Quy tắc |
|---|---|---|
| Additive | `delivery_count` | Có thể SUM qua mọi Dimension và thời gian |
| Numerator hỗ trợ | Delivery Time, valid pickup delay, valid distance, valid rating | Có thể SUM nội bộ để tính average nhưng không trình bày tổng như KPI nghiệp vụ |
| Non-additive | Average, Median, P90, P95, Rating average, Distance average | Phải tính lại trên tập dòng trong filter context |
| Non-additive ratio | Average Deliveries per Active Day, Share Above Baseline P90 | Tính lại numerator/denominator trong cùng context |
| Semi-additive | Không có | Dataset là event-level, không có balance hoặc periodic snapshot |

## 9. KPI traceability

| KPI | Trường Fact/Dimension hỗ trợ |
|---|---|
| KPI-01 Total Deliveries | `order_id`, `delivery_count` |
| KPI-02 Average Delivery Time | `delivery_time_minutes` |
| KPI-03 Median Delivery Time | `delivery_time_minutes` |
| KPI-04 P90 Delivery Time | `delivery_time_minutes` |
| KPI-05 P95 Delivery Time | `delivery_time_minutes` |
| KPI-06 Average Pickup Delay | `pickup_delay_minutes`, `pickup_rollover_flag` |
| KPI-07 Average Valid Delivery Distance | `delivery_distance_km`, `valid_distance_flag` |
| KPI-08 Average Valid Agent Rating | `agent_rating_valid`, `valid_rating_flag` |
| KPI-09 Average Deliveries per Active Day | `order_id`, `date_key`; distinct active dates trong Fact context |
| KPI-10 Share Above Baseline P90 | `delivery_time_minutes`, `above_baseline_p90_flag`; ngưỡng cố định 195 |

Thiết kế bao phủ đủ 8 Business Questions và 10 KPI chính. Các breakdown theo Date, Weather, Traffic, Vehicle, Area, Category, time period, age group, rating group và distance band đều có trường hỗ trợ.

## 10. Data quality và privacy constraints

- Không loại record chỉ vì thiếu Order Time, Weather, Traffic hoặc Rating.
- 91 dòng thiếu Order Time có `pickup_delay_minutes = NULL`.
- Rating 6,0 giữ ở `agent_rating_raw`, nhưng `agent_rating_valid = NULL` và `valid_rating_flag = false`.
- Tuổi dưới 18 được giữ và gắn `underage_agent_flag`; không tạo Agent Dimension.
- IQR outlier Delivery Time được giữ trong Fact.
- Tọa độ `(0,0)`, khoảng cách trên 50 km và anomaly không bị tự sửa.
- Exact drop coordinates không xuất hiện trong semantic/public DW model.
- Không tạo SLA, On-time Rate, late flag hoặc ngôn ngữ “giao trễ”.

## 11. Thiết kế bị loại

| Phương án | Lý do không chọn |
|---|---|
| `dim_agent` | Không có Agent ID; Age và Rating không nhận diện một agent ổn định |
| `dim_time` | Giờ và time period ít thuộc tính, có thể lưu trong Fact; tránh tăng độ phức tạp |
| Dimension riêng cho Weather và Traffic | Quá nhỏ; junk dimension đáp ứng phân tích với ít bảng hơn |
| Location Dimension từ exact coordinates | Không có location business key, cardinality cao và có rủi ro privacy |
| SCD Type 2 | Nguồn snapshot không có lịch sử thay đổi hoặc business key bền vững cho Dimension |
| Fact tổng hợp theo ngày/nhóm | Làm mất grain nguồn và không hỗ trợ percentile chính xác theo filter context |

## 12. Acceptance checklist

- [x] Một Fact duy nhất và năm Dimension, đúng phạm vi dự án.
- [x] Grain Fact rõ ràng và không vượt quá bằng chứng nguồn.
- [x] `Order_ID` được giữ làm degenerate business key.
- [x] Có surrogate key, Unknown Member và SCD policy.
- [x] Quan hệ 1 → nhiều, filter một chiều từ Dimension sang Fact.
- [x] Không tạo `dim_agent`, không tạo SLA hoặc On-time Rate.
- [x] Không công khai exact drop coordinate trong analytical model.
- [x] Bao phủ đủ 8 Business Questions và 10 KPI chính.
- [x] Không có semi-additive measure.
- [x] Chưa viết SQL, dbt model, Mage pipeline, Power BI hoặc AI component.

## 13. Trạng thái và task tiếp theo

- `MOD-01` đã hoàn thành và tài liệu này đã được phê duyệt ngày 2026-10-17.
- Task tiếp theo là `MOD-02` để vẽ và đặc tả Star Schema dựa trên logical design đã duyệt.
- `MAP-01` vẫn phụ thuộc vào thiết kế mô hình đã duyệt và chi tiết schema từ `MOD-02`.
- Chưa triển khai SQL, dbt, Mage.ai, Power BI hoặc AI.
