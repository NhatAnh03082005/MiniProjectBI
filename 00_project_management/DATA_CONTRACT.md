# Data Contract — Amazon Delivery BI

## 1. Document control

| Thuộc tính | Giá trị |
|---|---|
| Tên tài liệu | Data Contract — Amazon Delivery BI |
| Mục đích | Khóa interface dữ liệu để bốn thành viên triển khai độc lập mà không tự đổi grain, bảng, cột hoặc KPI |
| Trạng thái | **Draft for implementation alignment** |
| Phạm vi | Hợp đồng dữ liệu từ CSV nguồn đến Mage.ai, SQL Server staging, dbt, Data Warehouse, Power BI và AI assistant |
| Ngoài phạm vi | Không triển khai pipeline, model dbt, DDL vật lý, dashboard hoặc API trong tài liệu này |
| Cơ sở đã duyệt | MOD-01, KPI Dictionary, Business Requirements, Data Profile |
| Cơ sở đề xuất | MAP-01; kiểu vật lý, batch/audit và xử lý rejected cần được chốt ở các task triển khai tương ứng |

Tài liệu nguồn: [Dimensional Model](DIMENSIONAL_MODEL.md), [Source-to-Target Mapping](SOURCE_TO_TARGET_MAPPING.md), [KPI Dictionary](KPI_DICTIONARY.md), [Data Profile](DATA_PROFILE_AMAZON_DELIVERY.md), [Business Requirements](BUSINESS_REQUIREMENTS.md), [Naming Conventions](NAMING_CONVENTIONS.md), [Decision Log](DECISION_LOG.md), [Team Handoff Guide](TEAM_HANDOFF_GUIDE.md), [Task Board](TASK_BOARD.md).

Sự hiện diện của tài liệu và các thư mục scaffold **không chứng minh** pipeline, database, dbt models, dashboard hay AI interface đã được triển khai.

## 2. Nguyên tắc áp dụng

- Business Baseline và MOD-01 đã `Approved`. Tài liệu này là điểm bàn giao giữa các thành viên; không thay thế quyết định `Approved` trong các tài liệu nguồn.
- `Approved`: có thể dùng làm tiêu chí triển khai và nghiệm thu. `Proposed`: cần rà soát trước khi khóa thiết kế vật lý. `Pending`: chưa được quyết định, không được tự suy diễn.
- Khi có mâu thuẫn, ưu tiên tài liệu `Approved` mới nhất; không tự thay đổi grain, KPI hoặc model.
- Mọi thay đổi contract phải được review, phân tích ảnh hưởng và ghi vào Decision Log trước khi các consumer áp dụng.
- Raw phải bất biến. Chuẩn hóa, chuyển kiểu và tạo trường dẫn xuất chỉ bắt đầu từ staging/dbt.
- Không loại dòng chỉ vì thiếu Order Time, Weather, Traffic, Rating; rating ngoài miền, tuổi dưới 18, khoảng cách không hợp lệ hoặc IQR outlier.
- Grain chính thức của `dw.fact_delivery` là **một dòng cho một `Order_ID` nguồn**. Snapshot hiện tại có 43.739 dòng và 43.739 `Order_ID` phân biệt.
- Không có measure semi-additive vì dữ liệu chỉ chứa giao dịch phát sinh, không chứa số dư hoặc snapshot như tồn kho cuối kỳ.

## 3. Luồng dữ liệu tổng thể và cấu trúc triển khai

```text
amazon_delivery.csv
→ Mage.ai
→ staging.raw_amazon_delivery
→ dbt stg_amazon_delivery
→ dbt int_delivery_enriched
→ dw.dim_* + dw.fact_delivery
→ Power BI
→ Generative AI
```

Phân định trách nhiệm: Mage.ai ingest file, cấp batch metadata và logging; SQL Server Staging lưu bản tiếp nhận; dbt staging trim/null-normalization/parsing; dbt intermediate tạo derived fields và quality flags; dbt marts tạo Dimensions/Fact; Power BI quản lý relationships, DAX và dashboard; AI chỉ nhận KPI, breakdown và kết quả tổng hợp đã tính, không tính lại từ raw.

### 3.1. Quy ước thư mục

Cây hiện tại được giữ nguyên để tránh tạo cấu trúc song song. Các đường dẫn dưới đây là nơi làm việc chính thức cho giai đoạn triển khai:

| Nhu cầu | Đường dẫn sử dụng |
|---|---|
| Full-load data | `01_data/full_load/` |
| Incremental batch 01, 02 | `01_data/incremental/incremental_01/`, `01_data/incremental/incremental_02/` |
| Data samples | `01_data/samples/` |
| SQL Server DDL/database | `02_sql/database/` |
| SQL staging, warehouse, audit, validation | `02_sql/staging/`, `02_sql/warehouse/`, `02_sql/audit/`, `02_sql/validation/` |
| Mage full/incremental pipeline | `03_mage/pipelines/full_load/`, `03_mage/pipelines/incremental_load/` |
| dbt models/tests | `04_dbt/models/`, `04_dbt/tests/` |
| Power BI mock data/specification/artifact | `05_powerbi/mock_data/`, `05_powerbi/specifications/`, `05_powerbi/pbix/` |
| AI input/output/code | `06_ai/sample_inputs/`, `06_ai/sample_output/`, `06_ai/src/` |
| Report | `07_report/sections/`, `07_report/figures/`, `07_report/references/` |
| Evidence tập trung | `08_evidence/{mage,dbt,sql_server,powerbi,ai,end_to_end}/` |

File `.env.example` ở root là mẫu biến môi trường duy nhất; không lưu secret thật trong Git.

## 4. Source contract

### 4.1. File và schema nguồn

| Thuộc tính | Contract |
|---|---|
| Dataset | `amazon_delivery.csv` |
| Encoding/delimiter | UTF-8 không BOM; dấu phẩy `,` — đã xác nhận trong Data Profile |
| Header | Bắt buộc đủ đúng 16 cột nguồn; không tự đổi tên ở raw |
| Snapshot baseline | 43.739 dòng, 16 cột, ngày 2022-02-11 đến 2022-04-06 |
| Grain | Một dòng cho một `Order_ID` |
| Business key | `Order_ID`, không null và duy nhất sau trim |
| Raw behavior | Giữ nguyên chuỗi, hoa/thường, dấu tọa độ, khoảng trắng và biểu diễn giá trị thiếu |

Dataset được dùng theo tên người đăng Kaggle cung cấp; không khẳng định đây là dữ liệu vận hành chính thức của Amazon. Một dòng là bản ghi giao hàng nguồn, không mặc định đồng nghĩa một completed delivery. `Delivery_Time` hiển thị bằng phút theo project assumption, nhưng metadata Kaggle chưa xác nhận đơn vị; không được suy diễn SLA hoặc trạng thái giao trễ.

| Cột nguồn | Ý nghĩa / yêu cầu nhận dữ liệu | Đầu ra chuẩn hóa đề xuất |
|---|---|---|
| `Order_ID` | Mã giao hàng; trim đầu/cuối, giữ hoa/thường và khoảng trắng bên trong | `order_id varchar(32)` |
| `Agent_Age` | Tuổi agent; giá trị dưới 18 được gắn cờ, không loại dòng | `agent_age smallint` |
| `Agent_Rating` | Rating nguồn; null và giá trị 6 phải được giữ để truy vết | `agent_rating_raw decimal(4,2)` |
| `Store_Latitude` | Latitude cửa hàng; giữ dấu và `(0,0)` | `store_latitude decimal(12,8)` |
| `Store_Longitude` | Longitude cửa hàng; giữ dấu | `store_longitude decimal(12,8)` |
| `Drop_Latitude` | Latitude điểm giao; chỉ dùng ở lớp kỹ thuật | `drop_latitude decimal(12,8)` |
| `Drop_Longitude` | Longitude điểm giao; chỉ dùng ở lớp kỹ thuật | `drop_longitude decimal(12,8)` |
| `Order_Date` | Ngày đặt hàng định dạng `YYYY-MM-DD` | `order_date date` |
| `Order_Time` | Giờ đặt hàng `HH:MM:SS`; thiếu giữ null | `order_time time(0)` |
| `Pickup_Time` | Giờ pickup `HH:MM:SS`; dùng với rollover rule | `pickup_time time(0)` |
| `Weather` | Điều kiện thời tiết; trim, thiếu thành null ở staging | `weather_name nvarchar(32)` |
| `Traffic` | Mức giao thông; trim, thiếu thành null ở staging | `traffic_level nvarchar(32)` |
| `Vehicle` | Loại phương tiện; trim, giữ cả nhóm hiếm | `vehicle_type nvarchar(32)` |
| `Area` | Khu vực; raw bất biến, chuẩn hóa riêng ở lớp biến đổi | `area_name_raw`, `area_name nvarchar(64)` |
| `Delivery_Time` | Thời lượng giao hàng; giữ dải 10–270 và outlier | `delivery_time_minutes decimal(10,2)` |
| `Category` | Danh mục; trim, giữ đủ 16 nhóm và `Grocery` | `category_name nvarchar(64)` |

Các kiểu ở cột cuối là **Proposed theo MAP-01**, chưa phải DDL đã duyệt. Lỗi chuyển kiểu, tràn số hoặc vượt độ dài phải được audit; không âm thầm cắt, làm tròn hoặc đổi thành dữ liệu thiếu.

### 4.2. Batch proposal

Đây là phân hoạch đề xuất phục vụ diễn tập full/incremental; thiết kế watermark, late-arriving data, idempotency và rejected record thuộc LOAD-01.

| Batch | Thư mục | Khoảng ngày | Số dòng kỳ vọng | Mục đích |
|---|---|---:|---:|---|
| `full_load` | `01_data/full_load/` | 2022-02-11 → 2022-02-18 | 6.982 | Khởi tạo staging và DW |
| `incremental_01` | `01_data/incremental/incremental_01/` | 2022-03-01 → 2022-03-31 | 30.658 | Incremental lần 1 |
| `incremental_02` | `01_data/incremental/incremental_02/` | 2022-04-01 → 2022-04-06 | 6.099 | Incremental lần 2 |
| **Tổng** |  | 2022-02-11 → 2022-04-06 | **43.739** | Phải khớp snapshot nguồn |

Metadata tối thiểu cho mỗi batch: `load_batch_id`, `batch_type`, `source_file_name`, `started_at`, `finished_at`, `status`, `rows_read`, `rows_loaded`, `rows_rejected`, `error_message`. Checksum SHA-256 đầy đủ của file và khoảng ngày phải được lưu cùng manifest/audit. Chuỗi SHA phải được giữ nguyên đầy đủ, không rút gọn hoặc xóa.

## 5. Staging contract

### 5.1. `staging.raw_amazon_delivery`

| Thuộc tính | Contract |
|---|---|
| Owner ghi | Mage.ai |
| Grain | Một dòng vật lý từ file nguồn |
| Schema | Đủ 16 cột nguồn dưới dạng chuỗi/raw, cộng metadata ingest cần thiết |
| Bất biến | Không trim, sửa chính tả, đổi dấu tọa độ, chuẩn hóa null hoặc ghi đè giá trị nguồn |
| Lineage bắt buộc | `source_file_name`, `source_row_number`, `load_batch_id`, `loaded_at` |
| Rerun | Không được làm tăng bản ghi ngoài chủ đích; cơ chế chính xác **Pending LOAD-01** |
| Không được làm | Không tính KPI, không tạo dimension key, không loại outlier |

### 5.2. `stg_amazon_delivery`

| Thuộc tính | Contract |
|---|---|
| Owner ghi | dbt |
| Input | `staging.raw_amazon_delivery` |
| Grain | Một dòng cho một dòng raw; chưa join dimension |
| Output | 16 trường chuẩn hóa ở mục 4.1, cùng metadata lineage |
| Chuẩn hóa | Trim đầu/cuối; chuỗi rỗng/`NaN` tương đương thành SQL `NULL`; chuyển kiểu có kiểm soát |
| Kiểm tra | Đủ cột, parse ngày/giờ/số, `order_id` not null/unique ở tập hợp hợp lệ, ghi nhận lỗi chuyển kiểu |
| Không được làm | Không mất dòng vì null/outlier; không công bố tọa độ chi tiết ra semantic/public model |

## 6. dbt model contract

Owner dự kiến của từng model trong bảng là Thành viên 3; Thành viên 2 bàn giao raw staging và audit metadata đầu vào.

| Model | Input | Grain / output | Trách nhiệm | Không được làm | Kiểm tra tối thiểu |
|---|---|---|---|---|---|
| `stg_amazon_delivery` | Raw staging | Một dòng/raw record | Rename, trim, null handling, cast và lineage | Không join dimension, không tính KPI | 16 cột, accepted parse, business-key audit |
| `int_delivery_enriched` | `stg_amazon_delivery` | Một dòng/`order_id` | Tạo timestamp pickup, delay, Haversine, valid fields, groups và quality flags | Không loại IQR outlier/rating invalid/distance invalid | Unique/not-null `order_id`, rule/unit tests, row-count reconciliation |
| `dim_date` | Calendar + order dates | Một dòng/ngày lịch | Calendar 2022, key `YYYYMMDD`, Unknown key 0 | Không gắn Active Day cố định | Unique keys/date, range/accepted values |
| `dim_delivery_condition` | Enriched Weather + Traffic | Một dòng/tổ hợp chuẩn hóa | Tạo junk dimension và Unknown handling | Không tách thành hai FK | Unique natural key pair, key 0 tồn tại |
| `dim_vehicle` | Enriched Vehicle | Một dòng/vehicle chuẩn hóa | SCD Type 1, Unknown key 0 | Không bỏ `bicycle` | Unique/not-null key và natural key |
| `dim_area` | Enriched Area | Một dòng/area chuẩn hóa | Sửa `Metropolitian` → `Metropolitan`, giữ lineage raw nội bộ nếu cần | Không sửa raw | Unique/not-null key, spelling rule |
| `dim_category` | Enriched Category | Một dòng/category | SCD Type 1, Unknown key 0 | Không loại/đổi `Grocery` | Unique/not-null key, đủ member nguồn |
| `fact_delivery` | Enriched + 5 dimensions | Một dòng/`order_id`; 31 trường logic | Tra 5 FK, giữ measure/flag/audit theo MOD-01 | Không lưu average/percentile/rate; không lưu exact drop coordinates | 43.739 dòng kỳ vọng, unique keys, relationships, no orphan |

Tên model ở bảng trên là hợp đồng logic. Materialization, schema vật lý, incremental strategy và thứ tự job là **Pending** ở task triển khai.

## 7. Transformation rules

| Quy tắc | Contract | Trạng thái nguồn |
|---|---|---|
| Trim | Trim đầu/cuối từ dbt staging; giữ hoa/thường của `Order_ID` và không đổi raw | Approved |
| Null normalization | Chuỗi rỗng, `NaN` và giá trị null-like tương đương thành SQL `NULL` từ staging | Approved |
| Parse ngày/giờ | `Order_Date` theo `YYYY-MM-DD`; `Order_Time`/`Pickup_Time` theo `HH:MM:SS`; lỗi parse được audit | Approved logic; kiểu vật lý Proposed |
| `delivery_key` | SHA-256 đầy đủ của `order_id` đã trim, dạng hex 64 ký tự; ổn định qua rerun | Proposed MAP-01 |
| Pickup rollover | Nếu pickup < order thì cộng 1 ngày; thiếu đầu vào thì delay null | Approved logic; vật lý Proposed |
| `pickup_delay_minutes` | Chênh lệch phút giữa pickup timestamp và order timestamp | Approved logic; vật lý Proposed |
| Valid rating | Chỉ 1,0–5,0 vào `agent_rating_valid`; thiếu/ngoài miền thành null; raw vẫn giữ | Approved |
| Underage flag | `underage_agent_flag = 1` khi tuổi đã parse `<18`; không loại record | Approved |
| Valid distance | Haversine khi đủ 4 tọa độ hợp lệ, store ≠ `(0,0)`, distance ≤ 50 km | Approved logic; vật lý Proposed |
| Exact coordinates | Chỉ tồn tại ở raw/staging kỹ thuật, không công bố trong Fact semantic/public | Approved |
| Delivery-time outlier | Giữ toàn bộ; gắn IQR flag khi `< -15` hoặc `> 265` | Proposed MAP-01 diagnostic |
| Baseline P90 flag | `delivery_time_minutes > 195`; ngưỡng cố định để đối soát | Approved |
| Missing context | True nếu thiếu ít nhất một trong Order Time, Weather, Traffic | Approved |
| Area spelling | Chỉ sửa `Metropolitian` → `Metropolitan` ở lớp chuẩn hóa | Approved |

Ranh giới nhóm `time_period`, `age_group`, `rating_group`, `distance_band` dùng đúng mục 7.5 của MAP-01 và hiện mang trạng thái **Proposed**; không tự thay boundary khi triển khai.

## 8. Data Warehouse contract

### 8.1. Dimensions

| Bảng | Grain | Surrogate key | Natural key/attributes | Thuộc tính bắt buộc | Unknown / SCD | Quan hệ Fact |
|---|---|---|---|---|---|---|
| `dw.dim_date` | Một ngày lịch | `date_key` (`YYYYMMDD`) | `full_date` | `full_date`, `day_of_month`, `day_name`, `day_of_week_number`, `week_of_year`, `month_number`, `month_name`, `quarter_number`, `year` | Key 0; calendar tĩnh, không SCD | `date_key` 1 → nhiều |
| `dw.dim_delivery_condition` | Một tổ hợp Weather–Traffic | `delivery_condition_key` | `weather_name` + `traffic_level` | `weather_name`, `traffic_level` | Missing từng thuộc tính → `Unknown`; lookup failure → key 0; SCD 1 | `delivery_condition_key` 1 → nhiều |
| `dw.dim_vehicle` | Một loại phương tiện | `vehicle_key` | `vehicle_type` | `vehicle_type` | Key 0, nhãn `Unknown`; SCD 1 | `vehicle_key` 1 → nhiều |
| `dw.dim_area` | Một khu vực chuẩn hóa | `area_key` | `area_name` | `area_name`; `area_name_raw` chỉ khi cần lineage nội bộ | Key 0, nhãn `Unknown`; SCD 1 | `area_key` 1 → nhiều |
| `dw.dim_category` | Một category | `category_key` | `category_name` | `category_name` | Key 0, nhãn `Unknown`; SCD 1 | `category_key` 1 → nhiều |

Mọi surrogate key và natural key nghiệp vụ phải unique/not null theo quy tắc của từng dimension. Fact lookup bằng natural key chuẩn hóa; lookup failure dùng key 0 và phải có audit.

### 8.2. `dw.fact_delivery`

Grain: một dòng cho một `Order_ID`. Contract gồm đúng 31 trường logic của MOD-01/MAP-01:

| Nhóm | Trường |
|---|---|
| Khóa | `delivery_key`, `order_id`, `date_key`, `delivery_condition_key`, `vehicle_key`, `area_key`, `category_key` |
| Thời gian | `order_time`, `pickup_time`, `order_hour`, `time_period` |
| Agent/rating | `agent_age`, `age_group`, `underage_agent_flag`, `agent_rating_raw`, `agent_rating_valid`, `rating_group`, `valid_rating_flag` |
| Delivery/pickup | `delivery_time_minutes`, `above_baseline_p90_flag`, `delivery_time_iqr_outlier_flag`, `pickup_delay_minutes`, `pickup_rollover_flag` |
| Khoảng cách | `delivery_distance_km`, `valid_distance_flag`, `distance_band` |
| Đếm/chất lượng | `delivery_count`, `missing_operational_context_flag` |
| Audit | `source_file_name`, `load_batch_id`, `loaded_at` |

Quy tắc khóa và measure:

- `order_id` và `delivery_key` unique, not null; năm FK not null và luôn trỏ đến member tồn tại, kể cả key 0.
- `delivery_count = 1` trên mỗi dòng Fact hợp lệ và là measure additive.
- Average, median, percentile và tỷ lệ là non-additive; phải tính lại trong filter context.
- `agent_rating_raw` giữ rating đã parse kể cả 6,0; chỉ `agent_rating_valid` được dùng cho average hợp lệ.
- `pickup_delay_minutes` null nếu không tính được; không đổi null thành 0.
- `delivery_distance_km` null nếu không đạt valid-distance rule; không suy diễn lại tọa độ.
- Không thêm/bớt trường logic hoặc đưa exact delivery coordinates vào Fact khi chưa có quyết định mới được duyệt.

## 9. Power BI contract

### 9.1. Semantic source và relationships

- Power BI chỉ đọc các bảng `dw.*` đã qua kiểm tra, không nối trực tiếp CSV/raw/staging.
- Mô hình một chiều từ mỗi dimension đến `dw.fact_delivery`, quan hệ 1-n theo năm FK.
- Date table là `dw.dim_date`; `date_key = 0` không được tính là active day.
- Filter theo Weather/Traffic dùng chung `dim_delivery_condition`; Vehicle, Area, Category dùng dimension tương ứng.
- Dashboard tối thiểu có hai trang: **Overview** và **Detailed/Diagnostic Analytics**.

### 9.2. KPI bắt buộc

| ID | KPI | Nguồn tính / ràng buộc |
|---|---|---|
| KPI-01 | Total Deliveries | Distinct `order_id`; có thể đối soát bằng SUM `delivery_count` khi grain đúng |
| KPI-02 | Average Delivery Time | Average `delivery_time_minutes`, bỏ null, giữ outlier |
| KPI-03 | Median Delivery Time | Tính lại trên tập dòng hiện tại |
| KPI-04 | P90 Delivery Time | Percentile liên tục, tính lại theo filter context |
| KPI-05 | P95 Delivery Time | Cùng nguyên tắc KPI-04 |
| KPI-06 | Average Pickup Delay | Chỉ dòng có delay; không đổi null thành 0 |
| KPI-07 | Average Valid Delivery Distance | Chỉ `valid_distance_flag = 1` |
| KPI-08 | Average Valid Agent Rating | SUM giá trị rating hợp lệ / COUNT 43.632 dòng hợp lệ ở baseline; không dùng raw trực tiếp |
| KPI-09 | Average Deliveries per Active Day | Total Deliveries / DISTINCTCOUNT ngày có Fact trong cùng filter context; loại key 0 |
| KPI-10 | Share Above Baseline P90 | Số dòng thời lượng `>195` / số dòng có thời lượng hợp lệ |

Supporting diagnostic measures: Records Missing Operational Context, Records Missing Rating, Invalid Rating Count, Invalid Store Coordinate Count, Valid Distance Coverage, Delivery Count by Group và Offline Correlation. Chúng không thuộc 10 KPI chính và không được diễn giải tương quan là quan hệ nhân quả.

## 10. AI contract

AI assistant chỉ nhận KPI/breakdown đã tính từ semantic/query layer được kiểm soát; không đọc raw coordinates, secret hoặc tự tạo số liệu. Logical input tối thiểu:

```json
{
  "filter_context": {
    "date_from": "2022-02-11",
    "date_to": "2022-04-06"
  },
  "kpis": {
    "KPI-01": {
      "value": 0,
      "unit": "delivery record"
    }
  },
  "breakdowns": [],
  "data_quality": {},
  "limitations": []
}
```

Logical output tối thiểu:

```json
{
  "summary": "Tóm tắt dựa trên số liệu đầu vào.",
  "notable_points": [],
  "data_based_explanation": [],
  "limitations_warning": []
}
```

Giá trị trong ví dụ chỉ minh họa schema, không phải kết quả nghiệp vụ. Output phải nêu filter context, đơn vị, khoảng thời gian, sample size khi phù hợp và cảnh báo dữ liệu. AI không được khẳng định quan hệ nhân quả; gọi 195 phút là SLA; gọi record vượt 195 phút là “giao trễ”; tuyên bố dataset là dữ liệu vận hành chính thức của Amazon; hoặc nhận exact drop coordinates khi không cần thiết. API framework, authentication, endpoint, timeout, caching và SQL generation là **Pending AI-01**.

## 11. Data quality checklist

### 11.1. Source và batch

- [ ] Đúng 16 header; không thiếu/thừa/đổi tên cột ở raw.
- [ ] Tổng ba batch = 43.739; không chồng lặp hoặc hở khoảng ngày theo proposal.
- [ ] `Order_ID` phân biệt = 43.739; null = 0 ở snapshot baseline.
- [ ] Checksum SHA-256 đầy đủ của từng file được lưu và không bị thay đổi.
- [ ] Số dòng read/write/rejected có thể đối soát về nguồn.

### 11.2. Transformation và model

- [ ] Raw bất biến; mọi cast/trim/normalization có audit lỗi.
- [ ] 91 dòng thiếu Order Time không bị đổi thành nửa đêm hoặc loại bỏ.
- [ ] Pickup rollover = 828; delay null = 91; average baseline ≈ 9,991294 phút.
- [ ] Rating valid/missing/invalid = 43.632/54/53; average valid ≈ 4,632121.
- [ ] Distance valid/invalid = 40.046/3.693; average valid ≈ 9,717187 km.
- [ ] 79 IQR outlier Delivery Time được giữ; số dòng `>195` = 4.100.
- [ ] Mọi dimension có Unknown key 0; mọi FK Fact có parent; không orphan.
- [ ] `fact_delivery` có đúng 31 trường logic và không đổi grain khi join.
- [ ] Rerun cùng batch không nhân đôi Fact; cơ chế phải được chốt ở LOAD-01.

### 11.3. KPI và AI

- [ ] KPI baseline: Total 43.739; mean 124,905645; median 125; P90 195; P95 215.
- [ ] KPI-08 dùng SUM(valid rating) / COUNT(valid rating), denominator baseline 43.632.
- [ ] KPI-09 chỉ đếm ngày có Fact trong filter context, không đếm toàn bộ Date Dimension.
- [ ] KPI-10 dùng mẫu số là dòng có thời lượng hợp lệ.
- [ ] AI trả đúng filter context, đơn vị, sample size/`delivery_count` và warning cần thiết.
- [ ] Không có exact coordinates hoặc secret trong Power BI/AI output/evidence công khai.

## 12. Ownership và handoff

| Thành phần | Owner dự kiến | Input | Output | Điều kiện bàn giao |
|---|---|---|---|---|
| Technical scaffold/bootstrap | Trưởng nhóm | Data Contract, Mapping, cấu trúc project | SQL Server bootstrap, Mage smoke-test, dbt source/staging skeleton và integration contract | Kết nối tối thiểu chạy được; bàn giao contract ổn định cho các workstream |
| Mage.ai | Thành viên 2 phát triển pipeline chính thức trên scaffold của trưởng nhóm | CSV/batch manifest + Mage scaffold | Raw staging + batch log | Row count, checksum, metadata, error log và rerun evidence |
| SQL Server/Staging/Audit | Trưởng nhóm tạo bootstrap/schema contract; Thành viên 2 hoàn thiện ingestion/audit | Mage output + contract | Bootstrap/schema contract, staging/audit/validation đã duyệt | DDL review, 16 cột raw, audit query và evidence tại `08_evidence/sql_server/` |
| dbt/DWH | Trưởng nhóm tạo kết nối, source và staging skeleton; Thành viên 3 hoàn thiện intermediate, Dimensions, Fact, tests và docs | Raw staging + MAP-01 + dbt skeleton | Staging, intermediate, 5 dimensions, 1 fact, tests và docs | Tests pass; row/FK/KPI reconciliation; evidence tại `08_evidence/dbt/` |
| Power BI | Thành viên 4 | `dw.*` tables + KPI Dictionary | Semantic model, DAX, 2 trang dashboard | Relationships/KPI/baseline được kiểm tra; evidence tại `08_evidence/powerbi/` |
| AI | Trưởng nhóm | KPI, breakdown, quality và limitations đã tính | Summary/insight interface | Không hallucinate/causality/SLA; validation samples tại `08_evidence/ai/` |
| Report/Evidence | Trưởng nhóm điều phối, cả nhóm cung cấp | Evidence từng workstream | Report narrative, figures, references | Traceability đủ và không ghi nhận giả là đã triển khai |
| Integration | Trưởng nhóm chịu trách nhiệm chạy luồng end-to-end cùng cả nhóm | Tất cả deliverable đã nghiệm thu cục bộ | Luồng demo end-to-end | Contract-compatible, reconciliation pass, evidence tại `08_evidence/end_to_end/` |

Quy tắc handoff: producer phải cung cấp schema/manifest, số liệu đối soát và evidence; consumer không được tự đổi grain, tên trường, business rule hoặc ngưỡng. Scaffold/bootstrap và phần hoàn thiện của từng workstream phải được phân tách theo file hoặc thư mục chịu trách nhiệm để tránh hai người cùng sửa một file. Mọi thay đổi contract phải (1) nêu lý do, (2) kiểm tra ảnh hưởng, (3) được trưởng nhóm review, (4) cập nhật Decision Log và (5) thông báo cho các thành viên phụ thuộc trước khi triển khai.

## 13. Open items không tự quyết định trong tài liệu này

- Chiến lược watermark, late-arriving data, duplicate/rejected handling và idempotent load chi tiết: **Pending LOAD-01**.
- DDL vật lý cuối cùng, index, partition, schema materialization và orchestration schedule: **Pending các task triển khai**.
- Kiểu/độ dài trong MAP-01 và boundary nhóm: **Proposed**, cần duyệt trước khi khóa code.
- API framework, authentication và cơ chế query của AI: **Pending AI-01**.

## 14. Acceptance checklist

- [ ] Đủ đúng 16 cột nguồn và raw bất biến.
- [ ] Đúng một Fact `dw.fact_delivery` và năm Dimension đã duyệt; không có `dim_agent` hoặc `dim_time`.
- [ ] Grain Fact là một dòng cho một `Order_ID` hợp lệ, duy nhất; không mặc định completed delivery.
- [ ] `Order_ID` là degenerate business key; dimension dùng surrogate key số nguyên.
- [ ] Unknown Member key `0` tồn tại và mọi relationship Dimension 1 → Fact nhiều, filter một chiều.
- [ ] Quality/transformation rules khớp tài liệu Approved; phần Proposed/Pending không bị trình bày như quyết định cuối.
- [ ] Interface Power BI giữ đúng 10 KPI và supporting measures; không hard-code aggregate KPI vào Fact.
- [ ] Interface AI chỉ nhận số liệu đã tính và trả summary, điểm đáng chú ý, giải thích dựa trên số liệu, cảnh báo giới hạn.
- [ ] Không công bố exact drop coordinates, secret hoặc provenance vượt quá bằng chứng.
- [ ] Không nội dung nào được dùng để tuyên bố các thành phần kỹ thuật đã triển khai.
- [ ] Không mâu thuẫn với tài liệu `Approved` mới nhất; mọi thay đổi sau này đi qua change control.

