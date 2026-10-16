# Dataset Selection - Supermarket Sales

## Dataset Information

| Thuộc tính | Giá trị |
|---|---|
| Tên dataset | Supermarket Sales |
| Tác giả | Fares Ashraf |
| Nguồn | Kaggle |
| Link | <https://www.kaggle.com/datasets/faresashraf1001/supermarket-sales> |
| Chủ đề | Phân tích hoạt động bán hàng của chuỗi siêu thị |
| Số file lưu trong raw | 2 file: 1 CSV chính và 1 ZIP lưu trữ |
| File chính | `01_data/raw/supermarket_sales.csv` |
| File ZIP | `01_data/raw/archive/supermarket_sales_faresashraf_v2.zip` |
| Quy mô | 1.000 dòng dữ liệu, không tính header; 17 cột |
| Khoảng thời gian | 2019-01-01 đến 2019-03-30 |
| SHA-256 CSV | `C5E0490DA62001D3066A56B3AA9C891C8D3ED42B6C2D09C8CA18B2A409AC93CD` |

## Grain ở mức dữ liệu nguồn

Mỗi dòng đại diện cho một bản ghi giao dịch bán hàng duy nhất trong dữ liệu nguồn, được nhận diện bởi `Invoice ID`, phát sinh tại một chi nhánh, vào một thời điểm và gắn với một `Product line`. Dataset không có SKU hoặc chi tiết dòng hóa đơn nên không đủ cơ sở xác định cấu trúc hóa đơn vật lý bên dưới.

## Lý do lựa chọn

- Chủ đề bán hàng có ý nghĩa thực tiễn và phù hợp với Business Intelligence.
- Dữ liệu có thời gian, chi nhánh, thành phố, phân khúc khách hàng, ngành hàng và phương thức thanh toán để phân tích đa chiều.
- Các trường số hỗ trợ measures và KPI bán hàng; các công thức tiền đã được kiểm chứng trên toàn bộ 1.000 dòng.
- `Invoice ID` duy nhất trong snapshot, thuận lợi cho kiểm tra idempotency.
- Ba tháng dữ liệu cho phép mô phỏng một Full Load và hai Incremental Load theo tháng.
- Quy mô đủ nhỏ để hoàn thành trong phạm vi mini project nhưng vẫn hỗ trợ mô hình Star Schema và hai trang dashboard.

## Các chiều phân tích

- Ngày và tháng.
- Chi nhánh và thành phố trong cùng chiều Branch/Location.
- Customer type và Gender trong chiều Customer Segment.
- Product line.
- Payment method.
- Giờ hoặc khung giờ từ thuộc tính trong Fact, không tạo `dim_time`.

## KPI baseline

KPI chính: Total Sales, Total Quantity, Invoice Count, Average Order Value, Weighted Average Unit Price, Total COGS, Average Rating, Average Daily Sales và Monthly Sales Growth có chú thích.

KPI phụ: Total Gross Income và Average Gross Income per Invoice. Gross Income bằng Tax 5% trong dataset này nên không trình bày hai chỉ số như KPI độc lập. `gross margin percentage` cố định và không dùng làm KPI biến động.

Weighted Average Unit Price dùng `SUM(cogs) / SUM(Quantity)`; giá trị toàn dataset khoảng `55.823481`.

## Phương án Incremental Load

| Batch | Khoảng dữ liệu | Số dòng |
|---|---|---:|
| Full Load | 01/2019 | 352 |
| Incremental 1 | 02/2019 | 303 |
| Incremental 2 | 03/2019, đến ngày 30 | 345 |

Watermark dự kiến dựa trên Date kết hợp Time. `Invoice ID` được dùng để kiểm tra idempotency và tránh nạp trùng. Chưa tạo file batch hoặc pipeline.

## Hạn chế dữ liệu

- Chỉ có ba tháng dữ liệu, không đủ cơ sở phân tích mùa vụ hoặc xu hướng dài hạn.
- Không có SKU, tên sản phẩm chi tiết hoặc chi tiết dòng hóa đơn.
- Không có Customer ID; không hỗ trợ Customer Lifetime Value hoặc hành vi mua lặp lại.
- Không có tồn kho, discount, return hoặc chi phí vận hành.
- Branch và City ánh xạ một-một nhưng có hạn chế ngữ nghĩa từ nguồn.
- Không thể xác minh cấu trúc hóa đơn vật lý bên dưới.
- Có 9 giao dịch giá trị cao bị IQR gắn cờ nhưng chưa có bằng chứng là lỗi; các dòng này được giữ lại.

## Kết luận

Supermarket Sales phù hợp với mini project BI vì hỗ trợ một quy trình nghiệp vụ bán hàng, một Fact, năm Dimension baseline, các KPI bán hàng, phân tích theo thời gian và mô phỏng incremental load. Các giới hạn của dữ liệu đã được ghi nhận để tránh suy diễn vượt quá phạm vi nguồn.
