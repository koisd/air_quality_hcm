# -*- coding: utf-8 -*-
"""Tai ranh gioi TP.HCM (sau sap nhap 01/7/2025) va chia luoi 5 x 5 km.

Buoc nay khong can Google Earth Engine, chay duoc ngay:
    python src/make_grid.py

Nguon ranh gioi: GADM 4.1 cap tinh (ranh gioi dat lien, khong gom vung bien).
TP.HCM moi = TP.HCM cu + Binh Duong + Ba Ria - Vung Tau, bo Con Dao vi nam
cach dat lien khoang 200 km, khong phu hop dua vao cung mot luoi phan tich.
"""
import io
import sys
import zipfile

import geopandas as gpd
import requests
from shapely.geometry import box
from shapely.ops import unary_union

import config as cfg

GADM_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_VNM_1.json.zip"
HEADERS = {"User-Agent": "do-an-chat-luong-khong-khi-tphcm/1.0"}

# Ten tinh trong GADM (truoc sap nhap) hop thanh TP.HCM moi
TINH_HOP_NHAT = ["Hồ Chí Minh", "Bình Dương", "Bà Rịa - Vũng Tàu"]
VI_DO_CAT_CON_DAO = 9.5      # bo cac manh nam duoi vi do nay


def tai_ranh_gioi():
    """Ghep ranh gioi dat lien cua TP.HCM moi tu GADM cap tinh."""
    if cfg.BOUNDARY_FILE.exists():
        print("Da co ranh gioi:", cfg.BOUNDARY_FILE.name)
        return gpd.read_file(cfg.BOUNDARY_FILE)

    print("Dang tai ranh gioi cap tinh Viet Nam tu GADM ...")
    r = requests.get(GADM_URL, headers=HEADERS, timeout=300)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        ten = [n for n in z.namelist() if n.endswith(".json")][0]
        with z.open(ten) as f:
            vn = gpd.read_file(f)
    print("  tai xong, %d tinh" % len(vn))

    cot_ten = "NAME_1" if "NAME_1" in vn.columns else vn.columns[1]

    # GADM ghi ten tinh khong co dau cach ("HoChiMinh") -> chuan hoa truoc khi khop
    def chuan(x):
        return "".join(str(x).split()).lower()

    muc_tieu = {chuan(t) for t in TINH_HOP_NHAT}
    chon = vn[vn[cot_ten].map(chuan).isin(muc_tieu)]
    thieu = muc_tieu - set(chon[cot_ten].map(chuan))
    if thieu:
        raise SystemExit("Khong tim thay tinh: %s\nCac ten co trong file: %s"
                         % (thieu, sorted(vn[cot_ten].unique())[:60]))
    for _, h in chon.iterrows():
        print("  + %-22s %8.0f km2"
              % (h[cot_ten],
                 gpd.GeoSeries([h.geometry], crs=cfg.CRS_WGS84)
                 .to_crs(cfg.CRS_UTM).area.iloc[0] / 1e6))

    hop = unary_union(chon.geometry.values)

    # bo Con Dao va cac dao xa ngoai khoi
    manh = list(hop.geoms) if hop.geom_type == "MultiPolygon" else [hop]
    giu = [m for m in manh if m.bounds[3] >= VI_DO_CAT_CON_DAO]
    bo = len(manh) - len(giu)
    if bo:
        print("  bo %d manh nam duoi vi do %.1f (Con Dao / dao xa)"
              % (bo, VI_DO_CAT_CON_DAO))
    hop = unary_union(giu)

    gdf = gpd.GeoDataFrame({"ten": [cfg.TEN_TINH]}, geometry=[hop],
                           crs=cfg.CRS_WGS84)
    gdf.to_file(cfg.BOUNDARY_FILE, driver="GeoJSON")
    print("  luu:", cfg.BOUNDARY_FILE)
    return gdf


def tao_luoi(ranh_gioi):
    """Chia hop bao thanh o vuong GRID_SIZE_M met, giu lai o cham ranh gioi."""
    rg_utm = ranh_gioi.to_crs(cfg.CRS_UTM)
    vung = rg_utm.union_all() if hasattr(rg_utm, "union_all") else rg_utm.unary_union

    xmin, ymin, xmax, ymax = vung.bounds
    b = cfg.GRID_SIZE_M
    xmin, ymin = (xmin // b) * b, (ymin // b) * b

    o_vuong, hang, cot = [], [], []
    y, i = ymin, 0
    while y < ymax:
        x, j = xmin, 0
        while x < xmax:
            o = box(x, y, x + b, y + b)
            if o.intersects(vung):
                o_vuong.append(o)
                hang.append(i)
                cot.append(j)
            x += b
            j += 1
        y += b
        i += 1

    luoi = gpd.GeoDataFrame(
        {"hang": hang, "cot": cot,
         "ma_o": ["O_%02d_%02d" % (h, c) for h, c in zip(hang, cot)]},
        geometry=o_vuong, crs=cfg.CRS_UTM)

    # ty le dien tich o nam trong ranh gioi -> bo o chi cham me rat nho
    luoi["ty_le_trong"] = luoi.geometry.intersection(vung).area / luoi.geometry.area
    luoi = luoi[luoi["ty_le_trong"] >= 0.10].reset_index(drop=True)

    luoi["dien_tich_km2"] = (luoi.geometry.area / 1e6).round(2)
    tam = luoi.geometry.centroid.to_crs(cfg.CRS_WGS84)
    luoi = luoi.to_crs(cfg.CRS_WGS84)
    luoi["kinh_do_tam"] = tam.x.round(5)
    luoi["vi_do_tam"] = tam.y.round(5)
    luoi["ty_le_trong"] = luoi["ty_le_trong"].round(3)
    luoi["id_o"] = range(1, len(luoi) + 1)
    return luoi[["id_o", "ma_o", "hang", "cot", "kinh_do_tam", "vi_do_tam",
                 "dien_tich_km2", "ty_le_trong", "geometry"]]


def main():
    ranh_gioi = tai_ranh_gioi()
    dt = ranh_gioi.to_crs(cfg.CRS_UTM).area.sum() / 1e6
    b = ranh_gioi.total_bounds
    print("Dien tich dat lien: %.0f km2" % dt)
    print("Hop bao: lon %.2f–%.2f  lat %.2f–%.2f" % (b[0], b[2], b[1], b[3]))

    luoi = tao_luoi(ranh_gioi)
    luoi.to_file(cfg.GRID_FILE, driver="GeoJSON")

    km = cfg.GRID_SIZE_M // 1000
    print("So o luoi %d x %d km: %d" % (km, km, len(luoi)))
    print("Luu:", cfg.GRID_FILE)
    print(luoi[["ma_o", "kinh_do_tam", "vi_do_tam", "ty_le_trong"]]
          .head(5).to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
