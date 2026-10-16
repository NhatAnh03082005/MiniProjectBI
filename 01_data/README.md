# Data

## Official dataset

- **Dataset:** Amazon Delivery Dataset.
- **Người đăng Kaggle:** Sujal Suthar.
- **Nguồn:** <https://www.kaggle.com/datasets/sujalsuthar/amazon-delivery-dataset>.
- **License:** MIT, theo metadata đã xác minh trong báo cáo profiling.
- **CSV:** `raw/amazon_delivery.csv`.
- **ZIP:** `raw/archive/amazon_delivery_original.zip`.
- **Quy mô:** 43.739 dòng, không tính header; 16 cột.
- **Khoảng thời gian:** 2022-02-11 đến 2022-04-06; 44 Active Day.
- **SHA-256 CSV:** `B922DFBDFED11AC2C9508C9E915326364FC95A2D00440B4C3E01E56BFFB6A4ED`.
- **SHA-256 ZIP:** `0ADD736B4AFD2A616856003CBC736F05AFD02242AC4E3F416F5C07FC53EB25A8`.

> Dataset được sử dụng theo tên do người đăng Kaggle cung cấp. Project không khẳng định đây là dữ liệu vận hành chính thức của Amazon.

## Data handling rules

- Không chỉnh sửa, đổi tên, di chuyển hoặc ghi đè hai file raw.
- Không sửa dấu hoặc thay thế raw coordinates.
- Chỉ tạo artefact dẫn xuất từ bản sao sau khi Mapping và Load Design được duyệt.
- Cleaning và standardization thực hiện tại lớp transformation, không sửa raw.
- Rejected record phải kèm lý do và bằng chứng kiểm tra.
- Không công khai drop coordinate chính xác ở mức dòng.

## Ý nghĩa thư mục

| Thư mục | Mục đích |
|---|---|
| `raw/` | CSV nguồn nguyên trạng và ZIP archive |
| `full_load/` | Batch nạp ban đầu sau khi thiết kế được duyệt |
| `incremental/` | Batch tăng thêm sau khi thiết kế được duyệt |
| `rejected/` | Record bị từ chối kèm lý do khi pipeline được triển khai |

## Trạng thái

Dataset Selection, Data Profiling và Business Baseline đã hoàn thành. Chưa tạo batch, pipeline, SQL Server, staging hoặc Data Warehouse.
