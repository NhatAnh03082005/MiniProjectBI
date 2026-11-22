# Data Contract — triển khai hiện hành

Cập nhật 22/11/2026. Tài liệu mô tả interface quan sát từ code; không sửa logic, không coi thay đổi triển khai là phê duyệt lại Business Baseline/MOD-01.

## 1. Phạm vi và nguồn xác nhận

- Nguồn sự thật về hành vi: Mage contract/repository, SQL DDL, dbt SQL/YAML và `delivery_rules`, TMDL measures, AI analytics/data/grounding.
- [Data Dictionary](DATA_DICTIONARY.md): đầy đủ bảng/cột, kiểu, nullable DDL và logic.
- [Mapping](SOURCE_TO_TARGET_MAPPING.md): 16 cột nguồn, derived fields, lineage và thứ tự xử lý.
- [KPI Dictionary](KPI_DICTIONARY.md): định nghĩa, trace DAX/AI và giới hạn baseline.
- Tài liệu nghiệp vụ/profiling giữ vai trò thiết kế và bằng chứng lịch sử. Chênh lệch với code phải được nhóm xác nhận; không âm thầm thay business rules trong task metadata.

## 2. Nguồn và interface CSV

Amazon Delivery Dataset trên [Kaggle](https://www.kaggle.com/datasets/sujalsuthar/amazon-delivery-dataset). Snapshot gốc 43.739 dòng, 16 cột, 11/02–06/04/2022; không phải cam kết số dòng hiện tại của DDS.

Header đúng thứ tự:

```text
Order_ID,Agent_Age,Agent_Rating,Store_Latitude,Store_Longitude,Drop_Latitude,Drop_Longitude,Order_Date,Order_Time,Pickup_Time,Weather,Traffic,Vehicle,Area,Delivery_Time,Category
```

Mage đọc UTF-8, dtype string, không tự biến missing token thành NaN. Sai header hoặc ID lặp sau trim/case-fold trong cùng batch làm fail batch. ID null-like/quá 32 ký tự hoặc Order_Date không parse được bị reject từng dòng. 15 giá trị raw ngoài ID được SHA-256 JSON để phân biệt thay đổi.

Runtime variable `source_file_path` tùy chọn; tương đối từ `BI_PROJECT_ROOT`, mặc định `data/raw/amazon_delivery.csv`. Batch name sinh động. Không có LSET/CET; ngày nghiệp vụ không dùng lọc incremental. FULL_LOAD và INCREMENTAL đều upsert, không tự truncate.

## 3. Staging contract

`staging.raw_amazon_delivery`: 26 cột, một phiên bản hiện hành/Order_ID theo khóa Mage chuẩn hóa trim/case-fold.

- 16 giá trị nguồn giữ nguyên chuỗi; dbt mới trim/cast/normalize.
- ID mới insert; ID cũ/hash khác update 15 thuộc tính; hash giống unchanged.
- `load_batch_id`, `loaded_at`, `source_file_name`, `source_row_number` là insert đầu.
- `row_hash`, `updated_load_batch_id`, `updated_at`, `updated_source_file_name`, `updated_source_row_number` mô tả phiên bản hiện hành; insert cũng khởi tạo updated_*.
- Không lưu mọi phiên bản raw trong bảng này. Không khẳng định file nguồn được tự archive bởi loader; việc giữ file phục vụ replay phải được vận hành riêng.
- DDL cho phép một số NULL để tương thích legacy, không đồng nghĩa pipeline chấp nhận ID/ngày không hợp lệ.

## 4. Orchestration và authentication

```text
Loader → Validate → Export/upsert → Verify staging
       → build_amazon_delivery_dds → dbt build (models + tests) → đối soát DDS
```

Mage/dbt dùng cùng MSSQL_SERVER/MSSQL_DATABASE/MSSQL_DRIVER. Script demo hiện mặc định SQL Authentication (`sa`), hỏi mật khẩu ở terminal; runner profile dbt tham chiếu env_var cho user/password, không ghi mật khẩu vào source/profile. Có lựa chọn Windows Authentication.

Runner đặt `DBT_SQLSERVER_DATABASE=MSSQL_DATABASE` cho dbt source; target schema `dw`, threads=1. Không dùng profile cá nhân trỏ sang database khác. dbt build chạy kể cả loaded=0. Mỗi attempt có target/log riêng ở `logs/etl/<batch>/<attempt>/`.

Lịch/trigger do trưởng nhóm cấu hình riêng. Application lock bảo vệ thao tác upsert và khoảng dbt build/đối soát; vẫn phải chạy pipeline tuần tự vì giữa các block không có snapshot lock xuyên toàn run. Không hứa per-run snapshot cô lập nếu cố chạy chồng hoặc sửa staging ngoài pipeline.

## 5. dbt và DDS contract

| Model / đối tượng | Grain / materialization | Vai trò |
|---|---|---|
| stg_amazon_delivery | Một staging_row_id; view | Trim/null normalization/TRY_CONVERT/Area alias |
| int_delivery_enriched | Một staging_row_id; view | Hash khóa, nhóm, pickup, Haversine và flags trước accepted |
| int_delivery_validation_errors | Một lỗi/cột/staging_row_id; view | Required/cast/range/duplicate hard rules |
| int_delivery_accepted | Một order_id đạt hard rules; view | Anti-join error rows, đầu vào chung Fact và Dimension phân loại |
| delivery_rejections | Một lỗi/cột/staging_row_id; table rebuild | Trạng thái lỗi hiện tại, không phải lịch sử mỗi run |
| 5 dim_* | Ngày hoặc natural key; table rebuild | Calendar, Weather–Traffic, Vehicle, Area, Category; Unknown 0 |
| 4 dim_*_key_map | Một natural key; bảng kỹ thuật qua pre-hook | INT IDENTITY/unique keys giữ surrogate bền, không reset theo batch |
| fact_delivery | Một accepted order_id; table rebuild, 33 cột | 5 FK, measures/flags và lineage; không exact coordinates |

5 Dimension là `dim_date`, `dim_delivery_condition`, `dim_vehicle`, `dim_area`, `dim_category`. Không có dim_agent hoặc dim_time. Surrogate keys được tests kiểm tra not_null/unique/relationships; đây không phải cam kết có SQL FK vật lý trên Fact.

Các nhóm cột Fact:

- Khóa: delivery_key, order_id, date_key, delivery_condition_key, vehicle_key, area_key, category_key.
- Giờ: order_time, pickup_time, order_hour, time_period.
- Agent/rating: agent_age, age_group, underage_agent_flag, agent_rating_raw, agent_rating_valid, rating_group, valid_rating_flag.
- Delivery/pickup: delivery_time_minutes, above_baseline_p90_flag, delivery_time_iqr_outlier_flag, pickup_delay_minutes, pickup_rollover_flag.
- Khoảng cách: delivery_distance_km, valid_distance_flag, distance_outlier_flag, distance_status, distance_band.
- Count/chất lượng: delivery_count, missing_operational_context_flag.
- Lineage: source_file_name, load_batch_id, loaded_at (insert staging đầu, không phải thời gian dựng DDS).

## 6. Quality và phép biến đổi hiện hành

- Required: ID, age, rating, 4 tọa độ, Order_Date, Order_Time, Pickup_Time, Delivery_Time. Optional: Weather/Traffic/Vehicle/Area/Category, thiếu thành Unknown ở enriched.
- Age >=0; rating [1,5]; latitude [-90,90]; longitude [-180,180]; Delivery_Time >=0. Required missing/cast/range sai tạo dbt rejection và không vào Fact.
- Tuổi dưới 18 nhưng không âm, IQR outlier, store=(0,0), Haversine>50 không tự là hard reject.
- Haversine giữ giá trị >50; valid flag chỉ khi tính được và <=50. Store=(0,0) hoặc không tính được: distance NULL, status/band giải thích.
- Pickup nhỏ hơn order time cộng 1 ngày; thiếu đầu vào trả NULL ở enriched, không thay bằng 0.
- 195 phút là baseline cố định của nhóm; IQR bounds hiện -15 và 265. P90/P95 KPI tính lại theo filter.
- Nhóm tuổi/giờ/rating/khoảng cách lấy từ delivery_rules. Thay cấu hình không thuộc task metadata; AI còn kiểm tra ngưỡng 195/50 nên cần đồng bộ khi nhóm chủ động thay rule sau này.

## 7. Audit, lỗi và rerun

`audit.load_batch` là ingestion, tạo ở exporter; `audit.dbt_run` là attempt sau Verify, FK tới load_batch_id, grain 1:n.

Với ingestion SUCCEEDED:

```text
rows_read = rows_inserted + rows_updated + rows_unchanged + rows_rejected
rows_loaded = rows_inserted + rows_updated
```

Với toàn ETL SUCCEEDED: Verify thành công, dbt exit 0, artifact không fail/error và:

```text
staging_rows = fact_rows + COUNT(DISTINCT delivery_rejections.staging_row_id)
```

- Mage rejection loại trước staging; dbt rejection loại sau staging. Một staging row có nhiều dbt error records. Không cộng các số sai grain.
- dbt WARN rejection có chủ đích không tự là FAILED. error_message ingestion có thể chứa warning dù status SUCCEEDED.
- Lỗi dbt sau staging commit: ingestion vẫn SUCCEEDED, attempt/pipeline FAILED. Một số model dbt có thể đã dựng; không hứa rollback DDS toàn bộ.
- Rerun toàn pipeline cùng file sinh batch mới, dòng hợp lệ đã ghi thường unchanged, rồi dbt vẫn build. Retry riêng block dbt có attempt mới trên cùng batch; không nhân đôi counter ingestion khi join.
- result_summary là JSON snapshot các số đếm/tests/đối soát tại attempt, trường lỗi sớm có thể vắng mặt. Không dùng Fact hiện tại thay snapshot run cũ.
- Loader lỗi trước exporter có thể không có load_batch; Verify lỗi có thể không có dbt_run. Chưa có audit trigger/start mọi run hoặc heartbeat/stale recovery. Thiếu bản ghi dbt không được suy thành SUCCESS.
- UTC DATETIME2 cho vận hành; JSON có UTC offset. Business dates/times chưa có timezone nguồn xác nhận. Power BI hiển thị UTC+7 phải ghi nhãn rõ.

## 8. Power BI và AI consumer

- Power BI đọc Fact + 5 Dimension, relationship một–nhiều một chiều, Date Hierarchy Year/Quarter/Month/Date. Hiện 4 trang nghiệp vụ; trang ETL Monitoring là hạng mục riêng, không được coi là đã có từ tài liệu này.
- Import cần Refresh sau DDS cập nhật. AI ứng dụng đọc DDS riêng, không lấy trực tiếp filter context trong Power BI.
- KPI count hiện SUM(delivery_count); mean/median/percentile/rate phải tính lại trên accepted Fact theo filter, không cộng trung bình giữa các nhóm.
- Đơn vị phút là giả định; không có SLA, doanh thu, chi phí, Agent_ID. Không gọi vượt baseline là giao trễ hoặc kết luận quan hệ nhân quả.
- AI Python tính aggregates/breakdowns/evidence, Gemini tạo summary/explanations và hỏi đáp dựa trên chứng cứ; không sinh SQL tự do. Key nhập theo hướng dẫn AI, không thuộc dictionary/log.
- Payload LLM không chứa ID bản ghi/tọa độ chi tiết; bảng rejection.raw_value có thể chứa tọa độ nên chỉ đối soát kỹ thuật.
- Tên key JSON/phản hồi thực tế: xem ai/analytics.py, ai/grounding.py và ai/README.md, không dùng ví dụ logical schema cũ thay runtime schema.

## 9. Tiêu chí đối chiếu metadata

- [ ] Đúng 16 header CSV, 26 cột raw, 33 cột Fact theo code.
- [ ] Mô tả key/hash/lineage phân biệt insert đầu, update gần nhất và dbt attempt.
- [ ] Dictionary mô tả đủ cột DDL staging/audit và 11 model dbt.
- [ ] YAML giữ nguyên tests/config/relationships; chỉ mô tả và meta tài liệu thay đổi.
- [ ] Nghiệm thu số liệu trên đúng database/snapshot/filter; không gán số profiling nguồn làm KPI Fact.
- [ ] Phân biệt trạng thái ingestion, dbt, ETL; thiếu log/NULL không thành công giả.
- [ ] Không thay logic/schema/KPI/dashboard hoặc chạy ETL trong task metadata.

## 10. Khác biệt cần nhóm lưu ý

Thiết kế ban đầu giữ missing Order_Time/rating và rating 6 trong Fact; code hiện dùng required/range hard rules và tách rejection. Fact thêm distance_outlier_flag/distance_status so với 31 cột ban đầu, và giữ Haversine>50 để giải thích. Metadata này ghi nhận triển khai, không tự giải quyết tranh luận yêu cầu nghiệp vụ. Khi thay quy tắc phải cập nhật đồng thời dbt, KPI/AI, tài liệu và kiểm thử.

Các số profiling nguồn trong tài liệu gốc vẫn là bằng chứng lịch sử. Kết quả demo người dùng cung cấp: 43.741 staging = 43.596 Fact + 145 rejected; không dùng làm hằng số kiểm tra mọi lần chạy. Bằng chứng và giới hạn task: [Metadata handoff](../report/METADATA_AUDIT_HANDOFF.md).
