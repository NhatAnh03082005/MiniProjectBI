# Task Board

| ID | Giai đoạn | Công việc | Người phụ trách | Đầu vào | Đầu ra cần bàn giao | Deadline | Trạng thái | Vướng mắc |
|---|---|---|---|---|---|---|---|---|
| SET-01 | Project setup | Tạo cấu trúc project | Trưởng nhóm | Yêu cầu đề bài | Cấu trúc thư mục và tài liệu khởi tạo | Ngày 1 | Done | Không |
| DAT-01 | Dataset selection | Chọn và ghi nguồn dataset Kaggle | Cả nhóm, trưởng nhóm điều phối | Tiêu chí lựa chọn | `DATASET_SELECTION.md` | Ngày 1 | Done | Không |
| DAT-02 | Data profiling | Khảo sát cấu trúc và chất lượng dữ liệu | Trưởng nhóm | Dataset đã chọn | `DATA_PROFILE.md` | Ngày 1 | Done | Không |
| BUS-01 | Business requirements | Xác định bối cảnh nghiệp vụ chi tiết | Trưởng nhóm | DATA_PROFILE và phạm vi | Bối cảnh, mục tiêu và quy trình trong `BUSINESS_REQUIREMENTS.md` | Ngày 2 | Done | Không |
| BUS-02 | Business requirements | Xác định người sử dụng chính | Trưởng nhóm | Bối cảnh nghiệp vụ | Ba vai trò, nhu cầu quyết định và trang sử dụng trong `BUSINESS_REQUIREMENTS.md` | Ngày 2 | Done | Không |
| BUS-03 | Business requirements | Viết 6-8 câu hỏi nghiệp vụ | Trưởng nhóm + thành viên 4 | Bối cảnh và người dùng | Đúng 8 câu hỏi BQ-01 đến BQ-08 và traceability trong `BUSINESS_REQUIREMENTS.md` | Ngày 2 | Done | Không |
| KPI-01 | Business requirements | Chốt KPI Dictionary | Trưởng nhóm + thành viên 4 | KPI baseline và câu hỏi nghiệp vụ | 9 KPI chính, 2 KPI hỗ trợ, diagnostic measure và validation rules trong `KPI_DICTIONARY.md` | Ngày 2 | Done | Không |
| MOD-01 | Dimensional modeling | Chốt Star Schema | Trưởng nhóm + thành viên 3 | Yêu cầu nghiệp vụ và KPI Dictionary | Danh sách Fact/Dimension, grain, keys và relationships | Ngày 2 | Todo | Phụ thuộc KPI-01 |
| MOD-02 | Dimensional modeling | Vẽ Star Schema | Thành viên 3 | Star Schema đã chốt | Sơ đồ mô hình có khóa và quan hệ | Ngày 2 | Todo | Phụ thuộc MOD-01 |
| MAP-01 | Data mapping | Tạo Source-to-Target Mapping | Thành viên 3 | Data Profile và Star Schema | Mapping nguồn-đích cho toàn bộ cột | Ngày 2 | Todo | Phụ thuộc MOD-01 |
| LOAD-01 | Full/Incremental design | Thiết kế Full/Incremental Load | Thành viên 2 | Batch baseline và mapping | Quy tắc batch, watermark, idempotency và rerun | Ngày 2 | Todo | Phụ thuộc MAP-01 |
| ARC-01 | Architecture confirmation | Chốt kiến trúc công nghệ | Trưởng nhóm + cả nhóm | Yêu cầu kỹ thuật và mô hình | Sơ đồ kiến trúc, cấu hình chia sẻ và trách nhiệm thành phần | Ngày 2 | Todo | Chưa chốt SQL Server dùng chung |
| HOF-01 | Project coordination | Chuẩn bị gói bàn giao cho từng thành viên | Trưởng nhóm | Requirements, schema, mapping và kiến trúc | Checklist đầu vào/đầu ra cho 4 thành viên | Ngày 2 | Todo | Phụ thuộc BUS, MOD, MAP, LOAD, ARC |
| MAG-01 | Mage.ai | Xây dựng Full/Incremental Load, kiểm tra và logging | Thành viên 2 | Thiết kế load và mapping | Pipeline Mage.ai có log và bằng chứng chạy | Ngày 3 | Todo | Phụ thuộc LOAD-01, ARC-01 |
| DBT-01 | dbt | Xây dựng models, tests và documentation | Thành viên 3 | Staging và Star Schema | dbt project, tests, docs và lineage | Ngày 4 | Todo | Phụ thuộc MOD-01, MAP-01, MAG-01 |
| DWH-01 | Data Warehouse | Tạo và nạp Data Warehouse | Thành viên 3 | dbt models và thiết kế SQL Server | Fact/Dimension được nạp và đối soát | Ngày 4 | Todo | Phụ thuộc DBT-01 |
| PBI-01 | Power BI | Tạo semantic model và hai trang dashboard | Thành viên 4 | Data Warehouse và KPI Dictionary | File `.pbix`, DAX, relationships và hai trang dashboard | Ngày 5 | Todo | Phụ thuộc DWH-01, KPI-01 |
| AI-01 | Generative AI | Tạo AI Summary có thể kiểm chứng | Trưởng nhóm | KPI đã tính | Thành phần AI Summary và test cases | Ngày 5 | Todo | Phụ thuộc PBI-01 |
| RPT-01 | Report | Tổng hợp báo cáo | Trưởng nhóm, cả nhóm đóng góp | Bằng chứng triển khai | Báo cáo PDF hoàn chỉnh | Ngày 6 | Todo | Phụ thuộc các phần kỹ thuật |
| VID-01 | Video demo | Chuẩn bị kịch bản và ghi demo | Cả nhóm | Hệ thống hoàn chỉnh | Kịch bản và video demo end-to-end | Ngày 6 | Todo | Phụ thuộc E2E-01 |
| E2E-01 | End-to-end testing | Kiểm thử toàn bộ luồng và thu thập bằng chứng | Trưởng nhóm + cả nhóm | Các thành phần đã tích hợp | Biên bản, số liệu đối soát và bằng chứng kiểm thử | Ngày 6 | Todo | Phụ thuộc MAG/DBT/DWH/PBI/AI |
| SUB-01 | Final submission | Kiểm tra và đóng gói bài nộp | Trưởng nhóm | Toàn bộ deliverables | Gói nộp cuối cùng theo checklist | Ngày 6 | Todo | Phụ thuộc RPT-01, VID-01, E2E-01 |

> Các mốc “Ngày 1” đến “Ngày 6” là thứ tự trong quỹ thời gian 6 ngày; ngày lịch cụ thể chưa được nhóm cung cấp. Đã hoàn thành Project Setup, Dataset Selection, Data Profiling, Business Requirements và KPI Dictionary. Task tiếp theo là `MOD-01` - Chốt Star Schema.
