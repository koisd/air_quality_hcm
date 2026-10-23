# -*- coding: utf-8 -*-
"""Phan tich bo sung theo gop y cua co (23/10).

    python src/phan_tich.py [--hinh <thu muc luu hinh>]

1. Tuong quan giua cac chat o nhiem, thoi tiet, cay xanh
   (theo thoi gian trong tung o, va theo khong gian giua cac o).
2. Cac chat co anh huong lan nhau khong: moi chat (vd SO2) duoc du doan tu
   cac chat con lai + thoi tiet + cay xanh; so voi khi bo cac chat con lai.
3. Dau vao nao anh huong dau ra: hoan vi theo nhom bien tren mo hinh kich ban
   (NO2, AER_AI ngay t+1).
4. Kich ban dau vao: doi gio / mua / nhiet do / cay xanh -> dau ra doi bao nhieu.
5. Du bao tai mot diem (o chua trung tam Quan 1): thuc te vs du bao t+1..t+3.

Ket qua so: models/phan_tich.json; hinh: thu muc --hinh (mac dinh models/hinh).
"""
import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config as cfg
from them_bien import them_lan_can, them_ndvi
from train import chia_theo_thoi_gian, do_sai_so

CHAT = list(cfg.CHI_SO)                         # no2 co so2 o3 aer_ai
TT = ["nhiet_do", "toc_do_gio", "luong_mua"]
TEN = {"no2": "NO₂", "co": "CO", "so2": "SO₂", "o3": "O₃", "aer_ai": "Sol khí (AI)",
       "nhiet_do": "Nhiệt độ", "toc_do_gio": "Tốc độ gió", "luong_mua": "Lượng mưa",
       "ndvi": "Cây xanh (NDVI)"}
LICH = ["thang", "ngay_trong_tuan", "cuoi_tuan", "mua_mua", "sin_nam", "cos_nam"]
QUAN_1 = (106.700, 10.776)                       # kinh do, vi do trung tam Q.1
N_JOBS = 4
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})


def cua(c, goc):
    """Cot c co phai bien goc `goc` hoac bien tre/truot cua no khong."""
    return c == goc or c.startswith(goc + "_")


def nhom_bien(cot, chi_so):
    """Gom cac cot dau vao cua mo hinh kich ban thanh nhom de giai thich."""
    nhom = {"Ô lân cận (không gian)": [], "Lịch sử chính chất này": [],
            "Chất ô nhiễm khác": [], "Thời tiết đã qua": [],
            "Thời tiết ngày dự báo": [], "Cây xanh (NDVI)": [], "Lịch, mùa": []}
    for c in cot:
        if c.endswith("_lc"):
            nhom["Ô lân cận (không gian)"].append(c)
        elif c.endswith("_mai"):
            nhom["Thời tiết ngày dự báo"].append(c)
        elif cua(c, chi_so):
            nhom["Lịch sử chính chất này"].append(c)
        elif any(cua(c, k) for k in CHAT):
            nhom["Chất ô nhiễm khác"].append(c)
        elif any(cua(c, k) for k in TT):
            nhom["Thời tiết đã qua"].append(c)
        elif c == "ndvi":
            nhom["Cây xanh (NDVI)"].append(c)
        else:
            nhom["Lịch, mùa"].append(c)
    return {k: v for k, v in nhom.items() if v}


def xgb_nhanh(**kw):
    import xgboost as xgb
    tham = dict(n_estimators=400, learning_rate=0.08, max_depth=6, subsample=0.8,
                colsample_bytree=0.8, min_child_weight=5, tree_method="hist",
                early_stopping_rounds=30, n_jobs=N_JOBS, random_state=42)
    tham.update(kw)
    return xgb.XGBRegressor(**tham)


# ------------------------------------------------------------------ 1
def tuong_quan(df, thu_muc, kq):
    cot = CHAT + TT + ["ndvi"]
    # (a) theo thoi gian: tru trung binh rieng tung o -> chi con dao dong theo ngay
    lech = df[cot] - df.groupby("id_o")[cot].transform("mean")
    r_tg = lech.corr(method="spearman")
    # (b) theo khong gian: trung binh nhieu nam cua tung o
    r_kg = df.groupby("id_o")[cot].mean().corr(method="spearman")
    kq["tuong_quan_thoi_gian"] = r_tg.round(3).to_dict()
    kq["tuong_quan_khong_gian"] = r_kg.round(3).to_dict()

    nhan = [TEN[c] for c in cot]
    fig, ax = plt.subplots(1, 2, figsize=(14.5, 5.6),
                           gridspec_kw={"wspace": 0.55})
    for a, r, td in ((ax[0], r_tg, "(a) Theo thời gian (dao động từng ngày trong mỗi ô)"),
                     (ax[1], r_kg, "(b) Theo không gian (trung bình 2018–2026 của 318 ô)")):
        im = a.imshow(r.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
        a.set_xticks(range(len(cot)), nhan, rotation=45, ha="right")
        a.set_yticks(range(len(cot)), nhan)
        for i in range(len(cot)):
            for j in range(len(cot)):
                v = r.iat[i, j]
                a.text(j, i, "%.2f" % v, ha="center", va="center", fontsize=7.5,
                       color="white" if abs(v) > 0.6 else "black")
        a.set_title(td, fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Hệ số tương quan Spearman")
    fig.savefig(thu_muc / "GY1_tuong_quan.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("1. Tuong quan xong")


# ------------------------------------------------------------------ 2
def anh_huong_lan_nhau(df, thu_muc, kq):
    """Theo y tuong kiem dinh nhan qua Granger: du bao Y ngay t+1 tu
    (A) lich su cua chinh Y + thoi tiet + NDVI + lich, va
    (B) A + lich su 7 ngay cua cac chat con lai.
    R2(B) - R2(A) > 0 nghia la cac chat khac co mang thong tin anh huong toi Y."""
    tr, va, te = chia_theo_thoi_gian(df.ngay)
    rng = np.random.default_rng(0)
    bang = {}
    qt_mt = pd.DataFrame(0.0, index=CHAT + TT + ["ndvi"], columns=CHAT)
    goc_cot = [c for c in df.columns if not c.endswith("_lc")
               and not c.startswith("muc_tieu_") and c not in ("ngay", "id_o")]
    cua_tt = [c for c in goc_cot if any(cua(c, t) for t in TT)]
    for y_ten in CHAT:
        rieng = [c for c in goc_cot if cua(c, y_ten)]
        khac = [c for c in goc_cot if any(cua(c, k) for k in CHAT if k != y_ten)]
        nen = rieng + cua_tt + ["ndvi"] + LICH
        y = (df.groupby("id_o")[y_ten].shift(-1)
             * (1e6 if y_ten in ("no2", "so2") else 1.0))
        co = y.notna()
        # lay mau 300k dong train cho nhanh
        i_tr = np.flatnonzero(tr & co)
        i_tr = rng.choice(i_tr, min(300_000, len(i_tr)), replace=False)
        i_va, i_te = np.flatnonzero(va & co), np.flatnonzero(te & co)
        r2 = {}
        for ten, X_cot in (("co_chat_khac", nen + khac), ("khong_chat_khac", nen)):
            m = xgb_nhanh()
            m.fit(df.iloc[i_tr][X_cot], y.iloc[i_tr],
                  eval_set=[(df.iloc[i_va][X_cot], y.iloc[i_va])], verbose=False)
            r2[ten] = do_sai_so(y.iloc[i_te], m.predict(df.iloc[i_te][X_cot]))["r2"]
            if ten == "co_chat_khac":
                g = pd.Series(m.get_booster().get_score(importance_type="gain"))
                g = g.reindex(X_cot).fillna(0)
                g = g / g.sum()
                # cong don gain cua bien goc va cac bien tre/truot cua no
                for goc in CHAT + TT:
                    qt_mt.loc[goc, y_ten] = g[[c for c in X_cot if cua(c, goc)]].sum()
                qt_mt.loc["ndvi", y_ten] = g["ndvi"]
        r2["tang_them"] = r2["co_chat_khac"] - r2["khong_chat_khac"]
        bang[y_ten] = {k: round(v, 3) for k, v in r2.items()}
        print("  %-7s R2 co chat khac %.3f | khong %.3f" %
              (y_ten, r2["co_chat_khac"], r2["khong_chat_khac"]))
    kq["anh_huong_lan_nhau"] = bang
    kq["muc_dong_gop_dau_vao"] = qt_mt.round(3).to_dict()

    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    hien = qt_mt.copy()        # duong cheo = lich su cua chinh chat do
    im = ax.imshow(hien.to_numpy() * 100, cmap="YlOrRd", vmin=0)
    ax.set_xticks(range(len(CHAT)), ["→ " + TEN[c] for c in CHAT], rotation=30, ha="right")
    ax.set_yticks(range(len(hien)), [TEN[c] for c in hien.index])
    for i in range(len(hien)):
        for j in range(len(CHAT)):
            v = hien.iat[i, j]
            ax.text(j, i, "—" if np.isnan(v) else "%.0f%%" % (v * 100),
                    ha="center", va="center", fontsize=8)
    for j, c in enumerate(CHAT):
        ax.text(j, len(hien) - 0.1, "R² %.2f\n(%.2f)" % (bang[c]["co_chat_khac"],
                bang[c]["khong_chat_khac"]), ha="center", va="top", fontsize=7.5)
    ax.set_ylim(len(hien) + 0.9, -0.5)
    ax.set_title("Mức đóng góp của lịch sử 7 ngày từng đầu vào khi dự báo mỗi chất ngày t+1\n"
                 "dòng cuối: R² có chất khác (chỉ lịch sử chính nó + thời tiết)", fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.75, label="% đóng góp (gain)")
    fig.savefig(thu_muc / "GY2_anh_huong_lan_nhau.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("2. Anh huong lan nhau xong")


# ------------------------------------------------------------------ 3, 4
def doc_mo_hinh_kich_ban():
    import xgboost as xgb
    tt = json.loads((cfg.MODELS / "kich_ban.json").read_text(encoding="utf-8"))
    mh = {}
    for c in tt["he_so"]:
        m = xgb.XGBRegressor()
        m.load_model(cfg.MODELS / ("kich_ban_%s.json" % c))
        mh[c] = m
    return tt, mh


def dau_vao_dau_ra(df, thu_muc, kq):
    tt, mh = doc_mo_hinh_kich_ban()
    cot = tt["bien_dau_vao"]
    for b in TT:
        df[b + "_mai"] = df.groupby("id_o")[b].shift(-1)
    _, _, te = chia_theo_thoi_gian(df.ngay)
    rng = np.random.default_rng(1)
    kq["nhom_dau_vao"] = {}
    kq["kich_ban_duong_cong"] = {}
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    for k, chi_so in enumerate(cfg.CHI_SO_DU_BAO):
        he = tt["he_so"][chi_so]
        y = df["muc_tieu_%s_t1" % chi_so] * he
        idx = np.flatnonzero(te & y.notna() & df[cot].notna().all(axis=1).to_numpy())
        idx = rng.choice(idx, min(40_000, len(idx)), replace=False)
        X, yy = df.iloc[idx][cot].reset_index(drop=True), y.iloc[idx].to_numpy()
        m = mh[chi_so]
        rmse0 = np.sqrt(np.mean((m.predict(X) - yy) ** 2))
        tang = {}
        for ten, cs in nhom_bien(cot, chi_so).items():
            Xp = X.copy()
            Xp[cs] = X[cs].to_numpy()[rng.permutation(len(X))]
            tang[ten] = max(np.sqrt(np.mean((m.predict(Xp) - yy) ** 2)) - rmse0, 0)
        s = pd.Series(tang)
        s = (s / s.sum() * 100).sort_values()
        kq["nhom_dau_vao"][chi_so] = s.round(2).to_dict()
        ax[k].barh(s.index, s.values, color="#3B7DD8")
        for i, v in enumerate(s.values):
            ax[k].text(v + 0.5, i, "%.1f%%" % v, va="center", fontsize=8)
        ax[k].set_title("%s ngày t+1" % TEN[chi_so])
        ax[k].set_xlabel("% mức dựa vào (hoán vị nhóm biến)")

        # duong cong kich ban: doi tung dau vao, giu nguyen phan con lai
        X0 = X.sample(5000, random_state=2)
        p0 = m.predict(X0).mean()
        dc = {}
        for bien, gia_tri, cach in (
                ("toc_do_gio_mai", np.arange(0, 7.01, 0.5), "dat"),
                ("luong_mua_mai", np.arange(0, 61, 5), "dat"),
                ("nhiet_do_mai", np.arange(22, 33.1, 1), "dat"),
                ("ndvi", np.round(np.arange(-0.2, 0.31, 0.05), 2), "cong")):
            dong = []
            for v in gia_tri:
                Xs = X0.copy()
                Xs[bien] = (Xs[bien] + v).clip(-1, 1) if cach == "cong" else v
                dong.append((float(v), float((m.predict(Xs).mean() / p0 - 1) * 100)))
            dc[bien] = dong
        kq["kich_ban_duong_cong"][chi_so] = dc
    fig.tight_layout()
    fig.savefig(thu_muc / "GY3_dau_vao_dau_ra.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(1, 4, figsize=(15, 3.6), sharey=True)
    nhan = {"toc_do_gio_mai": "Tốc độ gió ngày mai (m/s)",
            "luong_mua_mai": "Lượng mưa ngày mai (mm)",
            "nhiet_do_mai": "Nhiệt độ ngày mai (°C)",
            "ndvi": "Cây xanh: NDVI thay đổi (+/−)"}
    for i, bien in enumerate(nhan):
        for chi_so, mau in (("no2", "#C0483F"), ("aer_ai", "#3B7DD8")):
            d = np.array(kq["kich_ban_duong_cong"][chi_so][bien])
            ax[i].plot(d[:, 0], d[:, 1], "-o", ms=3, color=mau, label=TEN[chi_so])
        ax[i].axhline(0, color="grey", lw=0.8)
        ax[i].set_xlabel(nhan[bien])
    ax[0].set_ylabel("% thay đổi dự báo t+1")
    ax[0].legend()
    fig.suptitle("Kịch bản đầu vào: thay đổi một yếu tố, giữ nguyên các yếu tố còn lại", fontsize=11)
    fig.tight_layout()
    fig.savefig(thu_muc / "GY4_kich_ban.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("3-4. Dau vao -> dau ra, kich ban xong")


# ------------------------------------------------------------------ 5
def du_bao_mot_diem(df, thu_muc, kq):
    import geopandas as gpd
    import xgboost as xgb
    from shapely.geometry import Point
    luoi = gpd.read_file(cfg.GRID_FILE)
    trong = luoi[luoi.contains(Point(*QUAN_1))]
    id_o = int(trong.id_o.iloc[0] if len(trong) else
               luoi.distance(Point(*QUAN_1)).idxmin())
    _, _, te = chia_theo_thoi_gian(df.ngay)
    d = df[te & (df.id_o == id_o)].sort_values("ngay")
    kq["mot_diem"] = {"id_o": id_o, "kinh_do": QUAN_1[0], "vi_do": QUAN_1[1]}
    fig, ax = plt.subplots(2, 1, figsize=(12, 6.2))
    for k, chi_so in enumerate(cfg.CHI_SO_DU_BAO):
        kq["mot_diem"][chi_so] = {}
        for h in (1, 2, 3):
            m = xgb.XGBRegressor()
            m.load_model(cfg.MODELS / ("xgboost_%s_t%d.json" % (chi_so, h)))
            cot = m.get_booster().feature_names
            ok = d["muc_tieu_%s_t%d" % (chi_so, h)].notna()
            p = m.predict(d.loc[ok, cot])
            that = d.loc[ok, "muc_tieu_%s_t%d" % (chi_so, h)]
            ss = do_sai_so(that, p)
            kq["mot_diem"][chi_so]["t%d" % h] = {"r2": round(ss["r2"], 3),
                                                 "mae": ss["mae"], "n": ss["n"]}
            if h == 1:
                ngay = d.loc[ok, "ngay"] + pd.Timedelta(days=1)
                ax[k].plot(ngay, that, color="#555", lw=1, label="Thực tế (vệ tinh)")
                ax[k].plot(ngay, p, color="#C0483F", lw=1, label="Dự báo t+1 (XGBoost)")
        ax[k].set_title("%s tại ô %d (chứa trung tâm Quận 1) — giai đoạn kiểm tra, R² t+1 = %.2f"
                        % (TEN[chi_so], id_o, kq["mot_diem"][chi_so]["t1"]["r2"]), fontsize=10)
        ax[k].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(thu_muc / "GY5_mot_diem.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("5. Du bao mot diem xong (o %d)" % id_o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hinh", default=str(cfg.MODELS / "hinh"))
    a = ap.parse_args()
    from pathlib import Path
    thu_muc = Path(a.hinh)
    thu_muc.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(cfg.PROCESSED / "dac_trung.parquet")
    df = them_lan_can(them_ndvi(df), CHAT)
    df = df.sort_values(["id_o", "ngay"]).reset_index(drop=True)
    print("Du lieu: %d dong, NDVI co %.0f%%" % (len(df), 100 * df.ndvi.notna().mean()))

    kq = {}
    tuong_quan(df, thu_muc, kq)
    anh_huong_lan_nhau(df, thu_muc, kq)
    dau_vao_dau_ra(df, thu_muc, kq)
    du_bao_mot_diem(df, thu_muc, kq)
    (cfg.MODELS / "phan_tich.json").write_text(
        json.dumps(kq, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("Luu models/phan_tich.json, hinh -> %s" % thu_muc)


if __name__ == "__main__":
    main()
