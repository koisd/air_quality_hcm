# Giám sát ô nhiễm không khí và dự báo chất lượng không khí TP.HCM

Đồ án học phần **Trí tuệ nhân tạo và Trực quan hoá dữ liệu** — Đề tài 2.

Thu thập dữ liệu vệ tinh Sentinel-5P và khí tượng ERA5-Land qua Google Earth
Engine, huấn luyện mô hình AI dự báo 1–3 ngày, hiển thị trên WebGIS.

---

> **Thành viên nhóm mới:** đọc [HUONG_DAN_NHOM.md](HUONG_DAN_NHOM.md) trước.
>
> **Mở web nhanh:** bấm đúp `chay_web.bat` (tự bật CSDL và mở trình duyệt). Đóng cửa sổ đen là tắt web.

## 1. Cài đặt

```bash
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### 1b. Cơ sở dữ liệu PostgreSQL 16 + PostGIS

Đã cài sẵn dạng giải nén (không cần quyền admin) tại `D:\pgsql`:

- Dữ liệu CSDL: `D:\pgsql\data`, cổng `5433` (máy đã có PostgreSQL 18 dùng cổng 5432), tài khoản `postgres`, không cần mật khẩu (chỉ nhận kết nối từ chính máy này)
- CSDL tên `khong_khi`
- **Không cần tự bật**: `api.py` và `nap_csdl.py` thấy PostgreSQL chưa chạy thì
  tự gọi `pg_ctl start`.
- Xem bảng bằng giao diện: mở `D:\pgsql\pgAdmin 4\runtime\pgAdmin4.exe`, hoặc
  dòng lệnh `D:\pgsql\bin\psql -U postgres -d khong_khi`.
- Tắt hẳn: `D:\pgsql\bin\pg_ctl -D D:\pgsql\data stop`

**Thành viên nhóm:** không cần làm theo mục này, xem
[HUONG_DAN_NHOM.md](HUONG_DAN_NHOM.md) (cài PostgreSQL thông thường + nạp file
`khong_khi.backup`, không cần tải lại dữ liệu từ GEE).

Cài lại trên máy khác: tải bản zip PostgreSQL 16 (EnterpriseDB, "binaries") và
`postgis-bundle-pg16-*.zip` (download.osgeo.org/postgis/windows/pg16), giải nén
PostGIS đè vào thư mục PostgreSQL, rồi chạy
`initdb -D <thu_muc>\data -U postgres -W -E UTF8`. Đổi đường dẫn qua biến môi
trường `PG_BIN`, `PG_DATA`, `PG_DSN` (xem `src/config.py`).

## 2. Chạy với dữ liệu thật

### 2.1. Đăng ký Google Earth Engine (làm một lần)

1. Đăng ký tài khoản tại <https://earthengine.google.com/signup> — miễn phí,
   dùng Gmail cá nhân hoặc email sinh viên.
2. Tạo một project trên <https://console.cloud.google.com> và bật
   **Earth Engine API** cho project đó.
3. Đăng nhập từ máy:

   ```bash
   earthengine authenticate
   ```

4. Ghi mã project vào `src/ee_project.txt` (một dòng duy nhất, không xuống
   dòng thừa). File này đã có sẵn nên **không cần làm lại**. Nếu cần đổi
   project thì sửa file đó, hoặc đặt biến môi trường `EE_PROJECT` để ghi đè.

### 2.1b. Tải lại sau khi tắt máy

Script tải theo từng tháng và tự bỏ qua tháng đã có, nên chỉ cần chạy lại:

```bash
bash src/tai_tat_ca.sh
```

Xem đã tải được bao nhiêu:

```bash
ls data/raw/*.csv | wc -l
```

### 2.2. Thu thập và huấn luyện

```bash
cd src
python make_grid.py                                     # nếu chưa chạy
python fetch_gee.py --chi-so all --tu 2018-07 --den 2026-09
python fetch_gee.py --khi-tuong  --tu 2018-07 --den 2026-09
python preprocess.py
python train.py --epochs 25
python predict.py
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

## 3. Cấu trúc thư mục

```
air_quality_hcm/
├── src/
│   ├── config.py           Cấu hình chung: phạm vi, mã dataset, tham số mô hình
│   ├── make_grid.py        Tải ranh giới TP.HCM, chia lưới 5×5 km
│   ├── fetch_gee.py        Thu thập Sentinel-5P + ERA5-Land từ GEE
│   ├── preprocess.py       Làm sạch, nội suy, sinh đặc trưng
│   ├── train.py            Huấn luyện & so sánh XGBoost / LSTM / GRU
│   ├── predict.py          Sinh bảng dự báo t+1…t+3
│   ├── db.py               Kết nối PostgreSQL, tự bật máy chủ nếu chưa chạy
│   ├── nap_csdl.py         Nạp ô lưới, quan trắc, khí tượng, mô hình, dự báo vào CSDL
│   └── api.py              Backend FastAPI (đọc từ PostgreSQL + PostGIS)
├── sql/schema.sql          Lược đồ 7 bảng (mục 8.4 báo cáo)
├── web/index.html          Giao diện WebGIS (Leaflet + Chart.js)
├── data/
│   ├── boundary/           Ranh giới + lưới + ảnh xem trước
│   ├── raw/                CSV thô từ GEE (một file mỗi tháng)
│   └── processed/          Bảng đã xử lý (.parquet) + bảng dự báo
└── models/                 Mô hình đã huấn luyện + ket_qua.json
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

## 4. Những điểm cần nắm khi bảo vệ

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

## 5. Ghi chú kỹ thuật

- **Ranh giới**: lấy từ GADM 4.1 cấp tỉnh rồi ghép 3 tỉnh cũ. Không dùng ranh
  giới OpenStreetMap vì polygon của OSM bao gồm cả vùng biển (36.000 km²).
- **ERA5-Land có độ trễ cập nhật**, không hợp cho dự báo thời gian thực. Khi
  triển khai thật nên thay bằng `NOAA/GFS0P25` (dữ liệu dự báo khí tượng).
- **Gió** lưu ở dạng hai thành phần `u`, `v`; `preprocess.py` gộp lại thành tốc
  độ gió tổng hợp. Nhiệt độ đổi từ Kelvin sang °C, lượng mưa từ m sang mm.
- **Ngưỡng cảnh báo** hiện tính theo phân vị 60% và 80% của chính chuỗi dữ liệu,
  vì giá trị mật độ cột không có ngưỡng AQI chính thức. Nếu cần ngưỡng chuẩn
  phải hiệu chỉnh về nồng độ mặt đất trước.
