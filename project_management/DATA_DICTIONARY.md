# Data Dictionary — triển khai hiện hành

Cập nhật: 22/11/2026. Phạm vi: metadata, không đổi DDL, SQL models, KPI hoặc pipeline.

## 1. Cách đọc và bằng chứng

- Staging/audit: kiểu và nullable lấy từ DDL trong repo; chưa truy vấn schema live trong task này.
- dbt: danh sách cột/kiểu cơ sở đối chiếu SQL và catalog đã lưu ngày 13/11/2026; độ dài chuỗi suy ra và nullable vật lý phải kiểm tra sys.columns/catalog mới khi triển khai. Không trình bày kiểu thiết kế tinyint/smallint như kiểu thực nếu DATEPART/UNION trả INT.
- Cột “Null/khóa” của dbt là quy tắc logic, không khẳng định có ràng buộc NOT NULL/PK/FK vật lý. dbt tests kiểm tra dữ liệu; không tự tạo foreign key SQL.
- Database phụ thuộc môi trường: runner dùng MSSQL_DATABASE đồng thời đặt DBT_SQLSERVER_DATABASE. Không gán cứng dữ liệu demo là production.
- 16 giá trị raw giữ nguyên trong phiên bản hiện hành; raw current-state có thể được cập nhật. File archive/replay không đồng nghĩa pipeline tự archive mọi file đầu vào.
- Dữ liệu lịch sử nguồn 43.739 dòng không đồng nghĩa số dòng Fact. Ảnh demo người dùng cung cấp: 43.741 staging = 43.596 Fact + 145 distinct rejected; đây là một snapshot, không phải hằng số.

## 2. Danh mục và grain

| Đối tượng | Grain / cập nhật |
|---|---|
| staging.raw_amazon_delivery | Current-state một dòng/Order_ID sau chính sách Mage; upsert, 26 cột |
| audit.load_batch | Một batch ingestion; 18 cột, tạo ở exporter |
| audit.dbt_run | Một attempt dbt sau Verify; 9 cột, FK tới batch ingestion |
| dw.dim_area | table; 2 cột; Bảng Area chuẩn hóa trong accepted, cộng Unknown key 0; khóa giữ bằng dw.dim_area_key_map. Không chứa tọa độ hay lịch sử SCD Type 2. |
| dw.dim_category | table; 2 cột; Bảng danh mục trong accepted, cộng Unknown key 0; khóa giữ bằng dw.dim_category_key_map, giữ Grocery độc lập. |
| dw.dim_vehicle | table; 2 cột; Bảng loại phương tiện trong accepted, cộng Unknown key 0; khóa giữ bằng dw.dim_vehicle_key_map. Không lưu lịch sử SCD Type 2. |
| dw.dim_delivery_condition | table; 3 cột; Bảng tổ hợp Weather–Traffic hiện có trong accepted, cộng Unknown/Unknown key 0. Khóa INT giữ ổn định bằng dw.dim_delivery_condition_key_map; bảng semantic được dựng lại. |
| dw.fact_delivery | table; 33 cột; Bảng 33 cột, dựng lại từ int_delivery_accepted và 5 Dimension; một dòng/order_id được chấp nhận, không khẳng định giao thành công. Có 5 FK logic được dbt tests kiểm tra; lineage file/batch/time là insert staging đầu, không phải dbt run mới nhất. |
| dw.dim_date | table; 10 cột; Bảng lịch theo delivery_rules.date_calendar (hiện 2022-01-01 đến 2022-12-31), thêm Unknown key 0; hỗ trợ hierarchy Year/Quarter/Month/Date. Thuộc tính INT có thể do UNION/DATEPART suy ra. |
| dw.delivery_rejections | table; 10 cột; Bảng 10 cột dựng lại theo trạng thái hard-rule hiện tại, một dòng/cột vi phạm của staging_row_id. Đếm DISTINCT staging_row_id để đối soát với Fact; không cộng trực tiếp với Mage rejected. |
| dw.stg_amazon_delivery | view; 22 cột; Chuẩn hóa một dòng cho mỗi current-state staging_row_id: trim/null normalization/TRY_CONVERT/Area alias. Không tự loại dòng; hard rules ở int_delivery_validation_errors. View trong schema của target (runner dùng dw). |
| dw.int_delivery_enriched | view; 37 cột; View dẫn xuất một dòng/current-state staging_row_id trước hard-rule filtering: hash khóa, nhóm, pickup, Haversine và cờ. Mage đã upsert khóa giữa các batch; CTE deduplication_pending là pass-through, không phải một cơ chế dedup mới. |
| dw.int_delivery_validation_errors | view; 10 cột; View một dòng cho mỗi vi phạm hard rule của cột ở current-state staging. Một dòng nguồn có thể có nhiều lỗi; không phải lịch sử lỗi từng lần dbt chạy. |
| dw.int_delivery_accepted | view; 37 cột; View dòng enriched không có vi phạm hard rule, một dòng/order_id hợp lệ; dùng chung cho Fact và Dimension phân loại. Required/range lấy từ delivery_rules, không từ số liệu profiling cũ. |
| dw.dim_*_key_map | 4 bảng kỹ thuật lưu surrogate key bền qua lần dựng Dimension; không phải 4 Dimension phân tích mới |

## 3. Staging và audit — kiểu theo DDL

### staging.raw_amazon_delivery

| Cột | Kiểu SQL | Nullable DDL | Ý nghĩa / lineage |
|---|---|---|---|
| `staging_row_id` | BIGINT | Không | Định danh BIGINT IDENTITY của dòng current-state staging; ổn định khi upsert cập nhật cùng đơn. Dùng nối lỗi dbt với staging, không phải ID mỗi lần chạy. |
| `Order_ID` | VARCHAR(32) | Có | Chuỗi khóa nguồn; Mage loại null-like/quá 32 ký tự, kiểm tra trùng sau trim/case-fold trong batch và upsert cùng khóa giữa các batch. DDL vẫn nullable, không đồng nghĩa pipeline chấp nhận ID rỗng. |
| `Agent_Age` | VARCHAR(16) | Có | Chuỗi nguồn Agent_Age giữ nguyên, chưa trim/cast; dbt tạo agent_age. Tuổi parse bằng TRY_CONVERT(smallint); thiếu/cast lỗi/âm bị hard-rule dbt loại theo cấu hình hiện tại. Tuổi 0–17 không âm vẫn giữ và gắn cờ dưới 18. |
| `Agent_Rating` | VARCHAR(16) | Có | Chuỗi nguồn Agent_Rating giữ nguyên, chưa trim/cast; dbt tạo agent_rating_raw. Rating nguồn sau TRY_CONVERT(decimal(4,2)); có thể thiếu/ngoài miền ở lớp trước accepted. Cấu hình hiện tại loại dòng thiếu hoặc ngoài [1,5] khỏi Fact; raw nguồn vẫn giữ ở staging. |
| `Store_Latitude` | VARCHAR(32) | Có | Chuỗi nguồn Store_Latitude giữ nguyên, chưa trim/cast; dbt tạo store_latitude. Vĩ độ cửa hàng parse decimal(12,8), miền [-90,90]; tọa độ chỉ thuộc lớp kỹ thuật để tính Haversine. |
| `Store_Longitude` | VARCHAR(32) | Có | Chuỗi nguồn Store_Longitude giữ nguyên, chưa trim/cast; dbt tạo store_longitude. Kinh độ cửa hàng parse decimal(12,8), miền [-180,180]; không đổi dấu hoặc đưa vào Fact/AI payload. |
| `Drop_Latitude` | VARCHAR(32) | Có | Chuỗi nguồn Drop_Latitude giữ nguyên, chưa trim/cast; dbt tạo drop_latitude. Vĩ độ điểm giao parse decimal(12,8), miền [-90,90]; không công bố tọa độ chi tiết trên semantic model. |
| `Drop_Longitude` | VARCHAR(32) | Có | Chuỗi nguồn Drop_Longitude giữ nguyên, chưa trim/cast; dbt tạo drop_longitude. Kinh độ điểm giao parse decimal(12,8), miền [-180,180]; dùng nội bộ tính Haversine. |
| `Order_Date` | VARCHAR(16) | Có | Chuỗi nguồn Order_Date giữ nguyên, chưa trim/cast; dbt tạo order_date. Ngày nghiệp vụ parse DATE theo style cấu hình (23); không phải thời gian chạy ETL hoặc watermark. Mage loại ngày không parse được trước staging. |
| `Order_Time` | VARCHAR(16) | Có | Chuỗi nguồn Order_Time giữ nguyên, chưa trim/cast; dbt tạo order_time. Giờ đặt hàng TRY_CONVERT(time(0)); thiếu/không parse được là hard-rule theo cấu hình required hiện tại, không thay bằng nửa đêm. |
| `Pickup_Time` | VARCHAR(16) | Có | Chuỗi nguồn Pickup_Time giữ nguyên, chưa trim/cast; dbt tạo pickup_time. Giờ pickup TRY_CONVERT(time(0)); thiếu/không parse được là hard-rule hiện tại. Pickup nhỏ hơn order time được giả định sang ngày kế tiếp. |
| `Weather` | VARCHAR(32) | Có | Chuỗi nguồn Weather giữ nguyên, chưa trim/cast; dbt tạo weather_name. Weather đã trim; ở enriched/Dimension, thiếu được gán Unknown khi trường optional. Một phần natural key tổ hợp Weather–Traffic. |
| `Traffic` | VARCHAR(32) | Có | Chuỗi nguồn Traffic giữ nguyên, chưa trim/cast; dbt tạo traffic_level. Traffic đã trim; ở enriched/Dimension thiếu thành Unknown khi optional; không phải trạng thái ETL. |
| `Vehicle` | VARCHAR(32) | Có | Chuỗi nguồn Vehicle giữ nguyên, chưa trim/cast; dbt tạo vehicle_type. Loại phương tiện đã trim; ở enriched/Dimension thiếu thành Unknown khi optional; không tự gộp bicycle vào loại khác. |
| `Area` | VARCHAR(64) | Có | Chuỗi nguồn Area giữ nguyên, chưa trim/cast; dbt tạo area_name_raw. Area đã trim tại dbt, giữ lỗi chính tả nguồn để đối soát; chuỗi nguyên trạng vẫn nằm trong staging.raw_amazon_delivery.Area. |
| `Delivery_Time` | VARCHAR(16) | Có | Chuỗi nguồn Delivery_Time giữ nguyên, chưa trim/cast; dbt tạo delivery_time_minutes. Thời lượng TRY_CONVERT(decimal(10,2)); đơn vị phút là giả định của nhóm, nguồn chưa xác nhận. Required và không âm theo cấu hình hiện tại; giữ IQR outlier. |
| `Category` | VARCHAR(64) | Có | Chuỗi nguồn Category giữ nguyên, chưa trim/cast; dbt tạo category_name. Danh mục đã trim; enriched/Dimension dùng Unknown khi thiếu optional. Grocery vẫn là nhóm độc lập. |
| `source_file_name` | NVARCHAR(260) | Không | Tên tệp của lần insert đầu tiên, truyền từ staging; không tự đổi sang tệp sửa mới nhất khi upsert. |
| `source_row_number` | BIGINT | Không | Số thứ tự bản ghi CSV (bắt đầu 1, không tính header) ở lần insert đầu; không đồng nhất số dòng vật lý nếu CSV có trường nhiều dòng. |
| `load_batch_id` | VARCHAR(64) | Không | FK/lineage tới audit.load_batch của lần insert đầu; không phải batch cập nhật gần nhất và không phải run dbt hiện tại. |
| `loaded_at` | DATETIME2(3) | Không | Thời điểm insert staging lần đầu, UTC DATETIME2(3), được truyền qua dbt tới Fact; không phải thời điểm build Fact/refresh Power BI. |
| `row_hash` | CHAR(64) | Có | CHAR(64) SHA-256 của JSON 15 giá trị raw ngoài Order_ID, giữ khoảng trắng/hoa thường và thứ tự HASH_COLUMNS; khác checksum tệp và delivery_key. Nullable để tương thích migration cũ. |
| `updated_load_batch_id` | VARCHAR(64) | Có | Batch gần nhất đã insert/update phiên bản hiện tại, FK audit.load_batch; insert mới cũng đặt bằng load_batch_id. Unchanged không thay đổi trường này. |
| `updated_at` | DATETIME2(3) | Có | UTC DATETIME2(3) của lần ghi phiên bản hiện tại; insert cũng được khởi tạo, unchanged không đổi; nullable cho dữ liệu legacy. |
| `updated_source_file_name` | NVARCHAR(260) | Có | Tên tệp tạo/cập nhật phiên bản hiện hành, khác source_file_name của insert đầu. |
| `updated_source_row_number` | BIGINT | Có | Vị trí bản ghi trong tệp tạo/cập nhật phiên bản hiện hành; bắt đầu 1, bỏ header. |

### audit.load_batch

| Cột | Kiểu SQL | Nullable DDL | Ý nghĩa / lineage |
|---|---|---|---|
| `load_batch_id` | VARCHAR(64) | Không | ID UUID batch ingestion; PK audit.load_batch; FK ở staging và audit.dbt_run. Trong staging/Fact lineage này là insert đầu, khác ID run lọc trong audit. |
| `batch_name` | VARCHAR(50) | Không | Tên động full/inc + thời gian UTC + suffix; không dùng làm watermark hay tên batch cố định. |
| `batch_type` | VARCHAR(20) | Không | FULL_LOAD hoặc INCREMENTAL. Cả hai dùng upsert; FULL_LOAD không tự truncate. |
| `source_file_name` | NVARCHAR(260) | Không | Tên tệp đầu vào batch, không phải đường dẫn đầy đủ. |
| `source_file_checksum` | CHAR(64) | Không | SHA-256 byte snapshot toàn tệp, khác row_hash và delivery_key. |
| `expected_date_from` | DATE | Có | Tên legacy: ngày nhỏ nhất của các dòng hợp lệ ở input hiện tại; chỉ metadata, không phải cửa sổ lọc. |
| `expected_date_to` | DATE | Có | Tên legacy: ngày lớn nhất của các dòng hợp lệ ở input; NULL nếu không có dòng hợp lệ. |
| `expected_row_count` | INT | Có | Tên legacy: số dòng đọc thực tế, không phải số gán cứng trước chạy. |
| `started_at` | DATETIME2(3) | Không | UTC thời điểm bắt đầu bước audit tương ứng. Ingestion tạo ở exporter; dbt attempt tạo sau Verify, không phải trigger start. |
| `finished_at` | DATETIME2(3) | Có | UTC kết thúc bước; NULL khi chưa ghi nhận kết thúc. STARTED kéo dài không tự chứng minh đang chạy sống. |
| `status` | VARCHAR(20) | Không | Trạng thái riêng của bảng: load_batch STARTED/SUCCEEDED/FAILED/SKIPPED; dbt_run STARTED/SUCCEEDED/FAILED. Không đổi SUCCEEDED ingestion thành toàn ETL thành công. |
| `rows_read` | INT | Không | Số dòng đầu vào ingestion, bỏ header; lỗi sớm có thể chưa có bộ đếm đầy đủ. |
| `rows_loaded` | INT | Không | rows_inserted + rows_updated khi thành công; không gồm unchanged, không phải tổng Fact. Có thể reset 0 khi rollback. |
| `rows_rejected` | INT | Không | Số dòng ID/ngày không hợp lệ bị Mage loại khỏi batch; khác hard-rule rejection ở dbt. |
| `rows_inserted` | INT | Không | Số ID mới insert staging trong transaction của batch. |
| `rows_updated` | INT | Không | Số ID hiện có với 15 thuộc tính raw thay đổi được ghi lại; không đồng nghĩa số dòng Fact tăng. |
| `rows_unchanged` | INT | Không | Số dòng hợp lệ có ID/hash trùng current state; không ghi lại dữ liệu và updated lineage. |
| `error_message` | NVARCHAR(MAX) | Có | Thông báo lỗi hoặc warning rejection. load_batch SUCCEEDED vẫn có thể có message; dùng status để xác định lỗi. Không lưu secrets. |

### audit.dbt_run

| Cột | Kiểu SQL | Nullable DDL | Ý nghĩa / lineage |
|---|---|---|---|
| `dbt_attempt_id` | VARCHAR(64) | Không | UUID PK một attempt block dbt; load_batch_id quan hệ 1:n khi chạy lại block trên cùng kết quả Verify. |
| `load_batch_id` | VARCHAR(64) | Không | ID UUID batch ingestion; PK audit.load_batch; FK ở staging và audit.dbt_run. Trong staging/Fact lineage này là insert đầu, khác ID run lọc trong audit. |
| `status` | VARCHAR(20) | Không | Trạng thái riêng của bảng: load_batch STARTED/SUCCEEDED/FAILED/SKIPPED; dbt_run STARTED/SUCCEEDED/FAILED. Không đổi SUCCEEDED ingestion thành toàn ETL thành công. |
| `started_at` | DATETIME2(3) | Không | UTC thời điểm bắt đầu bước audit tương ứng. Ingestion tạo ở exporter; dbt attempt tạo sau Verify, không phải trigger start. |
| `finished_at` | DATETIME2(3) | Có | UTC kết thúc bước; NULL khi chưa ghi nhận kết thúc. STARTED kéo dài không tự chứng minh đang chạy sống. |
| `exit_code` | INT | Có | Exit code process dbt; 0 mới là điều kiện cần, còn cần artifact và đối soát. NULL nếu chưa chạy/xong hoặc lỗi setup/timeout. |
| `log_directory` | NVARCHAR(1024) | Không | Đường dẫn logs/etl/<load_batch_id>/<dbt_attempt_id>; chỉ dùng trên máy chạy, không phải URL chia sẻ. |
| `result_summary` | NVARCHAR(MAX) | Có | JSON snapshot trạng thái, test counts, row counts và reconciliation của attempt. Trường chưa tới bước tính có thể vắng mặt, không tự coi là 0. |
| `error_message` | NVARCHAR(2000) | Có | Thông báo lỗi hoặc warning rejection. load_batch SUCCEEDED vẫn có thể có message; dùng status để xác định lỗi. Không lưu secrets. |

## 4. Các model dbt — kiểu cơ sở và quy tắc logic

### dw.dim_area

Bảng Area chuẩn hóa trong accepted, cộng Unknown key 0; khóa giữ bằng dw.dim_area_key_map. Không chứa tọa độ hay lịch sử SCD Type 2.

| Cột | Kiểu cơ sở / cast | Null/khóa logic | Ý nghĩa / quy tắc |
|---|---|---|---|
| `area_key` | INT | Không null; natural/surrogate key theo key-map | Surrogate INT từ dw.dim_area_key_map; 0 Unknown; Fact lookup Area đã chuẩn hóa. |
| `area_name` | NVARCHAR (chiều dài do SELECT suy ra) | Không null; natural/surrogate key theo key-map | Area chuẩn hóa bằng area_aliases (Metropolitian → Metropolitan); enriched/Dimension dùng Unknown cho thiếu optional. |

### dw.dim_category

Bảng danh mục trong accepted, cộng Unknown key 0; khóa giữ bằng dw.dim_category_key_map, giữ Grocery độc lập.

| Cột | Kiểu cơ sở / cast | Null/khóa logic | Ý nghĩa / quy tắc |
|---|---|---|---|
| `category_key` | INT | Không null; natural/surrogate key theo key-map | Surrogate INT từ dw.dim_category_key_map; 0 Unknown; không dùng tên nhóm làm khóa Fact. |
| `category_name` | NVARCHAR (chiều dài do SELECT suy ra) | Không null; natural/surrogate key theo key-map | Danh mục đã trim; enriched/Dimension dùng Unknown khi thiếu optional. Grocery vẫn là nhóm độc lập. |

### dw.dim_vehicle

Bảng loại phương tiện trong accepted, cộng Unknown key 0; khóa giữ bằng dw.dim_vehicle_key_map. Không lưu lịch sử SCD Type 2.

| Cột | Kiểu cơ sở / cast | Null/khóa logic | Ý nghĩa / quy tắc |
|---|---|---|---|
| `vehicle_key` | INT | Không null; natural/surrogate key theo key-map | Surrogate INT từ dw.dim_vehicle_key_map; 0 Unknown; Fact quan hệ nhiều–một tới dim_vehicle. |
| `vehicle_type` | NVARCHAR (chiều dài do SELECT suy ra) | Không null; natural/surrogate key theo key-map | Loại phương tiện đã trim; ở enriched/Dimension thiếu thành Unknown khi optional; không tự gộp bicycle vào loại khác. |

### dw.dim_delivery_condition

Bảng tổ hợp Weather–Traffic hiện có trong accepted, cộng Unknown/Unknown key 0. Khóa INT giữ ổn định bằng dw.dim_delivery_condition_key_map; bảng semantic được dựng lại.

| Cột | Kiểu cơ sở / cast | Null/khóa logic | Ý nghĩa / quy tắc |
|---|---|---|---|
| `delivery_condition_key` | INT | Không null; natural/surrogate key theo key-map | Surrogate INT từ key-map của cặp Weather–Traffic; 0 là tổ hợp Unknown/Unknown hoặc fallback lookup, không nhất thiết chỉ là lookup lỗi. |
| `weather_name` | NVARCHAR (chiều dài do SELECT suy ra) | Không null; natural/surrogate key theo key-map | Weather đã trim; ở enriched/Dimension, thiếu được gán Unknown khi trường optional. Một phần natural key tổ hợp Weather–Traffic. |
| `traffic_level` | NVARCHAR (chiều dài do SELECT suy ra) | Không null; natural/surrogate key theo key-map | Traffic đã trim; ở enriched/Dimension thiếu thành Unknown khi optional; không phải trạng thái ETL. |

### dw.fact_delivery

Bảng 33 cột, dựng lại từ int_delivery_accepted và 5 Dimension; một dòng/order_id được chấp nhận, không khẳng định giao thành công. Có 5 FK logic được dbt tests kiểm tra; lineage file/batch/time là insert staging đầu, không phải dbt run mới nhất.

| Cột | Kiểu cơ sở / cast | Null/khóa logic | Ý nghĩa / quy tắc |
|---|---|---|---|
| `delivery_key` | CHAR(64) | Không null theo logic/tests áp dụng | SHA2_256 của order_id đã trim, convert CHAR(64) hex trong SQL; khác row_hash của Mage. Xác định từ mã hiện hành, không tự chuẩn hóa hoa/thường trước hash. |
| `order_id` | VARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Order_ID đã trim, giữ hoa/thường. Mage nhận diện khóa bằng trim/case-fold để upsert; Fact kiểm soát duy nhất và không null. Không phải mã nhân viên hay chứng cứ giao thành công. |
| `date_key` | INT | Không null theo logic/tests áp dụng | INT YYYYMMDD; key 0 là Unknown. Fact lookup theo order_date, ngoài lịch hiện tại cũng có thể về 0; Active Days loại key 0. |
| `delivery_condition_key` | INT | Không null theo logic/tests áp dụng | Surrogate INT từ key-map của cặp Weather–Traffic; 0 là tổ hợp Unknown/Unknown hoặc fallback lookup, không nhất thiết chỉ là lookup lỗi. |
| `vehicle_key` | INT | Không null theo logic/tests áp dụng | Surrogate INT từ dw.dim_vehicle_key_map; 0 Unknown; Fact quan hệ nhiều–một tới dim_vehicle. |
| `area_key` | INT | Không null theo logic/tests áp dụng | Surrogate INT từ dw.dim_area_key_map; 0 Unknown; Fact lookup Area đã chuẩn hóa. |
| `category_key` | INT | Không null theo logic/tests áp dụng | Surrogate INT từ dw.dim_category_key_map; 0 Unknown; không dùng tên nhóm làm khóa Fact. |
| `order_time` | TIME(0) | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | Giờ đặt hàng TRY_CONVERT(time(0)); thiếu/không parse được là hard-rule theo cấu hình required hiện tại, không thay bằng nửa đêm. |
| `pickup_time` | TIME(0) | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | Giờ pickup TRY_CONVERT(time(0)); thiếu/không parse được là hard-rule hiện tại. Pickup nhỏ hơn order time được giả định sang ngày kế tiếp. |
| `order_hour` | INT | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | DATEPART(hour, order_time), kiểu INT do SQL suy ra, giá trị 0–23; NULL khi giờ thiếu ở lớp trước accepted. |
| `time_period` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Nhóm giờ cấu hình: Night <6, Morning <12, Afternoon <18, còn lại Evening; giờ thiếu thành Unknown ở enriched. |
| `agent_age` | SMALLINT | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | Tuổi parse bằng TRY_CONVERT(smallint); thiếu/cast lỗi/âm bị hard-rule dbt loại theo cấu hình hiện tại. Tuổi 0–17 không âm vẫn giữ và gắn cờ dưới 18. |
| `age_group` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Nhóm tuổi theo delivery_rules.age_groups: Under 18, 18-24, 25-34, 35-44, 45+; thiếu thành Unknown ở enriched. |
| `underage_agent_flag` | BIT | Không null theo logic/tests áp dụng | BIT: 1 khi tuổi parse dưới 18, còn lại 0; thiếu tuổi không tự được coi là hợp lệ. Không loại dòng chỉ vì tuổi dưới 18. |
| `agent_rating_raw` | DECIMAL(4,2) | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | Rating nguồn sau TRY_CONVERT(decimal(4,2)); có thể thiếu/ngoài miền ở lớp trước accepted. Cấu hình hiện tại loại dòng thiếu hoặc ngoài [1,5] khỏi Fact; raw nguồn vẫn giữ ở staging. |
| `agent_rating_valid` | DECIMAL(4,2) | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | Rating numeric thuộc [1,5], còn lại NULL ở enriched. KPI rating chỉ dùng trường này với valid_rating_flag=1. |
| `rating_group` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Nhóm rating theo cấu hình; Unknown khi thiếu, Invalid khi ngoài miền ở enriched. Những dòng vi phạm required/range hiện không vào Fact. |
| `valid_rating_flag` | BIT | Không null theo logic/tests áp dụng | BIT: 1 khi rating trong [1,5], ngược lại 0; dùng lọc KPI rating, không thay thế hard-rule accepted. |
| `delivery_time_minutes` | DECIMAL(10,2) | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | Thời lượng TRY_CONVERT(decimal(10,2)); đơn vị phút là giả định của nhóm, nguồn chưa xác nhận. Required và không âm theo cấu hình hiện tại; giữ IQR outlier. |
| `above_baseline_p90_flag` | BIT | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | BIT: 1 khi thời lượng >195 phút (baseline hiện tại), 0 nếu không vượt, NULL nếu thời lượng NULL; không phải SLA hoặc giao trễ. |
| `delivery_time_iqr_outlier_flag` | BIT | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | BIT: 1 nếu thời lượng <-15 hoặc >265 theo cấu hình hiện tại, 0 nếu trong khoảng, NULL nếu thiếu. Cờ thống kê, không tự loại dòng. |
| `pickup_delay_minutes` | DECIMAL(10,2) | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | DECIMAL(10,2): chênh lệch giây giữa pickup và order timestamp chia 60; cộng 1 ngày khi pickup_time < order_time. NULL khi thiếu đầu vào. |
| `pickup_rollover_flag` | BIT | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | BIT: 1 nếu pickup_time < order_time và hai giờ parse được, 0 nếu không; NULL nếu thiếu giờ. Quy tắc sang ngày là giả định xử lý của nhóm. |
| `delivery_distance_km` | FLOAT | Có thể NULL; xem quy tắc lớp dữ liệu | FLOAT: khoảng cách Haversine với bán kính 6371 km, không phải quãng đường giao thực. Giữ giá trị >50; NULL khi không tính được hoặc store=(0,0). |
| `valid_distance_flag` | BIT | Không null theo logic/tests áp dụng | BIT: 1 khi Haversine tính được và <=50 km theo cấu hình, còn lại 0. KPI khoảng cách phải lọc cờ này. |
| `distance_outlier_flag` | BIT | Không null theo logic/tests áp dụng | BIT: 1 nếu Haversine tính được >50 km, ngược lại 0; không tự loại dòng Fact. |
| `distance_status` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Nhãn nguyên nhân/đánh giá: Valid, Outlier >50 km, Store coordinates (0,0), Not calculable; sinh theo cấu hình khoảng cách. |
| `distance_band` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Nhóm Haversine theo cấu hình: [0,5), [5,10), [10,15), [15,20), [20,50] km và nhãn >50/không tính được/store=(0,0). Không gộp mọi dòng không hợp lệ thành Unknown. |
| `delivery_count` | TINYINT | Không null theo logic/tests áp dụng | TINYINT hằng số 1 cho mỗi dòng; SUM trong Fact bằng số bản ghi khi grain không trùng. Không phải số sản phẩm hoặc giao thành công. |
| `missing_operational_context_flag` | BIT | Không null theo logic/tests áp dụng | BIT: thiếu một trong order_time, weather_name, traffic_level theo delivery_rules.operational_context_fields. Không khẳng định đủ mọi trường vận hành. |
| `source_file_name` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Tên tệp của lần insert đầu tiên, truyền từ staging; không tự đổi sang tệp sửa mới nhất khi upsert. |
| `load_batch_id` | VARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | FK/lineage tới audit.load_batch của lần insert đầu; không phải batch cập nhật gần nhất và không phải run dbt hiện tại. |
| `loaded_at` | DATETIME2 | Không null theo logic/tests áp dụng | Thời điểm insert staging lần đầu, UTC DATETIME2(3), được truyền qua dbt tới Fact; không phải thời điểm build Fact/refresh Power BI. |

### dw.dim_date

Bảng lịch theo delivery_rules.date_calendar (hiện 2022-01-01 đến 2022-12-31), thêm Unknown key 0; hỗ trợ hierarchy Year/Quarter/Month/Date. Thuộc tính INT có thể do UNION/DATEPART suy ra.

| Cột | Kiểu cơ sở / cast | Null/khóa logic | Ý nghĩa / quy tắc |
|---|---|---|---|
| `date_key` | INT | Key 0 không null | INT YYYYMMDD; key 0 là Unknown. Fact lookup theo order_date, ngoài lịch hiện tại cũng có thể về 0; Active Days loại key 0. |
| `full_date` | DATE | NULL cho Unknown key 0 | Ngày lịch DATE của Dimension theo khoảng cấu hình; key 0 có NULL. Không phải danh sách chỉ những ngày có giao hàng. |
| `day_of_month` | INT | NULL cho Unknown key 0 | Ngày trong tháng DATEPART(day), SQL suy ra INT; NULL ở Unknown member. |
| `day_name` | NVARCHAR (chiều dài do SELECT suy ra) | Unknown label cho key 0 | Tên thứ tiếng Anh Monday–Sunday được sinh xác định; Unknown cho key 0. |
| `day_of_week_number` | INT | NULL cho Unknown key 0 | Số thứ: Monday=1 đến Sunday=7, không phụ thuộc DATEFIRST; NULL ở Unknown. |
| `week_of_year` | INT | NULL cho Unknown key 0 | Tuần ISO DATEPART(iso_week); không phải khóa tuần duy nhất giữa các năm. |
| `month_number` | INT | NULL cho Unknown key 0 | Tháng 1–12, INT do SELECT/UNION suy ra; NULL ở Unknown member. |
| `month_name` | NVARCHAR (chiều dài do SELECT suy ra) | Unknown label cho key 0 | Nhãn Tháng 1…Tháng 12; Unknown ở key 0. Cần sort theo month_number khi hiển thị. |
| `quarter_number` | INT | NULL cho Unknown key 0 | Quý 1–4, INT; NULL ở Unknown member. |
| `year` | INT | NULL cho Unknown key 0 | Năm dương lịch DATEPART(year), INT do UNION suy ra; NULL ở Unknown member. |

### dw.delivery_rejections

Bảng 10 cột dựng lại theo trạng thái hard-rule hiện tại, một dòng/cột vi phạm của staging_row_id. Đếm DISTINCT staging_row_id để đối soát với Fact; không cộng trực tiếp với Mage rejected.

| Cột | Kiểu cơ sở / cast | Null/khóa logic | Ý nghĩa / quy tắc |
|---|---|---|---|
| `staging_row_id` | BIGINT | Không null theo logic/tests áp dụng | Định danh BIGINT IDENTITY của dòng current-state staging; ổn định khi upsert cập nhật cùng đơn. Dùng nối lỗi dbt với staging, không phải ID mỗi lần chạy. |
| `order_id` | VARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Order_ID đã trim, giữ hoa/thường. Mage nhận diện khóa bằng trim/case-fold để upsert; Fact kiểm soát duy nhất và không null. Không phải mã nhân viên hay chứng cứ giao thành công. |
| `source_file_name` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Tên tệp của lần insert đầu tiên, truyền từ staging; không tự đổi sang tệp sửa mới nhất khi upsert. |
| `source_row_number` | BIGINT | Không null theo logic/tests áp dụng | Số thứ tự bản ghi CSV (bắt đầu 1, không tính header) ở lần insert đầu; không đồng nhất số dòng vật lý nếu CSV có trường nhiều dòng. |
| `load_batch_id` | VARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | FK/lineage tới audit.load_batch của lần insert đầu; không phải batch cập nhật gần nhất và không phải run dbt hiện tại. |
| `loaded_at` | DATETIME2 | Không null theo logic/tests áp dụng | Thời điểm insert staging lần đầu, UTC DATETIME2(3), được truyền qua dbt tới Fact; không phải thời điểm build Fact/refresh Power BI. |
| `column_name` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Tên cột CSV vi phạm hard rule; một staging_row_id có thể có nhiều cột lỗi. |
| `raw_value` | NVARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Giá trị raw của cột lỗi chuyển sang NVARCHAR(4000) để giải thích; có thể NULL. Có thể chứa tọa độ: chỉ dùng đối soát kỹ thuật, không gửi AI/public. |
| `error_code` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Mã hard rule, ví dụ MISSING_VALUE/MISSING_ORDER_ID, INVALID_CAST, DUPLICATE_ORDER_ID, NEGATIVE_VALUE, OUT_OF_RANGE; phụ thuộc cấu hình. |
| `expected_rule` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Mô tả điều kiện mong đợi của cột lấy từ delivery_rules.fields; optional được sửa nhãn tương ứng. |

### dw.stg_amazon_delivery

Chuẩn hóa một dòng cho mỗi current-state staging_row_id: trim/null normalization/TRY_CONVERT/Area alias. Không tự loại dòng; hard rules ở int_delivery_validation_errors. View trong schema của target (runner dùng dw).

| Cột | Kiểu cơ sở / cast | Null/khóa logic | Ý nghĩa / quy tắc |
|---|---|---|---|
| `staging_row_id` | BIGINT | Không null theo logic/tests áp dụng | Định danh BIGINT IDENTITY của dòng current-state staging; ổn định khi upsert cập nhật cùng đơn. Dùng nối lỗi dbt với staging, không phải ID mỗi lần chạy. |
| `order_id` | VARCHAR (chiều dài do SELECT suy ra) | Có thể NULL trước accepted; hard-rule downstream | Order_ID đã trim, giữ hoa/thường. Mage nhận diện khóa bằng trim/case-fold để upsert; Fact kiểm soát duy nhất và không null. Không phải mã nhân viên hay chứng cứ giao thành công. |
| `agent_age` | SMALLINT | Có thể NULL trước accepted; hard-rule downstream | Tuổi parse bằng TRY_CONVERT(smallint); thiếu/cast lỗi/âm bị hard-rule dbt loại theo cấu hình hiện tại. Tuổi 0–17 không âm vẫn giữ và gắn cờ dưới 18. |
| `agent_rating_raw` | DECIMAL(4,2) | Có thể NULL trước accepted; hard-rule downstream | Rating nguồn sau TRY_CONVERT(decimal(4,2)); có thể thiếu/ngoài miền ở lớp trước accepted. Cấu hình hiện tại loại dòng thiếu hoặc ngoài [1,5] khỏi Fact; raw nguồn vẫn giữ ở staging. |
| `store_latitude` | DECIMAL(12,8) | Có thể NULL; xem quy tắc lớp dữ liệu | Vĩ độ cửa hàng parse decimal(12,8), miền [-90,90]; tọa độ chỉ thuộc lớp kỹ thuật để tính Haversine. |
| `store_longitude` | DECIMAL(12,8) | Có thể NULL; xem quy tắc lớp dữ liệu | Kinh độ cửa hàng parse decimal(12,8), miền [-180,180]; không đổi dấu hoặc đưa vào Fact/AI payload. |
| `drop_latitude` | DECIMAL(12,8) | Có thể NULL; xem quy tắc lớp dữ liệu | Vĩ độ điểm giao parse decimal(12,8), miền [-90,90]; không công bố tọa độ chi tiết trên semantic model. |
| `drop_longitude` | DECIMAL(12,8) | Có thể NULL; xem quy tắc lớp dữ liệu | Kinh độ điểm giao parse decimal(12,8), miền [-180,180]; dùng nội bộ tính Haversine. |
| `order_date` | DATE | Có thể NULL; xem quy tắc lớp dữ liệu | Ngày nghiệp vụ parse DATE theo style cấu hình (23); không phải thời gian chạy ETL hoặc watermark. Mage loại ngày không parse được trước staging. |
| `order_time` | TIME(0) | Có thể NULL trước accepted; hard-rule downstream | Giờ đặt hàng TRY_CONVERT(time(0)); thiếu/không parse được là hard-rule theo cấu hình required hiện tại, không thay bằng nửa đêm. |
| `pickup_time` | TIME(0) | Có thể NULL trước accepted; hard-rule downstream | Giờ pickup TRY_CONVERT(time(0)); thiếu/không parse được là hard-rule hiện tại. Pickup nhỏ hơn order time được giả định sang ngày kế tiếp. |
| `weather_name` | VARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Weather đã trim; ở enriched/Dimension, thiếu được gán Unknown khi trường optional. Một phần natural key tổ hợp Weather–Traffic. |
| `traffic_level` | VARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Traffic đã trim; ở enriched/Dimension thiếu thành Unknown khi optional; không phải trạng thái ETL. |
| `vehicle_type` | VARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Loại phương tiện đã trim; ở enriched/Dimension thiếu thành Unknown khi optional; không tự gộp bicycle vào loại khác. |
| `area_name_raw` | VARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Area đã trim tại dbt, giữ lỗi chính tả nguồn để đối soát; chuỗi nguyên trạng vẫn nằm trong staging.raw_amazon_delivery.Area. |
| `area_name` | NVARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Area chuẩn hóa bằng area_aliases (Metropolitian → Metropolitan); enriched/Dimension dùng Unknown cho thiếu optional. |
| `delivery_time_minutes` | DECIMAL(10,2) | Có thể NULL trước accepted; hard-rule downstream | Thời lượng TRY_CONVERT(decimal(10,2)); đơn vị phút là giả định của nhóm, nguồn chưa xác nhận. Required và không âm theo cấu hình hiện tại; giữ IQR outlier. |
| `category_name` | VARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Danh mục đã trim; enriched/Dimension dùng Unknown khi thiếu optional. Grocery vẫn là nhóm độc lập. |
| `source_file_name` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Tên tệp của lần insert đầu tiên, truyền từ staging; không tự đổi sang tệp sửa mới nhất khi upsert. |
| `source_row_number` | BIGINT | Không null theo logic/tests áp dụng | Số thứ tự bản ghi CSV (bắt đầu 1, không tính header) ở lần insert đầu; không đồng nhất số dòng vật lý nếu CSV có trường nhiều dòng. |
| `load_batch_id` | VARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | FK/lineage tới audit.load_batch của lần insert đầu; không phải batch cập nhật gần nhất và không phải run dbt hiện tại. |
| `loaded_at` | DATETIME2 | Không null theo logic/tests áp dụng | Thời điểm insert staging lần đầu, UTC DATETIME2(3), được truyền qua dbt tới Fact; không phải thời điểm build Fact/refresh Power BI. |

### dw.int_delivery_enriched

View dẫn xuất một dòng/current-state staging_row_id trước hard-rule filtering: hash khóa, nhóm, pickup, Haversine và cờ. Mage đã upsert khóa giữa các batch; CTE deduplication_pending là pass-through, không phải một cơ chế dedup mới.

| Cột | Kiểu cơ sở / cast | Null/khóa logic | Ý nghĩa / quy tắc |
|---|---|---|---|
| `delivery_key` | CHAR(64) | Không null theo logic/tests áp dụng | SHA2_256 của order_id đã trim, convert CHAR(64) hex trong SQL; khác row_hash của Mage. Xác định từ mã hiện hành, không tự chuẩn hóa hoa/thường trước hash. |
| `staging_row_id` | BIGINT | Không null theo logic/tests áp dụng | Định danh BIGINT IDENTITY của dòng current-state staging; ổn định khi upsert cập nhật cùng đơn. Dùng nối lỗi dbt với staging, không phải ID mỗi lần chạy. |
| `order_id` | VARCHAR (chiều dài do SELECT suy ra) | Có thể NULL trước accepted; hard-rule downstream | Order_ID đã trim, giữ hoa/thường. Mage nhận diện khóa bằng trim/case-fold để upsert; Fact kiểm soát duy nhất và không null. Không phải mã nhân viên hay chứng cứ giao thành công. |
| `order_date` | DATE | Có thể NULL; xem quy tắc lớp dữ liệu | Ngày nghiệp vụ parse DATE theo style cấu hình (23); không phải thời gian chạy ETL hoặc watermark. Mage loại ngày không parse được trước staging. |
| `order_time` | TIME(0) | Có thể NULL trước accepted; hard-rule downstream | Giờ đặt hàng TRY_CONVERT(time(0)); thiếu/không parse được là hard-rule theo cấu hình required hiện tại, không thay bằng nửa đêm. |
| `pickup_time` | TIME(0) | Có thể NULL trước accepted; hard-rule downstream | Giờ pickup TRY_CONVERT(time(0)); thiếu/không parse được là hard-rule hiện tại. Pickup nhỏ hơn order time được giả định sang ngày kế tiếp. |
| `order_hour` | INT | Có thể NULL; xem quy tắc lớp dữ liệu | DATEPART(hour, order_time), kiểu INT do SQL suy ra, giá trị 0–23; NULL khi giờ thiếu ở lớp trước accepted. |
| `time_period` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Nhóm giờ cấu hình: Night <6, Morning <12, Afternoon <18, còn lại Evening; giờ thiếu thành Unknown ở enriched. |
| `agent_age` | SMALLINT | Có thể NULL trước accepted; hard-rule downstream | Tuổi parse bằng TRY_CONVERT(smallint); thiếu/cast lỗi/âm bị hard-rule dbt loại theo cấu hình hiện tại. Tuổi 0–17 không âm vẫn giữ và gắn cờ dưới 18. |
| `age_group` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Nhóm tuổi theo delivery_rules.age_groups: Under 18, 18-24, 25-34, 35-44, 45+; thiếu thành Unknown ở enriched. |
| `underage_agent_flag` | BIT | Không null theo logic/tests áp dụng | BIT: 1 khi tuổi parse dưới 18, còn lại 0; thiếu tuổi không tự được coi là hợp lệ. Không loại dòng chỉ vì tuổi dưới 18. |
| `agent_rating_raw` | DECIMAL(4,2) | Có thể NULL trước accepted; hard-rule downstream | Rating nguồn sau TRY_CONVERT(decimal(4,2)); có thể thiếu/ngoài miền ở lớp trước accepted. Cấu hình hiện tại loại dòng thiếu hoặc ngoài [1,5] khỏi Fact; raw nguồn vẫn giữ ở staging. |
| `agent_rating_valid` | DECIMAL(4,2) | Có thể NULL; xem quy tắc lớp dữ liệu | Rating numeric thuộc [1,5], còn lại NULL ở enriched. KPI rating chỉ dùng trường này với valid_rating_flag=1. |
| `rating_group` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Nhóm rating theo cấu hình; Unknown khi thiếu, Invalid khi ngoài miền ở enriched. Những dòng vi phạm required/range hiện không vào Fact. |
| `valid_rating_flag` | BIT | Không null theo logic/tests áp dụng | BIT: 1 khi rating trong [1,5], ngược lại 0; dùng lọc KPI rating, không thay thế hard-rule accepted. |
| `weather_name` | NVARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Weather đã trim; ở enriched/Dimension, thiếu được gán Unknown khi trường optional. Một phần natural key tổ hợp Weather–Traffic. |
| `traffic_level` | NVARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Traffic đã trim; ở enriched/Dimension thiếu thành Unknown khi optional; không phải trạng thái ETL. |
| `vehicle_type` | NVARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Loại phương tiện đã trim; ở enriched/Dimension thiếu thành Unknown khi optional; không tự gộp bicycle vào loại khác. |
| `area_name_raw` | VARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Area đã trim tại dbt, giữ lỗi chính tả nguồn để đối soát; chuỗi nguyên trạng vẫn nằm trong staging.raw_amazon_delivery.Area. |
| `area_name` | NVARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Area chuẩn hóa bằng area_aliases (Metropolitian → Metropolitan); enriched/Dimension dùng Unknown cho thiếu optional. |
| `category_name` | NVARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Danh mục đã trim; enriched/Dimension dùng Unknown khi thiếu optional. Grocery vẫn là nhóm độc lập. |
| `delivery_time_minutes` | DECIMAL(10,2) | Có thể NULL trước accepted; hard-rule downstream | Thời lượng TRY_CONVERT(decimal(10,2)); đơn vị phút là giả định của nhóm, nguồn chưa xác nhận. Required và không âm theo cấu hình hiện tại; giữ IQR outlier. |
| `above_baseline_p90_flag` | BIT | Có thể NULL; xem quy tắc lớp dữ liệu | BIT: 1 khi thời lượng >195 phút (baseline hiện tại), 0 nếu không vượt, NULL nếu thời lượng NULL; không phải SLA hoặc giao trễ. |
| `delivery_time_iqr_outlier_flag` | BIT | Có thể NULL; xem quy tắc lớp dữ liệu | BIT: 1 nếu thời lượng <-15 hoặc >265 theo cấu hình hiện tại, 0 nếu trong khoảng, NULL nếu thiếu. Cờ thống kê, không tự loại dòng. |
| `pickup_delay_minutes` | DECIMAL(10,2) | Có thể NULL; xem quy tắc lớp dữ liệu | DECIMAL(10,2): chênh lệch giây giữa pickup và order timestamp chia 60; cộng 1 ngày khi pickup_time < order_time. NULL khi thiếu đầu vào. |
| `pickup_rollover_flag` | BIT | Có thể NULL; xem quy tắc lớp dữ liệu | BIT: 1 nếu pickup_time < order_time và hai giờ parse được, 0 nếu không; NULL nếu thiếu giờ. Quy tắc sang ngày là giả định xử lý của nhóm. |
| `delivery_distance_km` | FLOAT | Có thể NULL; xem quy tắc lớp dữ liệu | FLOAT: khoảng cách Haversine với bán kính 6371 km, không phải quãng đường giao thực. Giữ giá trị >50; NULL khi không tính được hoặc store=(0,0). |
| `valid_distance_flag` | BIT | Không null theo logic/tests áp dụng | BIT: 1 khi Haversine tính được và <=50 km theo cấu hình, còn lại 0. KPI khoảng cách phải lọc cờ này. |
| `distance_outlier_flag` | BIT | Không null theo logic/tests áp dụng | BIT: 1 nếu Haversine tính được >50 km, ngược lại 0; không tự loại dòng Fact. |
| `distance_status` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Nhãn nguyên nhân/đánh giá: Valid, Outlier >50 km, Store coordinates (0,0), Not calculable; sinh theo cấu hình khoảng cách. |
| `distance_band` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Nhóm Haversine theo cấu hình: [0,5), [5,10), [10,15), [15,20), [20,50] km và nhãn >50/không tính được/store=(0,0). Không gộp mọi dòng không hợp lệ thành Unknown. |
| `delivery_count` | TINYINT | Không null theo logic/tests áp dụng | TINYINT hằng số 1 cho mỗi dòng; SUM trong Fact bằng số bản ghi khi grain không trùng. Không phải số sản phẩm hoặc giao thành công. |
| `missing_operational_context_flag` | BIT | Không null theo logic/tests áp dụng | BIT: thiếu một trong order_time, weather_name, traffic_level theo delivery_rules.operational_context_fields. Không khẳng định đủ mọi trường vận hành. |
| `source_file_name` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Tên tệp của lần insert đầu tiên, truyền từ staging; không tự đổi sang tệp sửa mới nhất khi upsert. |
| `source_row_number` | BIGINT | Không null theo logic/tests áp dụng | Số thứ tự bản ghi CSV (bắt đầu 1, không tính header) ở lần insert đầu; không đồng nhất số dòng vật lý nếu CSV có trường nhiều dòng. |
| `load_batch_id` | VARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | FK/lineage tới audit.load_batch của lần insert đầu; không phải batch cập nhật gần nhất và không phải run dbt hiện tại. |
| `loaded_at` | DATETIME2 | Không null theo logic/tests áp dụng | Thời điểm insert staging lần đầu, UTC DATETIME2(3), được truyền qua dbt tới Fact; không phải thời điểm build Fact/refresh Power BI. |

### dw.int_delivery_validation_errors

View một dòng cho mỗi vi phạm hard rule của cột ở current-state staging. Một dòng nguồn có thể có nhiều lỗi; không phải lịch sử lỗi từng lần dbt chạy.

| Cột | Kiểu cơ sở / cast | Null/khóa logic | Ý nghĩa / quy tắc |
|---|---|---|---|
| `staging_row_id` | BIGINT | Không null theo logic/tests áp dụng | Định danh BIGINT IDENTITY của dòng current-state staging; ổn định khi upsert cập nhật cùng đơn. Dùng nối lỗi dbt với staging, không phải ID mỗi lần chạy. |
| `order_id` | VARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Order_ID đã trim, giữ hoa/thường. Mage nhận diện khóa bằng trim/case-fold để upsert; Fact kiểm soát duy nhất và không null. Không phải mã nhân viên hay chứng cứ giao thành công. |
| `source_file_name` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Tên tệp của lần insert đầu tiên, truyền từ staging; không tự đổi sang tệp sửa mới nhất khi upsert. |
| `source_row_number` | BIGINT | Không null theo logic/tests áp dụng | Số thứ tự bản ghi CSV (bắt đầu 1, không tính header) ở lần insert đầu; không đồng nhất số dòng vật lý nếu CSV có trường nhiều dòng. |
| `load_batch_id` | VARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | FK/lineage tới audit.load_batch của lần insert đầu; không phải batch cập nhật gần nhất và không phải run dbt hiện tại. |
| `loaded_at` | DATETIME2 | Không null theo logic/tests áp dụng | Thời điểm insert staging lần đầu, UTC DATETIME2(3), được truyền qua dbt tới Fact; không phải thời điểm build Fact/refresh Power BI. |
| `column_name` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Tên cột CSV vi phạm hard rule; một staging_row_id có thể có nhiều cột lỗi. |
| `raw_value` | NVARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Giá trị raw của cột lỗi chuyển sang NVARCHAR(4000) để giải thích; có thể NULL. Có thể chứa tọa độ: chỉ dùng đối soát kỹ thuật, không gửi AI/public. |
| `error_code` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Mã hard rule, ví dụ MISSING_VALUE/MISSING_ORDER_ID, INVALID_CAST, DUPLICATE_ORDER_ID, NEGATIVE_VALUE, OUT_OF_RANGE; phụ thuộc cấu hình. |
| `expected_rule` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Mô tả điều kiện mong đợi của cột lấy từ delivery_rules.fields; optional được sửa nhãn tương ứng. |

### dw.int_delivery_accepted

View dòng enriched không có vi phạm hard rule, một dòng/order_id hợp lệ; dùng chung cho Fact và Dimension phân loại. Required/range lấy từ delivery_rules, không từ số liệu profiling cũ.

| Cột | Kiểu cơ sở / cast | Null/khóa logic | Ý nghĩa / quy tắc |
|---|---|---|---|
| `delivery_key` | CHAR(64) | Không null theo logic/tests áp dụng | SHA2_256 của order_id đã trim, convert CHAR(64) hex trong SQL; khác row_hash của Mage. Xác định từ mã hiện hành, không tự chuẩn hóa hoa/thường trước hash. |
| `staging_row_id` | BIGINT | Không null theo logic/tests áp dụng | Định danh BIGINT IDENTITY của dòng current-state staging; ổn định khi upsert cập nhật cùng đơn. Dùng nối lỗi dbt với staging, không phải ID mỗi lần chạy. |
| `order_id` | VARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Order_ID đã trim, giữ hoa/thường. Mage nhận diện khóa bằng trim/case-fold để upsert; Fact kiểm soát duy nhất và không null. Không phải mã nhân viên hay chứng cứ giao thành công. |
| `order_date` | DATE | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | Ngày nghiệp vụ parse DATE theo style cấu hình (23); không phải thời gian chạy ETL hoặc watermark. Mage loại ngày không parse được trước staging. |
| `order_time` | TIME(0) | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | Giờ đặt hàng TRY_CONVERT(time(0)); thiếu/không parse được là hard-rule theo cấu hình required hiện tại, không thay bằng nửa đêm. |
| `pickup_time` | TIME(0) | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | Giờ pickup TRY_CONVERT(time(0)); thiếu/không parse được là hard-rule hiện tại. Pickup nhỏ hơn order time được giả định sang ngày kế tiếp. |
| `order_hour` | INT | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | DATEPART(hour, order_time), kiểu INT do SQL suy ra, giá trị 0–23; NULL khi giờ thiếu ở lớp trước accepted. |
| `time_period` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Nhóm giờ cấu hình: Night <6, Morning <12, Afternoon <18, còn lại Evening; giờ thiếu thành Unknown ở enriched. |
| `agent_age` | SMALLINT | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | Tuổi parse bằng TRY_CONVERT(smallint); thiếu/cast lỗi/âm bị hard-rule dbt loại theo cấu hình hiện tại. Tuổi 0–17 không âm vẫn giữ và gắn cờ dưới 18. |
| `age_group` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Nhóm tuổi theo delivery_rules.age_groups: Under 18, 18-24, 25-34, 35-44, 45+; thiếu thành Unknown ở enriched. |
| `underage_agent_flag` | BIT | Không null theo logic/tests áp dụng | BIT: 1 khi tuổi parse dưới 18, còn lại 0; thiếu tuổi không tự được coi là hợp lệ. Không loại dòng chỉ vì tuổi dưới 18. |
| `agent_rating_raw` | DECIMAL(4,2) | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | Rating nguồn sau TRY_CONVERT(decimal(4,2)); có thể thiếu/ngoài miền ở lớp trước accepted. Cấu hình hiện tại loại dòng thiếu hoặc ngoài [1,5] khỏi Fact; raw nguồn vẫn giữ ở staging. |
| `agent_rating_valid` | DECIMAL(4,2) | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | Rating numeric thuộc [1,5], còn lại NULL ở enriched. KPI rating chỉ dùng trường này với valid_rating_flag=1. |
| `rating_group` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Nhóm rating theo cấu hình; Unknown khi thiếu, Invalid khi ngoài miền ở enriched. Những dòng vi phạm required/range hiện không vào Fact. |
| `valid_rating_flag` | BIT | Không null theo logic/tests áp dụng | BIT: 1 khi rating trong [1,5], ngược lại 0; dùng lọc KPI rating, không thay thế hard-rule accepted. |
| `weather_name` | NVARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Weather đã trim; ở enriched/Dimension, thiếu được gán Unknown khi trường optional. Một phần natural key tổ hợp Weather–Traffic. |
| `traffic_level` | NVARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Traffic đã trim; ở enriched/Dimension thiếu thành Unknown khi optional; không phải trạng thái ETL. |
| `vehicle_type` | NVARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Loại phương tiện đã trim; ở enriched/Dimension thiếu thành Unknown khi optional; không tự gộp bicycle vào loại khác. |
| `area_name_raw` | VARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Area đã trim tại dbt, giữ lỗi chính tả nguồn để đối soát; chuỗi nguyên trạng vẫn nằm trong staging.raw_amazon_delivery.Area. |
| `area_name` | NVARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Area chuẩn hóa bằng area_aliases (Metropolitian → Metropolitan); enriched/Dimension dùng Unknown cho thiếu optional. |
| `category_name` | NVARCHAR (chiều dài do SELECT suy ra) | Có thể NULL; xem quy tắc lớp dữ liệu | Danh mục đã trim; enriched/Dimension dùng Unknown khi thiếu optional. Grocery vẫn là nhóm độc lập. |
| `delivery_time_minutes` | DECIMAL(10,2) | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | Thời lượng TRY_CONVERT(decimal(10,2)); đơn vị phút là giả định của nhóm, nguồn chưa xác nhận. Required và không âm theo cấu hình hiện tại; giữ IQR outlier. |
| `above_baseline_p90_flag` | BIT | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | BIT: 1 khi thời lượng >195 phút (baseline hiện tại), 0 nếu không vượt, NULL nếu thời lượng NULL; không phải SLA hoặc giao trễ. |
| `delivery_time_iqr_outlier_flag` | BIT | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | BIT: 1 nếu thời lượng <-15 hoặc >265 theo cấu hình hiện tại, 0 nếu trong khoảng, NULL nếu thiếu. Cờ thống kê, không tự loại dòng. |
| `pickup_delay_minutes` | DECIMAL(10,2) | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | DECIMAL(10,2): chênh lệch giây giữa pickup và order timestamp chia 60; cộng 1 ngày khi pickup_time < order_time. NULL khi thiếu đầu vào. |
| `pickup_rollover_flag` | BIT | Không NULL theo hard-rule/đầu vào accepted hiện tại; không khẳng định DDL NOT NULL | BIT: 1 nếu pickup_time < order_time và hai giờ parse được, 0 nếu không; NULL nếu thiếu giờ. Quy tắc sang ngày là giả định xử lý của nhóm. |
| `delivery_distance_km` | FLOAT | Có thể NULL; xem quy tắc lớp dữ liệu | FLOAT: khoảng cách Haversine với bán kính 6371 km, không phải quãng đường giao thực. Giữ giá trị >50; NULL khi không tính được hoặc store=(0,0). |
| `valid_distance_flag` | BIT | Không null theo logic/tests áp dụng | BIT: 1 khi Haversine tính được và <=50 km theo cấu hình, còn lại 0. KPI khoảng cách phải lọc cờ này. |
| `distance_outlier_flag` | BIT | Không null theo logic/tests áp dụng | BIT: 1 nếu Haversine tính được >50 km, ngược lại 0; không tự loại dòng Fact. |
| `distance_status` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Nhãn nguyên nhân/đánh giá: Valid, Outlier >50 km, Store coordinates (0,0), Not calculable; sinh theo cấu hình khoảng cách. |
| `distance_band` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Nhóm Haversine theo cấu hình: [0,5), [5,10), [10,15), [15,20), [20,50] km và nhãn >50/không tính được/store=(0,0). Không gộp mọi dòng không hợp lệ thành Unknown. |
| `delivery_count` | TINYINT | Không null theo logic/tests áp dụng | TINYINT hằng số 1 cho mỗi dòng; SUM trong Fact bằng số bản ghi khi grain không trùng. Không phải số sản phẩm hoặc giao thành công. |
| `missing_operational_context_flag` | BIT | Không null theo logic/tests áp dụng | BIT: thiếu một trong order_time, weather_name, traffic_level theo delivery_rules.operational_context_fields. Không khẳng định đủ mọi trường vận hành. |
| `source_file_name` | NVARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | Tên tệp của lần insert đầu tiên, truyền từ staging; không tự đổi sang tệp sửa mới nhất khi upsert. |
| `source_row_number` | BIGINT | Không null theo logic/tests áp dụng | Số thứ tự bản ghi CSV (bắt đầu 1, không tính header) ở lần insert đầu; không đồng nhất số dòng vật lý nếu CSV có trường nhiều dòng. |
| `load_batch_id` | VARCHAR (chiều dài do SELECT suy ra) | Không null theo logic/tests áp dụng | FK/lineage tới audit.load_batch của lần insert đầu; không phải batch cập nhật gần nhất và không phải run dbt hiện tại. |
| `loaded_at` | DATETIME2 | Không null theo logic/tests áp dụng | Thời điểm insert staging lần đầu, UTC DATETIME2(3), được truyền qua dbt tới Fact; không phải thời điểm build Fact/refresh Power BI. |

## 5. Key-map kỹ thuật

| Bảng | Cột / ràng buộc theo macro | Vai trò |
|---|---|---|
| dw.dim_area_key_map | area_key INT IDENTITY PK; area_name NVARCHAR(64) NOT NULL UNIQUE | Giữ khóa Area qua rebuild |
| dw.dim_category_key_map | category_key INT IDENTITY PK; category_name NVARCHAR(64) NOT NULL UNIQUE | Giữ khóa Category |
| dw.dim_vehicle_key_map | vehicle_key INT IDENTITY PK; vehicle_type NVARCHAR(32) NOT NULL UNIQUE | Giữ khóa Vehicle |
| dw.dim_delivery_condition_key_map | delivery_condition_key INT IDENTITY PK; weather_name/traffic_level NVARCHAR(32) NOT NULL; UNIQUE cặp | Giữ khóa tổ hợp |

Các map được pre-hook ensure_* tạo/bổ sung member; key 0 Unknown. Member không còn trong accepted có thể vẫn tồn tại trong map nhưng không nhất thiết xuất hiện ở Dimension semantic. Không có valid_from/valid_to hoặc lịch sử SCD2. Không reset map khi rerun.

## 6. Audit, trạng thái, snapshot và giới hạn

- load_batch_id trong staging/Fact là insert đầu; updated_load_batch_id của staging mới chỉ lần ghi gần nhất (insert cũng khởi tạo updated_*). Không join Fact.load_batch_id để suy ra tất cả dòng được batch update.
- source_row_number bắt đầu 1 cho record CSV, không tính header; không phải số dòng editor nếu field chứa newline.
- SUCCEEDED ingestion: rows_read = inserted + updated + unchanged + Mage rejected; loaded = inserted + updated. Không áp cứng cho FAILED/STARTED do rollback/chưa đủ counter.
- etl_status SUCCEEDED cần Verify thành công + dbt exit 0 + artifact không fail/error + staging = Fact + COUNT(DISTINCT rejection.staging_row_id). dbt WARN có chủ đích không tự là FAILED.
- Retry cả pipeline tạo batch mới; retry riêng block dbt tạo attempt mới cùng batch. Khi join dashboard chọn attempt mới nhất hoặc hiển thị từng attempt, không SUM counter ingestion nhiều lần.
- NULL exit_code/finished_at hoặc thiếu JSON field không phải 0. STARTED có thể là tiến trình đã bị kill; chưa có heartbeat/stale detector tự động.
- Lỗi loader trước exporter có thể không có load_batch; lỗi Verify có thể không có dbt_run. Audit hiện chưa là lịch sử mọi trigger. Không gán missing dbt thành SUCCESS.
- DATETIME2 SQL lưu UTC không chứa timezone; JSON summary là ISO có offset UTC. Hiển thị UTC+7 cần chuyển rõ, không sửa giá trị nguồn. Thời gian nghiệp vụ không có timezone xác nhận.
- result_summary có identifiers, server/database, ingestion_status/dbt_status/etl_status, timestamps, log_directory; sau dbt thêm exit_code/invocation_id/nodes_total/nodes_failed/tests_total/tests_pass/tests_warn/tests_fail/tests_error/tests_skipped; sau đối soát thêm staging_rows/fact_rows/dbt_rejected_distinct_rows/reconciliation_status. Lỗi sớm có thể không có nhóm field sau.
- Các count trong JSON là snapshot lúc attempt chạy; Fact/rejection là trạng thái dựng lại. Không gắn COUNT Fact hiện tại cho run cũ. error_message ingestion có thể chỉ là warning rejection.
- Mật khẩu sa/API key không thuộc metadata lưu trữ. Không đưa env secret/connection string vào dictionary hoặc log; raw_value rejection có thể chứa tọa độ nên giới hạn người xem.

## 7. Tài liệu liên quan

- [Mapping và lineage](SOURCE_TO_TARGET_MAPPING.md)
- [KPI và khác biệt thiết kế/triển khai](KPI_DICTIONARY.md)
- [Data Contract](DATA_CONTRACT.md)
- [Handoff, bằng chứng và cách tạo docs](../report/METADATA_AUDIT_HANDOFF.md)
