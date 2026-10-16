# Team Handoff Guide - Tasks 7–9

## 1. Document Control

| Thuộc tính | Giá trị |
|---|---|
| Tên tài liệu | Team Handoff Guide - Tasks 7–9 |
| Mục đích | Bàn giao Business Baseline v1 và hướng dẫn thực hiện Dimensional Modeling, Source-to-Target Mapping, Full/Incremental Load Design |
| Phiên bản | Handoff v1 |
| Ngày cập nhật | 2026-10-16 |
| Trạng thái | Ready for Tasks 7–9 |
| Đối tượng sử dụng | Thành viên phụ trách Dimensional Modeling, Mapping và Load Design |
| Project root | `D:\BI\Mini Project\BI_AI_Project` |
| Branch baseline | `main` sau khi khởi tạo repository local |
| Commit baseline | Commit chứa tài liệu này; xác nhận bằng `git rev-parse HEAD` sau khi clone/pull |

## 2. Project Overview

Project xây dựng hệ thống Business Intelligence tích hợp Generative AI để phân tích hoạt động bán hàng của một chuỗi siêu thị. Dataset được sử dụng là **Supermarket Sales** của Fares Ashraf, gồm 1.000 bản ghi và 17 cột trong khoảng 2019-01-01 đến 2019-03-30.

Người dùng chính là **Sales/Operations Manager**. Hai nhóm người dùng phụ là **Branch Manager** và **BI Analyst**. Hệ thống hướng tới theo dõi quy mô bán hàng, xu hướng, đóng góp theo chi nhánh/ngành hàng/phân khúc/phương thức thanh toán/thời điểm và Rating, nhưng không suy luận nguyên nhân ngoài dữ liệu.

Luồng kiến trúc dự kiến:

`Kaggle CSV → Mage.ai → SQL Server staging → dbt → SQL Server dw → Power BI → Generative AI`

SQL Server dự kiến dùng ba schema: `staging`, `dw`, `audit`.

Sản phẩm cuối cùng gồm báo cáo PDF, source Mage.ai, source dbt, SQL scripts, thành phần AI, file Power BI `.pbix`, dataset và nguồn Kaggle, hướng dẫn cấu hình/chạy và video demo end-to-end. Kế hoạch nhóm có phạm vi 6 ngày.

Baseline chỉ dùng một Fact và năm Dimension vì dataset ghi nhận một quy trình bán hàng duy nhất, có ít nhóm phân loại ổn định và không có căn cứ dữ liệu cho SKU, khách hàng cá nhân, tồn kho hay quy trình nghiệp vụ bổ sung. Đây mới là baseline thiết kế; cấu trúc vật lý phải được chốt trong MOD-01.

## 3. Current Progress

| Giai đoạn | Task ID | Nội dung | Trạng thái | Tài liệu bằng chứng |
|---|---|---|---|---|
| Project Setup | SET-01 | Tạo cấu trúc project | Done | `README.md`, cấu trúc thư mục project |
| Dataset Selection | DAT-01 | Chọn và ghi nguồn dataset Kaggle | Done | `DATASET_SELECTION.md`, `01_data/README.md` |
| Data Profiling | DAT-02 | Khảo sát cấu trúc và chất lượng dữ liệu | Done | `DATA_PROFILE.md` |
| Business Requirements | BUS-01 | Chốt bối cảnh và quy trình nghiệp vụ | Done | `BUSINESS_REQUIREMENTS.md` |
| Business Requirements | BUS-02 | Chốt người dùng chính và phụ | Done | `BUSINESS_REQUIREMENTS.md` |
| Business Requirements | BUS-03 | Chốt đúng 8 Business Questions | Done | `BUSINESS_REQUIREMENTS.md` |
| KPI Dictionary | KPI-01 | Chốt KPI, công thức và validation baseline | Done | `KPI_DICTIONARY.md` |
| Dimensional Modeling | MOD-01 | Chốt Star Schema | Todo — task tiếp theo | Chưa có; dự kiến `DIMENSIONAL_MODEL.md` |
| Dimensional Modeling | MOD-02 | Vẽ Star Schema | Todo | Chưa có; dự kiến `STAR_SCHEMA.md` và file sơ đồ |
| Data Mapping | MAP-01 | Tạo Source-to-Target Mapping | Todo | Chưa có; dự kiến `SOURCE_TO_TARGET_MAPPING.md` |
| Load Design | LOAD-01 | Thiết kế Full/Incremental Load | Todo | Chưa có; dự kiến `LOAD_DESIGN.md` |

Giai đoạn 1–6 là **Business Baseline v1 — Locked**. Fact/Dimension hiện mới là baseline nghiệp vụ; keys, data types, SCD, mapping và load design chưa được chốt hoặc triển khai vật lý.

## 4. Mandatory Reading Order

1. `README.md` — hiểu mục tiêu, cấu trúc, kiến trúc, sản phẩm bàn giao và trạng thái tổng thể.
2. `00_project_management/PROJECT_CONTEXT.md` — hiểu bối cảnh, grain, baseline mô hình và giới hạn dữ liệu.
3. `00_project_management/PROJECT_SCOPE.md` — hiểu nội dung in scope, out of scope và các quyết định còn chờ.
4. `00_project_management/DATASET_SELECTION.md` — hiểu nguồn, lý do chọn dữ liệu, checksum và batch baseline.
5. `00_project_management/DATA_PROFILE.md` — hiểu 17 cột, chất lượng, công thức nguồn, cardinality và hạn chế đã kiểm chứng.
6. `00_project_management/BUSINESS_REQUIREMENTS.md` — hiểu người dùng, mục tiêu, đúng 8 Business Questions và traceability.
7. `00_project_management/KPI_DICTIONARY.md` — hiểu công thức, aggregation, filter context, baseline và cảnh báo của KPI.
8. `00_project_management/DECISION_LOG.md` — phân biệt quyết định đang hiệu lực với quyết định lịch sử đã `Superseded`.
9. `00_project_management/NAMING_CONVENTIONS.md` — dùng đúng tên raw, tên chuẩn hóa và quy ước artefact kỹ thuật.
10. `00_project_management/TASK_BOARD.md` — kiểm tra task, phụ thuộc, người phụ trách và Definition of Done ở mức kế hoạch.
11. `00_project_management/TEAM_HANDOFF_GUIDE.md` — thực hiện Task 7–9 đúng thứ tự, phạm vi và quy trình Git.

## 5. Non-negotiable Baseline

### 5.1. Dataset và tính toàn vẹn

- Dataset: Supermarket Sales của Fares Ashraf.
- Kaggle: <https://www.kaggle.com/datasets/faresashraf1001/supermarket-sales>.
- CSV: `01_data/raw/supermarket_sales.csv`, 1.000 dòng, 17 cột, từ 2019-01-01 đến 2019-03-30; tháng 03 chỉ đến ngày 30.
- CSV SHA-256: `C5E0490DA62001D3066A56B3AA9C891C8D3ED42B6C2D09C8CA18B2A409AC93CD`.
- ZIP: `01_data/raw/archive/supermarket_sales_faresashraf_v2.zip`.
- ZIP SHA-256: `8CF934EAE9105BD7AF8FD3ABEBB9F41003465FB0475875DE5CC97D2A0C8496B2`.
- Không chỉnh sửa, đổi tên, di chuyển hay ghi đè CSV/ZIP raw.

### 5.2. Grain và phạm vi dữ liệu

> Mỗi dòng đại diện cho một bản ghi giao dịch bán hàng duy nhất trong dữ liệu nguồn, được nhận diện bởi `Invoice ID`, phát sinh tại một chi nhánh, vào một thời điểm và gắn với một `Product line`.

Không gọi grain là dòng SKU và không khẳng định `Invoice ID` phản ánh đầy đủ cấu trúc hóa đơn vật lý. Dataset không có SKU, Product ID, Customer ID, Inventory, Discount, Return, Operating cost hoặc dữ liệu đủ để tính lợi nhuận ròng.

### 5.3. Fact, Dimension và thời gian

- Fact baseline: `fact_sales`; `Invoice ID` là degenerate business key.
- Đúng năm Dimension baseline: `dim_date`, `dim_branch_location`, `dim_customer_segment`, `dim_product_line`, `dim_payment_method`.
- Không tạo `dim_time`.
- `transaction_time`, `transaction_hour`, `time_period` dự kiến nằm trong Fact.
- Morning: `10:00–11:59`; Afternoon: `12:00–16:59`; Evening: `17:00–20:59`.
- Không tự thêm Fact hoặc Dimension. Thay đổi baseline chỉ được đề xuất có lập luận và phải được trưởng nhóm xác nhận trong Decision Log.

### 5.4. Sales và công thức nguồn

- Raw có `Sales`, không có `Total`; tên chuẩn hóa dự kiến là `sales_amount`.
- `cogs = Unit price × Quantity`.
- `Tax 5% = cogs × 5%`.
- `Sales = cogs + Tax 5% = cogs × 1.05`.
- `gross income = Tax 5%`.
- `gross margin percentage` cố định `4.761904762`.
- Không tạo cột nguồn `Total`, không gọi Gross Income là lợi nhuận ròng và không trình bày Gross Income/Tax như hai KPI độc lập.

### 5.5. KPI và aggregation

Chín KPI chính: Total Sales, Total Quantity, Invoice Count, Average Order Value, Weighted Average Unit Price, Total COGS, Average Rating, Average Daily Sales và Monthly Sales Growth.

Hai KPI hỗ trợ: Total Gross Income và Average Gross Income per Invoice. Diagnostic measure: Average Listed Unit Price per Transaction.

- Weighted Average Unit Price: `SUM(cogs) / SUM(Quantity)`; không dùng `SUM(Unit price)`.
- Average Daily Sales dùng ngày có giao dịch:

```DAX
Average Daily Sales :=
DIVIDE(
    [Total Sales],
    DISTINCTCOUNT(fact_sales[transaction_date])
)
```

- Monthly Sales Growth là ratio non-additive, không phải semi-additive.
- Dataset không có measure semi-additive vì không chứa balance hoặc snapshot như tồn kho cuối kỳ.
- Không tự gắn ký hiệu tiền tệ vì nguồn không xác nhận đơn vị tiền tệ.

### 5.6. Kỷ luật thay đổi

- Task 7–9 chỉ tạo thiết kế và tài liệu; không triển khai SQL Server, Mage.ai, dbt, Power BI hay AI.
- Không suy luận vượt quá dữ liệu và không tự thay đổi Business Baseline v1.
- Không sửa/xóa quyết định cũ. Mọi quyết định mới đã được trưởng nhóm xác nhận phải được thêm bằng Decision ID tiếp theo.

## 6. Task 7 — MOD-01 và MOD-02

### 6.1. MOD-01 — Chốt Star Schema

Đầu ra dự kiến: `00_project_management/DIMENSIONAL_MODEL.md`.

Tài liệu phải xác định business process, grain, Fact chính thức, danh sách Dimension, cột từng bảng, logical data type, primary key, surrogate key, business key, foreign key, degenerate business key, nullability, Default/Unknown Member, SCD strategy, measure và aggregation behavior, cardinality, filter direction dự kiến trong Power BI, cùng lý do giữ hoặc loại từng raw column.

#### `fact_sales`

Đánh giá các nhóm trường sau:

- Surrogate technical key như `sales_key` nếu nhóm quyết định cần.
- `invoice_id` — degenerate business key.
- Foreign keys tới đúng năm Dimension baseline.
- `transaction_time`, `transaction_hour`, `time_period`.
- `unit_price`, `quantity`, `tax_5_percent`, `sales_amount`, `cogs_amount`, `gross_margin_percentage`, `gross_income_amount`, `rating`.
- Metadata tải dữ liệu nếu có mục đích rõ ràng, ví dụ `batch_id`, `source_file_name`, `loaded_at`.

Không tự đưa metadata vào Fact. Hãy so sánh việc đặt metadata tại staging/audit với việc giữ trong Fact và ghi rõ lập luận.

#### `dim_date`

Đánh giá: `date_key`, `full_date`, `day_of_month`, `day_name`, `day_of_week_number`, `week_of_year`, `month_number`, `month_name`, `quarter_number`, `year`, `year_month`, `is_weekend`.

#### `dim_branch_location`

Đánh giá surrogate key, `branch`, `city`. Giữ nguyên ánh xạ nguồn:

- Alex → Yangon.
- Cairo → Mandalay.
- Giza → Naypyitaw.

Không tự sửa tên Branch theo City.

#### `dim_customer_segment`

Đánh giá surrogate key, `customer_type`, `gender`. Đây không phải Dimension Customer cá nhân.

#### `dim_product_line`

Đánh giá surrogate key và `product_line`. Đây không phải Product hoặc SKU Dimension.

#### `dim_payment_method`

Đánh giá surrogate key và `payment_method`.

#### Quyết định phải được đề xuất và chốt trong MOD-01

- Có dùng `sales_key` trong Fact hay không.
- Kiểu surrogate key.
- Unknown Member: khuyến nghị `0` hoặc `-1`, nhưng phải chọn một giá trị và dùng nhất quán.
- SCD: `dim_date` không áp dụng SCD; các Dimension phân loại nhỏ được khuyến nghị SCD Type 1 vì nguồn là snapshot tĩnh và không có lịch sử thay đổi.
- Giữ `gross_margin_percentage` trong Fact để bảo toàn nguồn/đối soát hay loại khỏi mart.
- Vị trí metadata tải dữ liệu.
- Kiểu dữ liệu SQL Server dự kiến.
- Quan hệ 1:* từ Dimension tới Fact.
- Single-direction filtering từ Dimension tới Fact.

Các mục trên là đề xuất cần review; không được mô tả như quyết định đã xác nhận từ Giai đoạn 1–6.

### 6.2. MOD-02 — Vẽ Star Schema

Đầu ra dự kiến:

- `00_project_management/STAR_SCHEMA.md`.
- File chỉnh sửa được, ưu tiên `07_report/figures/star_schema.drawio`.
- File dùng trong báo cáo, ưu tiên `07_report/figures/star_schema.png` hoặc `.svg`.

Sơ đồ phải đặt `fact_sales` ở trung tâm, có đúng năm Dimension baseline, hiển thị PK/FK và cardinality 1:*, không tạo Snowflake không cần thiết, không nối trực tiếp các Dimension, không thêm `dim_time`, `dim_customer` hoặc `dim_product`, và không dùng cột chưa có trong `DIMENSIONAL_MODEL.md`.

Nếu không có công cụ tạo `.drawio`, có thể dùng Mermaid trong `STAR_SCHEMA.md`, nhưng phải ghi rõ chưa tạo file draw.io.

## 7. Task 8 — MAP-01 Source-to-Target Mapping

Đầu ra dự kiến: `00_project_management/SOURCE_TO_TARGET_MAPPING.md`.

Mapping phải bao phủ đủ 17 cột nguồn. Mỗi dòng cần có: thứ tự, source file, source column, source type, source meaning, staging table, staging column, dbt staging model, standardized column, transformation rule, target table, target column, target type, nullable, Default/Unknown handling, data quality rule, dbt test dự kiến và ghi chú.

Các mapping tối thiểu:

| Source | Standardized |
|---|---|
| `Invoice ID` | `invoice_id` |
| `Customer type` | `customer_type` |
| `Product line` | `product_line` |
| `Unit price` | `unit_price` |
| `Tax 5%` | `tax_5_percent` |
| `Sales` | `sales_amount` |
| `Date` | `transaction_date` |
| `Time` | `transaction_time` |
| `Payment` | `payment_method` |
| `gross margin percentage` | `gross_margin_percentage` |
| `gross income` | `gross_income_amount` |
| `Rating` | `rating` |

Không đổi tên cột trong raw CSV. Chuẩn hóa chỉ diễn ra ở dbt staging model. Mapping còn phải mô tả `date_key`, các Dimension surrogate key, `transaction_hour`, `time_period` và metadata/audit key nếu MOD-01 đã chốt. Không làm mất bất kỳ cột nguồn nào mà không giải thích lý do.

## 8. Task 9 — LOAD-01 Full/Incremental Load Design

Đầu ra dự kiến: `00_project_management/LOAD_DESIGN.md`. Task này chỉ thiết kế, chưa tạo batch, bảng SQL hay pipeline.

### 8.1. Batch baseline

| Batch | Khoảng dữ liệu | Số dòng |
|---|---|---:|
| Full Load | 2019-01-01 đến 2019-01-31 | 352 |
| Incremental 1 | 2019-02-01 đến 2019-02-28 | 303 |
| Incremental 2 | 2019-03-01 đến 2019-03-30 | 345 |
| Tổng | 2019-01-01 đến 2019-03-30 | 1.000 |

### 8.2. Watermark và idempotency

- Watermark dựa trên `Date + Time`; có thể chuẩn hóa thành `transaction_timestamp` nếu thiết kế yêu cầu.
- `Invoice ID` dùng cho idempotency và duplicate protection.
- Mô tả cách chạy lại cùng batch không tạo bản ghi trùng.
- Phân biệt duplicate trong cùng batch và duplicate với dữ liệu đã nạp.
- Không tự xóa dữ liệu lịch sử khi rerun.
- Định nghĩa rõ kết quả `insert`, `skip`, `reject`, `fail`.

### 8.3. Audit logging

Đề xuất logic cho `audit.etl_run_log` với tối thiểu: `run_id`, `pipeline_name`, `batch_name`, `load_type`, `source_file`, `watermark_start`, `watermark_end`, `started_at`, `ended_at`, `status`, `rows_read`, `rows_inserted`, `rows_updated`, `rows_skipped`, `rows_rejected`, `error_message`.

Đây là thiết kế logic; không tạo bảng SQL trong Task 9.

### 8.4. Rerun, recovery và reconciliation

Thiết kế phải nêu điều kiện rerun, tiêu chí batch thành công/thất bại, cách ngăn duplicate, cách tiếp tục sau lỗi, cách đối soát số dòng, điều kiện ghi rejected record và điều kiện dừng toàn batch.

Kiểm tra bắt buộc:

- Full Load = 352.
- Incremental 1 = 303.
- Incremental 2 = 345.
- Tổng sau ba batch = 1.000.
- `Invoice ID` distinct = 1.000.
- Không null key bắt buộc.
- Công thức Sales/COGS/Tax vẫn đúng.
- Checksum raw không đổi.

## 9. Definition of Done cho Task 7–9

### MOD-01

- Grain nhất quán với baseline.
- Có một Fact và đúng năm Dimension.
- Chốt keys, Unknown Member và SCD.
- Có data types và relationships.
- Không phát sinh Dimension không có căn cứ.

### MOD-02

- Sơ đồ khớp hoàn toàn với `DIMENSIONAL_MODEL.md`.
- Có PK/FK và cardinality.
- Có file nguồn chỉnh sửa được hoặc Mermaid.
- Có hình dùng được trong báo cáo nếu công cụ hỗ trợ.

### MAP-01

- Mapping đủ 17 cột nguồn và các cột dẫn xuất.
- Có transformation và test dự kiến.
- Không tạo cột `Total`.
- Không làm mất cột nguồn mà không giải thích.

### LOAD-01

- Có batch, watermark, idempotency, audit, rerun và reconciliation.
- Tổng batch bằng 1.000 dòng.
- Không sửa raw.
- Chưa triển khai pipeline.

Chỉ sau khi đạt toàn bộ acceptance criteria và được trưởng nhóm review mới cập nhật Task Board sang `Done`.

## 10. Files được phép tạo hoặc cập nhật

### Được tạo

- `00_project_management/DIMENSIONAL_MODEL.md`.
- `00_project_management/STAR_SCHEMA.md`.
- `00_project_management/SOURCE_TO_TARGET_MAPPING.md`.
- `00_project_management/LOAD_DESIGN.md`.
- File sơ đồ trong `07_report/figures/`.

### Được cập nhật có kiểm soát sau khi task hoàn thành

- `00_project_management/TASK_BOARD.md`.
- `00_project_management/DECISION_LOG.md`.
- `00_project_management/PROJECT_CONTEXT.md`.
- `00_project_management/PROJECT_SCOPE.md`.
- `00_project_management/NAMING_CONVENTIONS.md` nếu có tên vật lý mới được chốt.
- `README.md` chỉ để cập nhật liên kết hoặc trạng thái.

### Không được chỉnh sửa trong Task 7–9

- CSV/ZIP raw.
- `00_project_management/DATA_PROFILE.md`.
- `00_project_management/DATASET_SELECTION.md`.
- `00_project_management/BUSINESS_REQUIREMENTS.md`.
- `00_project_management/KPI_DICTIONARY.md`, trừ khi phát hiện lỗi và được trưởng nhóm đồng ý.
- File kỹ thuật Mage.ai, dbt, SQL Server, Power BI hoặc AI.

## 11. Git Collaboration Workflow

Sau khi nhận repository:

```powershell
git clone <REPOSITORY_URL>
cd BI_AI_Project
git switch main
git pull --ff-only
git switch -c feature/task-7-9-modeling
```

Trong quá trình làm:

```powershell
git status
git add <các-file-liên-quan>
git commit -m "docs: complete dimensional model and load design"
git push -u origin feature/task-7-9-modeling
```

Quy tắc:

- Không làm trực tiếp trên `main` nếu nhóm sử dụng pull request.
- Không dùng `git push --force` hoặc `git push --force-with-lease`.
- Không dùng `git reset --hard`.
- Không xóa lịch sử Decision Log.
- Không commit `.env`, password, API key, token, private key hoặc credential.
- Không commit runtime, cache, virtual environment hoặc recording tạm dung lượng lớn.
- Pull Request phải mô tả file đã tạo, quyết định đã chốt, kiểm tra đã chạy và vấn đề còn pending.

## 12. Handoff Checklist

- [ ] Đã clone đúng repository.
- [ ] Đã đọc tài liệu theo thứ tự bắt buộc.
- [ ] Đã hiểu grain và giới hạn của `Invoice ID`.
- [ ] Đã hiểu raw có `Sales`, không có cột `Total`.
- [ ] Đã hiểu dataset không có SKU hoặc Customer ID.
- [ ] Đã hiểu một Fact và đúng năm Dimension baseline.
- [ ] Đã hiểu KPI và aggregation behavior.
- [ ] Đã hiểu dataset không có semi-additive measure.
- [ ] Đã hiểu Task 7–9 chỉ là thiết kế, chưa triển khai vật lý.
- [ ] Đã tạo branch riêng `feature/task-7-9-modeling`.
- [ ] Đã biết các file được phép tạo hoặc cập nhật.
- [ ] Đã biết Definition of Done của từng task.
- [ ] Đã biết báo blocker và quyết định cần xác nhận cho trưởng nhóm.

## 13. Báo cáo kết quả khi hoàn thành Task 7–9

Thành viên phải báo cáo:

- File đã đọc.
- File đã tạo.
- File đã cập nhật.
- Grain.
- Fact và Dimension.
- Keys.
- Unknown Member.
- SCD.
- Source-to-Target Mapping.
- Batch/load design.
- Validation đã chạy.
- Checksum raw trước và sau.
- Những vấn đề cần trưởng nhóm xác nhận.
- Commit hash.
- Branch và Pull Request link.
