# -*- coding: utf-8 -*-
"""Bien bo sung theo gop y cua co (23/10): cay xanh va yeu to khong gian.

- ndvi        : chi so cay xanh NDVI tu Sentinel-2 10 m (fetch_gee.py --ndvi),
                moi thang 1 gia tri/o -> noi suy tuyen tinh thanh tung ngay.
- <chi_so>_lc : trung binh cua chi so o cac o lan can (8 o xung quanh) cung
                ngay -> mo hinh biet o nha ben canh dang o nhiem ra sao.

Khong sua bang dac_trung.parquet goc nen mo hinh chinh (train.py) giu nguyen.
"""
import numpy as np
import pandas as pd

import config as cfg


def doc_ndvi():
    """Bang (ngay, id_o, ndvi) theo ngay tu cac file data/raw/ndvi_*.csv."""
    files = sorted(cfg.RAW.glob("ndvi_*.csv"))
    if not files:
        raise SystemExit("Chua co NDVI. Chay: python src/fetch_gee.py --ndvi")
    d = pd.concat([pd.read_csv(f, parse_dates=["ngay"]) for f in files])
    # gia tri dai dien giua thang (ngay 15) de noi suy giua cac thang
    d["ngay"] = d.ngay + pd.Timedelta(days=14)
    rong = d.pivot_table(index="ngay", columns="id_o", values="gia_tri")
    ngay = pd.date_range(rong.index.min() - pd.Timedelta(days=14),
                         rong.index.max() + pd.Timedelta(days=16), freq="D")
    rong = (rong.reindex(ngay).interpolate(method="time", limit_area="inside")
                .ffill().bfill())
    return (rong.stack().rename("ndvi").reset_index()
                .rename(columns={"level_0": "ngay"}))


def ban_do_lan_can():
    """id_o -> danh sach id_o cac o lan can (tam cach nhau <= 1.5 canh o)."""
    import geopandas as gpd
    luoi = gpd.read_file(cfg.GRID_FILE).to_crs(cfg.CRS_UTM)
    tam = np.c_[luoi.centroid.x, luoi.centroid.y]
    ids = luoi.id_o.to_numpy()
    kc = np.hypot(*(tam[:, None, :] - tam[None, :, :]).transpose(2, 0, 1))
    gan = (kc > 0) & (kc <= 1.5 * cfg.GRID_SIZE_M)
    return {int(ids[i]): ids[gan[i]].astype(int).tolist() for i in range(len(ids))}


def them_lan_can(df, cot):
    """Them cot <c>_lc = trung binh cung ngay cua cac o lan can."""
    lc = ban_do_lan_can()
    canh = pd.DataFrame([(o, n) for o, ds in lc.items() for n in ds],
                        columns=["id_o", "id_lc"])
    nguon = df[["ngay", "id_o"] + cot].rename(columns={"id_o": "id_lc"})
    tb = (canh.merge(nguon, on="id_lc").groupby(["ngay", "id_o"])[cot].mean()
              .add_suffix("_lc").reset_index())
    return df.merge(tb, on=["ngay", "id_o"], how="left")


def them_ndvi(df):
    return df.merge(doc_ndvi(), on=["ngay", "id_o"], how="left")
