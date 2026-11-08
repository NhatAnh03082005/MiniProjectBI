# Amazon Delivery BI - Power BI

Thư mục này chứa mã nguồn và tài liệu cộng tác cho báo cáo Power BI.

## Cấu trúc

```text
powerbi/
|-- AmazonDeliveryBI_Overview.pbix   # Bản baseline/backup, không dùng để Git merge
|-- project/                         # Lưu Power BI Project (.pbip) dùng để cộng tác
|-- dax/                             # Tài liệu measure DAX dùng chung
|-- theme/                           # Theme JSON
|-- mockups/                         # Ảnh/mockup tham khảo
|-- mock_data/                       # Dữ liệu mẫu nếu cần
|-- specifications/                  # Đặc tả từng trang
|-- pbix/                            # Bản PBIX đóng gói để bàn giao
`-- TEAM_WORKFLOW.md                 # Quy trình branch, commit và merge
```

## Bắt đầu

1. Mở `AmazonDeliveryBI_Overview.pbix` bằng Power BI Desktop.
2. Chọn **File > Save As > Power BI Project (.pbip)**.
3. Lưu project vào thư mục `powerbi/project`.
4. Commit toàn bộ file `.pbip`, thư mục `.Report` và `.SemanticModel` được Power BI tạo.
5. Mỗi thành viên tạo một feature branch và chỉ chỉnh trang được giao.

Không tạo thủ công nội dung bên trong project PBIP. Power BI Desktop phải là công cụ sinh và cập nhật các file này.

Chi tiết xem [TEAM_WORKFLOW.md](TEAM_WORKFLOW.md).
