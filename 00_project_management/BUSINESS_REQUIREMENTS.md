# Business Requirements - Supermarket Sales BI

## 1. Document Control

| Thuộc tính | Giá trị |
|---|---|
| Tên tài liệu | Business Requirements - Supermarket Sales BI |
| Dataset | Supermarket Sales của Fares Ashraf |
| Phiên bản | Baseline v1 |
| Trạng thái | Approved baseline for dimensional modeling |
| Ngày cập nhật | 2026-10-16 |
| Người xác nhận | Trưởng nhóm |
| Tài liệu đầu vào | `PROJECT_CONTEXT.md`, `PROJECT_SCOPE.md`, `DATASET_SELECTION.md`, `DATA_PROFILE.md`, `DECISION_LOG.md`, `TASK_BOARD.md`, `NAMING_CONVENTIONS.md` |

## 2. Business Context

Hệ thống BI được xây dựng để phân tích hoạt động bán hàng của một chuỗi siêu thị trên snapshot 1.000 bản ghi giao dịch từ 2019-01-01 đến 2019-03-30. Dữ liệu trực tiếp cung cấp thời gian giao dịch, Branch, City, Customer type, Gender, Product line, Payment, Quantity, Unit price, Sales, COGS, Tax, Gross Income và Rating.

Bối cảnh quản lý do nhóm xây dựng là hỗ trợ Sales/Operations Manager theo dõi quy mô và biến động bán hàng, so sánh các nhóm đóng góp và nhận diện khu vực cần xem xét sâu hơn. Đây là tình huống phân tích dựa trên dataset; không khẳng định dữ liệu đại diện cho một doanh nghiệp có thật nếu nguồn không xác nhận.

Hệ thống BI có vai trò chuẩn hóa định nghĩa KPI, cung cấp hai lớp phân tích Overview và Detailed/Diagnostic, và tạo nền tảng cho AI Summary chỉ sử dụng số liệu đã tính. Dataset không cho phép kết luận nguyên nhân, cấu trúc hóa đơn vật lý, hiệu quả SKU, hành vi khách hàng cá nhân, tồn kho, hoàn trả, giảm giá, chi phí vận hành, lợi nhuận ròng, mùa vụ hoặc xu hướng dài hạn.

## 3. Business Process

| Thuộc tính | Mô tả |
|---|---|
| Tên quy trình | Phân tích giao dịch bán hàng tại chuỗi siêu thị |
| Sự kiện nghiệp vụ | Một bản ghi giao dịch bán hàng được ghi nhận trong dữ liệu nguồn |
| Grain | Mỗi dòng đại diện cho một bản ghi giao dịch bán hàng duy nhất trong dữ liệu nguồn, được nhận diện bởi `Invoice ID`, phát sinh tại một chi nhánh, vào một thời điểm và gắn với một `Product line` |
| Điểm bắt đầu | Giao dịch bán hàng được ghi nhận |
| Điểm kết thúc | Bản ghi có mã giao dịch, chi nhánh, thời gian, phân khúc khách hàng, ngành hàng, phương thức thanh toán, số lượng, Sales, COGS, Tax và Rating |
| Đối tượng phân tích | Date, Branch/City, Customer type, Gender, Product line, Payment, transaction hour/time period |
| Measures | Quantity, Sales, COGS, Tax 5%, Gross Income, Unit price và Rating với phép tổng hợp phù hợp |
| Ngoài phạm vi | Tồn kho, return, discount, nhập hàng, chi phí vận hành, khách hàng cá nhân, SKU, lợi nhuận ròng và dự báo dài hạn |

Dataset không có SKU hoặc chi tiết dòng hóa đơn, nên grain trên không khẳng định một `Invoice ID` tương ứng toàn bộ hóa đơn vật lý hay một dòng SKU.

## 4. Business Users

| Vai trò | Mức độ ưu tiên | Mục tiêu | Quyết định cần hỗ trợ | Thông tin cần xem | Trang dashboard dự kiến |
|---|---|---|---|---|---|
| Sales/Operations Manager | Chính | Theo dõi quy mô, xu hướng và nhóm đóng góp | Ưu tiên khu vực cần theo dõi; chọn chiều phân tích cần xem sâu | KPI tổng quan, xu hướng tháng/ngày, Branch, Product line, Customer segment, Payment | Overview; Detailed/Diagnostic |
| Branch Manager | Phụ | Theo dõi kết quả và cơ cấu bán hàng theo chi nhánh | So sánh chi nhánh với các chi nhánh khác và nhận diện nhóm đóng góp | Sales, Quantity, Invoice Count, AOV, Rating, Product line, Customer type, time period | Detailed/Diagnostic |
| BI Analyst | Phụ | Kiểm tra KPI và chuẩn bị insight có thể đối soát | Xác minh số liệu, điều tra breakdown và chuẩn bị nội dung AI Summary | Định nghĩa KPI, filter context, dữ liệu chi tiết và cảnh báo phạm vi | Overview; Detailed/Diagnostic |

## 5. Business Objectives

| ID | Mục tiêu | KPI liên quan |
|---|---|---|
| BO-01 | Theo dõi quy mô bán hàng trong phạm vi dữ liệu | Total Sales, Total Quantity, Invoice Count, Average Order Value |
| BO-02 | Theo dõi biến động bán hàng theo ngày và tháng | Total Sales, Average Daily Sales, Monthly Sales Growth |
| BO-03 | So sánh đóng góp giữa các chi nhánh | Total Sales, Total Quantity, Invoice Count |
| BO-04 | Xác định Product line đóng góp cao hoặc thấp | Total Sales, Total Quantity, Weighted Average Unit Price, Total COGS |
| BO-05 | Phân tích cơ cấu khách hàng và phương thức thanh toán | Total Sales, Average Order Value, Invoice Count |
| BO-06 | Nhận diện khung giờ giao dịch đáng chú ý và theo dõi Rating | Total Sales, Invoice Count, Average Rating |
| BO-07 | Hỗ trợ AI Summary có thể đối chiếu với KPI và breakdown trên dashboard | Chín KPI chính; KPI hỗ trợ chỉ dùng khi có nhãn và ngữ cảnh phù hợp |

Mỗi mục tiêu chỉ dùng các trường có trong dataset và không yêu cầu suy luận nhân quả.

## 6. Business Questions

| ID | Câu hỏi | Người dùng quan tâm | KPI/measures liên quan | Dimension/bộ lọc | Dữ liệu nguồn | Visual dự kiến | Trang | Giới hạn diễn giải |
|---|---|---|---|---|---|---|---|---|
| BQ-01 | Tổng Sales, Quantity, số Invoice và Average Order Value trong kỳ là bao nhiêu? | Sales/Operations Manager, BI Analyst | Total Sales, Total Quantity, Invoice Count, Average Order Value | Date và các slicer chung | Sales, Quantity, Invoice ID, Date | KPI cards | Overview | Invoice Count là số `Invoice ID` phân biệt; không suy ra cấu trúc hóa đơn vật lý |
| BQ-02 | Sales biến động theo ngày và tháng như thế nào? | Sales/Operations Manager, BI Analyst | Total Sales, Average Daily Sales, Monthly Sales Growth | Date, Branch, Product line | Sales, Date | Line chart theo ngày/tháng | Overview | Chỉ có 3 tháng, 2 kỳ tăng trưởng; tháng 03 đến ngày 30; không suy luận mùa vụ |
| BQ-03 | Chi nhánh nào đóng góp nhiều hoặc ít nhất vào Total Sales, Quantity và Invoice Count? | Sales/Operations Manager, Branch Manager | Total Sales, Total Quantity, Invoice Count | Branch/City, Date | Branch, City, Sales, Quantity, Invoice ID | Ranked bar chart | Overview hoặc Detailed/Diagnostic | Branch và City ánh xạ một-một; không dùng hai breakdown như insight độc lập |
| BQ-04 | Product Line nào đóng góp nhiều hoặc ít nhất vào Sales và Quantity? | Sales/Operations Manager, Branch Manager, BI Analyst | Total Sales, Total Quantity; diagnostic: Weighted Average Unit Price, Total COGS | Product line, Branch, Date | Product line, Sales, Quantity, cogs | Ranked bar chart và tooltip | Detailed/Diagnostic | Product line không phải Product hoặc SKU; không kết luận hiệu quả sản phẩm chi tiết |
| BQ-05 | Cơ cấu Sales và Average Order Value khác nhau như thế nào giữa Customer Type và Gender? | Sales/Operations Manager, BI Analyst | Total Sales, Average Order Value, Invoice Count | Customer type, Gender, Date, Branch | Customer type, Gender, Sales, Invoice ID | Matrix hoặc clustered bar chart | Detailed/Diagnostic | Không có Customer ID; không phân tích cá nhân, retention hoặc CLV |
| BQ-06 | Các Payment Method được sử dụng với tỷ trọng và giá trị giao dịch như thế nào? | Sales/Operations Manager, Branch Manager | Invoice Count, Total Sales, Average Order Value | Payment, Branch, Date | Payment, Invoice ID, Sales | Bar chart và tỷ trọng | Detailed/Diagnostic | Không có phí hoặc trạng thái thanh toán; không kết luận hiệu quả chi phí |
| BQ-07 | Sales và Invoice Count phân bố như thế nào theo giờ hoặc Time Period? | Sales/Operations Manager, Branch Manager, BI Analyst | Total Sales, Invoice Count | transaction hour, time period, Branch, Date | Time, Sales, Invoice ID | Column chart theo giờ/khung giờ | Detailed/Diagnostic | Time Period là nhóm phân tích nội bộ trong phạm vi giờ quan sát, không phải chuẩn chung |
| BQ-08 | Average Rating khác nhau như thế nào giữa Branch và Product Line, và nhóm nào cần được chú ý? | Sales/Operations Manager, Branch Manager, BI Analyst | Average Rating, Invoice Count | Branch, Product line, Date | Rating, Branch, Product line, Invoice ID | Heatmap hoặc matrix | Detailed/Diagnostic | Rating không chứng minh nguyên nhân hoặc mức độ hài lòng của khách hàng cá nhân |

Các câu hỏi chỉ xác định quy mô, phân bố, so sánh và nhóm đóng góp vào biến động quan sát được; không khẳng định nguyên nhân ngoài dữ liệu.

## 7. Functional Requirements

| ID | Yêu cầu |
|---|---|
| FR-01 | Hệ thống phải hiển thị các KPI tổng quan theo filter context hiện hành. |
| FR-02 | Hệ thống phải cho phép phân tích Sales theo ngày và tháng. |
| FR-03 | Hệ thống phải hỗ trợ lọc theo Branch, Product line, Customer type, Gender và Payment method. |
| FR-04 | Hệ thống phải hỗ trợ phân tích theo `transaction_hour` hoặc `time_period`. |
| FR-05 | Hệ thống phải hỗ trợ drill-down hoặc drill-through từ Overview tới Detailed/Diagnostic. |
| FR-06 | Hệ thống phải cho phép so sánh các nhóm trong cùng Dimension và hiển thị số bản ghi làm ngữ cảnh. |
| FR-07 | Dashboard phải hiển thị cảnh báo phạm vi 2019-01-01 đến 2019-03-30 và giới hạn của Monthly Sales Growth. |
| FR-08 | AI Summary chỉ được sử dụng KPI hoặc breakdown đã được semantic model tính. |
| FR-09 | Mọi nhận định trong AI Summary phải có thể đối chiếu với KPI, filter và visual trên dashboard. |
| FR-10 | Branch và City phải dùng chung ngữ cảnh `dim_branch_location`; không trình bày hai insight trùng cấu trúc như độc lập. |

## 8. Non-functional Requirements

| ID | Yêu cầu |
|---|---|
| NFR-01 | KPI phải chính xác, có định nghĩa và có thể đối soát từ source tới dashboard. |
| NFR-02 | Raw CSV và ZIP không được chỉnh sửa, đổi tên hoặc ghi đè. |
| NFR-03 | Quá trình nạp phải idempotent; `Invoice ID` được dùng để phát hiện nạp trùng trong snapshot. |
| NFR-04 | Pipeline phải có khả năng chạy lại và ghi log trạng thái, số dòng, lỗi. |
| NFR-05 | Không hard-code password, credential hoặc API key. |
| NFR-06 | Tên nguồn và tên chuẩn hóa phải nhất quán: raw `Sales`, dự kiến dbt `sales_amount`; không tạo cột nguồn `Total`. |
| NFR-07 | Models, tests, mapping và lineage phải được tài liệu hóa. |
| NFR-08 | AI không được tự tạo số liệu, suy luận nguyên nhân hoặc dùng dữ liệu ngoài filter context đã cung cấp. |
| NFR-09 | Dashboard phải ghi rõ phạm vi ngày của dữ liệu và trạng thái tháng 03 kết thúc ngày 30. |
| NFR-10 | Không gắn ký hiệu tiền tệ cụ thể vì dataset không xác nhận đơn vị tiền tệ; dùng số không kèm ký hiệu hoặc mô tả “monetary units”. |

## 9. Time Period Baseline

| Time Period | Khoảng giờ |
|---|---|
| Morning | 10:00-11:59 |
| Afternoon | 12:00-16:59 |
| Evening | 17:00-20:59 |

Các nhãn này chỉ phục vụ phân nhóm phân tích trong phạm vi giờ quan sát của dataset, không mang ý nghĩa chuẩn chung cho mọi doanh nghiệp. Chưa tạo cột hoặc transformation trong task hiện tại.

## 10. Scope and Limitations

- Dataset chỉ chứa ba tháng; tháng 03 kết thúc ngày 30.
- Không có SKU hoặc chi tiết dòng hóa đơn.
- Không có Customer ID.
- Không có inventory, discount, return hoặc operating cost.
- Không phân tích lợi nhuận ròng.
- Không suy luận mùa vụ hoặc xu hướng dài hạn.
- Branch và City ánh xạ một-một; hai breakdown tạo cùng cơ cấu phân nhóm.
- Gross Income bằng Tax 5% trên toàn bộ snapshot; không trình bày như hai KPI độc lập.
- `gross margin percentage` cố định `4.761904762`; không dùng làm KPI hoặc biểu đồ biến động.
- Chín giao dịch giá trị cao bị IQR gắn cờ được giữ lại vì chưa có bằng chứng là lỗi.
- Dataset không xác nhận đơn vị tiền tệ.

## 11. Traceability Matrix

| Business Objective | Business Question | KPI | Dashboard Page | AI Summary eligibility |
|---|---|---|---|---|
| BO-01 | BQ-01 | Total Sales; Total Quantity; Invoice Count; Average Order Value | Overview | Có |
| BO-02 | BQ-02 | Total Sales; Average Daily Sales; Monthly Sales Growth | Overview | Có; Monthly Sales Growth phải kèm cảnh báo |
| BO-03 | BQ-03 | Total Sales; Total Quantity; Invoice Count | Overview; Detailed/Diagnostic | Có |
| BO-04 | BQ-04 | Total Sales; Total Quantity; Weighted Average Unit Price; Total COGS | Detailed/Diagnostic | Có; Product line không phải SKU |
| BO-05 | BQ-05 | Total Sales; Average Order Value; Invoice Count | Detailed/Diagnostic | Có; không suy luận khách hàng cá nhân |
| BO-05 | BQ-06 | Total Sales; Invoice Count; Average Order Value | Detailed/Diagnostic | Có; không suy luận phí thanh toán |
| BO-06 | BQ-07 | Total Sales; Invoice Count | Detailed/Diagnostic | Có |
| BO-06 | BQ-08 | Average Rating; Invoice Count | Detailed/Diagnostic | Có; không suy luận nguyên nhân |
| BO-07 | BQ-01 đến BQ-08 | Chín KPI chính; KPI hỗ trợ khi được yêu cầu và gắn nhãn | Overview; Detailed/Diagnostic | Có nếu số liệu xuất phát từ semantic model và có thể đối chiếu |

Mỗi KPI chính phục vụ ít nhất một Business Question. KPI hỗ trợ không được ưu tiên trên Overview và không thay thế KPI chính.

## 12. Acceptance Criteria

Business Requirements được xem là hoàn thành khi:

- Có bối cảnh, quy trình nghiệp vụ và ba vai trò người dùng.
- Có đúng 8 Business Questions, từ BQ-01 đến BQ-08.
- Mọi câu hỏi có thể trả lời bằng các trường hiện có.
- Không có câu hỏi yêu cầu SKU, Customer ID, tồn kho hoặc lợi nhuận ròng.
- Có Traceability Matrix nối Objective, Question, KPI, Dashboard Page và AI eligibility.
- Mỗi KPI chính liên kết với ít nhất một Business Question.
- Time Period baseline được ghi nhận nhưng chưa triển khai transformation.
- Nội dung không mâu thuẫn với `DATA_PROFILE.md` và `DECISION_LOG.md`.
