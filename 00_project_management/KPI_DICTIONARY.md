# KPI Dictionary - Supermarket Sales BI

## 1. Document Control

| Thuộc tính               | Giá trị                                                          |
| ------------------------ | ---------------------------------------------------------------- |
| Tên tài liệu             | KPI Dictionary - Supermarket Sales BI                            |
| Dataset                  | Supermarket Sales của Fares Ashraf                               |
| Phiên bản                | Baseline v1                                                      |
| Trạng thái               | Approved baseline for dimensional modeling                       |
| Ngày cập nhật            | 2026-10-16                                                       |
| Phạm vi dữ liệu đối soát | 1.000 bản ghi, từ 2019-01-01 đến 2019-03-30                      |
| Tài liệu liên quan       | `BUSINESS_REQUIREMENTS.md`, `DATA_PROFILE.md`, `DECISION_LOG.md` |

## 2. Quy ước chung

- Grain nguồn: mỗi dòng là một bản ghi giao dịch bán hàng duy nhất, nhận diện bởi `Invoice ID`.
- Fact dự kiến: `fact_sales`; tên cột vật lý sẽ được chốt ở MOD-01.
- Raw dùng `Sales`; tên chuẩn hóa dự kiến là `sales_amount`. Nguồn không có cột `Total`.
- KPI phản hồi filter context hợp lệ của Date, Branch/City, Customer type, Gender, Product line, Payment và time period, trừ khi định nghĩa riêng ghi khác.
- Các số tiền hiển thị không kèm ký hiệu tiền tệ vì dataset không xác nhận đơn vị tiền tệ.
- `Gross Income` bằng `Tax 5%` trên toàn bộ snapshot; hai trường không được trình bày như hai KPI độc lập.
- `gross margin percentage` cố định `4.761904762`, không dùng làm KPI.
- Additive measure có thể cộng theo các chiều; non-additive measure và ratio/average phải được tính lại trong filter context, không cộng các kết quả con.
- Dataset hiện tại không có measure semi-additive vì chỉ chứa dữ liệu giao dịch phát sinh, không chứa số dư hoặc snapshot như tồn kho cuối kỳ.
- Supporting và Diagnostic measure chỉ hỗ trợ phân tích/đối soát, không mặc nhiên là KPI trên trang Overview. Mục 8 quy định các chỉ số không được sử dụng.
- Giá trị baseline dưới đây được đọc và đối soát trực tiếp từ raw CSV với bộ lọc toàn bộ snapshot, khoảng ngày 2019-01-01 đến 2019-03-30; không phải số ước tính và CSV không bị chỉnh sửa.

## 3. Baseline đối soát

| Chỉ số                                    | Giá trị toàn bộ snapshot | Định dạng gợi ý |
| ----------------------------------------- | -----------------------: | --------------- |
| Total Sales                               |               322966.749 | `322,966.749`   |
| Total Quantity                            |                     5510 | `5,510`         |
| Invoice Count                             |                     1000 | `1,000`         |
| Average Order Value                       |               322.966749 | `322.97`        |
| Weighted Average Unit Price               |         55.8234809437387 | `55.82`         |
| Total COGS                                |                307587.38 | `307,587.38`    |
| Average Rating                            |                   6.9727 | `6.97`          |
| Average Daily Sales                       |          3628.8398764045 | `3,628.84`      |
| Total Gross Income                        |                15379.369 | `15,379.369`    |
| Average Gross Income per Invoice          |                15.379369 | `15.38`         |
| Average Listed Unit Price per Transaction |                 55.67213 | `55.67`         |

Monthly Sales baseline:

| Tháng   | Total Sales | Invoice Count | Monthly Sales Growth |
| ------- | ----------: | ------------: | -------------------: |
| 2019-01 |  116291.868 |           352 |        Không áp dụng |
| 2019-02 |   97219.374 |           303 |            -16.4005% |
| 2019-03 |  109455.507 |           345 |             12.5861% |

Tháng 03 chỉ có dữ liệu đến ngày 30. Monthly Sales Growth chỉ có hai kỳ so sánh và không được dùng để kết luận mùa vụ hay xu hướng dài hạn.

## 4. KPI chính

### KPI-01 - Total Sales

| Thuộc tính            | Định nghĩa                                                         |
| --------------------- | ------------------------------------------------------------------ |
| KPI ID                | KPI-01                                                             |
| Tên hiển thị          | Total Sales                                                        |
| Nhóm                  | Primary - Sales                                                    |
| Mục đích              | Đo tổng giá trị bán hàng gồm thuế trong filter context.            |
| Business Question     | BQ-01, BQ-02, BQ-03, BQ-04, BQ-05, BQ-06, BQ-07                    |
| Định nghĩa nghiệp vụ  | Tổng trường raw `Sales` của các bản ghi thuộc filter context.      |
| Công thức nghiệp vụ   | `Total Sales = SUM(Sales)`                                         |
| SQL/pseudo-SQL        | `SUM(fact_sales.sales_amount)`                                     |
| DAX/pseudo-DAX        | `Total Sales := SUM(fact_sales[sales_amount])`                     |
| Cột nguồn             | `Sales`                                                            |
| Tên chuẩn hóa dự kiến | `sales_amount`                                                     |
| Grain tính            | Bản ghi giao dịch nguồn; sau đó cộng theo context.                 |
| Aggregation           | Additive theo các Dimension baseline.                              |
| Filter context        | Phản hồi toàn bộ bộ lọc hợp lệ.                                    |
| Đơn vị                | Monetary units, không gắn ký hiệu tiền tệ.                         |
| Định dạng             | Số thập phân, 2-3 chữ số tùy visual.                               |
| Visual / trang        | KPI card, line chart, ranked bar; Overview và Detailed/Diagnostic. |
| AI Summary            | Được dùng; phải nêu kỳ và breakdown/filter liên quan.              |
| Quy tắc kiểm tra      | Đối soát với `Total COGS + Total Tax` trong cùng context.          |
| Baseline kiểm tra     | `322966.749`.                                                      |
| Giới hạn diễn giải    | Không phải doanh thu thuần; không suy ra lợi nhuận ròng.           |

### KPI-02 - Total Quantity

| Thuộc tính                | Định nghĩa                                                          |
| ------------------------- | ------------------------------------------------------------------- |
| KPI ID                    | KPI-02                                                              |
| Tên hiển thị              | Total Quantity                                                      |
| Nhóm                      | Primary - Volume                                                    |
| Mục đích                  | Đo tổng số lượng đơn vị được ghi nhận.                              |
| Business Question         | BQ-01, BQ-03, BQ-04                                                 |
| Định nghĩa nghiệp vụ      | Tổng `Quantity` của các bản ghi thuộc filter context.               |
| Công thức nghiệp vụ       | `Total Quantity = SUM(Quantity)`                                    |
| SQL/pseudo-SQL            | `SUM(fact_sales.quantity)`                                          |
| DAX/pseudo-DAX            | `Total Quantity := SUM(fact_sales[quantity])`                       |
| Cột nguồn / tên chuẩn hóa | `Quantity` / `quantity`                                             |
| Grain tính                | Bản ghi giao dịch nguồn; sau đó cộng theo context.                  |
| Aggregation               | Additive.                                                           |
| Filter context            | Phản hồi toàn bộ bộ lọc hợp lệ.                                     |
| Đơn vị / định dạng        | Units; số nguyên có phân tách hàng nghìn.                           |
| Visual / trang            | KPI card, bar chart; Overview và Detailed/Diagnostic.               |
| AI Summary                | Được dùng khi ghi rõ nhóm so sánh.                                  |
| Quy tắc kiểm tra          | Tổng Quantity phải bằng tổng trực tiếp từ các dòng sau cùng filter. |
| Baseline kiểm tra         | `5510`.                                                             |
| Giới hạn diễn giải        | Không có SKU nên không phân tích số lượng theo sản phẩm chi tiết.   |

### KPI-03 - Invoice Count

| Thuộc tính                | Định nghĩa                                                             |
| ------------------------- | ---------------------------------------------------------------------- |
| KPI ID                    | KPI-03                                                                 |
| Tên hiển thị              | Invoice Count                                                          |
| Nhóm                      | Primary - Transaction volume                                           |
| Mục đích                  | Đếm số mã giao dịch duy nhất trong filter context.                     |
| Business Question         | BQ-01, BQ-03, BQ-05, BQ-06, BQ-07, BQ-08                               |
| Định nghĩa nghiệp vụ      | Số `Invoice ID` phân biệt; `Invoice ID` là degenerate business key.    |
| Công thức nghiệp vụ       | `Invoice Count = COUNT(DISTINCT Invoice ID)`                           |
| SQL/pseudo-SQL            | `COUNT(DISTINCT fact_sales.invoice_id)`                                |
| DAX/pseudo-DAX            | `Invoice Count := DISTINCTCOUNT(fact_sales[invoice_id])`               |
| Cột nguồn / tên chuẩn hóa | `Invoice ID` / `invoice_id`                                            |
| Grain tính                | Mã giao dịch duy nhất trong context.                                   |
| Aggregation               | Non-additive qua các nhóm chồng lấn; luôn tính lại distinct count.     |
| Filter context            | Phản hồi toàn bộ bộ lọc hợp lệ.                                        |
| Đơn vị / định dạng        | Invoices; số nguyên.                                                   |
| Visual / trang            | KPI card, bar/column chart; Overview và Detailed/Diagnostic.           |
| AI Summary                | Được dùng; không gọi là số hóa đơn vật lý đã xác minh.                 |
| Quy tắc kiểm tra          | Không vượt số dòng; snapshot hiện tại phải bằng 1.000.                 |
| Baseline kiểm tra         | `1000`, bằng số dòng của snapshot.                                     |
| Giới hạn diễn giải        | Dataset không đủ cơ sở xác minh cấu trúc hóa đơn vật lý hoặc dòng SKU. |

### KPI-04 - Average Order Value

| Thuộc tính            | Định nghĩa                                                                       |
| --------------------- | -------------------------------------------------------------------------------- |
| KPI ID                | KPI-04                                                                           |
| Tên hiển thị          | Average Order Value                                                              |
| Nhóm                  | Primary - Sales efficiency                                                       |
| Mục đích              | Đo giá trị Sales trung bình trên một `Invoice ID` duy nhất.                      |
| Business Question     | BQ-01, BQ-05, BQ-06                                                              |
| Định nghĩa nghiệp vụ  | Total Sales chia Invoice Count trong cùng filter context.                        |
| Công thức nghiệp vụ   | `Average Order Value = Total Sales / Invoice Count`                              |
| SQL/pseudo-SQL        | `SUM(sales_amount) / NULLIF(COUNT(DISTINCT invoice_id), 0)`                      |
| DAX/pseudo-DAX        | `Average Order Value := DIVIDE([Total Sales], [Invoice Count])`                  |
| Cột nguồn             | `Sales`, `Invoice ID`                                                            |
| Tên chuẩn hóa dự kiến | `sales_amount`, `invoice_id`                                                     |
| Grain tính            | Context tổng hợp; không cộng các giá trị AOV con.                                |
| Aggregation           | Ratio, non-additive.                                                             |
| Filter context        | Tử số và mẫu số dùng cùng context.                                               |
| Đơn vị / định dạng    | Monetary units per invoice; 2 chữ số thập phân, không ký hiệu tiền tệ.           |
| Visual / trang        | KPI card, matrix hoặc bar; Overview và Detailed/Diagnostic.                      |
| AI Summary            | Được dùng nếu kèm Invoice Count để tạo ngữ cảnh.                                 |
| Quy tắc kiểm tra      | Phải bằng Total Sales chia Invoice Count; trả blank nếu mẫu số bằng 0.           |
| Baseline kiểm tra     | `322.966749`.                                                                    |
| Giới hạn diễn giải    | “Order” là nhãn KPI cho `Invoice ID`, không khẳng định cấu trúc đơn hàng vật lý. |

### KPI-05 - Weighted Average Unit Price

| Thuộc tính            | Định nghĩa                                                                    |
| --------------------- | ----------------------------------------------------------------------------- |
| KPI ID                | KPI-05                                                                        |
| Tên hiển thị          | Weighted Average Unit Price                                                   |
| Nhóm                  | Primary - Price diagnostic                                                    |
| Mục đích              | Đo đơn giá bình quân có trọng số theo Quantity.                               |
| Business Question     | BQ-04                                                                         |
| Định nghĩa nghiệp vụ  | Tổng COGS chia Total Quantity trong cùng filter context.                      |
| Công thức nghiệp vụ   | `Weighted Average Unit Price = SUM(cogs) / SUM(Quantity)`                     |
| SQL/pseudo-SQL        | `SUM(fact_sales.cogs_amount) / NULLIF(SUM(fact_sales.quantity), 0)`           |
| DAX/pseudo-DAX        | `Weighted Average Unit Price := DIVIDE([Total COGS], [Total Quantity])`       |
| Cột nguồn             | `cogs`, `Quantity`; quan hệ dòng đã kiểm tra: `cogs = Unit price × Quantity`. |
| Tên chuẩn hóa dự kiến | `cogs_amount`, `quantity`                                                     |
| Grain tính            | Context tổng hợp; trọng số là Quantity.                                       |
| Aggregation           | Ratio, non-additive. Không sử dụng `SUM(Unit price)`.                         |
| Filter context        | Tử số và mẫu số dùng cùng context.                                            |
| Đơn vị / định dạng    | Monetary units per unit; 2 chữ số thập phân, không ký hiệu tiền tệ.           |
| Visual / trang        | Tooltip, matrix hoặc bar; Detailed/Diagnostic.                                |
| AI Summary            | Được dùng như chỉ số chẩn đoán khi nêu rõ là bình quân có trọng số.           |
| Quy tắc kiểm tra      | Phải bằng Total COGS chia Total Quantity; trả blank nếu mẫu số bằng 0.        |
| Baseline kiểm tra     | `55.8234809437387`.                                                           |
| Giới hạn diễn giải    | Không thay thế Average Order Value; không cộng `Unit price`.                  |

### KPI-06 - Total COGS

| Thuộc tính                | Định nghĩa                                                                                       |
| ------------------------- | ------------------------------------------------------------------------------------------------ |
| KPI ID                    | KPI-06                                                                                           |
| Tên hiển thị              | Total COGS                                                                                       |
| Nhóm                      | Primary - Cost baseline                                                                          |
| Mục đích                  | Đo tổng giá vốn được cung cấp trong dataset.                                                     |
| Business Question         | BQ-04                                                                                            |
| Định nghĩa nghiệp vụ      | Tổng raw `cogs` của các bản ghi thuộc filter context.                                            |
| Công thức nghiệp vụ       | `Total COGS = SUM(cogs)`                                                                         |
| SQL/pseudo-SQL            | `SUM(fact_sales.cogs_amount)`                                                                    |
| DAX/pseudo-DAX            | `Total COGS := SUM(fact_sales[cogs_amount])`                                                     |
| Cột nguồn / tên chuẩn hóa | `cogs` / `cogs_amount`                                                                           |
| Grain tính                | Bản ghi giao dịch nguồn; sau đó cộng theo context.                                               |
| Aggregation               | Additive.                                                                                        |
| Filter context            | Phản hồi toàn bộ bộ lọc hợp lệ.                                                                  |
| Đơn vị / định dạng        | Monetary units; 2 chữ số thập phân, không ký hiệu tiền tệ.                                       |
| Visual / trang            | Tooltip, matrix hoặc bar; Detailed/Diagnostic.                                                   |
| AI Summary                | Được dùng khi có so sánh rõ ràng và không gọi là tổng chi phí vận hành.                          |
| Quy tắc kiểm tra          | Đối soát tổng trực tiếp từ `cogs`; cùng Total Tax phải khớp Total Sales.                         |
| Baseline kiểm tra         | `307587.38`.                                                                                     |
| Giới hạn diễn giải        | Chỉ là COGS trong nguồn; không bao gồm chi phí vận hành và không cho phép suy ra lợi nhuận ròng. |

### KPI-07 - Average Rating

| Thuộc tính                | Định nghĩa                                                                           |
| ------------------------- | ------------------------------------------------------------------------------------ |
| KPI ID                    | KPI-07                                                                               |
| Tên hiển thị              | Average Rating                                                                       |
| Nhóm                      | Primary - Experience signal                                                          |
| Mục đích                  | Đo Rating trung bình của các bản ghi trong filter context.                           |
| Business Question         | BQ-08                                                                                |
| Định nghĩa nghiệp vụ      | Trung bình số học của `Rating`.                                                      |
| Công thức nghiệp vụ       | `Average Rating = AVG(Rating)`                                                       |
| SQL/pseudo-SQL            | `AVG(CAST(fact_sales.rating AS decimal))`                                            |
| DAX/pseudo-DAX            | `Average Rating := AVERAGE(fact_sales[rating])`                                      |
| Cột nguồn / tên chuẩn hóa | `Rating` / `rating`                                                                  |
| Grain tính                | Trung bình trên bản ghi giao dịch nguồn trong context.                               |
| Aggregation               | Average, non-additive.                                                               |
| Filter context            | Phản hồi toàn bộ bộ lọc hợp lệ.                                                      |
| Đơn vị / định dạng        | Rating points; 2 chữ số thập phân.                                                   |
| Visual / trang            | KPI card, heatmap hoặc matrix; Overview và Detailed/Diagnostic.                      |
| AI Summary                | Được dùng khi nêu cả nhóm và số bản ghi liên quan.                                   |
| Quy tắc kiểm tra          | Giá trị phải nằm trong miền Rating quan sát `4.0-10.0`; không dùng phép cộng Rating. |
| Baseline kiểm tra         | `6.9727`; miền dữ liệu quan sát `4.0-10.0`.                                          |
| Giới hạn diễn giải        | Không chứng minh nguyên nhân hay mức hài lòng của một khách hàng cụ thể.             |

### KPI-08 - Average Daily Sales

| Thuộc tính            | Định nghĩa                                                                                                                                                          |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| KPI ID                | KPI-08                                                                                                                                                              |
| Tên hiển thị          | Average Daily Sales                                                                                                                                                 |
| Nhóm                  | Primary - Time trend                                                                                                                                                |
| Mục đích              | Chuẩn hóa Sales theo số ngày có dữ liệu trong filter context.                                                                                                       |
| Business Question     | BQ-02                                                                                                                                                               |
| Định nghĩa nghiệp vụ  | Total Sales chia số ngày giao dịch phân biệt trong context.                                                                                                         |
| Công thức nghiệp vụ   | `Average Daily Sales = Total Sales / DISTINCTCOUNT(Date)`                                                                                                           |
| SQL/pseudo-SQL        | `SUM(sales_amount) / NULLIF(COUNT(DISTINCT transaction_date), 0)`                                                                                                   |
| DAX/pseudo-DAX        | `Average Daily Sales := DIVIDE([Total Sales], DISTINCTCOUNT(fact_sales[transaction_date]))`                                                                                 |
| Cột nguồn             | `Sales`, `Date`                                                                                                                                                     |
| Tên chuẩn hóa dự kiến | `sales_amount`, `transaction_date`                                                                                                                                  |
| Grain tính            | Context tổng hợp theo số ngày có giao dịch.                                                                                                                         |
| Aggregation           | Ratio, non-additive.                                                                                                                                                |
| Filter context        | Tử số và mẫu số dùng cùng context; không tự thêm ngày không có trong phạm vi nguồn.                                                                                 |
| Đơn vị / định dạng    | Monetary units per active date; 2 chữ số thập phân, không ký hiệu tiền tệ.                                                                                          |
| Visual / trang        | KPI card, line chart; Overview.                                                                                                                                     |
| AI Summary            | Được dùng khi nêu rõ khoảng ngày.                                                                                                                                   |
| Quy tắc kiểm tra      | Phải bằng Total Sales chia số Date phân biệt có giao dịch; trả blank nếu không có ngày.                                                                             |
| Baseline kiểm tra     | `3628.8398764045`, dựa trên 89 ngày phân biệt.                                                                                                                      |
| Giới hạn diễn giải    | Không phải bình quân trên một quý chuẩn; tháng 03 kết thúc ngày 30.                                                                                                 |

### KPI-09 - Monthly Sales Growth

| Thuộc tính            | Định nghĩa                                                                                                                   |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| KPI ID                | KPI-09                                                                                                                       |
| Tên hiển thị          | Monthly Sales Growth                                                                                                         |
| Nhóm                  | Primary - Time trend                                                                                                         |
| Mục đích              | Đo tỷ lệ thay đổi Total Sales so với tháng liền trước.                                                                       |
| Business Question     | BQ-02                                                                                                                        |
| Định nghĩa nghiệp vụ  | Chênh lệch Sales tháng hiện tại và tháng trước, chia Sales tháng trước.                                                      |
| Công thức nghiệp vụ   | `Monthly Sales Growth = (Current Month Sales - Previous Month Sales) / Previous Month Sales`                                 |
| SQL/pseudo-SQL        | `(monthly_sales - LAG(monthly_sales) OVER (ORDER BY year_month)) / NULLIF(LAG(monthly_sales) OVER (ORDER BY year_month), 0)` |
| DAX/pseudo-DAX        | `Monthly Sales Growth := DIVIDE([Total Sales] - [Previous Month Sales], [Previous Month Sales])`                             |
| Cột nguồn             | `Sales`, `Date`                                                                                                              |
| Tên chuẩn hóa dự kiến | `sales_amount`, `transaction_date`; thuộc tính tháng từ `dim_date`.                                                          |
| Grain tính            | Tháng lịch trong filter context.                                                                                             |
| Aggregation           | Ratio, non-additive; tính lại theo từng tháng, không cộng các tỷ lệ.                                                         |
| Filter context        | Giữ context nhóm phân tích; dịch context thời gian về tháng liền trước.                                                      |
| Đơn vị / định dạng    | Percentage; 2 chữ số thập phân.                                                                                              |
| Visual / trang        | Line/column chart và tooltip; Overview.                                                                                      |
| AI Summary            | Được dùng nhưng bắt buộc kèm cảnh báo chỉ có hai kỳ so sánh và tháng 03 đến ngày 30.                                         |
| Quy tắc kiểm tra      | Tháng đầu trả blank; các tháng sau đối soát với Sales tháng trước và không chia cho 0.                                       |
| Baseline kiểm tra     | 2019-02: `-16.4005%`; 2019-03: `12.5861%`; 2019-01: blank/không áp dụng.                                                     |
| Giới hạn diễn giải    | Không kết luận mùa vụ, xu hướng dài hạn hay nguyên nhân; so sánh tháng 03 chịu giới hạn kỳ dữ liệu.                          |

## 5. KPI hỗ trợ

### SUP-01 - Total Gross Income

| Thuộc tính                | Định nghĩa                                                                           |
| ------------------------- | ------------------------------------------------------------------------------------ |
| KPI ID                    | SUP-01                                                                               |
| Tên hiển thị              | Total Gross Income                                                                   |
| Nhóm                      | Supporting - Source reconciliation measure                                           |
| Mục đích                  | Cung cấp giá trị Gross Income khi phân tích chi tiết hoặc đối soát.                  |
| Business Question         | Hỗ trợ BQ-01 và BQ-04; không ưu tiên trên Overview.                                  |
| Định nghĩa / công thức    | `Total Gross Income = SUM(Gross Income)`; bằng `SUM(Tax 5%)` trên snapshot.          |
| SQL / DAX                 | `SUM(fact_sales.gross_income_amount)` / `SUM(fact_sales[gross_income_amount])`       |
| Cột nguồn / tên chuẩn hóa | `gross income` / `gross_income_amount`                                               |
| Grain / aggregation       | Bản ghi giao dịch nguồn; additive.                                                   |
| Filter context            | Phản hồi toàn bộ bộ lọc hợp lệ.                                                      |
| Đơn vị / định dạng        | Monetary units; 2-3 chữ số thập phân, không ký hiệu tiền tệ.                         |
| Visual / trang            | Tooltip hoặc bảng đối soát; Detailed/Diagnostic.                                     |
| AI Summary                | Chỉ dùng khi được yêu cầu và phải gọi đúng là Gross Income trong nguồn.              |
| Quy tắc kiểm tra          | Phải bằng tổng `Tax 5%` trong cùng context.                                          |
| Baseline kiểm tra         | `15379.369`; phải bằng Total Tax.                                                    |
| Giới hạn diễn giải        | Không phải lợi nhuận ròng; không trình bày đồng thời với Tax 5% như hai KPI độc lập. |

### SUP-02 - Average Gross Income per Invoice

| Thuộc tính             | Định nghĩa                                                                                                           |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------- |
| KPI ID                 | SUP-02                                                                                                               |
| Tên hiển thị           | Average Gross Income per Invoice                                                                                     |
| Nhóm                   | Supporting - Source reconciliation measure                                                                           |
| Mục đích               | Đo Gross Income trung bình trên một `Invoice ID`.                                                                    |
| Business Question      | Hỗ trợ BQ-01 và BQ-04; không ưu tiên trên Overview.                                                                  |
| Định nghĩa / công thức | `Average Gross Income per Invoice = Total Gross Income / Invoice Count`                                              |
| SQL / DAX              | `SUM(gross_income_amount) / NULLIF(COUNT(DISTINCT invoice_id), 0)` / `DIVIDE([Total Gross Income], [Invoice Count])` |
| Cột nguồn              | `gross income`, `Invoice ID`                                                                                         |
| Tên chuẩn hóa dự kiến  | `gross_income_amount`, `invoice_id`                                                                                  |
| Grain / aggregation    | Context tổng hợp; ratio, non-additive.                                                                               |
| Filter context         | Tử số và mẫu số dùng cùng context.                                                                                   |
| Đơn vị / định dạng     | Monetary units per invoice; 2 chữ số thập phân, không ký hiệu tiền tệ.                                               |
| Visual / trang         | Tooltip hoặc bảng đối soát; Detailed/Diagnostic.                                                                     |
| AI Summary             | Chỉ dùng khi được yêu cầu và có Invoice Count làm ngữ cảnh.                                                          |
| Quy tắc kiểm tra       | Phải bằng Total Gross Income chia Invoice Count; trả blank nếu mẫu số bằng 0.                                        |
| Baseline kiểm tra      | `15.379369`.                                                                                                         |
| Giới hạn diễn giải     | Không phải lợi nhuận ròng trên đơn hàng; `Invoice ID` không xác minh hóa đơn vật lý.                                 |

## 6. Chỉ số chẩn đoán, không phải KPI chính

### DIA-01 - Average Listed Unit Price per Transaction

| Thuộc tính                | Định nghĩa                                                                                        |
| ------------------------- | ------------------------------------------------------------------------------------------------- |
| KPI ID                    | DIA-01                                                                                            |
| Tên hiển thị              | Average Listed Unit Price per Transaction                                                         |
| Nhóm                      | Diagnostic measure                                                                                |
| Mục đích                  | Mô tả trung bình số học của giá niêm yết trên các bản ghi, dùng để đối chiếu với KPI có trọng số. |
| Business Question         | Hỗ trợ chẩn đoán BQ-04.                                                                           |
| Định nghĩa / công thức    | `Average Listed Unit Price per Transaction = AVG(Unit price)`                                     |
| SQL / DAX                 | `AVG(unit_price)` / `AVERAGE(fact_sales[unit_price])`                                             |
| Cột nguồn / tên chuẩn hóa | `Unit price` / `unit_price`                                                                       |
| Grain / aggregation       | Trung bình trên bản ghi; non-additive.                                                            |
| Filter context            | Phản hồi toàn bộ bộ lọc hợp lệ.                                                                   |
| Đơn vị / định dạng        | Monetary units per listed unit; 2 chữ số thập phân, không ký hiệu tiền tệ.                        |
| Visual / trang            | Tooltip hoặc bảng kiểm tra; Detailed/Diagnostic.                                                  |
| AI Summary                | Không dùng mặc định; chỉ dùng khi phân biệt rõ với Weighted Average Unit Price.                   |
| Quy tắc kiểm tra          | Phải bằng trung bình số học trực tiếp của `Unit price` trong cùng context.                        |
| Baseline kiểm tra         | `55.67213`.                                                                                       |
| Giới hạn diễn giải        | Không có trọng số Quantity và không thay thế KPI-05. Không sử dụng `SUM(Unit price)`.             |

## 7. Quy tắc kiểm tra KPI

| ID     | Quy tắc                                                                                           | Kết quả baseline mong đợi              |
| ------ | ------------------------------------------------------------------------------------------------- | -------------------------------------- |
| VAL-01 | `Total Sales = Total COGS + Total Tax` trong cùng context, trong giới hạn làm tròn nguồn.         | `322966.749 = 307587.38 + 15379.369`   |
| VAL-02 | `Total Tax = Total Gross Income`.                                                                 | Cùng bằng `15379.369`.                 |
| VAL-03 | `Weighted Average Unit Price = Total COGS / Total Quantity`.                                      | `55.8234809437387`.                    |
| VAL-04 | `Invoice Count <= số dòng`; với snapshot hiện tại hai giá trị bằng nhau.                          | `1000 = 1000`.                         |
| VAL-05 | Average Order Value phải dùng distinct `Invoice ID` và cùng filter context với Total Sales.       | `322.966749`.                          |
| VAL-06 | Average Rating phải nằm trong miền Rating hợp lệ của nguồn.                                       | `6.9727`, nằm trong `4.0-10.0`.        |
| VAL-07 | Average Daily Sales dùng số Date phân biệt có giao dịch.                                          | `322966.749 / 89 = 3628.8398764045`.   |
| VAL-08 | Tháng đầu tiên không có Monthly Sales Growth; mẫu số bằng 0 trả blank, không trả vô cực.          | 2019-01 blank.                         |
| VAL-09 | Tử số và mẫu số của mọi ratio phải chịu cùng filter context, trừ phép dịch thời gian được nêu rõ. | Không có context lệch.                 |
| VAL-10 | Không KPI nào gắn ký hiệu tiền tệ cụ thể trước khi đơn vị tiền tệ được xác nhận.                  | Chỉ hiển thị số hoặc “monetary units”. |

## 8. Không sử dụng như KPI

- Không sử dụng `SUM(Unit price)`: phép cộng giá niêm yết không có ý nghĩa nghiệp vụ. KPI có trọng số phải dùng `SUM(cogs) / SUM(Quantity)`.
- Không sử dụng `gross margin percentage` làm KPI vì trường này cố định `4.761904762` trong snapshot.
- Không hiển thị `Tax 5%` và `Gross Income` như hai KPI độc lập vì chúng bằng nhau.
- Không gọi Gross Income là lợi nhuận ròng.
- Không dùng trường giả định `Total`; raw field chính xác là `Sales`.
- Không dùng Sales by Branch và Sales by City như hai insight độc lập vì Branch-City ánh xạ một-một.
- Không tạo KPI inventory, return, discount, customer retention hoặc Customer Lifetime Value vì nguồn không có dữ liệu cần thiết.
- Không tự quy định đơn vị hoặc ký hiệu tiền tệ.

## 9. Acceptance Criteria

- Có đúng 9 KPI chính, 2 KPI hỗ trợ và 1 chỉ số chẩn đoán được gắn nhãn rõ ràng.
- Mỗi KPI chính liên kết với ít nhất một Business Question.
- Mỗi định nghĩa có công thức nghiệp vụ, pseudo-SQL, pseudo-DAX, grain, aggregation, filter context, đơn vị, định dạng, visual, trang, điều kiện dùng cho AI, baseline và giới hạn diễn giải.
- Weighted Average Unit Price dùng `SUM(cogs) / SUM(Quantity)`.
- Monthly Sales Growth có cảnh báo về chỉ hai kỳ so sánh và tháng 03 kết thúc ngày 30.
- Không có ký hiệu tiền tệ cụ thể, không có KPI lợi nhuận ròng và không tạo cột nguồn `Total`.
- Các quy tắc đối soát khớp `DATA_PROFILE.md` mà không sửa raw data.
