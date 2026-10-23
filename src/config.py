# -*- coding: utf-8 -*-
"""Cau hinh chung cho toan bo du an."""
import os
import sys
from pathlib import Path

# Console Windows mac dinh dung cp1252, khong in duoc tieng Viet -> ep UTF-8
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent

# Ma project Google Cloud da bat Earth Engine API.
# Uu tien bien moi truong EE_PROJECT, neu khong co thi doc file src/ee_project.txt
_f_project = Path(__file__).resolve().parent / "ee_project.txt"
EE_PROJECT = (os.environ.get("EE_PROJECT", "").strip()
              or (_f_project.read_text(encoding="utf-8").strip()
                  if _f_project.exists() else ""))
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
BOUNDARY = DATA / "boundary"
MODELS = ROOT / "models"
for _d in (RAW, PROCESSED, BOUNDARY, MODELS):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------- Pham vi
# Hop bao TP.HCM sau sap nhap 01/7/2025 (phan dat lien, khong gom Con Dao).
# Con Dao nam cach xa ~200 km ve phia nam nen tach rieng neu can.
BBOX = (106.30, 10.30, 107.62, 11.50)   # lon_min, lat_min, lon_max, lat_max

TEN_TINH = "Thành phố Hồ Chí Minh"
CRS_WGS84 = "EPSG:4326"
CRS_UTM = "EPSG:32648"        # UTM zone 48N - dung de chia luoi theo met
GRID_SIZE_M = 5000            # canh o luoi 5 km

BOUNDARY_FILE = BOUNDARY / "tphcm.geojson"
GRID_FILE = BOUNDARY / "grid_5km.geojson"

# --------------------------------------------------------------- Thoi gian
NGAY_BAT_DAU = "2018-07-01"
NGAY_KET_THUC = "2026-09-30"

# --------------------------------------------------------------- Du lieu GEE
# Moi chi so: collection GEE, band chinh, ngay bat dau co du lieu,
# va co ap dung loc may theo band cloud_fraction hay khong.
CHI_SO = {
    "no2": {
        "collection": "COPERNICUS/S5P/OFFL/L3_NO2",
        "band": "tropospheric_NO2_column_number_density",
        "tu_ngay": "2018-06-28", "loc_may": True,
        "don_vi": "mol/m²", "ten": "NO₂ tầng đối lưu"},
    "co": {
        "collection": "COPERNICUS/S5P/OFFL/L3_CO",
        "band": "CO_column_number_density",
        "tu_ngay": "2018-06-28", "loc_may": False,
        "don_vi": "mol/m²", "ten": "CO toàn cột"},
    "so2": {
        "collection": "COPERNICUS/S5P/OFFL/L3_SO2",
        "band": "SO2_column_number_density",
        "tu_ngay": "2018-12-05", "loc_may": True,
        "don_vi": "mol/m²", "ten": "SO₂"},
    "o3": {
        "collection": "COPERNICUS/S5P/OFFL/L3_O3",
        "band": "O3_column_number_density",
        "tu_ngay": "2018-09-08", "loc_may": True,
        "don_vi": "mol/m²", "ten": "O₃ toàn cột"},
    "aer_ai": {
        "collection": "COPERNICUS/S5P/OFFL/L3_AER_AI",
        "band": "absorbing_aerosol_index",
        "tu_ngay": "2018-07-04", "loc_may": False,
        "don_vi": "không thứ nguyên", "ten": "Chỉ số sol khí hấp thụ"},
}

SCALE_S5P = 1113.2     # met - do phan giai luoi L3 cua Sentinel-5P tren GEE
SCALE_ERA5 = 11132.0   # met - do phan giai ERA5-Land
SCALE_S2 = 10          # met - Sentinel-2 band B4/B8 (tinh NDVI cay xanh)
S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"

# Chi so duoc huan luyen mo hinh du bao (xem muc 6.2 bao cao)
CHI_SO_DU_BAO = ["no2", "aer_ai"]

ERA5_COLLECTION = "ECMWF/ERA5_LAND/HOURLY"
ERA5_BANDS = {
    "temperature_2m": "nhiet_do",
    "u_component_of_wind_10m": "gio_u",
    "v_component_of_wind_10m": "gio_v",
    "total_precipitation_hourly": "luong_mua",
}

# --------------------------------------------------------------- CSDL
# PostgreSQL 16 + PostGIS cai dang zip tai D:\pgsql (khong can quyen admin),
# chay cong 5433 vi cong 5432 danh cho PostgreSQL 18 co san tren may.
# Doi bang bien moi truong PG_BIN / PG_DATA / PG_DSN neu cai cho khac.
PG_BIN = Path(os.environ.get("PG_BIN", r"D:\pgsql\bin"))
PG_DATA = Path(os.environ.get("PG_DATA", r"D:\pgsql\data"))
PG_DSN = os.environ.get(
    "PG_DSN", "postgresql://postgres@localhost:5433/khong_khi")

CLOUD_MAX = 0.3              # nguong che mai khi loc anh S5P

# --------------------------------------------------------------- Mo hinh
CUA_SO = 7                    # so ngay dau vao (t-6 ... t)
TAM_DU_BAO = 3                # du bao t+1, t+2, t+3
TY_LE_TRAIN = 0.70            # chia theo thoi gian
TY_LE_VAL = 0.15              # phan con lai la test

# --------------------------------------------------------------- Canh bao
# Nguong tam thoi theo phan vi cua chinh chuoi du lieu, se hieu chinh sau
NGUONG_CANH_BAO = {
    "no2": [("Tốt", 0.00, 0.60, "#2E8B62"),
            ("Trung bình", 0.60, 0.80, "#C9841B"),
            ("Xấu", 0.80, 1.01, "#C0483F")],
    "aer_ai": [("Tốt", 0.00, 0.60, "#2E8B62"),
               ("Trung bình", 0.60, 0.80, "#C9841B"),
               ("Xấu", 0.80, 1.01, "#C0483F")],
}
