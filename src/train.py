# -*- coding: utf-8 -*-
"""Huan luyen va so sanh XGBoost, LSTM, GRU cho bai toan du bao.

    python src/train.py --chi-so no2 --epochs 20      # du lieu that

Chia du lieu theo THOI GIAN (khong xao tron) de tranh ro ri thong tin tuong lai:
    70% dau  -> train
    15% tiep -> validation
    15% cuoi -> test
Ket qua luu vao models/ket_qua.json va models/*.
"""
import argparse
import json
import time

import numpy as np
import pandas as pd

import config as cfg

BIEN_DONG = None        # dat trong main sau khi biet cot nao co that


def chia_theo_thoi_gian(ngay):
    """Tra ve 3 mat na train / val / test theo moc thoi gian."""
    moc = np.sort(ngay.unique())
    i1 = int(len(moc) * cfg.TY_LE_TRAIN)
    i2 = int(len(moc) * (cfg.TY_LE_TRAIN + cfg.TY_LE_VAL))
    return (ngay < moc[i1]), (ngay >= moc[i1]) & (ngay < moc[i2]), (ngay >= moc[i2])


def do_sai_so(that, du_doan):
    that, du_doan = np.asarray(that, float), np.asarray(du_doan, float)
    ok = np.isfinite(that) & np.isfinite(du_doan)
    that, du_doan = that[ok], du_doan[ok]
    if len(that) == 0:
        return {}
    sai = du_doan - that
    ss_tong = np.sum((that - that.mean()) ** 2)
    khac_0 = np.abs(that) > 1e-12
    return {
        "rmse": float(np.sqrt(np.mean(sai ** 2))),
        "mae": float(np.mean(np.abs(sai))),
        "mape": float(np.mean(np.abs(sai[khac_0] / that[khac_0])) * 100),
        "r2": float(1 - np.sum(sai ** 2) / ss_tong) if ss_tong > 0 else float("nan"),
        "n": int(len(that)),
    }


# --------------------------------------------------------------- XGBoost
def huan_luyen_xgboost(df, cot_dac_trung, chi_so, tam, mat_na):
    import xgboost as xgb

    m_tr, m_va, m_te = mat_na
    muc_tieu = "muc_tieu_%s_t%d" % (chi_so, tam)
    co = df[muc_tieu].notna()

    X = df.loc[:, cot_dac_trung]
    y = df[muc_tieu]

    mo_hinh = xgb.XGBRegressor(
        n_estimators=600, learning_rate=0.05, max_depth=6,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
        reg_lambda=1.0, tree_method="hist", early_stopping_rounds=40,
        n_jobs=-1, random_state=42)
    mo_hinh.fit(X[m_tr & co], y[m_tr & co],
                eval_set=[(X[m_va & co], y[m_va & co])], verbose=False)

    du_doan = mo_hinh.predict(X[m_te & co])
    ss = do_sai_so(y[m_te & co], du_doan)

    ten = "xgboost_%s_t%d" % (chi_so, tam)
    mo_hinh.save_model(cfg.MODELS / (ten + ".json"))

    quan_trong = (pd.Series(mo_hinh.feature_importances_, index=cot_dac_trung)
                  .sort_values(ascending=False))
    quan_trong.head(25).to_csv(cfg.MODELS / ("quan_trong_%s_t%d.csv"
                                             % (chi_so, tam)),
                               header=["muc_quan_trong"])
    return ss, quan_trong


# ------------------------------------------------------------ mang hoi quy
def huan_luyen_rnn(df, bien, chi_so, loai, epochs, batch, seed=42):
    """Huan luyen LSTM hoac GRU du bao cung luc t+1..t+3."""
    import torch
    import torch.nn as nn
    from numpy.lib.stride_tricks import sliding_window_view

    torch.manual_seed(seed)
    df = df.sort_values(["id_o", "ngay"])
    muc_tieu = ["muc_tieu_%s_t%d" % (chi_so, h)
                for h in range(1, cfg.TAM_DU_BAO + 1)]

    Xs, Ys, Ms = [], [], []
    for _, nhom in df.groupby("id_o", sort=False):
        if len(nhom) < cfg.CUA_SO:
            continue
        v = nhom[bien].to_numpy(np.float32)
        cua = np.transpose(sliding_window_view(v, cfg.CUA_SO, axis=0), (0, 2, 1))
        Xs.append(cua)
        Ys.append(nhom[muc_tieu].to_numpy(np.float32)[cfg.CUA_SO - 1:])
        Ms.append(nhom[["m_tr", "m_va", "m_te"]].to_numpy()[cfg.CUA_SO - 1:])
    X = np.concatenate(Xs)
    Y = np.concatenate(Ys)
    M = np.concatenate(Ms)

    hop_le = np.isfinite(X).all(axis=(1, 2)) & np.isfinite(Y).all(axis=1)
    X, Y, M = X[hop_le], Y[hop_le], M[hop_le]
    tr, va, te = M[:, 0].astype(bool), M[:, 1].astype(bool), M[:, 2].astype(bool)

    # chuan hoa theo thong ke cua tap train
    tb = X[tr].reshape(-1, X.shape[2]).mean(0)
    do_lech = X[tr].reshape(-1, X.shape[2]).std(0) + 1e-8
    y_tb, y_lech = Y[tr].mean(0), Y[tr].std(0) + 1e-8
    Xn = (X - tb) / do_lech
    Yn = (Y - y_tb) / y_lech

    class Mang(nn.Module):
        def __init__(self, n_bien, an=64):
            super().__init__()
            lop = nn.LSTM if loai == "lstm" else nn.GRU
            self.rnn = lop(n_bien, an, num_layers=1, batch_first=True)
            self.bo = nn.Dropout(0.15)
            self.ra = nn.Linear(an, cfg.TAM_DU_BAO)

        def forward(self, x):
            o, _ = self.rnn(x)
            return self.ra(self.bo(o[:, -1, :]))

    thiet_bi = "cuda" if torch.cuda.is_available() else "cpu"
    mo_hinh = Mang(X.shape[2]).to(thiet_bi)
    toi_uu = torch.optim.Adam(mo_hinh.parameters(), lr=1e-3)
    ham_mat = nn.MSELoss()

    def tensor(a):
        return torch.tensor(a, dtype=torch.float32, device=thiet_bi)

    Xtr, Ytr = tensor(Xn[tr]), tensor(Yn[tr])
    Xva, Yva = tensor(Xn[va]), tensor(Yn[va])

    tot_nhat, kien_nhan, trang_thai = float("inf"), 0, None
    for ep in range(1, epochs + 1):
        mo_hinh.train()
        thu_tu = torch.randperm(len(Xtr), device=thiet_bi)
        tong = 0.0
        for i in range(0, len(thu_tu), batch):
            idx = thu_tu[i:i + batch]
            toi_uu.zero_grad()
            mat = ham_mat(mo_hinh(Xtr[idx]), Ytr[idx])
            mat.backward()
            toi_uu.step()
            tong += float(mat) * len(idx)
        mo_hinh.eval()
        with torch.no_grad():
            mat_va = float(ham_mat(mo_hinh(Xva), Yva))
        print("    epoch %2d/%d  train %.5f  val %.5f"
              % (ep, epochs, tong / len(Xtr), mat_va))
        if mat_va < tot_nhat - 1e-5:
            tot_nhat, kien_nhan = mat_va, 0
            trang_thai = {k: v.clone() for k, v in mo_hinh.state_dict().items()}
        else:
            kien_nhan += 1
            if kien_nhan >= 3:
                print("    dung som o epoch %d" % ep)
                break
    if trang_thai:
        mo_hinh.load_state_dict(trang_thai)

    mo_hinh.eval()
    with torch.no_grad():
        dd = mo_hinh(tensor(Xn[te])).cpu().numpy() * y_lech + y_tb

    ket_qua = {}
    for h in range(cfg.TAM_DU_BAO):
        ket_qua["t%d" % (h + 1)] = do_sai_so(Y[te][:, h], dd[:, h])

    import torch as _t
    _t.save({"state_dict": mo_hinh.state_dict(), "bien": bien, "loai": loai,
             "tb": tb, "do_lech": do_lech, "y_tb": y_tb, "y_lech": y_lech,
             "cua_so": cfg.CUA_SO, "tam": cfg.TAM_DU_BAO},
            cfg.MODELS / ("%s_%s.pt" % (loai, chi_so)))
    return ket_qua


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hau-to", default="", help='hau to ten file (mac dinh rong)')
    ap.add_argument("--chi-so", default=",".join(cfg.CHI_SO_DU_BAO))
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--bo-rnn", action="store_true", help="chi chay XGBoost")
    a = ap.parse_args()

    f = cfg.PROCESSED / ("dac_trung%s.parquet" % a.hau_to)
    if not f.exists():
        raise SystemExit("Chua co %s. Chay truoc src/preprocess.py" % f)
    df = pd.read_parquet(f)
    print("Du lieu: %d dong, %s -> %s"
          % (len(df), df.ngay.min().date(), df.ngay.max().date()))

    m_tr, m_va, m_te = chia_theo_thoi_gian(df.ngay)
    df["m_tr"], df["m_va"], df["m_te"] = m_tr, m_va, m_te
    print("Chia: train %d | val %d | test %d" % (m_tr.sum(), m_va.sum(), m_te.sum()))
    print("  train den %s, test tu %s"
          % (df.ngay[m_tr].max().date(), df.ngay[m_te].min().date()))

    bo = {"ngay", "id_o", "m_tr", "m_va", "m_te"}
    cot_dac_trung = [c for c in df.columns
                     if c not in bo and not c.startswith("muc_tieu_")]
    bien_dong = [c for c in (list(cfg.CHI_SO) + ["nhiet_do", "toc_do_gio",
                                                 "luong_mua", "sin_nam",
                                                 "cos_nam", "cuoi_tuan"])
                 if c in df.columns]
    print("Dac trung XGBoost: %d cot | bien chuoi cho RNN: %d"
          % (len(cot_dac_trung), len(bien_dong)))

    ket_qua = {}
    for chi_so in [c.strip() for c in a.chi_so.split(",") if c.strip()]:
        if "muc_tieu_%s_t1" % chi_so not in df.columns:
            print("Bo qua %s (khong co cot muc tieu)" % chi_so)
            continue
        print("\n" + "=" * 62)
        print("CHI SO: %s" % chi_so.upper())
        print("=" * 62)
        ket_qua[chi_so] = {}

        print("  [XGBoost]")
        xgb_kq = {}
        for h in range(1, cfg.TAM_DU_BAO + 1):
            t0 = time.time()
            ss, qt = huan_luyen_xgboost(df, cot_dac_trung, chi_so, h,
                                        (m_tr, m_va, m_te))
            xgb_kq["t%d" % h] = ss
            print("    t+%d  RMSE %.4g  MAE %.4g  R2 %.3f   (%.0fs)"
                  % (h, ss["rmse"], ss["mae"], ss["r2"], time.time() - t0))
            if h == 1:
                print("    5 dac trung quan trong nhat: %s"
                      % ", ".join(qt.head(5).index))
        ket_qua[chi_so]["xgboost"] = xgb_kq

        if not a.bo_rnn:
            for loai in ("lstm", "gru"):
                print("  [%s]" % loai.upper())
                t0 = time.time()
                kq = huan_luyen_rnn(df, bien_dong, chi_so, loai,
                                    a.epochs, a.batch)
                ket_qua[chi_so][loai] = kq
                for h in range(1, cfg.TAM_DU_BAO + 1):
                    s = kq["t%d" % h]
                    print("    t+%d  RMSE %.4g  MAE %.4g  R2 %.3f"
                          % (h, s["rmse"], s["mae"], s["r2"]))
                print("    (%.0fs)" % (time.time() - t0))

    f_kq = cfg.MODELS / ("ket_qua%s.json" % a.hau_to)
    f_kq.write_text(json.dumps(ket_qua, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    print("\nLuu ket qua:", f_kq)

    print("\n" + "=" * 62)
    print("BANG SO SANH (t+1, tren tap test)")
    print("=" * 62)
    print("%-10s %-10s %10s %10s %8s" % ("chi so", "mo hinh", "RMSE", "MAE", "R2"))
    for cs, mh in ket_qua.items():
        for ten, kq in mh.items():
            s = kq.get("t1", {})
            if s:
                print("%-10s %-10s %10.4g %10.4g %8.3f"
                      % (cs, ten, s["rmse"], s["mae"], s["r2"]))


if __name__ == "__main__":
    main()
