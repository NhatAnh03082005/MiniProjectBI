# Chạy AI-Assisted Analytics với Gemini

Tài liệu này hướng dẫn cách cài đặt, cấu hình và sử dụng chức năng AI-Assisted Analytics của mục 3.5. Ứng dụng đọc dữ liệu từ DDS trên SQL Server, tính các chỉ số cần thiết và chuẩn bị nhận xét kèm số liệu đối chiếu. Gemini chọn những nhận xét phù hợp để tạo bản tóm tắt hoặc trả lời câu hỏi; nội dung hiển thị trên giao diện được tạo từ các số liệu đã kiểm tra.

Power BI và ứng dụng AI cùng đọc DDS nhưng có bộ lọc riêng. Cần chọn cùng phạm vi ở hai nơi khi đối chiếu.

## 1. Chuẩn bị trên máy

| Thành phần | Cần chuẩn bị |
|---|---|
| Hệ điều hành | Windows 64-bit; dùng PowerShell để chạy các lệnh bên dưới |
| Python | CPython thông thường 64-bit, phiên bản 3.11–3.13; ưu tiên 3.11 đã kiểm tra. Không dùng bản free-threaded (`3.13t`, `3.14t`…) với bộ thư viện đã pin này. [Tải Python cho Windows](https://www.python.org/downloads/windows/) |
| SQL Server | Database `AmazonDeliveryBI` có năm Dimension và Fact trong schema `dw`; tài khoản Windows hiện tại có quyền đọc các bảng này |
| ODBC | [Microsoft ODBC Driver 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server); tên driver nhập trên app phải khớp driver đã cài |
| Gemini | Có Internet và Gemini API key còn quyền truy cập/quota cho model được chọn |

**Nếu máy đã chạy được Power BI từ DDS hiện hành:** dùng lại SQL instance và database đó, sau đó chuyển sang bước 2. Không cần chạy lại ETL mỗi lần mở AI.

**Nếu máy chưa có DDS:** việc tải mã nguồn hoặc chạy `ai/run.ps1` không tự tạo database hay nạp CSV. Chuẩn bị dữ liệu theo thứ tự:

1. [SQL bootstrap](../sql/README.md): tạo database/schema/staging. Chọn database chính `AmazonDeliveryBI`.
2. [Hướng dẫn thiết lập Mage](../MAGE_TEAM_SETUP.md): chuẩn bị môi trường Mage và nạp dữ liệu vào staging.
3. [dbt](../dbt_project/README.md): cấu hình profile, dựng Dimension/Fact và chạy kiểm thử. Nếu đặt `profiles.yml` ngay trong `dbt_project`, chạy `dbt debug --profiles-dir .` và `dbt build --profiles-dir .` từ thư mục đó, bằng môi trường dbt đã cấu hình.

Dùng **cùng một SQL instance** xuyên suốt các bước. `localhost` và `localhost\SQLEXPRESS` có thể là hai instance khác nhau; sửa các ví dụ trong hướng dẫn theo instance thực tế trên máy. SQL bootstrap mới chỉ tạo phần SQL ban đầu; phải nạp Mage và hoàn tất dbt trước khi AI đọc DDS.

Có thể kiểm tra bằng SSMS trên database đã chọn:

```sql
USE AmazonDeliveryBI;
SELECT COUNT_BIG(*) AS delivery_records FROM dw.fact_delivery;
```

Các bảng AI sử dụng: `dw.fact_delivery`, `dw.dim_date`, `dw.dim_delivery_condition`, `dw.dim_vehicle`, `dw.dim_area`, `dw.dim_category`. Chờ ETL/dbt kết thúc rồi mới lấy dữ liệu từ app.

## 2. Cài và mở ứng dụng

Mở PowerShell **tại thư mục gốc của mã nguồn**, nơi có `README.md`, `ai/`, `sql/` và `dbt_project/`. Các lệnh bên dưới dùng đường dẫn tương đối nên không phụ thuộc vào vị trí lưu mã nguồn, miễn là PowerShell đang mở đúng thư mục gốc.

Chạy lần đầu, hoặc sau khi `ai/requirements.txt` thay đổi:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\ai\run.ps1 -Install
```

Các lần mở tiếp theo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\ai\run.ps1
```

Script chọn Python phù hợp, tạo `.ai_venv` riêng khi chưa có, cài thư viện khi cần và mở server tại **http://127.0.0.1:8501**. Truy cập địa chỉ này bằng trình duyệt trên chính máy đang chạy. Giữ terminal mở; bấm `Ctrl+C` trong terminal để dừng. Không cần kích hoạt venv thủ công, chạy quyền Administrator hoặc cài thư viện AI vào môi trường Mage/dbt.

Nếu cổng 8501 đang có ứng dụng khác:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\ai\run.ps1 -Port 8502
```

Khi đó mở **http://127.0.0.1:8502**. Địa chỉ `127.0.0.1` chỉ truy cập được trên máy đang chạy ứng dụng; đây không phải địa chỉ triển khai công khai.

## 3. Kết nối DDS và nhập API key

Mở thanh bên bằng mũi tên góc trái, điền:

| Ô trên giao diện | Cách điền |
|---|---|
| **SQL Server** | Instance thực tế; mặc định `localhost\SQLEXPRESS` |
| **Database** | Mặc định `AmazonDeliveryBI` |
| **ODBC Driver** | Mặc định `ODBC Driver 18 for SQL Server`; nếu chỉ cài Driver 17, nhập đúng `ODBC Driver 17 for SQL Server` |
| **Tin cậy chứng chỉ SQL Server cục bộ** | Dành cho SQL Express cục bộ. Với server có chứng chỉ được tin cậy, bỏ chọn để xác thực chứng chỉ |

Bấm **Kết nối và tải dữ liệu**. Kết nối dùng **Windows Authentication**, theo tài khoản đang chạy ứng dụng. Nếu SQL Server dùng riêng SQL login, cần thống nhất với người quản lý DDS cách cấp quyền Windows; giao diện hiện chưa có ô SQL username/password.

Để bật phần AI:

1. Tạo Gemini API key tại [Google AI Studio](https://aistudio.google.com/apikey), hoặc dùng key đã được cấp cho tài khoản đang chạy ứng dụng.
2. Dán key vào ô mật khẩu **Gemini API key**, rồi nhấn `Enter` hoặc bấm ra ngoài ô để áp dụng.
3. Giữ model mặc định `gemini-3.5-flash-lite`, hoặc bấm **Xem mô hình khả dụng** và chọn model mà key được phép dùng. Quyền truy cập, quota và chi phí phụ thuộc tài khoản/model.
4. Nếu muốn dùng lại key trên máy này, bấm **Lưu key trên máy**. Ứng dụng lưu vào Windows Credential Manager của tài khoản Windows hiện tại; các phiên sau trên cùng tài khoản/máy có thể nạp lại key. Đây là lựa chọn chủ động, không phải yêu cầu để chạy AI.
5. Thu thanh bên lại trước khi quay video hoặc trình bày.

**Không cần sửa code hay tạo file `.env` để nhập key.** Nếu chưa lưu key trên máy, phiên mới bắt đầu với ô key trống. Nếu đã lưu, key được nạp từ Windows Credential Manager và vẫn hiển thị dưới dạng mật khẩu. Key không được ghi vào mã nguồn, URL, prompt, log hay JSON tải xuống. **Xóa khóa phiên** chỉ xóa key và kết quả khỏi phiên hiện tại; **Xóa key đã lưu** xóa cả bản lưu trên máy và key trong phiên hiện tại. Không gửi key qua chat hoặc đưa vào Git.

Key đã lưu gắn với tài khoản Windows và máy hiện tại. Key không đi cùng mã nguồn và cũng không tự xuất hiện khi chạy ứng dụng trên máy khác. Cơ chế này chỉ phù hợp với ứng dụng chạy cục bộ; không dùng để triển khai một server dùng chung nếu chưa có lớp xác thực riêng. Khi quay video, giữ ô key ở trạng thái che mật khẩu.

Ứng dụng không tự đọc `.env`, `GEMINI_API_KEY` hay các biến `DBT_SQLSERVER_*`. Trong các biến môi trường cấu hình kết nối, chỉ `MSSQL_SERVER` được dùng làm giá trị mặc định cho ô SQL Server; giá trị này vẫn có thể sửa trên giao diện. Khi chưa nhập key, ứng dụng vẫn có thể lấy DDS và hiển thị tab **Số liệu đối chiếu**.

## 4. Sử dụng và demo

1. **Xem toàn bộ dữ liệu:** giữ đủ khoảng ngày, để trống các lựa chọn Phương tiện, Danh mục, Khu vực và bộ lọc bổ sung; lựa chọn trống có nghĩa là tất cả.
2. **Tạo tóm tắt:** trong tab **AI phân tích**, bấm **Tạo tóm tắt và phân tích**. Kết quả gồm **Tóm tắt KPI** và **Xu hướng và khác biệt cần chú ý**.
3. **Kiểm chứng:** mở **Số liệu cho nhận xét…** dưới từng câu để xem giá trị, đơn vị, cỡ mẫu, nguồn và ngữ cảnh. Tab **Số liệu đối chiếu → Theo ngày và theo nhóm** có các bảng và biểu đồ đối chiếu.
4. **Hỏi về dữ liệu:** giữ chế độ **Phân tích dữ liệu**, mở **Gợi ý câu hỏi và phạm vi hỗ trợ** nếu muốn xem ví dụ, hoặc viết câu hỏi theo cách tự nhiên rồi bấm **Giải thích câu hỏi**. Không cần nhấn `Ctrl+Enter`; nút sẽ đổi sang màu cam ngay khi ô hỏi có nội dung và lần bấm sẽ gửi nội dung đang nhập. Chọn một câu gợi ý chỉ điền nội dung vào ô hỏi; Gemini vẫn chỉ được gọi sau khi bấm nút. Kết quả hỏi riêng chỉ hiển thị câu hỏi, câu trả lời và số liệu dẫn chứng; nút tạo tóm tắt không gửi nội dung ô câu hỏi.
5. **Hỏi kiến thức chung:** chọn **Hỏi Gemini chung**, nhập câu hỏi rồi bấm **Giải thích câu hỏi**. Luồng này không gửi DDS, bộ lọc hoặc số liệu dashboard; câu trả lời được ghi rõ là kiến thức chung và không có dẫn chứng BI. Chuyển lại **Phân tích dữ liệu** khi cần kết quả đáp ứng mục 3.5.
6. **Đổi phạm vi:** xóa câu hỏi, chọn Danh mục **Grocery**, giữ các bộ lọc khác ở tất cả, rồi tạo lại tóm tắt. Nhận xét cũ bị xóa khi bộ lọc hoặc thiết lập thay đổi; nội dung câu hỏi mới được áp dụng khi bấm **Giải thích câu hỏi**. API chỉ được gọi khi bấm một trong hai nút tạo kết quả.
7. **Lưu kết quả:** mở **Thông tin kết quả và tải xuống → Tải kết quả AI (JSON)**. Model, snapshot, `claim_id`, câu đã dựng, template, mã dẫn chứng và số lần gọi được giữ để kiểm tra lại. `usage_scope=final_attempt_only` nghĩa là token usage chỉ thuộc lần thành công cuối; các lần thử trước có thể vẫn tiêu thụ quota. Bản số liệu tổng hợp tải riêng ở tab đối chiếu.
8. **Thử câu ngoài phạm vi dữ liệu:** trong chế độ **Phân tích dữ liệu**, hỏi “Dự báo doanh thu tháng sau là bao nhiêu?”. Ứng dụng cần báo câu hỏi nằm ngoài phạm vi dữ liệu hiện có; không biến dữ liệu giao hàng thành doanh thu dự đoán. Nếu chỉ muốn trao đổi kiến thức chung, chủ động chuyển sang **Hỏi Gemini chung** để tránh nhầm câu trả lời chung với kết quả dashboard.

Với **Số liệu đối chiếu → Theo ngày và theo nhóm → Ngày × khung giờ**, xem ma trận trung bình theo từng ngày trong tuần và khung giờ, kèm ma trận cỡ mẫu thời lượng hợp lệ. Không cộng hoặc lấy trung bình các trung bình của những ô này để thay cho KPI toàn bộ dữ liệu.

Các câu phù hợp để quay thử:

- “Mức giao thông nào có thời gian giao trung bình cao nhất và thấp nhất? Chênh lệch đã tính là bao nhiêu?”
- “Trong các cặp ngày lịch liền nhau đủ mẫu, mức tăng thời gian giao trung bình lớn nhất xảy ra giữa ngày nào? Trung bình và cỡ mẫu mỗi ngày là bao nhiêu?”
- “P90 là gì và giải thích rõ thông số này giúp tôi”
- “Có bao nhiêu ngày có bản ghi và bao nhiêu ngày không có bản ghi?”
- “Khoảng cách hợp lệ trung bình là bao nhiêu?”

Bạn không cần nhớ một mẫu câu cố định. Các câu phía trên chỉ là ví dụ để demo và kiểm thử hồi quy, không phải danh sách câu hỏi được phép. Ứng dụng nhận cách hỏi tự nhiên về ý nghĩa hoặc giá trị của KPI, xu hướng theo ngày và so sánh giữa các nhóm giao thông, thời tiết, phương tiện, khu vực, danh mục, khung giờ hoặc khoảng cách. Những cách hỏi như `What's P90?`, `Có bao nhiêu giao hàng?`, `P90 right now?`, `Phân tích giao thông` hoặc `Jam compared to High` đều được đưa về đúng chỉ số hay phép so sánh tương ứng. Các lỗi gõ rõ nghĩa cũng được chuẩn hóa trước khi gọi Gemini, chẳng hạn `p9o` thành `P90`, `motocycle` thành `motorcycle` kể cả trong câu `phân tích KPI của motocycle`, hoặc `semi urban` thành `Semi-Urban`. Tên quá khác, mơ hồ hoặc không có trong dữ liệu vẫn bị từ chối thay vì đoán bừa.

Có thể nêu hai nhóm cụ thể để xem số liệu của từng nhóm; nếu hỏi một chênh lệch chính xác, hệ thống chỉ trả lời khi chênh lệch đó đã được tính sẵn. Câu nhận diện rõ đi theo đường xử lý nhanh; cách diễn đạt mới sẽ được Gemini hiểu theo ngữ nghĩa và chọn trong tập nhận xét đã kiểm chứng phù hợp với chủ đề. Gemini không được tự tạo câu trả lời, số liệu hoặc nhóm mới.

Hai thông báo từ chối có ý nghĩa khác nhau:

- **Ngoài phạm vi dữ liệu:** câu hỏi yêu cầu dữ liệu hoặc kết luận ứng dụng không có, chẳng hạn doanh thu, dự báo, nguyên nhân, SQL, từng đơn hàng hoặc địa điểm không thuộc dữ liệu. Hãy đổi câu hỏi theo các chủ đề được ghi trong phần gợi ý.
- **Chưa đủ dữ liệu trong phạm vi đang chọn:** nội dung câu hỏi được hỗ trợ, nhưng bộ lọc hiện tại không còn đủ chứng cứ để trả lời. Hãy nới bộ lọc hoặc chọn phạm vi khác.

Câu hỏi không phải truy vấn dữ liệu tùy ý. Muốn đổi ngày, danh mục hoặc khu vực, dùng bộ lọc trước rồi tạo lại nhận xét. Ứng dụng không bỏ qua địa điểm, điều kiện hoặc chỉ số lạ, và không thay chúng bằng một chỉ số gần giống. Ví dụ, “tỷ lệ vượt P90” không được đổi thành tỷ lệ vượt mốc cố định 195 phút; đây là hai phép tính khác nhau. Nếu cần giải thích nhiều KPI, nên chia thành các câu ngắn thay vì yêu cầu quá nhiều định nghĩa trong một lượt. Câu chỉ dùng đại từ như “còn chỉ số này?” mà không nêu rõ chỉ số trong cùng lượt sẽ bị từ chối vì ứng dụng không đoán ngữ cảnh hội thoại trước đó.

Trên snapshot đã kiểm tra lại ngày 22/11/2026: toàn bộ Fact có **43.594 bản ghi**, trung bình **124,92 phút**, P90 **195 phút**; chênh lệch Jam–Low khoảng **46,40 phút**. Grocery có **2.687 bản ghi**, trung bình **26,54 phút**, P90 **40 phút**. Đây là mốc kiểm tra của snapshot, không phải các giá trị gán cứng; chúng có thể đổi sau khi nạp dữ liệu mới.

Đối chiếu Power BI bằng project hiện có tại [AmazonDeliveryBI.pbip](../powerbi/project/AmazonDeliveryBI.pbip). Chọn cùng ngày/phương tiện/danh mục/khu vực và bỏ các lựa chọn visual không tương ứng. **Home → Refresh** trong Power BI sau khi DDS thay đổi; dữ liệu Import không tự cập nhật cùng app AI. Nếu chọn các ngày rời rạc, dùng **Bộ lọc bổ sung → Chọn ngày riêng lẻ khi đối chiếu Power BI**; lựa chọn này thay thế khoảng ngày phía trên.

## 5. Xử lý lỗi thường gặp

| Hiện tượng | Cách kiểm tra |
|---|---|
| Không tìm thấy Python phù hợp | Cài CPython 3.11–3.13 thông thường 64-bit, mở terminal mới rồi chạy lại. `py -0p` giúp xem các bản Python đã đăng ký; tránh bản có hậu tố `t` |
| Thiếu thư viện hoặc cài dở | Chạy lại `run.ps1 -Install`. Nếu `.ai_venv` được tạo bằng Python không tương thích, dừng app và đổi tên thư mục này để tạo môi trường mới; không sửa môi trường Mage/dbt |
| Thiếu ODBC / không đọc được DDS | Kiểm tra driver đã cài, tên instance/database, dịch vụ SQL Server và quyền Windows. Kiểm tra sáu bảng `dw` ở bước 1; chỉ có staging thì cần hoàn tất dbt |
| Kết nối SQL được nhưng đọc DDS bị timeout | Kiểm tra chờ cấp bộ nhớ SQL (`RESOURCE_SEMAPHORE`) và các truy vấn đang chạy. Bản đọc DDS hiện không sắp xếp toàn bộ dữ liệu trong SQL; fingerprint tự sắp xếp ở Python. Không chỉ tăng timeout hoặc đổi sang đọc dữ liệu chưa commit |
| Nút tạo AI chưa bật | **Phân tích dữ liệu** cần bản ghi trong phạm vi đang chọn, key đã áp dụng và tên model. **Hỏi Gemini chung** chỉ cần key và tên model; không cần tải DDS |
| Key/model bị từ chối hoặc hết quota | Kiểm tra key, Internet, quota và **Xem mô hình khả dụng**. Lỗi xác thực, model không tồn tại hoặc quota không có thời gian chờ ngắn không được tự thử lại |
| Gemini tạm lỗi hoặc phản hồi chưa hợp lệ | Một lần bấm có tối đa 3 yêu cầu, dùng chung giới hạn cho lỗi kết nối, lỗi dịch vụ và lựa chọn nhận xét sai. Chờ giữa các lần; tôn trọng `Retry-After` ngắn tối đa 5 giây. Hết giới hạn thì báo lỗi và giữ số liệu đối chiếu, không tạo kết quả AI thay thế hoặc tự đổi model |
| Báo câu hỏi nằm ngoài phạm vi | Câu hỏi đang yêu cầu dữ liệu hoặc kết luận ứng dụng không có. Mở phần gợi ý để xem chủ đề được hỗ trợ, sau đó viết lại theo KPI, xu hướng ngày hoặc so sánh nhóm |
| Báo chưa đủ dữ liệu trong phạm vi | Câu hỏi được hỗ trợ nhưng bộ lọc hiện tại thiếu chứng cứ. Nới bộ lọc ngày/nhóm hoặc chọn phạm vi khác rồi gửi lại |
| Muốn hỏi chủ đề không thuộc dashboard | Chọn **Hỏi Gemini chung**. Câu trả lời ở chế độ này không dùng DDS và không có số liệu đối chiếu; không dùng nó làm bằng chứng cho phần 3.5 |
| KPI khác Power BI | Chọn cùng bộ lọc, xóa lựa chọn trên visual và Refresh Power BI. App không tự lấy slicer/cross-highlight/drill-through từ Desktop |
| Grocery hiện “—” ở tỷ lệ vượt baseline | Measure DAX hiện dùng `COUNT` không `COALESCE`, nên trả BLANK khi không có bản ghi vượt ngưỡng. Không đọc dấu này thành mất toàn bộ dữ liệu hoặc tỷ lệ 0% |

## 6. Phạm vi và nguyên lý

| Yêu cầu mục 3.5 | Thành phần đáp ứng |
|---|---|
| Dùng LLM/dịch vụ Generative AI | Gọi Gemini `generateContent` thật bằng key nhập khi chạy |
| Tạo AI-generated Summary từ KPI | Gemini chọn và sắp xếp nhận xét có dẫn chứng qua nút **Tạo tóm tắt và phân tích** |
| Giải thích xu hướng, biến động hoặc vấn đề | Chứng cứ theo ngày và các nhóm giao thông, thời tiết, phương tiện, khu vực, danh mục, khung giờ, khoảng cách; có các chênh lệch tính sẵn |
| Dựa trên dữ liệu, có thể kiểm chứng | Claim ID gắn với câu và dẫn chứng do ứng dụng kiểm soát; kiểm tra snapshot, đơn vị, cỡ mẫu, ngữ cảnh, phép so sánh và phạm vi câu hỏi trước khi hiển thị |
| Khuyến khích hỏi bằng ngôn ngữ tự nhiên | Ô câu hỏi, danh sách ví dụ và nút **Giải thích câu hỏi**; hỗ trợ cách diễn đạt khác nhau trong phạm vi hiện tại |

Luồng xử lý: **DDS → Python tính KPI/bảng nhóm/chứng cứ và danh mục nhận xét → nhận diện trực tiếp câu hỏi rõ hoặc nhờ Gemini hiểu cách diễn đạt tự nhiên → Gemini chọn claim ID phù hợp → kiểm tra lựa chọn → dựng câu từ chứng cứ → hiển thị kèm số liệu đối chiếu**.

Luồng **Hỏi Gemini chung** tách riêng: **câu hỏi → Gemini → câu trả lời văn bản**. Luồng này không nhận bundle, Fact, bộ lọc hay thông tin kết nối; giao diện luôn ghi rõ kết quả không dựa trên dashboard. Đây là tiện ích hỏi đáp, không thay thế luồng có dẫn chứng dùng để đáp ứng mục 3.5.

Trong chế độ **Phân tích dữ liệu**, Gemini không được gửi câu văn tự do để hiển thị. Phản hồi chỉ có `snapshot_id`, danh sách claim ID cho `summary`, `explanations`, `answer` và `answer_status`. Bốn trạng thái trả lời là `not_requested`, `answered`, `insufficient_data` và `unsupported_question`. Danh mục nhận xét được dựng lại từ cùng snapshot, không nhận nội dung câu hay số do model tự viết. Ví dụ, nhận xét ngày luôn tách số ngày có bản ghi và số ngày không có bản ghi thành hai câu, không biến một nhóm thành tổng của nhóm kia. So sánh ngày gắn đủ ngày, trung bình và cỡ mẫu của cả hai phía; so sánh nhóm kiểm tra lại chênh lệch và mẫu số trước khi cho phép lựa chọn.

Trong chế độ **Phân tích dữ liệu**, Gemini chỉ nhận số liệu tổng hợp, không nhận từng dòng Fact, Order ID, tọa độ chính xác hoặc thông tin kết nối SQL. Chế độ **Hỏi Gemini chung** chỉ gửi nội dung câu hỏi, không gửi bundle dữ liệu. Ứng dụng không sinh SQL từ câu hỏi và không ghi thay đổi vào DDS. Mỗi lần lấy dữ liệu dùng một transaction đọc nhất quán rồi đóng kết nối; tránh lấy số liệu khi ETL/dbt đang dựng lại DDS.

Các giới hạn cần giữ khi trình bày:

- Chênh lệch giữa nhóm là mô tả, chưa chứng minh quan hệ nhân quả. Không có dữ liệu doanh thu/chi phí để trả lời KPI tài chính hoặc dự báo chúng.
- Mốc **195 phút** là baseline thống kê cố định, không phải SLA hay tỷ lệ giao trễ. P90 theo bộ lọc được tính lại; hai khái niệm không được dùng thay nhau.
- Nhóm ít mẫu và Unknown cần đọc cùng cỡ mẫu. Ngày không có bản ghi không chứng minh giao hàng đã dừng; các tháng có thể không đủ ngày.
- Câu chứa số thuộc danh mục do ứng dụng kiểm soát; Gemini chọn nội dung và thứ tự, không tự viết lại quan hệ giữa các số. Cách này giảm bớt sự linh hoạt để kết quả có thể kiểm chứng. Khi trình bày, cần chọn đúng bộ lọc, đọc dẫn chứng và tránh khẳng định dữ liệu nguồn hoặc dịch vụ bên ngoài luôn chính xác hay luôn hoạt động.
- Khoảng cách/rating dùng các cờ hợp lệ của Fact. Coverage khoảng cách giữ riêng cách viết measure của Operational Drivers và Area & Category khi chúng khác nhau ở BLANK/0.

## 7. Kiểm thử và kiểm tra trước khi sử dụng

Chạy các lệnh sau từ thư mục gốc của mã nguồn sau khi cài môi trường AI:

```powershell
# Kiểm thử cục bộ: không gọi Gemini thật, không thay đổi DDS.
.\.ai_venv\Scripts\python.exe -m unittest discover -s ai\tests -v
.\.ai_venv\Scripts\python.exe -m pip check
```

Test SQL đối soát chỉ đọc chạy riêng khi DDS sẵn sàng:

```powershell
$env:RUN_AI_DDS_TESTS='1'
$env:MSSQL_SERVER='localhost\SQLEXPRESS' # Sửa theo instance của máy.
.\.ai_venv\Scripts\python.exe -m unittest discover -s ai\tests -v
Remove-Item Env:\RUN_AI_DDS_TESTS
```

Không gán cứng số lượng kiểm thử trong tài liệu: hãy dùng kết quả cuối cùng của lệnh `unittest discover` trên đúng phiên bản mã nguồn đang chạy. Các test bao phủ tính KPI, cỡ mẫu hợp lệ, chứng cứ BLANK, biến động ngày, đơn vị và phạm vi câu hỏi, câu hỏi nhiều KPI, claim ID, giới hạn thử lại, gọi API giả lập, giao diện và lưu key. Cả năm câu hỏi mẫu ở mục 4 đều có kiểm thử hồi quy. Phần kiểm tra credential dùng key giả, không đọc hoặc thay đổi key thật đã lưu trên máy.

Gemini thật và giao diện đã được kiểm tra với tóm tắt toàn bộ dữ liệu, so sánh Jam–Low, câu hỏi đồng thời P90 và trung bình, số ngày có/không có bản ghi, khoảng cách trung bình và mức tăng ngày lớn nhất kèm đầy đủ ngày, trung bình, cỡ mẫu. Tóm tắt Grocery dùng đúng phạm vi; câu hỏi tỷ lệ vượt baseline giữ BLANK, không tự đổi thành 0%. Câu hỏi dự báo doanh thu bị từ chối. Có yêu cầu thành công ở lần gọi thứ hai; giao diện hiển thị đúng số lần gọi. Bản JSON tải từ giao diện đã được đọc lại để kiểm tra claim ID, metadata và việc không chứa key. API vẫn phụ thuộc vào kết nối Internet, quyền truy cập và quota của tài khoản; kết quả kiểm tra không đồng nghĩa dịch vụ bên ngoài sẽ luôn hoạt động ổn định.

Trước khi quay demo hoặc chạy trên một máy mới, hãy tải đúng phiên bản mã nguồn, mở ứng dụng, kết nối DDS và nhập API key cho phiên chạy đó. Sau khi dữ liệu xuất hiện, tạo một bản tóm tắt, mở số liệu đối chiếu, thử một câu hỏi và đổi bộ lọc để kiểm tra việc tạo lại kết quả. Các test dùng HTTP giả lập không thay thế lần gọi Gemini thật, vì quyền truy cập và quota có thể khác giữa các tài khoản. Có thể tải kết quả JSON từ giao diện để kiểm tra, nhưng không cần lưu kết quả chạy thử vào Git.

Thư mục `ai/` gồm `app.py` (giao diện), `data.py` (đọc DDS), `analytics.py` (tính số liệu), `gemini.py` (gọi API), `grounding.py` (kiểm tra dẫn chứng), `credentials.py` (kết nối Windows Credential Manager, không chứa key), `__init__.py`, `requirements.txt`, `run.ps1`, tài liệu này và thư mục `tests/`. Giữ thư mục `tests/` để kiểm tra lại sau mỗi lần dữ liệu hoặc code thay đổi.

Không đưa `.ai_venv/`, `__pycache__/`, `.env`, API key, log, ảnh thử nghiệm hoặc kết quả tải xuống vào Git. Các thư mục môi trường và cache đã có quy tắc ignore. Mã nguồn không chứa database hay API key; mỗi máy cần kết nối đến DDS và cung cấp key riêng khi chạy.

## Tài liệu kỹ thuật

- [Google: API keys](https://ai.google.dev/gemini-api/docs/api-key)
- [Google: generateContent REST](https://ai.google.dev/api/generate-content)
- [Google: structured outputs và giới hạn kiểm chứng ngữ nghĩa](https://ai.google.dev/gemini-api/docs/structured-output)
- [Google: danh sách model](https://ai.google.dev/api/models)
- [Google: hạn mức API theo dự án](https://aistudio.google.com/docs/rate-limits)
- [Microsoft: DAX COUNT và BLANK](https://learn.microsoft.com/en-us/dax/count-function-dax)
- [Streamlit: kiểm thử ứng dụng](https://docs.streamlit.io/develop/concepts/app-testing)
- [Microsoft: Windows generic credential và phạm vi lưu theo tài khoản/máy](https://learn.microsoft.com/en-us/windows/win32/api/wincred/ns-wincred-credentialw)
