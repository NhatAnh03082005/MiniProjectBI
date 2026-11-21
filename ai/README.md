# Chạy AI-Assisted Analytics với Gemini

Hướng dẫn dành cho thành viên nhận source và chạy mục 3.5. Ứng dụng mở trên trình duyệt, lấy dữ liệu từ DDS SQL Server rồi dùng Gemini để tóm tắt KPI, giải thích khác biệt và trả lời câu hỏi bằng tiếng Việt.

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

**Nếu máy chưa có DDS:** việc pull source hoặc chạy `ai/run.ps1` không tạo database hay nạp CSV. Chuẩn bị dữ liệu theo thứ tự:

1. [SQL bootstrap](../sql/README.md): tạo database/schema/staging. Chọn database chính `AmazonDeliveryBI`.
2. [Mage team setup](../MAGE_TEAM_SETUP.md): cấu hình môi trường Mage và nạp dữ liệu vào staging.
3. [dbt](../dbt_project/README.md): cấu hình profile, dựng Dimension/Fact và chạy kiểm thử. Nếu đặt `profiles.yml` ngay trong `dbt_project`, chạy `dbt debug --profiles-dir .` và `dbt build --profiles-dir .` từ thư mục đó, bằng môi trường dbt đã cấu hình.

Dùng **cùng một SQL instance** xuyên suốt các bước. `localhost` và `localhost\SQLEXPRESS` có thể là hai instance khác nhau; sửa các ví dụ trong hướng dẫn theo instance thực tế trên máy. SQL bootstrap mới chỉ tạo phần SQL ban đầu; phải nạp Mage và hoàn tất dbt trước khi AI đọc DDS.

Có thể kiểm tra bằng SSMS trên database đã chọn:

```sql
USE AmazonDeliveryBI;
SELECT COUNT_BIG(*) AS delivery_records FROM dw.fact_delivery;
```

Các bảng AI sử dụng: `dw.fact_delivery`, `dw.dim_date`, `dw.dim_delivery_condition`, `dw.dim_vehicle`, `dw.dim_area`, `dw.dim_category`. Chờ ETL/dbt kết thúc rồi mới lấy dữ liệu từ app.

## 2. Cài và mở ứng dụng

Mở PowerShell **tại thư mục gốc repository**, nơi có `README.md`, `ai/`, `sql/` và `dbt_project/`. Không dùng đường dẫn cá nhân của thành viên khác.

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

Khi đó mở **http://127.0.0.1:8502**. Địa chỉ `127.0.0.1` thuộc máy của từng người; source này không tự triển khai một website chung cho cả nhóm.

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

1. Tạo/lấy Gemini API key tại [Google AI Studio](https://aistudio.google.com/apikey). Mỗi thành viên có thể dùng key của mình.
2. Dán key vào ô mật khẩu **Gemini API key**, rồi nhấn `Enter` hoặc bấm ra ngoài ô để áp dụng.
3. Giữ model mặc định `gemini-3.5-flash-lite`, hoặc bấm **Xem mô hình khả dụng** và chọn model mà key được phép dùng. Quyền truy cập, quota và chi phí phụ thuộc tài khoản/model.
4. Nếu muốn dùng lại key trên máy này, bấm **Lưu key trên máy**. Ứng dụng lưu vào Windows Credential Manager của tài khoản Windows hiện tại; các phiên sau trên cùng tài khoản/máy có thể nạp lại key. Đây là lựa chọn chủ động, không phải yêu cầu để chạy AI.
5. Thu thanh bên lại trước khi quay video hoặc trình bày.

**Không cần sửa code hay tạo file `.env` để nhập key.** Nếu chưa lưu key trên máy, phiên mới bắt đầu với ô key trống. Nếu đã lưu, key được nạp từ Windows Credential Manager và vẫn hiển thị dưới dạng mật khẩu. Key không được ghi vào source, URL, prompt, log hay JSON tải xuống. **Xóa khóa phiên** chỉ xóa key/kết quả khỏi phiên hiện tại; **Xóa key đã lưu** xóa bản lưu của ứng dụng trên máy này và xóa key khỏi phiên hiện tại. Không gửi key qua chat hoặc đưa vào Git.

Kho lưu này gắn với tài khoản Windows đang chạy app, không đi theo Git và không tự mang sang máy thành viên khác. Ứng dụng chạy cục bộ; không dùng cơ chế ghi nhớ này để triển khai một server dùng chung không có đăng nhập. Khi quay video, giữ ô key ở trạng thái che mật khẩu.

Ứng dụng không tự đọc `.env`, `GEMINI_API_KEY` hay các biến `DBT_SQLSERVER_*`. Trong các biến môi trường cấu hình kết nối, chỉ `MSSQL_SERVER` được dùng làm giá trị mặc định cho ô SQL Server; người dùng vẫn có thể sửa trên giao diện. Khi chưa nhập key, vẫn có thể lấy DDS và đọc tab **Số liệu đối chiếu**.

## 4. Sử dụng và demo

1. **Xem toàn bộ dữ liệu:** giữ đủ khoảng ngày, để trống các lựa chọn Phương tiện, Danh mục, Khu vực và bộ lọc bổ sung; lựa chọn trống có nghĩa là tất cả.
2. **Tạo tóm tắt:** trong tab **AI phân tích**, bấm **Tạo tóm tắt và phân tích**. Kết quả gồm **Tóm tắt KPI** và **Xu hướng và khác biệt cần chú ý**.
3. **Kiểm chứng:** mở **Số liệu cho nhận xét…** dưới từng câu để xem giá trị, đơn vị, cỡ mẫu, nguồn và ngữ cảnh. Tab **Số liệu đối chiếu → Theo ngày và theo nhóm** có các bảng và biểu đồ đối chiếu.
4. **Hỏi AI:** nhập câu hỏi rồi bấm **Giải thích câu hỏi**, ví dụ: “Mức giao thông nào có thời gian giao trung bình cao nhất và thấp nhất? Chênh lệch đã tính là bao nhiêu?”. Nút tạo tóm tắt không gửi nội dung ô câu hỏi.
5. **Đổi phạm vi:** xóa câu hỏi, chọn Danh mục **Grocery**, giữ các bộ lọc khác ở tất cả, rồi tạo lại tóm tắt. Nhận xét cũ bị xóa khi bộ lọc hoặc thiết lập thay đổi; API chỉ được gọi khi bấm nút.
6. **Lưu kết quả:** mở **Thông tin kết quả và tải xuống → Tải kết quả AI (JSON)**. Model, mã phạm vi dữ liệu, template và mã dẫn chứng được giữ để kiểm tra lại. Bản số liệu tổng hợp tải riêng ở tab đối chiếu.
7. **Thử câu ngoài phạm vi:** hỏi “Dự báo doanh thu tháng sau là bao nhiêu?” bằng nút **Giải thích câu hỏi**. Ứng dụng cần báo chưa đủ số liệu để trả lời; không biến dữ liệu giao hàng thành doanh thu dự đoán. Mở các dẫn chứng khi kiểm tra nhận xét đi kèm.

Với **Số liệu đối chiếu → Theo ngày và theo nhóm → Ngày × khung giờ**, xem ma trận trung bình theo từng ngày trong tuần và khung giờ, kèm ma trận số bản ghi. Không cộng hoặc lấy trung bình các trung bình của những ô này để thay cho KPI toàn bộ dữ liệu.

Trên snapshot đã kiểm tra ngày 17/11/2026: toàn bộ Fact có **43.594 bản ghi**, trung bình **124,92 phút**, P90 **195 phút**; chênh lệch Jam–Low khoảng **46,40 phút**. Grocery có **2.687 bản ghi**, trung bình **26,54 phút**, P90 **40 phút**. Đây là mốc kiểm tra của snapshot, không phải các giá trị gán cứng; chúng có thể đổi sau khi nạp dữ liệu mới.

Đối chiếu Power BI bằng project hiện có tại [AmazonDeliveryBI.pbip](../powerbi/project/AmazonDeliveryBI.pbip). Chọn cùng ngày/phương tiện/danh mục/khu vực và bỏ các lựa chọn visual không tương ứng. **Home → Refresh** trong Power BI sau khi DDS thay đổi; dữ liệu Import không tự cập nhật cùng app AI. Nếu chọn các ngày rời rạc, dùng **Bộ lọc bổ sung → Chọn ngày riêng lẻ khi đối chiếu Power BI**; lựa chọn này thay thế khoảng ngày phía trên.

## 5. Xử lý lỗi thường gặp

| Hiện tượng | Cách kiểm tra |
|---|---|
| Không tìm thấy Python phù hợp | Cài CPython 3.11–3.13 thông thường 64-bit, mở terminal mới rồi chạy lại. `py -0p` giúp xem các bản Python đã đăng ký; tránh bản có hậu tố `t` |
| Thiếu thư viện hoặc cài dở | Chạy lại `run.ps1 -Install`. Nếu `.ai_venv` được tạo bằng Python không tương thích, dừng app và đổi tên thư mục này để tạo môi trường mới; không sửa môi trường Mage/dbt |
| Thiếu ODBC / không đọc được DDS | Kiểm tra driver đã cài, tên instance/database, dịch vụ SQL Server và quyền Windows. Kiểm tra sáu bảng `dw` ở bước 1; chỉ có staging thì cần hoàn tất dbt |
| Kết nối SQL được nhưng đọc DDS bị timeout | Kiểm tra chờ cấp bộ nhớ SQL (`RESOURCE_SEMAPHORE`) và các truy vấn đang chạy. Bản đọc DDS hiện không sắp xếp toàn bộ dữ liệu trong SQL; fingerprint tự sắp xếp ở Python. Không chỉ tăng timeout hoặc đổi sang đọc dữ liệu chưa commit |
| Nút tạo AI chưa bật | Cần có bản ghi trong phạm vi đang chọn, key đã áp dụng và tên model. Có thể xem dữ liệu trước khi nhập key |
| Key/model bị từ chối, hết quota hoặc Gemini tạm lỗi | Kiểm tra key, Internet, quota và **Xem mô hình khả dụng**. Chờ rồi chủ động thử lại nếu lỗi dịch vụ; ứng dụng không tự gọi lặp hoặc tự đổi model |
| Kết quả bị từ chối vì số/mã dẫn chứng | Phản hồi không vượt qua kiểm tra; không được hiển thị như kết quả hợp lệ. Bấm tạo lại; đối chiếu bảng số liệu nếu lỗi lặp lại |
| KPI khác Power BI | Chọn cùng bộ lọc, xóa lựa chọn trên visual và Refresh Power BI. App không tự lấy slicer/cross-highlight/drill-through từ Desktop |
| Grocery hiện “—” ở tỷ lệ vượt baseline | Measure DAX hiện dùng `COUNT` không `COALESCE`, nên trả BLANK khi không có bản ghi vượt ngưỡng. Không đọc dấu này thành mất toàn bộ dữ liệu hoặc tỷ lệ 0% |

## 6. Phạm vi và nguyên lý

| Yêu cầu mục 3.5 | Thành phần đáp ứng |
|---|---|
| Dùng LLM/dịch vụ Generative AI | Gọi Gemini `generateContent` thật bằng key nhập khi chạy |
| Tạo AI-generated Summary từ KPI | Nút **Tạo tóm tắt và phân tích** |
| Giải thích xu hướng, biến động hoặc vấn đề | Chứng cứ theo ngày và các nhóm giao thông, thời tiết, phương tiện, khu vực, danh mục, khung giờ, khoảng cách; có các chênh lệch tính sẵn |
| Dựa trên dữ liệu, có thể kiểm chứng | ID dẫn chứng, giá trị, đơn vị, cỡ mẫu, ngữ cảnh và kiểm tra phản hồi trước khi hiển thị |
| Khuyến khích hỏi bằng ngôn ngữ tự nhiên | Ô câu hỏi và nút **Giải thích câu hỏi**, theo phạm vi hiện tại |

Luồng xử lý: **DDS → Python tính KPI/bảng nhóm/chứng cứ → Gemini viết nhận xét → kiểm tra số và mã dẫn chứng → hiển thị kèm số liệu đối chiếu**.

Gemini chỉ nhận số liệu tổng hợp, không nhận từng dòng Fact, Order ID, tọa độ chính xác hoặc thông tin kết nối SQL. Ứng dụng không sinh SQL từ câu hỏi và không ghi thay đổi vào DDS. Mỗi lần lấy dữ liệu dùng một transaction đọc nhất quán rồi đóng kết nối; tránh lấy số liệu khi ETL/dbt đang dựng lại DDS.

Các giới hạn cần giữ khi trình bày:

- Chênh lệch giữa nhóm là mô tả, chưa chứng minh quan hệ nhân quả. Không có dữ liệu doanh thu/chi phí để trả lời KPI tài chính hoặc dự báo chúng.
- Mốc **195 phút** là baseline thống kê cố định, không phải SLA hay tỷ lệ giao trễ. P90 theo bộ lọc được tính lại; hai khái niệm không được dùng thay nhau.
- Nhóm ít mẫu và Unknown cần đọc cùng cỡ mẫu. Ngày không có bản ghi không chứng minh giao hàng đã dừng; các tháng có thể không đủ ngày.
- Số và mã dẫn chứng được kiểm tra, nhưng ngữ nghĩa mọi câu văn của LLM vẫn cần người xem đối chiếu. Không khẳng định hệ thống bảo đảm mọi nhận xét đều đúng.
- Khoảng cách/rating dùng các cờ hợp lệ của Fact. Coverage khoảng cách giữ riêng cách viết measure của Operational Drivers và Area & Category khi chúng khác nhau ở BLANK/0.

## 7. Kiểm thử và bàn giao source

Chạy từ root repository sau khi cài môi trường AI:

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

Kết quả kiểm tra ngày 21/11/2026: **79/79 kiểm thử đạt**, gồm đối soát DDS chỉ đọc trong 9 phạm vi; `pip check` đạt. Các test bao phủ tính KPI, cỡ mẫu hợp lệ, chứng cứ BLANK, biến động ngày, giới hạn số fact, gọi API giả lập, giao diện và lưu key. Test credential dùng key giả, không đọc hoặc sửa key thật của người chạy.

Gemini thật đã chạy thành công với toàn bộ dữ liệu kèm câu hỏi Jam–Low, tóm tắt Grocery và câu hỏi doanh thu ngoài phạm vi. Phép thử hỏi đầy đủ ngày, trung bình và cỡ mẫu của mức tăng ngày lớn nhất **chưa được tính là đạt**: có lần dịch vụ lỗi tạm thời, có lần trả mã thay thế sai và bị ứng dụng chặn. Bố cục KPI, trục biểu đồ, ma trận ngày × khung giờ và việc nạp lại key đã lưu cũng đã được kiểm tra trên giao diện.

Trước khi bàn giao/quay demo trên máy khác: mở app bằng source đã pull, lấy DDS, nhập key của người chạy, tạo summary, mở chứng cứ, hỏi một câu và đổi bộ lọc để tạo lại. Test dùng HTTP giả lập không thay thế bước gọi Gemini thật; môi trường/quota của người nhận cần kiểm tra riêng. Kết quả JSON có thể tải từ giao diện để đối chiếu, không cần lưu kết quả chạy thử vào source.

Các file cần chia sẻ nằm gọn trong `ai/`: `app.py` (giao diện), `data.py` (đọc DDS), `analytics.py` (tính số liệu), `gemini.py` (gọi API), `grounding.py` (kiểm tra dẫn chứng), `credentials.py` (adapter Windows Credential Manager, không chứa key), `__init__.py` (package), `requirements.txt`, `run.ps1`, hướng dẫn này và `tests/`. Giữ các test để kiểm tra khi dữ liệu hoặc code thay đổi.

Không đưa `.ai_venv/`, `__pycache__/`, `.env`, key, log, ảnh/chứng cứ thử nghiệm hay kết quả cá nhân tải xuống vào Git. Môi trường và cache này đã có quy tắc ignore. Pull source không mang theo database hoặc key của thành viên khác.

## Tài liệu kỹ thuật

- [Google: API keys](https://ai.google.dev/gemini-api/docs/api-key)
- [Google: generateContent REST](https://ai.google.dev/api/generate-content)
- [Google: structured outputs và giới hạn kiểm chứng ngữ nghĩa](https://ai.google.dev/gemini-api/docs/structured-output)
- [Google: danh sách model](https://ai.google.dev/api/models)
- [Microsoft: DAX COUNT và BLANK](https://learn.microsoft.com/en-us/dax/count-function-dax)
- [Streamlit: kiểm thử ứng dụng](https://docs.streamlit.io/develop/concepts/app-testing)
- [Microsoft: Windows generic credential và phạm vi lưu theo tài khoản/máy](https://learn.microsoft.com/en-us/windows/win32/api/wincred/ns-wincred-credentialw)
