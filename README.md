# Business Intelligence System for Last-Mile Delivery Analysis with Generative AI

## Mục tiêu

Xây dựng hệ thống Business Intelligence tích hợp Generative AI để phân tích hiệu suất giao hàng chặng cuối từ dữ liệu nguồn đến dashboard và AI Summary có thể kiểm chứng.

## Dataset

- **Tên:** Amazon Delivery Dataset.
- **Người đăng Kaggle:** Sujal Suthar.
- **Nguồn:** <https://www.kaggle.com/datasets/sujalsuthar/amazon-delivery-dataset>.
- **License:** MIT, theo metadata đã xác minh trong báo cáo profiling.
- **Quy mô:** 43.739 dòng, 16 cột.
- **Khoảng thời gian:** 2022-02-11 đến 2022-04-06; 44 ngày có dữ liệu.
- **Chủ đề:** phân tích hiệu suất giao hàng chặng cuối.

> Dataset được sử dụng theo tên do người đăng Kaggle cung cấp. Project không khẳng định đây là dữ liệu vận hành chính thức của Amazon.

## Tài liệu hiện hành

- [Dataset Selection](00_project_management/DATASET_SELECTION.md)
- [Data Profile](00_project_management/DATA_PROFILE_AMAZON_DELIVERY.md)
- [Business Requirements](00_project_management/BUSINESS_REQUIREMENTS.md)
- [KPI Dictionary](00_project_management/KPI_DICTIONARY.md)
- [Approved Dimensional Model](00_project_management/DIMENSIONAL_MODEL.md)
- [Team Handoff Guide](00_project_management/TEAM_HANDOFF_GUIDE.md)
- [Task Board](00_project_management/TASK_BOARD.md)
- [Decision Log](00_project_management/DECISION_LOG.md)

## Business Baseline

- Grain nghiệp vụ: một dòng là một bản ghi giao hàng nguồn duy nhất, nhận diện bởi `Order_ID`; không khẳng định completed delivery.
- Đúng 8 Business Questions mang tính mô tả/chẩn đoán.
- Đúng 10 KPI chính, không có KPI tài chính và không có On-time Delivery Rate.
- Delivery Time dùng phút theo project assumption; metadata Kaggle truy xuất được chưa xác nhận đơn vị.
- Share Above Baseline P90 dùng ngưỡng thống kê nội bộ cố định 195 phút, không phải SLA.
- Quality rules đã khóa cho missing, pickup rollover, rating, age, categorical values và distance.

## Trạng thái

| Hạng mục | Trạng thái |
|---|---|
| Project Setup | Done |
| Dataset Selection v2 | Done |
| Data Profiling v2 | Done |
| Business Requirements v2 | Done |
| Business Questions v2 | Done |
| KPI Dictionary v2 | Done |
| Team Handoff v2 | Done |
| Logical Dimensional Model — MOD-01 | Approved / Done |
| Star Schema diagram — MOD-02 | Todo |
| Technical Implementation | Not deployed |

Task tiếp theo là `MOD-02` — vẽ và đặc tả Star Schema dựa trên logical model đã Approved. Chưa hoàn thành Star Schema diagram, Mapping, Mage.ai, dbt, SQL Server/Data Warehouse, Power BI hoặc AI component.

## Cấu trúc thư mục

- `00_project_management`: tài liệu quản lý và quyết định.
- `01_data`: dữ liệu raw, full load, incremental và rejected.
- `02_sql`: script database, staging, warehouse và audit.
- `03_mage`: mã nguồn và kiểm thử Mage.ai.
- `04_dbt`: models, tests, macros, seeds và snapshots dbt.
- `05_powerbi`: PBIX, DAX, mockup và theme.
- `06_ai`: mã nguồn, prompt, test và input mẫu cho AI.
- `07_report`: nội dung, hình và tài liệu tham khảo của báo cáo.
- `08_evidence`: bằng chứng kiểm thử theo từng thành phần.
- `09_demo`: kịch bản và bản ghi demo.
- `config`: ví dụ cấu hình không chứa bí mật.
