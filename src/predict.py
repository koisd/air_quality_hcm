# -*- coding: utf-8 -*-
"""Chay mo hinh da huan luyen de sinh du bao cho ngay moi nhat co du lieu.

    python src/predict.py

Ket qua ghi vao data/processed/du_bao*.parquet - dung bang du_bao trong thiet ke
CSDL. Trang WebGIS chi doc bang nay, khong goi lai mo hinh.
Nen chay mot lan moi ngay sau khi da cap nhat du lieu.
"""
import argparse
import json

import numpy as np
import pandas as pd

import config as cfg


def nguong_tu_du_lieu(chuoi):
    """Tinh nguong canh bao theo phan vi 60% va 80% cua chinh chuoi lich su."""
    s = chuoi.dropna()
    if s.empty:
        return None
    return float(s.quantile(0.60)), float(s.quantile(0.80))


def muc_canh_bao(gt, nguong):
    if nguong is None or not np.isfinite(gt):
        return "Không xác định"
    if gt < nguong[0]:
        return "Tốt"
    if gt < nguong[1]:
        return "Trung bình"
    return "Xấu"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hau-to", default="")
    ap.add_argument("--so-ngay", type=int, default=1,
                    help="sinh du bao cho N ngay cuoi cung (mac dinh 1)")
    a = ap.parse_args()

    import xgboost as xgb

    f = cfg.PROCESSED / ("dac_trung%s.parquet" % a.hau_to)
    if not f.exists():
        raise SystemExit("Chua co %s. Chay src/preprocess.py truoc" % f)
    df = pd.read_parquet(f)

    bo = {"ngay", "id_o", "m_tr", "m_va", "m_te"}
    cot_dac_trung = [c for c in df.columns
                     if c not in bo and not c.startswith("muc_tieu_")]

    dong = []
    for chi_so in cfg.CHI_SO_DU_BAO:
        if chi_so not in df.columns:
            continue
        # Ngay goc = ngay moi nhat CO so do cua chinh chi so nay. Sentinel-5P
        # thuong tre vai ngay so voi ERA5, lay ngay cuoi cua ca bang thi mo hinh
        # khong thay gia tri gan day nao cua chi so (toan NaN).
        co_do = df.loc[df[chi_so].notna(), "ngay"].unique()
        cac_ngay = np.sort(co_do)[-a.so_ngay:]
        goc = df[df.ngay.isin(cac_ngay)].copy()
        print("%s: du bao tu %d ngay goc (%s -> %s), %d o luoi, %.0f%% o co so do"
              % (chi_so, len(cac_ngay), pd.Timestamp(cac_ngay[0]).date(),
                 pd.Timestamp(cac_ngay[-1]).date(), goc.id_o.nunique(),
                 100 * goc[chi_so].notna().mean()))
        nguong = nguong_tu_du_lieu(df[chi_so])
        print("  %s: nguong Tot<%.4g, Trung binh<%.4g"
              % (chi_so, nguong[0], nguong[1]) if nguong else chi_so)
        for h in range(1, cfg.TAM_DU_BAO + 1):
            duong_dan = cfg.MODELS / ("xgboost_%s_t%d.json" % (chi_so, h))
            if not duong_dan.exists():
                print("    thieu mo hinh %s -> bo qua" % duong_dan.name)
                continue
            mo_hinh = xgb.XGBRegressor()
            mo_hinh.load_model(duong_dan)
            dd = mo_hinh.predict(goc[cot_dac_trung])
            for id_o, ngay_goc, gt in zip(goc.id_o, goc.ngay, dd):
                dong.append({
                    "id_o": int(id_o),
                    "chi_so": chi_so,
                    "ngay_chay": pd.Timestamp(ngay_goc).normalize(),
                    "ngay_du_bao": pd.Timestamp(ngay_goc).normalize()
                    + pd.Timedelta(days=h),
                    "tam": h,
                    "gia_tri_du_bao": float(gt),
                    "muc_canh_bao": muc_canh_bao(float(gt), nguong),
                    "mo_hinh": "xgboost",
                })

    if not dong:
        raise SystemExit("Khong sinh duoc du bao nao. Da chay src/train.py chua?")

    du_bao = pd.DataFrame(dong)
    out = cfg.PROCESSED / ("du_bao%s.parquet" % a.hau_to)
    du_bao.to_parquet(out, index=False)
    print("Luu %d dong du bao -> %s" % (len(du_bao), out))

    # luu nguong de web dung chung mot bang mau
    nguong_json = {}
    for chi_so in cfg.CHI_SO:
        if chi_so in df.columns:
            ng = nguong_tu_du_lieu(df[chi_so])
            if ng:
                nguong_json[chi_so] = {"tot_duoi": ng[0], "trung_binh_duoi": ng[1]}
    (cfg.PROCESSED / ("nguong%s.json" % a.hau_to)).write_text(
        json.dumps(nguong_json, indent=2), encoding="utf-8")
    print(du_bao.groupby(["chi_so", "tam"]).gia_tri_du_bao
          .agg(["mean", "min", "max"]).to_string())


if __name__ == "__main__":
    main()
