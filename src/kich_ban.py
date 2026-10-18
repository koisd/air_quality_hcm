# -*- coding: utf-8 -*-
"""Mo hinh kich ban thoi tiet: neu ngay mai mua / gio / nong khac di thi
chi so du bao t+1 thay doi ra sao.

    python src/kich_ban.py

Khac voi mo hinh du bao chinh (train.py) chi dung thoi tiet DA XAY RA, mo hinh
nay them 3 bien thoi tiet cua chinh ngay du bao (nhiet_do_mai, toc_do_gio_mai,
luong_mua_mai). Khi chay that, 3 bien nay lay tu ban tin du bao thoi tiet; tren
web nguoi dung tu dat gia tri de so sanh cac kich ban.

NO2 duoc doi sang don vi 1e-6 mol/m2 truoc khi huan luyen: gia tri goc ~1e-5
qua nho so voi he so dieu chuan cua XGBoost (reg_lambda=1) nen cac nhanh tach
theo bien yeu bi trieu tieu.

Ket qua:
    models/kich_ban_<chi_so>.json     mo hinh XGBoost
    models/kich_ban.json              sai so, he so doi don vi, khi hau thang
    data/processed/kich_ban_goc.parquet   dong dac trung moi nhat cua tung o
"""
import argparse
import json

import numpy as np
import pandas as pd

import config as cfg
from train import chia_theo_thoi_gian, do_sai_so

BIEN_TT = ["nhiet_do", "toc_do_gio", "luong_mua"]
HE_SO = {"no2": 1e6, "aer_ai": 1.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hau-to", default="")
    a = ap.parse_args()

    import xgboost as xgb

    df = pd.read_parquet(cfg.PROCESSED / ("dac_trung%s.parquet" % a.hau_to))
    df = df.sort_values(["id_o", "ngay"]).reset_index(drop=True)
    bo = {"ngay", "id_o", "m_tr", "m_va", "m_te"}
    cot_goc = [c for c in df.columns
               if c not in bo and not c.startswith("muc_tieu_")]
    for b in BIEN_TT:
        df[b + "_mai"] = df.groupby("id_o")[b].shift(-1)
    cot = cot_goc + [b + "_mai" for b in BIEN_TT]
    tr, va, te = chia_theo_thoi_gian(df.ngay)

    # Khi hau tung thang (trung binh moi o) -> kich ban "binh thuong"
    thang = df.ngay.dt.month
    khi_hau = (df.groupby([df.id_o, thang])[BIEN_TT].mean()
               .round(3).reset_index().rename(columns={"ngay": "thang"}))

    tong = {"bien_dau_vao": cot, "he_so": HE_SO, "chi_so": {}}
    goc = []
    for chi_so in cfg.CHI_SO_DU_BAO:
        k = HE_SO[chi_so]
        y = df["muc_tieu_%s_t1" % chi_so] * k
        co = y.notna()
        mh = xgb.XGBRegressor(
            n_estimators=600, learning_rate=0.05, max_depth=6,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
            reg_lambda=1.0, tree_method="hist", early_stopping_rounds=40,
            n_jobs=-1, random_state=42)
        mh.fit(df.loc[tr & co, cot], y[tr & co],
               eval_set=[(df.loc[va & co, cot], y[va & co])], verbose=False)
        ss = do_sai_so(y[te & co] / k, mh.predict(df.loc[te & co, cot]) / k)
        mh.save_model(cfg.MODELS / ("kich_ban_%s.json" % chi_so))
        qt = pd.Series(mh.feature_importances_, index=cot)
        tong["chi_so"][chi_so] = {
            "sai_so_test": ss,
            "quan_trong_thoi_tiet_mai": {b + "_mai": float(qt[b + "_mai"])
                                         for b in BIEN_TT},
        }
        print("%s: R2 test %.3f, RMSE %.3g" % (chi_so, ss["r2"], ss["rmse"]))

        # dong goc = ngay moi nhat co so do cua chi so nay (S5P tre hon ERA5)
        ngay_goc = df.loc[df[chi_so].notna(), "ngay"].max()
        d = df.loc[df.ngay == ngay_goc, ["ngay", "id_o"] + cot_goc].copy()
        d.insert(0, "chi_so", chi_so)
        goc.append(d)

    pd.concat(goc).to_parquet(cfg.PROCESSED / ("kich_ban_goc%s.parquet"
                                               % a.hau_to), index=False)
    khi_hau.to_parquet(cfg.PROCESSED / ("khi_hau_thang%s.parquet" % a.hau_to),
                       index=False)
    (cfg.MODELS / "kich_ban.json").write_text(
        json.dumps(tong, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Luu mo hinh kich ban -> models/kich_ban_*.json")


if __name__ == "__main__":
    main()
