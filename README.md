# Giám sát & dự báo chất lượng không khí TP.HCM

Hệ thống WebGIS theo dõi và dự báo ô nhiễm không khí trên toàn địa bàn
TP.HCM (sau sáp nhập 01/7/2025) từ dữ liệu vệ tinh **Sentinel-5P** và khí tượng
**ERA5-Land**, dùng mô hình AI dự báo trước **1–3 ngày**.

**Tính năng chính**

- **Bản đồ ô nhiễm theo ngày** cho 5 chỉ số (NO₂, CO, SO₂, O₃, Aerosol Index)
  trên lưới 318 ô 5 × 5 km, dữ liệu từ 07/2018 đến 09/2026.
- **Dự báo 1–3 ngày** cho NO₂ và Aerosol Index, kèm mức cảnh báo.
- **Chi tiết từng khu vực**: bấm lên bản đồ để xem chuỗi lịch sử, dự báo và
  ảnh vệ tinh Sentinel-2 màu thật của ô đó.
- **Mô phỏng kịch bản**: thay đổi thời tiết ngày mai (gió, mưa, nhiệt độ) hoặc
  độ phủ cây xanh (NDVI) và xem mức ô nhiễm dự kiến thay đổi ra sao.
- **API mở** (FastAPI) cho mọi dữ liệu trên bản đồ, kèm bảng so sánh sai số
  các mô hình XGBoost, LSTM, GRU.

---

## Cài đặt

**Yêu cầu:** Windows 10/11 64-bit, ~2 GB ổ trống, có kết nối Internet khi cài.
Không cần quyền quản trị, không cần cài sẵn Python hay PostgreSQL.

1. **Tải về:** trên trang này bấm **Code → Download ZIP**, rồi giải nén
   (chuột phải → *Extract All*). Nên giải nén vào thư mục có đường dẫn ngắn,
   ví dụ `C:\GiamSatKhongKhi`.
2. **Cài đặt:** mở thư mục vừa giải nén, bấm đúp **`cai_dat.bat`**.
   Bộ cài tự làm mọi việc, khoảng 5–15 phút tuỳ tốc độ mạng:

   | Bước | Nội dung |
   |---|---|
   | 1 | Tìm Python 3.10–3.13; nếu chưa có thì tự cài Python 3.12 |
   | 2 | Tạo môi trường Python riêng và cài thư viện |
   | 3 | Tải PostgreSQL 16 + PostGIS bản chạy trong thư mục (~165 MB) |
   | 4 | Khởi tạo cơ sở dữ liệu và nạp toàn bộ dữ liệu (~73 MB) |

   Khi thấy dòng **`[5/5] Hoàn tất`** là xong.
3. **Mở ứng dụng:** bấm đúp **`chay_web.bat`**. Trình duyệt tự mở
   <http://127.0.0.1:8000> khi ứng dụng sẵn sàng. Đóng cửa sổ đen là tắt.

> Nếu Windows hiện *"Windows protected your PC"*, bấm **More info → Run anyway**.
> Đây là cảnh báo chung cho mọi tệp tải từ Internet.

Mọi thành phần được cài vào thư mục `runtime\` bên trong thư mục ứng dụng và
không ảnh hưởng tới phần mềm khác trên máy (kể cả PostgreSQL đã cài sẵn, nếu có).
**Gỡ cài đặt:** tắt ứng dụng rồi xoá cả thư mục.

### Xử lý sự cố

| Hiện tượng | Cách xử lý |
|---|---|
| Bộ cài báo lỗi khi tải | Kiểm tra mạng rồi chạy lại `cai_dat.bat`; các bước đã xong sẽ được bỏ qua |
| `chay_web.bat` báo *chưa được cài đặt* | Chạy `cai_dat.bat` trước |
| Mở lần đầu sau khi máy tắt đột ngột thì chờ lâu | Cơ sở dữ liệu đang tự khôi phục, chờ 1–2 phút |
| Bản đồ không có nền | Máy không có mạng (nền bản đồ tải từ Esri) |
| Cổng 8000 đã bị dùng | Mở cửa sổ lệnh trong thư mục `src`, chạy `..\runtime\venv\Scripts\python api.py --cong 8001`, rồi mở <http://127.0.0.1:8001> |
| Cần cài lại dữ liệu từ đầu | Xoá thư mục `runtime\data` rồi chạy lại `cai_dat.bat` |

---

## Hướng dẫn sử dụng

- **Chọn chỉ số và ngày** ở thanh bên trái; bản đồ tô màu theo giá trị từng ô.
  Các ngày mùa mưa có thể bị mây che (ô trắng); chọn ngày mùa khô
  (tháng 12–4) để có bản đồ đầy đủ.
- **Bấm vào một ô** để xem lịch sử, dự báo 3 ngày tới và ảnh vệ tinh của khu vực.
- **Kịch bản thời tiết ngày mai**: chọn nhanh *Bình thường / Gió mạnh / Mưa lớn /
  Nắng nóng, lặng gió / Trồng thêm cây xanh*, hoặc kéo các thanh trượt, rồi bật
  *Hiện kịch bản trên bản đồ* để xem mức thay đổi theo từng ô.

---

## Dữ liệu và mô hình

| Hạng mục | Chi tiết |
|---|---|
| Vệ tinh | Sentinel-5P TROPOMI (Copernicus), 1 lần/ngày khoảng 13h30, đo **mật độ cột khí** (mol/m²), không phải nồng độ mặt đất |
| Khí tượng | ERA5-Land: nhiệt độ, tốc độ gió, lượng mưa |
| Cây xanh | NDVI từ Sentinel-2, độ phân giải 10 m |
| Phạm vi | TP.HCM sau sáp nhập (gồm Bình Dương, Bà Rịa–Vũng Tàu), 6.709 km² đất liền, không gồm Côn Đảo |
| Lưới | 318 ô 5 × 5 km. Pixel Sentinel-5P là 5,5 × 3,5 km, lớn hơn phần lớn phường/xã, nên dùng lưới đều thay cho ranh giới hành chính |
| Thời gian | NO₂, CO từ 28/6/2018; AER_AI 4/7/2018; O₃ 8/9/2018; SO₂ 5/12/2018 |
| Xử lý thiếu | Ngày bị mây che được nội suy tuyến tính, tối đa 5 ngày liên tiếp |
| Mô hình | XGBoost, LSTM, GRU; chia dữ liệu theo thời gian 70/15/15, không xáo trộn |
| Độ chính xác (NO₂, t+1) | LSTM R² = 0,77; GRU 0,77; XGBoost 0,75 |
| Ngưỡng cảnh báo | Theo phân vị 60% và 80% của chuỗi dữ liệu, vì mật độ cột chưa có ngưỡng AQI chính thức |

Cơ sở dữ liệu PostgreSQL + PostGIS gồm 7 bảng:

| Bảng | Số dòng | Ghi chú |
|---|---|---|
| `quan_trac` | ~4,6 triệu | ô × ngày × chỉ số, cột `noi_suy` đánh dấu giá trị nội suy |
| `khi_tuong` | ~0,94 triệu | nhiệt độ, tốc độ gió, lượng mưa |
| `o_luoi` | 318 | ranh giới `geometry(Polygon, 4326)`, chỉ mục GIST |
| `du_bao` | 1.908 / lần chạy | 318 ô × 2 chỉ số × 3 ngày |
| `mo_hinh` | 18 / lần huấn luyện | 2 chỉ số × 3 mô hình × 3 tầm, kèm RMSE/MAE/MAPE/R² |
| `chi_so`, `nguong_canh_bao` | 5, 15 | danh mục |

PostGIS dùng để trả lưới dạng GeoJSON (`ST_AsGeoJSON`) và tìm ô chứa điểm bấm
trên bản đồ (`ST_Contains`).

### API

Máy chủ FastAPI tại `http://127.0.0.1:8000`, tài liệu tương tác ở `/docs`.

| Endpoint | Chức năng |
|---|---|
| `GET /api/thong-tin` | Khoảng ngày, danh mục chỉ số, ngưỡng cảnh báo |
| `GET /api/luoi` | Ranh giới các ô lưới (GeoJSON) |
| `GET /api/o-tai-diem?kinh_do=&vi_do=` | Ô lưới chứa toạ độ |
| `GET /api/ban-do?chi_so=&ngay=` | Giá trị từng ô trong một ngày |
| `GET /api/lich-su?id_o=&chi_so=` | Chuỗi lịch sử của một ô |
| `GET /api/du-bao?id_o=&chi_so=` | Dự báo t+1…t+3 mới nhất |
| `GET /api/danh-gia` | So sánh sai số các mô hình |
| `GET /api/kich-ban?chi_so=&luong_mua=&toc_do_gio=&nhiet_do=&ndvi_doi=` | Dự báo t+1 theo kịch bản thời tiết, cây xanh |

---

## Cấu trúc thư mục

```
├── cai_dat.bat / cai_dat.ps1   Bộ cài đặt
├── chay_web.bat                Mở ứng dụng
├── src/
│   ├── api.py                  Máy chủ FastAPI (đọc PostgreSQL + PostGIS)
│   ├── config.py               Cấu hình chung: phạm vi, dataset, tham số mô hình
│   ├── db.py                   Kết nối CSDL, tự khởi động PostgreSQL khi cần
│   ├── make_grid.py            Ranh giới TP.HCM, chia lưới 5 × 5 km
│   ├── fetch_gee.py            Thu thập Sentinel-5P, ERA5-Land, NDVI từ Google Earth Engine
│   ├── preprocess.py           Làm sạch, nội suy, sinh đặc trưng
│   ├── them_bien.py            Thêm NDVI và trung bình ô lân cận
│   ├── train.py                Huấn luyện, so sánh XGBoost / LSTM / GRU
│   ├── predict.py              Sinh dự báo t+1…t+3
│   ├── kich_ban.py             Mô hình kịch bản thời tiết, cây xanh
│   ├── phan_tich.py            Phân tích quan hệ giữa các chất và các yếu tố đầu vào
│   ├── tai_anh.py              Ảnh Sentinel-2 màu thật cho từng ô
│   └── nap_csdl.py             Nạp dữ liệu vào PostgreSQL
├── sql/schema.sql              Lược đồ CSDL
├── web/                        Giao diện (Leaflet + Chart.js), ảnh từng ô
├── data/boundary/              Ranh giới và lưới
├── models/                     Mô hình đã huấn luyện, kết quả đánh giá
├── requirements-web.txt        Thư viện để chạy ứng dụng
└── requirements.txt            Thư viện đầy đủ (thu thập + huấn luyện)
```

---

## Dành cho nhà phát triển

### Dùng PostgreSQL có sẵn trên máy

Thay cho bước 3–4 của bộ cài: cài PostgreSQL 16+ kèm PostGIS 3.x, tải
`khong_khi.backup` ở mục [Releases](https://github.com/koisd/air_quality_hcm/releases/tag/du-lieu), rồi:

```powershell
createdb -U postgres khong_khi
pg_restore -U postgres -d khong_khi --no-owner khong_khi.backup
setx PG_DSN "postgresql://postgres:<mật_khẩu>@localhost:5432/khong_khi"
pip install -r requirements-web.txt
cd src; python api.py
```

Các biến môi trường `PG_DSN`, `PG_BIN`, `PG_DATA` ghi đè cấu hình mặc định
(xem `src/config.py`).

### Thu thập dữ liệu và huấn luyện lại

```bash
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu
earthengine authenticate
```

Ghi mã Google Cloud project đã bật Earth Engine API vào `src/ee_project.txt`
(hoặc biến môi trường `EE_PROJECT`), rồi:

```bash
cd src
python make_grid.py
python fetch_gee.py --chi-so all --tu 2018-07 --den 2026-09
python fetch_gee.py --khi-tuong  --tu 2018-07 --den 2026-09
python fetch_gee.py --ndvi       --tu 2018-07 --den 2026-09
python preprocess.py
python them_bien.py
python train.py --epochs 25
python predict.py
python kich_ban.py
python tai_anh.py
python nap_csdl.py            # lần sau chỉ cần: python nap_csdl.py --chi-du-bao
```

`fetch_gee.py` tải theo từng tháng và tự bỏ qua tháng đã có, nên có thể dừng
rồi chạy tiếp (`bash src/tai_tat_ca.sh` chạy toàn bộ).

### Ghi chú kỹ thuật

- Ranh giới lấy từ GADM 4.1 cấp tỉnh, ghép 3 tỉnh cũ (polygon OpenStreetMap
  gồm cả vùng biển, ~36.000 km²).
- ERA5-Land cập nhật trễ vài ngày; khi chạy thời gian thực nên thay bằng
  dữ liệu dự báo khí tượng `NOAA/GFS0P25`, và Sentinel-5P OFFL bằng NRTI.
- Gió lưu dạng hai thành phần `u`, `v`, gộp thành tốc độ gió; nhiệt độ đổi
  K → °C, lượng mưa m → mm.

---

## Nguồn dữ liệu và thành phần bên thứ ba

Dữ liệu Copernicus Sentinel-5P, Sentinel-2 (ESA) và ERA5-Land (ECMWF) truy cập qua
Google Earth Engine; ranh giới hành chính GADM 4.1; bản đồ nền Esri World Street Map.
Bộ cài kèm PostgreSQL (PostgreSQL License) và PostGIS (GPL v2); giấy phép nằm trong
`runtime\pgsql` sau khi cài.
