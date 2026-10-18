# Hướng dẫn cho thành viên nhóm

Làm theo thứ tự. Phần A bắt buộc. Phần B chỉ cần nếu muốn **chạy web trên máy mình**.
Phần C dành cho người **sửa code**.

> Chỉ cần **xem web**, không cần cài gì: xin chủ dự án (tài khoản GitHub `koisd`) link `trycloudflare.com`
> (link chỉ mở được khi máy chủ dự án đang bật web).

---

## A. Lấy code về máy (10 phút)

1. Tạo tài khoản GitHub (nếu chưa có) và gửi **tên tài khoản** cho chủ dự án (`koisd`) để được mời vào.
2. Mở email, bấm **Accept invitation** để vào dự án `koisd/air_quality_hcm`.
3. Cài **GitHub Desktop**: <https://desktop.github.com>, đăng nhập bằng tài khoản GitHub.
4. Trong GitHub Desktop: **File → Clone repository** → chọn `koisd/air_quality_hcm`
   → chọn thư mục lưu (ví dụ `D:\project\air_quality_hcm`) → **Clone**.

Tới đây đã xem và sửa code được bằng VS Code.

---

## B. Chạy web trên máy mình (khoảng 30 phút)

Làm theo **mục 1 trong [README.md](README.md)**: cài Python + thư viện, cài PostgreSQL + PostGIS,
tải file `khong_khi.backup` ở mục **Releases** của repo rồi nạp vào, bấm đúp `chay_web.bat`.
Bảng "Gặp lỗi" ở cuối mục đó có cách sửa các lỗi hay gặp.

---

## C. Quy tắc khi sửa code

Mọi thành viên được mời đều **có quyền sửa toàn bộ code**, kể cả nhánh chính `main`.
Họ **không** xoá được dự án, không đổi cài đặt, không mời thêm người. GitHub luôn lưu
lịch sử, nên lỡ sửa sai vẫn khôi phục được. Để không giẫm chân nhau, cả nhóm thống nhất:

1. **Không sửa trực tiếp trên `main`.** Mỗi việc tạo một nhánh riêng:
   GitHub Desktop → **Current branch → New branch** → đặt tên như `giao-dien-bieu-do`.
2. Sửa code, rồi trong GitHub Desktop ghi mô tả ngắn → **Commit** → **Push origin**.
3. Bấm **Create Pull Request**. Chủ dự án xem và bấm **Merge** để gộp vào `main`.
4. Trước khi bắt đầu việc mới: chuyển về `main` → bấm **Fetch origin / Pull** để lấy
   code mới nhất của cả nhóm.

**Không đưa lên GitHub:** file `src/ee_project.txt`, mật khẩu, thư mục `data/raw`,
`data/processed` (đã được chặn sẵn trong `.gitignore`).

Phân công phần việc xem mục 11 trong báo cáo.
