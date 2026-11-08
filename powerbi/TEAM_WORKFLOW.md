# Quy trình cộng tác Power BI

## Nguyên tắc

- `main` luôn là phiên bản tích hợp ổn định.
- Mỗi thành viên làm trên một branch và chỉ chỉnh trang được giao.
- Chỉ leader sửa semantic model, Power Query, relationship, theme và thành phần dùng chung.
- Không merge các file `.pbix`. Git chỉ merge project `.pbip`/PBIR dạng văn bản.
- Không đổi tên, xóa, tạo mới hoặc sắp xếp lại trang khi chưa thống nhất với leader.

## Phân nhánh đề xuất

```text
feature/page-1-overview
feature/page-2-delivery
feature/page-3-customer
feature/page-4-geography
```

Tên branch có thể đổi theo tên thật của bốn trang.

## Quy trình thành viên

```bash
git switch main
git pull origin main
git switch -c feature/page-x
```

Sau đó mở file `.pbip` trong `powerbi/project` bằng Power BI Desktop, chỉnh đúng trang được giao và Save.

Kiểm tra thay đổi trước khi commit:

```bash
git status
git diff --stat
```

Commit và push:

```bash
git add powerbi/project
git commit -m "feat(powerbi): complete page x"
git push -u origin feature/page-x
```

## Quy trình leader merge

Merge từng branch một:

```bash
git switch main
git pull origin main
git merge --no-ff feature/page-x
```

Sau mỗi lần merge:

1. Mở file `.pbip` bằng Power BI Desktop.
2. Kiểm tra trang vừa merge, slicer, interaction, tooltip và navigation.
3. Refresh dữ liệu và sửa lỗi nếu có.
4. Chỉ merge branch tiếp theo sau khi project mở bình thường.

Nếu `pages.json` conflict chỉ vì thứ tự/trang active, ưu tiên phiên bản trên `main`, sau đó sắp xếp lại bằng Power BI Desktop. Không tự đổi tên thư mục page có ID kỹ thuật.

## Đóng gói bản cuối

Khi bốn trang đã được merge và kiểm thử, mở `.pbip` trên `main`, chọn **File > Save As** và lưu bản bàn giao vào:

```text
powerbi/pbix/AmazonDeliveryBI_Final.pbix
```

PBIP tiếp tục là mã nguồn; PBIX là file bàn giao/publish.
