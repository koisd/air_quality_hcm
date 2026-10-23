# -*- coding: utf-8 -*-
"""Lam sach, noi suy va sinh dac trung tu du lieu tho trong data/raw/.

    python src/preprocess.py

Dau ra:
    data/processed/bang_ngay.parquet   - bang ngay x o luoi x chi so (da noi suy)
    data/processed/dac_trung.parquet   - them lag, trung binh truot, bien mua
"""
import argparse
import sys

import numpy as np
import pandas as pd

import config as cfg

COT_CHI_SO = list(cfg.CHI_SO)
COT_KHI_TUONG = ["nhiet_do", "toc_do_gio", "luong_mua"]
GIOI_HAN_NOI_SUY = 5          # khong noi suy qua 5 ngay trong lien tiep


def doc_tho(thu_muc):
    """Gop toan bo CSV trong thu muc nguon thanh mot bang dang dai."""
    # NDVI (1 gia tri/thang) duoc ghep rieng trong them_bien.py
    files = sorted(f for f in thu_muc.glob("*.csv")
                   if not f.name.startswith("ndvi_"))
    if not files:
        sys.exit("Khong co file CSV nao trong %s. Chay truoc: "
                 "python src/fetch_gee.py"
                 % thu_muc)
    phan = []
    for f in files:
        df = pd.read_csv(f, parse_dates=["ngay"])
        phan.append(df)
    df = pd.concat(phan, ignore_index=True)
    print("Doc %d file, %d dong tho" % (len(files), len(df)))
    return df


def dan_rong(df):
    """Chuyen dang dai -> rong: moi dong la (ngay, id_o), moi chi so mot cot."""
    rong = (df.pivot_table(index=["ngay", "id_o"], columns="bien",
                           values="gia_tri", aggfunc="mean")
              .reset_index())
    rong.columns.name = None

    # gio u, v -> toc do gio tong hop (m/s)
    if {"gio_u", "gio_v"}.issubset(rong.columns):
        rong["toc_do_gio"] = np.hypot(rong["gio_u"], rong["gio_v"])
        rong = rong.drop(columns=["gio_u", "gio_v"])
    if "nhiet_do" in rong.columns:      # Kelvin -> do C cho de doc
        rong["nhiet_do"] = rong["nhiet_do"] - 273.15
    if "luong_mua" in rong.columns:     # m -> mm
        rong["luong_mua"] = rong["luong_mua"] * 1000.0
    return rong


def loc_ngoai_lai(df, cot):
    """Bo gia tri ngoai lai theo quy tac IQR tren tung chi so."""
    for c in cot:
        if c not in df.columns:
            continue
        q1, q3 = df[c].quantile([0.25, 0.75])
        iqr = q3 - q1
        thap, cao = q1 - 3 * iqr, q3 + 3 * iqr
        n = ((df[c] < thap) | (df[c] > cao)).sum()
        df.loc[(df[c] < thap) | (df[c] > cao), c] = np.nan
        if n:
            print("  %-10s bo %d gia tri ngoai lai" % (c, n))
    return df


def day_du_ngay(df):
    """Bao dam moi o luoi co du moi ngay trong khoang (ngay thieu -> NaN)."""
    ngay = pd.date_range(df.ngay.min(), df.ngay.max(), freq="D")
    o = df.id_o.unique()
    khung = pd.MultiIndex.from_product([ngay, o], names=["ngay", "id_o"])
    return (df.set_index(["ngay", "id_o"]).reindex(khung).reset_index())


def noi_suy(df, cot):
    """Noi suy tuyen tinh theo thoi gian trong tung o luoi."""
    df = df.sort_values(["id_o", "ngay"])
    co = [c for c in cot if c in df.columns]
    truoc = df[co].isna().sum()
    df[co] = (df.groupby("id_o")[co]
                .transform(lambda s: s.interpolate(method="linear",
                                                   limit=GIOI_HAN_NOI_SUY,
                                                   limit_direction="both")))
    sau = df[co].isna().sum()
    for c in co:
        tong = len(df)
        print("  %-10s thieu %5.1f%% -> con %5.1f%%"
              % (c, 100 * truoc[c] / tong, 100 * sau[c] / tong))
    return df


def sinh_dac_trung(df):
    """Them bien tre, trung binh truot va bien thoi vu."""
    df = df.sort_values(["id_o", "ngay"]).copy()
    goc = [c for c in COT_CHI_SO + COT_KHI_TUONG if c in df.columns]

    g = df.groupby("id_o")
    for c in goc:
        for k in range(1, cfg.CUA_SO):
            df["%s_lag%d" % (c, k)] = g[c].shift(k)
        df["%s_tb3" % c] = g[c].transform(
            lambda s: s.rolling(3, min_periods=2).mean())
        df["%s_tb7" % c] = g[c].transform(
            lambda s: s.rolling(7, min_periods=3).mean())

    df["thang"] = df.ngay.dt.month
    df["ngay_trong_tuan"] = df.ngay.dt.dayofweek
    df["cuoi_tuan"] = (df.ngay_trong_tuan >= 5).astype(int)
    # TP.HCM: mua mua thang 5-11, mua kho thang 12-4
    df["mua_mua"] = df.thang.between(5, 11).astype(int)
    # tinh chu ky trong nam de mo hinh nam duoc tinh tuan hoan
    ngay_nam = df.ngay.dt.dayofyear
    df["sin_nam"] = np.sin(2 * np.pi * ngay_nam / 365.25)
    df["cos_nam"] = np.cos(2 * np.pi * ngay_nam / 365.25)

    # muc tieu: gia tri cua t+1 ... t+TAM_DU_BAO
    for c in cfg.CHI_SO_DU_BAO:
        if c not in df.columns:
            continue
        for h in range(1, cfg.TAM_DU_BAO + 1):
            df["muc_tieu_%s_t%d" % (c, h)] = df.groupby("id_o")[c].shift(-h)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vao", default=str(cfg.RAW),
                    help="thu muc chua CSV tho (mac dinh data/raw)")
    ap.add_argument("--hau-to", default="",
                    help='hau to ten file dau ra (mac dinh rong)')
    a = ap.parse_args()

    thu_muc = cfg.ROOT / a.vao if not str(a.vao).startswith(("/", "\\")) \
        and ":" not in str(a.vao) else __import__("pathlib").Path(a.vao)
    bang_ngay = cfg.PROCESSED / ("bang_ngay%s.parquet" % a.hau_to)
    dac_trung = cfg.PROCESSED / ("dac_trung%s.parquet" % a.hau_to)

    tho = doc_tho(thu_muc)
    rong = dan_rong(tho)
    print("Bang rong: %d dong x %d cot, tu %s den %s"
          % (len(rong), len(rong.columns),
             rong.ngay.min().date(), rong.ngay.max().date()))

    print("Loc ngoai lai:")
    rong = loc_ngoai_lai(rong, COT_CHI_SO)

    rong = day_du_ngay(rong)
    # Ghi lai o nao dang trong truoc khi noi suy -> cot noi_suy trong CSDL
    co = [c for c in COT_CHI_SO if c in rong.columns]
    thieu = rong[["ngay", "id_o"]].copy()
    thieu[co] = rong[co].isna()

    print("Noi suy (toi da %d ngay lien tiep):" % GIOI_HAN_NOI_SUY)
    rong = noi_suy(rong, COT_CHI_SO + COT_KHI_TUONG)

    rong.to_parquet(bang_ngay, index=False)
    print("Luu:", bang_ngay)
    f_thieu = cfg.PROCESSED / ("co_noi_suy%s.parquet" % a.hau_to)
    thieu.to_parquet(f_thieu, index=False)
    print("Luu:", f_thieu)

    dt = sinh_dac_trung(rong)
    dt.to_parquet(dac_trung, index=False)
    print("Luu: %s  (%d dong x %d cot)" % (dac_trung, len(dt), len(dt.columns)))


if __name__ == "__main__":
    main()
