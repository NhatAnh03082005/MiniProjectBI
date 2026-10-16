# Data Profile - Supermarket Sales

SHA-256: C5E0490DA62001D3066A56B3AA9C891C8D3ED42B6C2D09C8CA18B2A409AC93CD

Chuỗi SHA-256 ở dòng đầu được giữ nguyên theo yêu cầu. Chuỗi này là checksum trước phân tích của file `supermarket_sales.csv`.

## 1. Executive Summary

- File được phân tích: `01_data/raw/supermarket_sales.csv`.
- Dataset có 1.000 dòng dữ liệu và 17 cột.
- Dữ liệu bao phủ từ 2019-01-01 đến 2019-03-30, gồm 89 ngày trong 3 tháng của năm 2019.
- Không phát hiện null, chuỗi rỗng, chuỗi chỉ có khoảng trắng, khoảng trắng thừa, lỗi chuyển kiểu, dòng trùng hoàn toàn hoặc `Invoice ID` trùng.
- Toàn bộ giá trị số đạt các quy tắc miền giá trị được kiểm tra.
- File thực tế không có cột `Total`; cột tương ứng là `Sales`. Công thức tương đương `Sales = cogs + Tax 5%` đạt 1.000/1.000 dòng với ngưỡng sai số 0,01.
- `gross income = Tax 5%` đạt 1.000/1.000 dòng.
- `gross margin percentage` có đúng một giá trị `4.761904762` trên toàn bộ dataset. Cột này không phân biệt giao dịch và không hữu ích như một KPI biến động.
- Grain chính thức của file nguồn là một bản ghi giao dịch bán hàng duy nhất cho mỗi `Invoice ID`, phát sinh tại một chi nhánh, vào một thời điểm và gắn với một `Product line`. Dataset không có SKU hoặc chi tiết dòng hóa đơn nên không đủ cơ sở xác định cấu trúc hóa đơn vật lý bên dưới.
- Ba công thức bổ sung `cogs = Unit price × Quantity`, `Tax 5% = cogs × 5%` và `Sales = cogs × 1.05` đều đạt 1.000/1.000 dòng với ngưỡng sai số 0,01. Vì vậy KPI đơn giá bình quân chính được chốt là `SUM(cogs) / SUM(Quantity)`.
- Dữ liệu phù hợp để mô phỏng Full Load tháng 01/2019, Incremental 1 tháng 02/2019 và Incremental 2 tháng 03/2019.

## 2. Dataset Source

| Thuộc tính              | Giá trị                                                             |
| ----------------------- | ------------------------------------------------------------------- |
| Dataset                 | Supermarket Sales                                                   |
| Tác giả Kaggle          | Fares Ashraf                                                        |
| Nguồn                   | <https://www.kaggle.com/datasets/faresashraf1001/supermarket-sales> |
| Chủ đề                  | Phân tích hoạt động bán hàng của chuỗi siêu thị                     |
| File phân tích          | `supermarket_sales.csv`                                             |
| SHA-256 trước phân tích | `C5E0490DA62001D3066A56B3AA9C891C8D3ED42B6C2D09C8CA18B2A409AC93CD`  |

## 3. Files Found in Raw Folder

| Đường dẫn tương đối                                        | Loại |   Kích thước | Cách xử lý                                          |
| ---------------------------------------------------------- | ---: | -----------: | --------------------------------------------------- |
| `01_data/raw/supermarket_sales.csv`                        |  CSV | 140.285 byte | File dữ liệu chính được đọc để profiling            |
| `01_data/raw/archive/supermarket_sales_faresashraf_v2.zip` |  ZIP |  37.407 byte | Giữ nguyên, không đọc trực tiếp, không giải nén lại |

Không có CSV thứ hai trong thư mục raw.

## 4. Dataset Structure

### 4.1. Thông tin kỹ thuật

| Thuộc tính      | Kết quả                                                                                                                                                                                                        |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Encoding        | UTF-8 có BOM (`EF BB BF`)                                                                                                                                                                                      |
| Ký tự phân cách | Dấu phẩy (`,`)                                                                                                                                                                                                 |
| Dòng dữ liệu    | 1.000, không tính header                                                                                                                                                                                       |
| Số cột          | 17                                                                                                                                                                                                             |
| Tên cột         | `Invoice ID`, `Branch`, `City`, `Customer type`, `Gender`, `Product line`, `Unit price`, `Quantity`, `Tax 5%`, `Sales`, `Date`, `Time`, `Payment`, `cogs`, `gross margin percentage`, `gross income`, `Rating` |

### 4.2. Năm dòng mẫu

Dataset không có tên, email, số điện thoại, địa chỉ cá nhân hoặc mã khách hàng cá nhân. `Invoice ID` là mã giao dịch, không phải định danh cá nhân.

| Invoice ID  | Branch | City      | Customer type | Gender | Product line           | Unit price | Quantity |  Tax 5% |    Sales | Date      | Time        | Payment     |   cogs | gross margin percentage | gross income | Rating |
| ----------- | ------ | --------- | ------------- | ------ | ---------------------- | ---------: | -------: | ------: | -------: | --------- | ----------- | ----------- | -----: | ----------------------: | -----------: | -----: |
| 750-67-8428 | Alex   | Yangon    | Member        | Female | Health and beauty      |      74.69 |        7 | 26.1415 | 548.9715 | 1/5/2019  | 1:08:00 PM  | Ewallet     | 522.83 |             4.761904762 |      26.1415 |    9.1 |
| 226-31-3081 | Giza   | Naypyitaw | Normal        | Female | Electronic accessories |      15.28 |        5 |    3.82 |    80.22 | 3/8/2019  | 10:29:00 AM | Cash        |   76.4 |             4.761904762 |         3.82 |    9.6 |
| 631-41-3108 | Alex   | Yangon    | Normal        | Female | Home and lifestyle     |      46.33 |        7 | 16.2155 | 340.5255 | 3/3/2019  | 1:23:00 PM  | Credit card | 324.31 |             4.761904762 |      16.2155 |    7.4 |
| 123-19-1176 | Alex   | Yangon    | Member        | Female | Health and beauty      |      58.22 |        8 |  23.288 |  489.048 | 1/27/2019 | 8:33:00 PM  | Ewallet     | 465.76 |             4.761904762 |       23.288 |    8.4 |
| 373-73-7910 | Alex   | Yangon    | Member        | Female | Sports and travel      |      86.31 |        7 | 30.2085 | 634.3785 | 2/8/2019  | 10:37:00 AM | Ewallet     | 604.17 |             4.761904762 |      30.2085 |    5.3 |

## 5. Preliminary Data Dictionary

`csv.DictReader` đọc mọi giá trị CSV dưới dạng chuỗi. Cột “Kiểu dữ liệu đề xuất” thể hiện kiểu nên dùng sau khi làm sạch và nạp dữ liệu, không phải thay đổi đã được áp dụng.

| Tên cột gốc             | Tên đề xuất chuẩn hóa     | Kiểu dữ liệu đọc được | Kiểu dữ liệu đề xuất | Ý nghĩa nghiệp vụ dự kiến              | Ví dụ               |
| ----------------------- | ------------------------- | --------------------- | -------------------- | -------------------------------------- | ------------------- |
| Invoice ID              | `invoice_id`              | string                | varchar/business key | Mã hóa đơn hoặc giao dịch nguồn        | `750-67-8428`       |
| Branch                  | `branch`                  | string                | varchar              | Nhãn chi nhánh trong dữ liệu nguồn     | `Alex`              |
| City                    | `city`                    | string                | varchar              | Thành phố gắn với chi nhánh            | `Yangon`            |
| Customer type           | `customer_type`           | string                | varchar              | Phân khúc Member/Normal                | `Member`            |
| Gender                  | `gender`                  | string                | varchar              | Nhóm giới tính do nguồn cung cấp       | `Female`            |
| Product line            | `product_line`            | string                | varchar              | Nhóm ngành hàng, không phải SKU        | `Health and beauty` |
| Unit price              | `unit_price`              | string                | decimal(18,2)        | Đơn giá một đơn vị                     | `74.69`             |
| Quantity                | `quantity`                | string                | integer              | Số lượng đơn vị trong giao dịch        | `7`                 |
| Tax 5%                  | `tax_5_percent`           | string                | decimal(18,4)        | Thuế 5% theo nguồn                     | `26.1415`           |
| Sales                   | `sales_amount`            | string                | decimal(18,4)        | Tổng giá trị bán hàng gồm thuế         | `548.9715`          |
| Date                    | `transaction_date`        | string                | date                 | Ngày giao dịch                         | `1/5/2019`          |
| Time                    | `transaction_time`        | string                | time                 | Giờ giao dịch theo định dạng 12 giờ    | `1:08:00 PM`        |
| Payment                 | `payment_method`          | string                | varchar              | Phương thức thanh toán                 | `Ewallet`           |
| cogs                    | `cogs`                    | string                | decimal(18,2)        | Giá vốn hàng bán theo nguồn            | `522.83`            |
| gross margin percentage | `gross_margin_percentage` | string                | decimal(18,9)        | Tỷ lệ gross margin cố định trong nguồn | `4.761904762`       |
| gross income            | `gross_income`            | string                | decimal(18,4)        | Thu nhập gộp theo dữ liệu nguồn        | `26.1415`           |
| Rating                  | `rating`                  | string                | decimal(3,1)         | Điểm đánh giá giao dịch                | `9.1`               |

Ý nghĩa nghiệp vụ trên là diễn giải từ tên cột, giá trị quan sát và mô tả dataset. File CSV không bị đổi tên cột trong task này. File nguồn không có cột `Total`; `Sales` là tổng giá trị bán hàng gồm thuế, được giữ nguyên trong raw data và dự kiến chuẩn hóa thành `sales_amount` trong dbt. Không tạo cột nguồn giả tên `Total`.

## 6. Data Quality Results

### 6.1. Kiểm tra theo cột

Tất cả 17 cột đều có kết quả: null = 0; tỷ lệ null = 0,00%; chuỗi rỗng = 0; chỉ chứa khoảng trắng = 0; khoảng trắng thừa đầu/cuối = 0; giá trị không chuyển được sang kiểu đề xuất = 0.

| Cột                     | Giá trị phân biệt | Null | Rỗng | Chỉ khoảng trắng | Thừa khoảng trắng | Sai kiểu đề xuất |
| ----------------------- | ----------------: | ---: | ---: | ---------------: | ----------------: | ---------------: |
| Invoice ID              |             1.000 |    0 |    0 |                0 |                 0 |                0 |
| Branch                  |                 3 |    0 |    0 |                0 |                 0 |                0 |
| City                    |                 3 |    0 |    0 |                0 |                 0 |                0 |
| Customer type           |                 2 |    0 |    0 |                0 |                 0 |                0 |
| Gender                  |                 2 |    0 |    0 |                0 |                 0 |                0 |
| Product line            |                 6 |    0 |    0 |                0 |                 0 |                0 |
| Unit price              |               943 |    0 |    0 |                0 |                 0 |                0 |
| Quantity                |                10 |    0 |    0 |                0 |                 0 |                0 |
| Tax 5%                  |               990 |    0 |    0 |                0 |                 0 |                0 |
| Sales                   |               990 |    0 |    0 |                0 |                 0 |                0 |
| Date                    |                89 |    0 |    0 |                0 |                 0 |                0 |
| Time                    |               506 |    0 |    0 |                0 |                 0 |                0 |
| Payment                 |                 3 |    0 |    0 |                0 |                 0 |                0 |
| cogs                    |               990 |    0 |    0 |                0 |                 0 |                0 |
| gross margin percentage |                 1 |    0 |    0 |                0 |                 0 |                0 |
| gross income            |               990 |    0 |    0 |                0 |                 0 |                0 |
| Rating                  |                61 |    0 |    0 |                0 |                 0 |                0 |

### 6.2. Kiểm tra miền giá trị

| Quy tắc                          | Số dòng vi phạm |
| -------------------------------- | --------------: |
| `Unit price > 0`                 |               0 |
| `Quantity` là số nguyên và `> 0` |               0 |
| `Tax 5% >= 0`                    |               0 |
| `Sales > 0`                      |               0 |
| `cogs >= 0`                      |               0 |
| `gross income >= 0`              |               0 |
| `Rating` trong `[0, 10]`         |               0 |

## 7. Duplicate and Invoice ID Analysis

| Kiểm tra                    | Kết quả |
| --------------------------- | ------: |
| Dòng trùng hoàn toàn        |       0 |
| Tỷ lệ dòng thuộc nhóm trùng |   0,00% |
| `Invoice ID` null hoặc rỗng |       0 |
| `Invoice ID` phân biệt      |   1.000 |
| ID bị trùng                 |       0 |
| Dòng liên quan đến ID trùng |       0 |

Kết luận: trong file hiện tại, `Invoice ID` có thể dùng làm khóa nghiệp vụ của từng dòng. Kết luận này chỉ áp dụng cho snapshot đã phân tích; pipeline sau này vẫn cần kiểm tra uniqueness và not-null cho mỗi lần nạp.

## 8. Date and Time Analysis

### 8.1. Định dạng và tính hợp lệ

- `Date` được xác minh là `M/D/YYYY` theo quy ước tháng/ngày/năm.
- Parse theo `MM/DD/YYYY` hợp lệ 1.000/1.000 dòng.
- Parse theo `DD/MM/YYYY` chỉ hợp lệ 413 dòng và thất bại 587 dòng. Ví dụ `1/27/2019`, `3/25/2019` và `2/25/2019` loại bỏ cách hiểu ngày/tháng/năm.
- Ngày không hợp lệ: 0.
- `Time` có định dạng `h:mm:ss AM/PM`; giờ không hợp lệ: 0.
- Giờ sớm nhất: 10:00; giờ muộn nhất: 20:59.

### 8.2. Phạm vi thời gian

| Chỉ tiêu          |    Kết quả |
| ----------------- | ---------: |
| Ngày nhỏ nhất     | 2019-01-01 |
| Ngày lớn nhất     | 2019-03-30 |
| Số ngày phân biệt |         89 |
| Số tháng          |          3 |
| Số năm            |          1 |

| Tháng   | Số dòng | Tỷ lệ |
| ------- | ------: | ----: |
| 2019-01 |     352 | 35,2% |
| 2019-02 |     303 | 30,3% |
| 2019-03 |     345 | 34,5% |

Dữ liệu phù hợp để mô phỏng incremental load theo tháng vì có ba tháng liền nhau và mọi dòng đều parse được ngày. Khoảng thời gian chỉ dài ba tháng nên phân tích xu hướng dài hạn hoặc mùa vụ là không đủ cơ sở.

## 9. Categorical Column Analysis

### 9.1. Giá trị và tần suất

| Cột           | Giá trị                | Số dòng | Tỷ lệ |
| ------------- | ---------------------- | ------: | ----: |
| Branch        | Alex                   |     340 | 34,0% |
| Branch        | Cairo                  |     332 | 33,2% |
| Branch        | Giza                   |     328 | 32,8% |
| City          | Yangon                 |     340 | 34,0% |
| City          | Mandalay               |     332 | 33,2% |
| City          | Naypyitaw              |     328 | 32,8% |
| Customer type | Member                 |     565 | 56,5% |
| Customer type | Normal                 |     435 | 43,5% |
| Gender        | Female                 |     571 | 57,1% |
| Gender        | Male                   |     429 | 42,9% |
| Product line  | Electronic accessories |     170 | 17,0% |
| Product line  | Fashion accessories    |     178 | 17,8% |
| Product line  | Food and beverages     |     174 | 17,4% |
| Product line  | Health and beauty      |     152 | 15,2% |
| Product line  | Home and lifestyle     |     160 | 16,0% |
| Product line  | Sports and travel      |     166 | 16,6% |
| Payment       | Cash                   |     344 | 34,4% |
| Payment       | Credit card            |     311 | 31,1% |
| Payment       | Ewallet                |     345 | 34,5% |

Không phát hiện biến thể khác chữ hoa/chữ thường, lỗi khoảng trắng hoặc giá trị gần giống cho cùng một nhóm trong sáu cột phân loại.

### 9.2. Quan hệ phụ thuộc

| Branch | City duy nhất | Số dòng |
| ------ | ------------- | ------: |
| Alex   | Yangon        |     340 |
| Cairo  | Mandalay      |     332 |
| Giza   | Naypyitaw     |     328 |

Mỗi `Branch` ánh xạ đúng một `City`, và mỗi `City` cũng ánh xạ đúng một `Branch`. `Branch` được xem là nhãn nhận diện chi nhánh theo dữ liệu nguồn, không mặc định là địa danh; `City` được giữ là thuộc tính thành phố do nguồn cung cấp. Hai trường phù hợp đặt chung trong `dim_branch_location`. Phân tích Sales by Branch và Sales by City tạo cùng cơ cấu phân nhóm, nên dashboard không cần đặt đồng thời cả hai biểu đồ. Sự khác biệt ngữ nghĩa giữa tên Branch và City là hạn chế dữ liệu nguồn, không phải lỗi kỹ thuật có thể tự sửa. Các ánh xạ `Alex -> Yangon`, `Cairo -> Mandalay`, `Giza -> Naypyitaw` được giữ nguyên.

## 10. Numerical Column Analysis

Các giá trị bất thường thống kê dùng quy tắc IQR: nhỏ hơn `Q1 - 1,5 x IQR` hoặc lớn hơn `Q3 + 1,5 x IQR`. Đây chỉ là cờ rà soát, không phải kết luận dữ liệu sai.

| Cột                     | Hợp lệ |         Min |         Max |        Mean |      Median | Bằng 0 |  Âm | Cờ IQR |
| ----------------------- | -----: | ----------: | ----------: | ----------: | ----------: | -----: | --: | -----: |
| Unit price              |  1.000 |       10,08 |       99,96 |     55,6721 |       55,23 |      0 |   0 |      0 |
| Quantity                |  1.000 |           1 |          10 |        5,51 |           5 |      0 |   0 |      0 |
| Tax 5%                  |  1.000 |      0,5085 |       49,65 |   15,379369 |      12,088 |      0 |   0 |      9 |
| Sales                   |  1.000 |     10,6785 |    1.042,65 |  322,966749 |     253,848 |      0 |   0 |      9 |
| cogs                    |  1.000 |       10,17 |      993,00 |   307,58738 |      241,76 |      0 |   0 |      9 |
| gross margin percentage |  1.000 | 4,761904762 | 4,761904762 | 4,761904762 | 4,761904762 |      0 |   0 |      0 |
| gross income            |  1.000 |      0,5085 |       49,65 |   15,379369 |      12,088 |      0 |   0 |      9 |
| Rating                  |  1.000 |         4,0 |        10,0 |      6,9727 |         7,0 |      0 |   0 |      0 |

Chín giao dịch giá trị cao bị gắn cờ đồng thời ở `Sales`, `cogs`, `Tax 5%` và `gross income`. Năm ví dụ đầu có `Invoice ID`: `234-65-2137`, `687-47-8271`, `860-79-0874`, `554-42-2417`, `271-88-8734`. Các dòng này vẫn thỏa công thức nghiệp vụ và miền giá trị, nên chưa có bằng chứng chúng là lỗi.

## 11. Business Formula Validation

Ngưỡng sai số cho giá trị tiền là 0,01.

| Công thức | Đạt | Không đạt | Độ lệch lớn nhất | Ví dụ không đạt | Kết luận |
|---|---:|---:|---:|---|---|
| `cogs = Unit price × Quantity` | 1.000 | 0 | `1,14 × 10^-13` | Không có | Đạt toàn bộ |
| `Tax 5% = cogs × 5%` | 1.000 | 0 | `7,11 × 10^-15` | Không có | Đạt toàn bộ |
| `Sales = cogs × 1.05` | 1.000 | 0 | `1,14 × 10^-13` | Không có | Đạt toàn bộ |
| `Sales = cogs + Tax 5%` | 1.000 | 0 | `1,14 × 10^-13` | Không có | Đạt toàn bộ; dùng `Sales` vì file không có `Total` |
| `gross income = Tax 5%` | 1.000 | 0 | 0 | Không có | Đạt toàn bộ |
| `gross margin percentage` cố định | 1.000 | 0 | 0 | Không có | Có đúng một giá trị trên toàn bộ dữ liệu |

Vì `cogs = Unit price x Quantity` đạt toàn bộ 1.000 dòng, đơn giá bình quân có trọng số có thể tính bằng `SUM(cogs) / SUM(Quantity)`. Trên snapshot hiện tại, `SUM(cogs) = 307.587,38`, `SUM(Quantity) = 5.510`, nên Weighted Average Unit Price là khoảng `55,823481` trên mỗi đơn vị đã bán.

`gross margin percentage` có 1 giá trị phân biệt, min = max = `4.761904762`. Cột không thay đổi giữa các giao dịch. Nó có thể giữ lại để đối soát kỹ thuật hoặc mô tả quy tắc nguồn, nhưng không nên dùng làm KPI phân tích hay biểu đồ biến động.

## 12. Proposed Grain

**Grain đề xuất:** mỗi dòng đại diện cho một bản ghi giao dịch bán hàng duy nhất trong dữ liệu nguồn, được nhận diện bởi `Invoice ID`, phát sinh tại một chi nhánh, vào một thời điểm và gắn với một `Product line`. Dataset không có SKU hoặc chi tiết dòng hóa đơn nên không đủ cơ sở để xác định cấu trúc hóa đơn vật lý bên dưới.

- **Mức độ tin cậy cao đối với grain của file nguồn:** một dòng cho mỗi `Invoice ID`; 1.000 dòng có 1.000 ID duy nhất.
- **Giới hạn về nghiệp vụ:** không thể kết luận một hóa đơn ngoài thực tế chỉ chứa một sản phẩm hoặc một `Product line`.

## 13. Proposed Fact and Dimensions Assessment

### 13.1. Fact dự kiến

Đề xuất một `fact_sales` ở grain một bản ghi giao dịch nguồn duy nhất cho mỗi `Invoice ID`. Đây là grain kỹ thuật của file, không phải khẳng định về cấu trúc hóa đơn vật lý. `Invoice ID` là degenerate business key trong Fact, không phải một Dimension riêng. Các foreign key dự kiến liên kết tới Date, Branch/Location, Customer Segment, Product Line và Payment Method.

Giữ `transaction_time` trong Fact và dự kiến tạo thêm `transaction_hour`, `time_period`. Không tạo `dim_time` trong phạm vi hiện tại. Ranh giới Morning, Afternoon và Evening chỉ được chốt trong Business Requirements hoặc Transformation. Khi dashboard cần phân tích theo giờ, dùng `transaction_hour` hoặc `time_period`.

File nguồn không có cột `Total`. `Sales` là tổng giá trị bán hàng gồm thuế theo dữ liệu nguồn. Raw data giữ nguyên tên `Sales`; dbt dự kiến chuẩn hóa thành `sales_amount`; không tạo cột nguồn giả tên `Total`.

Không phải mọi cột số trong Fact đều được phép cộng:

| Trường | Phân loại | Phép tổng hợp phù hợp | Ghi chú |
|---|---|---|---|
| `Quantity` | Additive | `SUM` | Cộng được qua các bản ghi và Dimension |
| `Sales` | Additive | `SUM` | Tổng giá trị bán hàng gồm thuế; dự kiến đổi tên `sales_amount` trong dbt |
| `cogs` | Additive | `SUM` | Cộng được qua các bản ghi và Dimension |
| `Tax 5%` | Additive | `SUM` | Cộng được qua các bản ghi và Dimension |
| `gross income` | Additive về mặt kỹ thuật | `SUM`, chỉ để đối soát hoặc KPI phụ | Trùng hoàn toàn với `Tax 5%`; không trình bày hai chỉ số như KPI độc lập |
| `Unit price` | Non-additive | `SUM(cogs) / SUM(Quantity)` hoặc `AVERAGE` có nhãn riêng | Không dùng `SUM(Unit price)` |
| `Rating` | Non-additive | `AVERAGE` | Không cộng điểm đánh giá |
| `gross margin percentage` | Non-additive và cố định | Không dùng làm KPI biến động | Chỉ giữ để bảo toàn nguồn và đối soát |

### 13.2. Dimension dự kiến

| Dimension chính thức đề xuất | Thuộc tính nguồn chính | Lập luận |
|---|---|---|
| `dim_date` | Date | 89 ngày trong 3 tháng; hỗ trợ lịch, xu hướng và incremental load |
| `dim_branch_location` | Branch, City | Branch-City ánh xạ một-một; giữ nguyên nhãn nguồn trong cùng một Dimension |
| `dim_customer_segment` | Customer type, Gender | Phân tích phân khúc; không đại diện khách hàng cá nhân vì không có Customer ID |
| `dim_product_line` | Product line | Có 6 nhóm ngành hàng ổn định; không phải Product hoặc SKU |
| `dim_payment_method` | Payment | Có 3 phương thức, phù hợp làm slicer và quản trị nhãn |

Không tạo `dim_time`, Dimension Product/SKU, Customer cá nhân, Inventory hoặc Employee. Đây là đề xuất mô hình dựa trên profiling; chưa tạo bảng thật.

## 14. Proposed KPI Assessment

Mọi KPI dưới đây dùng một bản ghi giao dịch nguồn theo `Invoice ID` làm grain kỹ thuật. Tên “Invoice” trong KPI phản ánh trường nguồn, không chứng minh cấu trúc hóa đơn vật lý bên dưới.

### 14.1. KPI chính

| KPI | Tính được | Công thức sơ bộ | Cột nguồn | Rủi ro diễn giải | Dashboard |
|---|---|---|---|---|---|
| Total Sales | Có | `SUM(Sales)` | Sales | `Sales` là tổng gồm thuế; raw giữ tên `Sales`, dbt dự kiến dùng `sales_amount` | Nên dùng |
| Total Quantity | Có | `SUM(Quantity)` | Quantity | Tổng đơn vị ở grain bản ghi giao dịch; không có SKU | Nên dùng |
| Invoice Count | Có | `DISTINCTCOUNT(Invoice ID)` | Invoice ID | Là số bản ghi giao dịch nguồn duy nhất trong snapshot | Nên dùng |
| Average Order Value | Có | `SUM(Sales) / DISTINCTCOUNT(Invoice ID)` | Sales, Invoice ID | Giá trị trung bình trên mỗi `Invoice ID`; không suy ra cấu trúc hóa đơn vật lý | Nên dùng với định nghĩa rõ |
| Weighted Average Unit Price | Có | `SUM(cogs) / SUM(Quantity)` | cogs, Quantity | Đơn giá bình quân trên mỗi đơn vị đã bán; hợp lệ vì công thức COGS đạt 1.000/1.000 dòng | Nên dùng |
| Total COGS | Có | `SUM(cogs)` | cogs | Theo định nghĩa nguồn | Nên dùng |
| Average Rating | Có | `AVERAGE(Rating)` | Rating | Không có số người đánh giá hoặc trọng số | Nên dùng với chú thích |
| Average Daily Sales | Có | `SUM(Sales) / DISTINCTCOUNT(Date)` | Sales, Date | Trung bình trên các ngày có quan sát; giúp so sánh kỳ có số ngày khác nhau | Nên dùng |
| Monthly Sales Growth | Có về mặt tính toán | `(Sales tháng này - Sales tháng trước) / Sales tháng trước` | Sales, Date | Chỉ có 3 tháng và 2 kỳ tăng trưởng; không đủ suy luận mùa vụ hoặc xu hướng dài hạn | Dùng hạn chế, bắt buộc chú thích |

Chỉ số phụ có thể lưu để tham khảo: **Average Listed Unit Price per Transaction** = `AVERAGE(Unit price)`. Chỉ số này là trung bình không trọng số của mức giá niêm yết trên mỗi bản ghi và không được gọi cùng tên với Weighted Average Unit Price.

### 14.2. KPI phụ

| KPI | Tính được | Công thức sơ bộ | Cột nguồn | Cách sử dụng |
|---|---|---|---|---|
| Total Gross Income | Có | `SUM(gross income)` | gross income | Không ưu tiên trên Overview. Nếu dùng, ghi rõ: “Gross Income theo định nghĩa dữ liệu nguồn và bằng Tax 5% trong dataset này” |
| Average Gross Income per Invoice | Có | `SUM(gross income) / DISTINCTCOUNT(Invoice ID)` | gross income, Invoice ID | Không ưu tiên trên Overview; không gọi là lợi nhuận ròng |

Không trình bày Total Tax và Total Gross Income như hai KPI độc lập. Giữ `gross_income` trong Fact để bảo toàn dữ liệu nguồn và phục vụ đối soát. Không dùng `gross margin percentage` làm KPI hoặc biểu đồ biến động.

### 14.3. Breakdown theo Dimension

- Sales by Branch. City nằm trong cùng `dim_branch_location`; không đặt Sales by Branch và Sales by City như hai insight độc lập vì cơ cấu phân nhóm giống nhau.
- Sales by Product Line.
- Sales by Customer Type.
- Sales by Gender.
- Sales by Payment Method.
- Sales by Date/Month.
- Sales by Time Period nếu `time_period` được triển khai.

Các breakdown là cách phân rã Total Sales theo Dimension, không nhất thiết là KPI độc lập. Không suy luận tồn kho, Customer Lifetime Value, hành vi khách hàng riêng lẻ hoặc hiệu quả SKU vì dataset không hỗ trợ.

## 15. Incremental Load Recommendation

| Batch         | Khoảng ngày               | Số dòng | Vai trò đề xuất            |
| ------------- | ------------------------- | ------: | -------------------------- |
| Full Load     | 2019-01-01 đến 2019-01-31 |     352 | Nạp ban đầu                |
| Incremental 1 | 2019-02-01 đến 2019-02-28 |     303 | Lần nạp tăng thêm thứ nhất |
| Incremental 2 | 2019-03-01 đến 2019-03-30 |     345 | Lần nạp tăng thêm thứ hai  |

Khi triển khai sau này, watermark có thể dựa trên `Date` kết hợp `Time`; `Invoice ID` dùng để kiểm tra idempotency và tránh nạp trùng. Phương án trên chỉ là đề xuất, chưa tạo file batch và chưa triển khai pipeline.

Dữ liệu quan sát của tháng 03/2019 kết thúc vào ngày 30/03/2019. Không có đủ bằng chứng để kết luận dữ liệu ngày 31/03 bị thiếu hay ngày đó không phát sinh giao dịch. Phương án Incremental 2 vẫn chấp nhận toàn bộ dữ liệu tháng 03 hiện có đến ngày 30.

## 16. Data Limitations

- Chỉ có dữ liệu trong ba tháng của một năm, không đủ phân tích mùa vụ hoặc xu hướng dài hạn.
- Không có SKU, tên sản phẩm hoặc chi tiết line item.
- Không có Customer ID, nên không phân tích khách hàng riêng lẻ, mua lặp lại hoặc Customer Lifetime Value.
- Không có dữ liệu tồn kho, chi phí vận hành, giảm giá, hoàn trả hoặc trạng thái giao dịch.
- `gross income` trùng hoàn toàn với `Tax 5%`; cần giữ đúng tên nguồn và không diễn giải là lợi nhuận ròng.
- `gross margin percentage` cố định, không cung cấp biến thiên phân tích.
- `Branch` và `City` ánh xạ một-một nên hai breakdown có thể lặp lại cùng một cấu trúc phân nhóm.
- Dữ liệu quan sát tháng 03 kết thúc ở ngày 30. Không đủ bằng chứng để kết luận ngày 31 bị thiếu hay không phát sinh giao dịch.

## 17. Confirmed Modeling Decisions and Remaining Limitations

### 17.1. Confirmed Modeling Decisions

- Sử dụng cột nguồn `Sales`; giữ nguyên trong raw và dự kiến chuẩn hóa thành `sales_amount` trong dbt. Không tạo cột nguồn giả tên `Total`.
- Grain là một bản ghi giao dịch nguồn duy nhất theo `Invoice ID`, không phải khẳng định về cấu trúc hóa đơn vật lý.
- Weighted Average Unit Price dùng `SUM(cogs) / SUM(Quantity)` vì công thức COGS đã được xác minh 1.000/1.000 dòng.
- Không tạo Time Dimension. Giữ `transaction_time` trong Fact và dự kiến tạo `transaction_hour`, `time_period`; ranh giới time period được chốt ở Business Requirements hoặc Transformation.
- Gộp Branch và City trong `dim_branch_location`, giữ nguyên nhãn nguồn.
- Chấp nhận chia Full Load và Incremental Load theo ba tháng như mục 15.
- Không dùng `gross margin percentage` làm KPI.
- Không trình bày Tax và Gross Income như hai KPI độc lập.
- Không xóa hoặc chỉnh sửa 9 giao dịch bị IQR gắn cờ.

### 17.2. Remaining Limitations

- Chỉ có ba tháng dữ liệu và chỉ tạo được hai kỳ Monthly Sales Growth.
- Không có SKU hoặc chi tiết dòng hóa đơn.
- Không có Customer ID.
- Không có tồn kho, discount, return hoặc chi phí vận hành.
- Không đủ cơ sở phân tích mùa vụ hoặc xu hướng dài hạn.
- Branch và City có hạn chế ngữ nghĩa từ nguồn dù ánh xạ một-một ổn định.
- Không thể xác minh cấu trúc hóa đơn vật lý bên dưới.

## 18. Profiling Conclusion

Dataset có chất lượng cấu trúc tốt cho mini project: đầy đủ 1.000 dòng, `Invoice ID` duy nhất, ngày giờ hợp lệ, cột phân loại nhất quán và các công thức tiền đối soát được. Grain chính thức là một bản ghi giao dịch nguồn duy nhất cho mỗi `Invoice ID`; không đủ cơ sở kết luận cấu trúc hóa đơn vật lý hoặc dòng SKU bên dưới.

Đề xuất mô hình gồm `fact_sales` và năm Dimension: `dim_date`, `dim_branch_location`, `dim_customer_segment`, `dim_product_line`, `dim_payment_method`. `Invoice ID` là degenerate business key. Không tạo `dim_time`; giữ thời gian và các thuộc tính giờ/khung giờ dự kiến trong Fact.

File nguồn không có `Total`. Raw giữ nguyên `Sales`, dbt dự kiến chuẩn hóa thành `sales_amount`, và không tạo cột nguồn giả. Weighted Average Unit Price được chốt là `SUM(cogs) / SUM(Quantity)`. `gross income` được giữ để bảo toàn nguồn nhưng chỉ là KPI phụ vì bằng `Tax 5%`; `gross margin percentage` không dùng làm KPI. Các hạn chế chính là phạm vi ba tháng, thiếu SKU/Customer ID/dữ liệu tồn kho và không thể xác minh cấu trúc hóa đơn vật lý. Không có dữ liệu nguồn nào được chỉnh sửa trong quá trình rà soát.
