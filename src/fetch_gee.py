# -*- coding: utf-8 -*-
"""Thu thap du lieu Sentinel-5P va ERA5-Land tu Google Earth Engine.

Chay theo tung thang, moi thang luu mot file CSV trong data/raw/ nen co the
dung giua chung roi chay lai ma khong mat cong (tu bo qua thang da co).

    python src/fetch_gee.py --chi-so no2 --tu 2024-01 --den 2024-12
    python src/fetch_gee.py --chi-so all --tu 2018-07 --den 2026-09
    python src/fetch_gee.py --khi-tuong --tu 2018-07 --den 2026-09

Lan dau chay can dang nhap Google Earth Engine:
    earthengine authenticate
va dat bien moi truong EE_PROJECT bang ma du an Google Cloud da bat GEE API.
"""
import argparse
import os
import sys
from calendar import monthrange
from datetime import date

import pandas as pd

import config as cfg

try:
    import ee
except ImportError:
    sys.exit("Chua cai earthengine-api. Chay: pip install earthengine-api")


# --------------------------------------------------------------------- GEE
def khoi_tao():
    """Khoi tao ket noi Earth Engine."""
    du_an = cfg.EE_PROJECT
    try:
        if du_an:
            ee.Initialize(project=du_an)
        else:
            ee.Initialize()
    except Exception as e:
        print("Khong khoi tao duoc Earth Engine:", e, file=sys.stderr)
        print("\nCac buoc can lam mot lan:", file=sys.stderr)
        print("  1. Dang ky tai https://earthengine.google.com/signup "
              "(mien phi, dung Gmail)", file=sys.stderr)
        print("  2. Tao mot project tren Google Cloud va bat Earth Engine API",
              file=sys.stderr)
        print("  3. Chay lenh:  earthengine authenticate", file=sys.stderr)
        print("  4. Dat bien moi truong EE_PROJECT = ma project vua tao",
              file=sys.stderr)
        sys.exit(1)
    print("Earth Engine san sang" + (" (project %s)" % du_an if du_an else ""))


def doc_luoi():
    """Doc luoi 5 km tu file GeoJSON va chuyen thanh FeatureCollection."""
    if not cfg.GRID_FILE.exists():
        sys.exit("Chua co luoi. Chay truoc: python src/make_grid.py")
    import geopandas as gpd
    luoi = gpd.read_file(cfg.GRID_FILE)[["id_o", "ma_o", "geometry"]]
    feats = [
        ee.Feature(ee.Geometry(g.__geo_interface__),
                   {"id_o": int(i), "ma_o": str(m)})
        for i, m, g in zip(luoi.id_o, luoi.ma_o, luoi.geometry)
    ]
    print("Luoi: %d o" % len(feats))
    return ee.FeatureCollection(feats), luoi


def _anh_rong(ten_band):
    """Anh trang hoan toan bi che, dung de collection rong van co du band."""
    return (ee.Image.constant(0).rename(ten_band).toFloat()
            .updateMask(ee.Image.constant(0)))


def anh_thang_s5p(ma_chi_so, nam, thang):
    """Gop anh Sentinel-5P cua ca thang thanh 1 anh nhieu band (1 band/ngay)."""
    ct = cfg.CHI_SO[ma_chi_so]
    so_ngay = monthrange(nam, thang)[1]
    dau_thang = ee.Date("%04d-%02d-01" % (nam, thang))

    col = ee.ImageCollection(ct["collection"])
    trong = _anh_rong(ct["band"])

    def mot_ngay(d):
        t0 = dau_thang.advance(ee.Number(d), "day")
        t1 = t0.advance(1, "day")
        c = col.filterDate(t0, t1)
        if ct["loc_may"]:
            c = c.map(lambda im: im.updateMask(
                im.select("cloud_fraction").lt(cfg.CLOUD_MAX)))
        c = c.select([ct["band"]])
        c = c.merge(ee.ImageCollection([trong]))
        return c.mean().rename(t0.format("YYYY_MM_dd"))

    ngay = ee.List.sequence(0, so_ngay - 1)
    return ee.ImageCollection(ngay.map(mot_ngay)).toBands(), so_ngay


def anh_thang_era5(nam, thang):
    """Gop ERA5-Land ca thang: nhiet do/gio lay trung binh, mua lay tong."""
    so_ngay = monthrange(nam, thang)[1]
    dau_thang = ee.Date("%04d-%02d-01" % (nam, thang))
    col = ee.ImageCollection(cfg.ERA5_COLLECTION)
    bands = list(cfg.ERA5_BANDS.keys())
    trong = ee.Image.constant([0] * len(bands)).rename(bands).toFloat() \
        .updateMask(ee.Image.constant(0))

    def mot_ngay(d):
        t0 = dau_thang.advance(ee.Number(d), "day")
        t1 = t0.advance(1, "day")
        c = col.filterDate(t0, t1).select(bands).merge(
            ee.ImageCollection([trong]))
        tb = c.mean()
        tong_mua = c.select("total_precipitation_hourly").sum()
        anh = tb.addBands(tong_mua.rename("total_precipitation_hourly"), None, True)
        hau_to = t0.format("YYYY_MM_dd")
        return anh.rename([ee.String(b).cat("__").cat(hau_to) for b in bands])

    ngay = ee.List.sequence(0, so_ngay - 1)
    return ee.ImageCollection(ngay.map(mot_ngay)).toBands(), so_ngay


def anh_thang_ndvi(nam, thang):
    """NDVI trung vi ca thang tu Sentinel-2 (10 m), bo pixel may/bong may/nuoc.

    Band dat ten "ndvi_YYYY_MM_01" -> moi o luoi mot gia tri cho ca thang.
    """
    t0 = ee.Date("%04d-%02d-01" % (nam, thang))
    # SCL: 4 thuc vat, 5 dat trong, 6 nuoc, 7 chua phan loai -> giu 4, 5, 7
    def lam_sach(im):
        scl = im.select("SCL")
        tot = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(7))
        return im.updateMask(tot).normalizedDifference(["B8", "B4"]).toFloat()
    col = (ee.ImageCollection(cfg.S2_COLLECTION)
           .filterDate(t0, t0.advance(1, "month"))
           .filterBounds(ee.Geometry.Rectangle(list(cfg.BBOX)))
           .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
           .map(lam_sach))
    ten = "ndvi_%04d_%02d_01" % (nam, thang)
    anh = col.merge(ee.ImageCollection([_anh_rong("nd")])).median()
    return anh.rename(ten), 1


def lay_bang(anh, luoi_ee, scale):
    """reduceRegions tren luoi roi keo ket qua ve may."""
    kq = anh.reduceRegions(collection=luoi_ee,
                           # forEach: anh 1 band (NDVI) van giu ten band
                           # thay vi bi dat thanh "mean"
                           reducer=ee.Reducer.mean().forEach(anh.bandNames()),
                           scale=scale,
                           tileScale=4)
    return kq.getInfo()["features"]


# ------------------------------------------------------------------ xu ly
def _dai_hoa(feats, ten_cot):
    """Doi ket qua GEE (moi o mot dong, moi ngay mot cot) sang dang dai."""
    dong = []
    for f in feats:
        pr = f["properties"]
        id_o = pr.get("id_o")
        for k, v in pr.items():
            if k in ("id_o", "ma_o") or v is None:
                continue
            # ten band dang "<index>_<YYYY_MM_dd>" hoac "<bien>__<YYYY_MM_dd>"
            phan = k.split("_")
            if len(phan) < 3:
                continue
            ngay = "-".join(phan[-3:])
            bien = ten_cot
            if "__" in k:
                bien = k.split("__")[0].split("_", 1)[-1]
                bien = cfg.ERA5_BANDS.get(bien, bien)
            dong.append((ngay, id_o, bien, v))
    df = pd.DataFrame(dong, columns=["ngay", "id_o", "bien", "gia_tri"])
    if df.empty:
        return df
    df["ngay"] = pd.to_datetime(df["ngay"], format="%Y-%m-%d", errors="coerce")
    return df.dropna(subset=["ngay"]).sort_values(["ngay", "id_o"])


def cac_thang(tu, den):
    y0, m0 = int(tu[:4]), int(tu[5:7])
    y1, m1 = int(den[:4]), int(den[5:7])
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def chay_mot_nguon(ten, lay_anh, scale, luoi_ee, tu, den, ghi_de):
    for nam, thang in cac_thang(tu, den):
        out = cfg.RAW / ("%s_%04d-%02d.csv" % (ten, nam, thang))
        if out.exists() and not ghi_de:
            print("  bo qua (da co): %s" % out.name)
            continue
        try:
            anh, so_ngay = lay_anh(nam, thang)
            feats = lay_bang(anh, luoi_ee, scale)
            df = _dai_hoa(feats, ten)
            if df.empty:
                print("  %04d-%02d: khong co du lieu" % (nam, thang))
                continue
            df.to_csv(out, index=False)
            co = df.groupby("ngay").gia_tri.count()
            print("  %04d-%02d: %5d dong, %2d/%2d ngay co du lieu -> %s"
                  % (nam, thang, len(df), len(co), so_ngay, out.name))
        except Exception as e:
            print("  %04d-%02d LOI: %s" % (nam, thang, e), file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chi-so", default="", help="no2 | co | so2 | o3 | aer_ai | all")
    ap.add_argument("--khi-tuong", action="store_true", help="tai ERA5-Land")
    ap.add_argument("--ndvi", action="store_true",
                    help="tai NDVI Sentinel-2 10 m (moi thang 1 gia tri/o)")
    ap.add_argument("--tu", default=cfg.NGAY_BAT_DAU[:7], help="YYYY-MM")
    ap.add_argument("--den", default=date.today().strftime("%Y-%m"), help="YYYY-MM")
    ap.add_argument("--ghi-de", action="store_true", help="tai lai ca thang da co")
    a = ap.parse_args()

    if not a.chi_so and not a.khi_tuong and not a.ndvi:
        ap.error("Can --chi-so, --khi-tuong hoac --ndvi")

    khoi_tao()
    luoi_ee, _ = doc_luoi()

    if a.chi_so:
        ds = list(cfg.CHI_SO) if a.chi_so == "all" else [a.chi_so]
        for ma in ds:
            if ma not in cfg.CHI_SO:
                sys.exit("Khong biet chi so: %s" % ma)
            tu = max(a.tu, cfg.CHI_SO[ma]["tu_ngay"][:7])
            print("\n[%s] %s -> %s" % (ma.upper(), tu, a.den))
            chay_mot_nguon(ma,
                           lambda y, m, _ma=ma: anh_thang_s5p(_ma, y, m),
                           cfg.SCALE_S5P, luoi_ee, tu, a.den, a.ghi_de)

    if a.khi_tuong:
        print("\n[ERA5-LAND] %s -> %s" % (a.tu, a.den))
        chay_mot_nguon("era5", anh_thang_era5, cfg.SCALE_ERA5,
                       luoi_ee, a.tu, a.den, a.ghi_de)

    if a.ndvi:
        print("\n[NDVI SENTINEL-2] %s -> %s" % (a.tu, a.den))
        chay_mot_nguon("ndvi", anh_thang_ndvi, cfg.SCALE_S2,
                       luoi_ee, a.tu, a.den, a.ghi_de)


if __name__ == "__main__":
    main()
