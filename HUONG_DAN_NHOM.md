# Hướng dẫn cho thành viên nhóm

Làm theo thứ tự. Phần A bắt buộc. Phần B chỉ cần nếu muốn **chạy web trên máy mình**.
Phần C dành cho người **sửa code**.

> Chỉ cần **xem web**, không cần cài gì: xin nhóm trưởng link `trycloudflare.com`
> (link chỉ mở được khi máy nhóm trưởng đang bật web).

---

## A. Lấy code về máy (10 phút)

1. Tạo tài khoản GitHub (nếu chưa có) và gửi **tên tài khoản** cho nhóm trưởng.
2. Mở email, bấm **Accept invitation** để vào dự án `koisd/air_quality_hcm`.
3. Cài **GitHub Desktop**: <https://desktop.github.com>, đăng nhập bằng tài khoản GitHub.
4. Trong GitHub Desktop: **File → Clone repository** → chọn `koisd/air_quality_hcm`
   → chọn thư mục lưu (ví dụ `D:\project\air_quality_hcm`) → **Clone**.

Tới đây đã xem và sửa code được bằng VS Code.

---

## B. Chạy web trên máy mình (khoảng 30 phút)

### B1. Cài Python

- Tải Python 3.11 trở lên tại <https://www.python.org/downloads/>.
- Khi cài **nhớ tick ô "Add python.exe to PATH"**.
- Mở **PowerShell** trong thư mục dự án, cài thư viện:

```powershell
# Chỉ để chạy web (nhẹ, nhanh):
pip install fastapi "uvicorn[standard]" "psycopg[binary]"

# Nếu muốn thu thập dữ liệu / huấn luyện lại mô hình thì cài đủ:
# pip install -r requirements.txt
```

### B2. Cài PostgreSQL 16 + PostGIS

1. Tải bộ cài **PostgreSQL 16** cho Windows:
   <https://www.enterprisedb.com/downloads/postgres-postgresql-downloads>
2. Cài với mặc định. Khi hỏi **mật khẩu** cho tài khoản `postgres`, đặt mật khẩu
   **đơn giản, chỉ gồm chữ và số** (ví dụ `postgres123`) và **ghi nhớ lại**.
   Cổng giữ nguyên `5432`.
3. Cuối quá trình cài, để tick **Stack Builder** rồi bấm Finish. Trong Stack Builder:
   chọn `PostgreSQL 16` → mục **Spatial Extensions** → tick **PostGIS 3.x Bundle**
   → Next và cài với mặc định.

### B3. Nạp dữ liệu

1. Tải file **`khong_khi.backup`** (~73 MB) từ link Google Drive nhóm trưởng gửi,
   để vào thư mục `Downloads`.
2. Mở PowerShell, chạy từng lệnh (thay `postgres123` bằng mật khẩu của bạn ở bước B2):

```powershell
$env:PGPASSWORD = "postgres123"
$pg = "C:\Program Files\PostgreSQL\16\bin"
& "$pg\createdb.exe" -U postgres khong_khi
& "$pg\pg_restore.exe" -U postgres -d khong_khi --no-owner "$HOME\Downloads\khong_khi.backup"
```

Lệnh cuối chạy khoảng 1–2 phút, không báo gì là thành công.

3. Báo cho code biết cách kết nối (chạy **một lần**, rồi **đóng và mở lại** PowerShell):

```powershell
setx PG_DSN "postgresql://postgres:postgres123@localhost:5432/khong_khi"
```

### B4. Mở web

Bấm đúp file **`chay_web.bat`** trong thư mục dự án. Khoảng 10 giây sau trình duyệt
tự mở <http://127.0.0.1:8000>. Đóng cửa sổ đen là tắt web.

**Gặp lỗi?**

| Thông báo | Cách sửa |
|---|---|
| `'python' is not recognized` | Cài lại Python, nhớ tick "Add to PATH" |
| `No module named fastapi` | Chạy lại lệnh `pip install` ở bước B1 |
| `password authentication failed` | Sai mật khẩu trong lệnh `setx` ở bước B3 |
| `type "geometry" does not exist` khi nạp | Chưa cài PostGIS (bước B2.3). Cài xong thì xoá CSDL `khong_khi` rồi nạp lại |
| `CSDL trong` | Bước B3 chưa chạy xong |

---

## C. Quy tắc khi sửa code

Mọi thành viên được mời đều **có quyền sửa toàn bộ code**, kể cả nhánh chính `main`.
Họ **không** xoá được dự án, không đổi cài đặt, không mời thêm người. GitHub luôn lưu
lịch sử, nên lỡ sửa sai vẫn khôi phục được. Để không giẫm chân nhau, cả nhóm thống nhất:

1. **Không sửa trực tiếp trên `main`.** Mỗi việc tạo một nhánh riêng:
   GitHub Desktop → **Current branch → New branch** → đặt tên như `giao-dien-bieu-do`.
2. Sửa code, rồi trong GitHub Desktop ghi mô tả ngắn → **Commit** → **Push origin**.
3. Bấm **Create Pull Request**. Nhóm trưởng xem và bấm **Merge** để gộp vào `main`.
4. Trước khi bắt đầu việc mới: chuyển về `main` → bấm **Fetch origin / Pull** để lấy
   code mới nhất của cả nhóm.

**Không đưa lên GitHub:** file `src/ee_project.txt`, mật khẩu, thư mục `data/raw`,
`data/processed` (đã được chặn sẵn trong `.gitignore`).

Phân công phần việc xem mục 11 trong báo cáo.
