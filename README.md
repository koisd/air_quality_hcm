# Giám sát ô nhiễm không khí và dự báo chất lượng không khí TP.HCM

Đồ án học phần **Trí tuệ nhân tạo và Trực quan hoá dữ liệu** — Đề tài 2.

Thu thập dữ liệu vệ tinh Sentinel-5P và khí tượng ERA5-Land qua Google Earth
Engine, huấn luyện mô hình AI dự báo 1–3 ngày, hiển thị trên WebGIS.

---

## 1. Cài đặt để chạy web (máy Windows bất kỳ)

Không cần tải lại dữ liệu vệ tinh: toàn bộ dữ liệu đã xử lý nằm trong file sao
lưu CSDL `khong_khi.backup` (~73 MB) ở mục
[Releases](https://github.com/koisd/air_quality_hcm/releases/tag/du-lieu) của repo.
Mất khoảng 30 phút, chủ yếu là thời gian tải và cài PostgreSQL.

> Chỉ muốn **xem web**, không cài gì: xin chủ dự án link `trycloudflare.com`
> (chỉ mở được khi máy chủ dự án đang bật web).

### Bước 1. Lấy code

Repo đang để **private**, phải được chủ dự án (`koisd`) mời vào trước. Sau đó:

```powershell
git clone https://github.com/koisd/air_quality_hcm.git
```

Không quen dòng lệnh thì dùng GitHub Desktop: **File → Clone repository** →
chọn `koisd/air_quality_hcm`.

### Bước 2. Cài Python và thư viện

1. Cài **Python 3.11–3.13 (64-bit)** từ <https://www.python.org/downloads/>,
   khi cài **tick ô "Add python.exe to PATH"**.
2. Mở PowerShell **trong thư mục dự án**, chạy:

```powershell
pip install -r requirements-web.txt
```

(Chỉ gồm thư viện cho web. Muốn thu thập dữ liệu / huấn luyện lại thì cài đủ
`requirements.txt`, xem mục 3.)

### Bước 3. Cài PostgreSQL + PostGIS

1. Tải bộ cài **PostgreSQL 16** (hoặc mới hơn: 17, 18 đều được) cho Windows:
   <https://www.enterprisedb.com/downloads/postgres-postgresql-downloads>
2. Cài mặc định, cổng giữ `5432`. Khi hỏi mật khẩu cho tài khoản `postgres`,
   đặt mật khẩu **chỉ gồm chữ và số** (ví dụ `postgres123`) và ghi nhớ lại.
3. Cuối quá trình cài, để tick **Stack Builder** → Finish. Trong Stack Builder
   chọn bản PostgreSQL vừa cài → **Spatial Extensions** → tick **PostGIS 3.x
   Bundle** → cài mặc định.

### Bước 4. Nạp dữ liệu

1. Vào <https://github.com/koisd/air_quality_hcm/releases/tag/du-lieu> (đăng nhập
   GitHub), tải **`khong_khi.backup`** về thư mục `Downloads`.
2. Mở PowerShell, chạy lần lượt (thay `postgres123` bằng mật khẩu ở bước 3,
   thay `16` nếu cài bản khác):

```powershell
$env:PGPASSWORD = "postgres123"
$pg = "C:\Program Files\PostgreSQL\16\bin"
& "$pg\createdb.exe" -U postgres khong_khi
& "$pg\pg_restore.exe" -U postgres -d khong_khi --no-owner "$HOME\Downloads\khong_khi.backup"
```

   Lệnh cuối chạy khoảng 20 giây – 2 phút, không báo gì là thành công.

3. Báo cho code biết cách kết nối CSDL (chạy **một lần**, rồi **đóng và mở lại**
   PowerShell / cửa sổ dòng lệnh):

```powershell
setx PG_DSN "postgresql://postgres:postgres123@localhost:5432/khong_khi"
```

### Bước 5. Mở web

Bấm đúp **`chay_web.bat`** trong thư mục dự án. Trình duyệt tự mở
<http://127.0.0.1:8000> khi web sẵn sàng. Đóng cửa sổ đen là tắt web.

Hoặc chạy tay: `cd src` rồi `python api.py`.

### Gặp lỗi

| Thông báo | Cách sửa |
|---|---|
| `'python' is not recognized` | Cài lại Python, nhớ tick "Add python.exe to PATH" |
| `Chua cai du thu vien` / `No module named ...` | Chạy lại `pip install -r requirements-web.txt` (bước 2) |
| `password authentication failed` | Sai mật khẩu trong lệnh `setx` ở bước 4.3 |
| `connection refused` / `Connection timed out` | PostgreSQL chưa chạy: mở **Services**, bật `postgresql-x64-16` |
| `type "geometry" does not exist` khi nạp | Chưa cài PostGIS (bước 3.3). Cài xong thì xoá CSDL `khong_khi` (`dropdb.exe -U postgres khong_khi`) rồi nạp lại |
| `CSDL trong` | Bước 4 chưa chạy xong |
| Web mở nhưng không có bản đồ nền | Máy không có mạng (bản đồ nền tải từ Esri) |
| Cổng 8000 đã bị dùng | `python api.py --cong 8001` rồi mở `http://127.0.0.1:8001` |

---

## 2. Máy của chủ dự án

PostgreSQL 16 + PostGIS cài dạng giải nén (không cần quyền admin) tại `D:\pgsql`:

- Dữ liệu CSDL: `D:\pgsql\data`, cổng `5433` (máy đã có PostgreSQL 18 dùng cổng
  5432), tài khoản `postgres`, không cần mật khẩu (chỉ nhận kết nối từ chính máy này).
- **Không cần tự bật**: `api.py` và `nap_csdl.py` thấy PostgreSQL chưa chạy thì
  tự gọi `pg_ctl start` (sau khi tắt máy đột ngột có thể mất 1–2 phút để khôi phục).
- Xem bảng: `D:\pgsql\pgAdmin 4\runtime\pgAdmin4.exe`, hoặc
  `D:\pgsql\bin\psql -U postgres -p 5433 -d khong_khi`.
- Tắt hẳn: `D:\pgsql\bin\pg_ctl -D D:\pgsql\data stop`
- Đổi đường dẫn qua biến môi trường `PG_BIN`, `PG_DATA`, `PG_DSN` (xem `src/config.py`).
  Trên máy khác không có `D:\pgsql` thì code tự bỏ qua bước bật máy chủ.

Tạo lại file sao lưu và cập nhật lên Releases sau khi nạp dữ liệu mới:

```powershell
D:\pgsql\bin\pg_dump -U postgres -p 5433 -Fc --no-owner -f khong_khi.backup khong_khi
gh release upload du-lieu khong_khi.backup --clobber
```

---

## 3. Thu thập dữ liệu và huấn luyện lại (không bắt buộc)

Chỉ cần khi muốn tải dữ liệu vệ tinh mới hoặc huấn luyện lại mô hình.

```bash
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### 3.1. Đăng ký Google Earth Engine (làm một lần)

1. Đăng ký tài khoản tại <https://earthengine.google.com/signup> — miễn phí,
   dùng Gmail cá nhân hoặc email sinh viên.
2. Tạo một project trên <https://console.cloud.google.com> và bật
   **Earth Engine API** cho project đó.
3. Đăng nhập từ máy:

   ```bash
   earthengine authenticate
   ```

4. Ghi mã project vào `src/ee_project.txt` (một dòng duy nhất). File này **không**
   đưa lên GitHub, mỗi người dùng project của mình. Hoặc đặt biến môi trường
   `EE_PROJECT` thay cho file.

### 3.2. Tải lại sau khi tắt máy

Script tải theo từng tháng và tự bỏ qua tháng đã có, nên chỉ cần chạy lại:

```bash
bash src/tai_tat_ca.sh
```

Xem đã tải được bao nhiêu:

```bash
ls data/raw/*.csv | wc -l
```

### 3.3. Thu thập và huấn luyện

```bash
cd src
python make_grid.py                                     # nếu chưa chạy
python fetch_gee.py --chi-so all --tu 2018-07 --den 2026-09
python fetch_gee.py --khi-tuong  --tu 2018-07 --den 2026-09
python preprocess.py
python train.py --epochs 25
python predict.py
python kich_ban.py        # mô hình kịch bản thời tiết ngày mai (~2 phút)
python tai_anh.py         # ảnh Sentinel-2 màu thật cho từng ô (web/static/anh)
python nap_csdl.py        # nạp tất cả vào PostgreSQL (~1,5 phút)
python api.py             # mở http://127.0.0.1:8000
```

Sau khi huấn luyện hoặc dự báo lại, chỉ cần `python nap_csdl.py --chi-du-bao`
để thêm lần chạy mới vào bảng `mo_hinh` và `du_bao` (các lần chạy cũ được giữ
lại để sau này đối chiếu dự báo với thực tế).

`fetch_gee.py` chạy theo từng tháng và **tự bỏ qua tháng đã tải**, nên có thể
dừng giữa chừng rồi chạy lại mà không mất công. Toàn bộ giai đoạn 2018–2026 mất
khá lâu, nên chạy thử một năm trước:

```bash
python fetch_gee.py --chi-so no2 --tu 2025-01 --den 2025-12
```

---

## 4. Cấu trúc thư mục

```
air_quality_hcm/
├── src/
│   ├── config.py           Cấu hình chung: phạm vi, mã dataset, tham số mô hình
│   ├── make_grid.py        Tải ranh giới TP.HCM, chia lưới 5×5 km
│   ├── fetch_gee.py        Thu thập Sentinel-5P + ERA5-Land từ GEE
│   ├── preprocess.py       Làm sạch, nội suy, sinh đặc trưng
│   ├── train.py            Huấn luyện & so sánh XGBoost / LSTM / GRU
│   ├── predict.py          Sinh bảng dự báo t+1…t+3
│   ├── kich_ban.py         Mô hình kịch bản: thời tiết ngày mai thay đổi → dự báo t+1
│   ├── tai_anh.py          Tải ảnh Sentinel-2 màu thật cho từng ô lưới
│   ├── db.py               Kết nối PostgreSQL, tự bật máy chủ nếu chưa chạy
│   ├── nap_csdl.py         Nạp ô lưới, quan trắc, khí tượng, mô hình, dự báo vào CSDL
│   └── api.py              Backend FastAPI (đọc từ PostgreSQL + PostGIS)
├── sql/schema.sql          Lược đồ 7 bảng (mục 8.4 báo cáo)
├── web/
│   ├── index.html          Giao diện WebGIS (Leaflet + Chart.js)
│   └── static/anh/         Ảnh Sentinel-2 màu thật của từng ô (tai_anh.py)
├── data/
│   ├── boundary/           Ranh giới + lưới + ảnh xem trước
│   ├── raw/                CSV thô từ GEE (một file mỗi tháng)
│   └── processed/          Bảng đã xử lý (.parquet); chỉ 2 file cho kịch bản thời tiết lên GitHub
├── models/                 Mô hình đã huấn luyện + ket_qua.json
├── chay_web.bat            Bấm đúp để mở web
├── requirements-web.txt    Thư viện chỉ để chạy web
└── requirements.txt        Thư viện đầy đủ (thu thập + huấn luyện)
```

### Cơ sở dữ liệu

| Bảng | Số dòng | Ghi chú |
|---|---|---|
| `quan_trac` | ~4,6 triệu | ô × ngày × chỉ số, cột `noi_suy` đánh dấu giá trị nội suy |
| `khi_tuong` | ~0,94 triệu | nhiệt độ, tốc độ gió, lượng mưa |
| `o_luoi` | 318 | ranh giới `geometry(Polygon, 4326)`, chỉ mục GIST |
| `du_bao` | 1.908 / lần chạy | 318 ô × 2 chỉ số × 3 ngày |
| `mo_hinh` | 18 / lần huấn luyện | 2 chỉ số × 3 mô hình × 3 tầm, kèm RMSE/MAE/MAPE/R² |
| `chi_so`, `nguong_canh_bao` | 5, 15 | danh mục |

PostGIS được dùng thật ở hai chỗ: `/api/luoi` trả GeoJSON bằng `ST_AsGeoJSON`,
và khi bấm lên bản đồ, `/api/o-tai-diem` tìm ô chứa toạ độ bằng `ST_Contains`.

---

## 5. Những điểm cần nắm khi bảo vệ

| Câu hỏi | Trả lời |
|---|---|
| Vệ tinh đo gì? | **Mật độ cột khí** (mol/m²) — tổng lượng khí trong cả cột không khí, **không phải** nồng độ mặt đất (µg/m³) |
| Bao lâu đo một lần? | 1 lần/ngày, khoảng **13h30** giờ địa phương (quỹ đạo đồng bộ mặt trời) |
| Dữ liệu từ khi nào? | NO₂ và CO từ **28/6/2018**, AER_AI 4/7/2018, O₃ 8/9/2018, SO₂ 5/12/2018 |
| Mây che thì sao? | Mất dữ liệu ngày đó. Mùa mưa (tháng 5–11) mất nhiều. Xử lý bằng **nội suy tuyến tính**, tối đa 5 ngày liên tiếp |
| Sao chia ô lưới mà không theo phường? | Pixel Sentinel-5P là 5,5×3,5 km (~19 km²), **lớn hơn đa số phường**. Gom theo phường sẽ trùng giá trị. Lưới còn giữ chuỗi liền mạch khi địa giới đổi ngày 1/7/2025 |
| Phạm vi không gian? | TP.HCM sau sáp nhập (gồm Bình Dương, Bà Rịa–Vũng Tàu), **6.709 km² đất liền**, chia thành **318 ô** 5×5 km. Không tính Côn Đảo vì cách đất liền ~200 km |
| Dự báo những chỉ số nào? | **NO₂** (đủ 3 mô hình) và **Aerosol Index**. CO, SO₂, O₃ chỉ hiển thị bản đồ |
| Chia dữ liệu thế nào? | Theo **thứ tự thời gian** (70/15/15), không xáo trộn, để tránh rò rỉ thông tin tương lai vào tập huấn luyện |

---

## 6. Ghi chú kỹ thuật

- **Ranh giới**: lấy từ GADM 4.1 cấp tỉnh rồi ghép 3 tỉnh cũ. Không dùng ranh
  giới OpenStreetMap vì polygon của OSM bao gồm cả vùng biển (36.000 km²).
- **ERA5-Land có độ trễ cập nhật**, không hợp cho dự báo thời gian thực. Khi
  triển khai thật nên thay bằng `NOAA/GFS0P25` (dữ liệu dự báo khí tượng).
- **Gió** lưu ở dạng hai thành phần `u`, `v`; `preprocess.py` gộp lại thành tốc
  độ gió tổng hợp. Nhiệt độ đổi từ Kelvin sang °C, lượng mưa từ m sang mm.
- **Ngưỡng cảnh báo** hiện tính theo phân vị 60% và 80% của chính chuỗi dữ liệu,
  vì giá trị mật độ cột không có ngưỡng AQI chính thức. Nếu cần ngưỡng chuẩn
  phải hiệu chỉnh về nồng độ mặt đất trước.
