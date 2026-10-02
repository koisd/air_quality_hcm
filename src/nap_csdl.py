# -*- coding: utf-8 -*-
"""Nap ket qua xu ly vao PostgreSQL + PostGIS.

    python src/nap_csdl.py                 # du lieu that -> CSDL khong_khi
    python src/nap_csdl.py --chi-du-bao    # chi them lan du bao moi (hang ngay)

Mac dinh tao lai toan bo bang theo sql/schema.sql roi nap:
    o_luoi (ranh gioi POLYGON), chi_so, nguong_canh_bao,
    quan_trac (+ co noi suy), khi_tuong, mo_hinh, du_bao.
"""
import argparse
import json
import time
from datetime import datetime

import pandas as pd
import psycopg

import config as cfg
import db

MUC = [("Tốt", "#2E8B62", "Không khí trong lành, sinh hoạt bình thường."),
       ("Trung bình", "#C9841B",
        "Người nhạy cảm (trẻ em, người già, bệnh hô hấp) nên hạn chế ở ngoài lâu."),
       ("Xấu", "#C0483F",
        "Hạn chế ra ngoài, đeo khẩu trang khi đi đường, đóng cửa sổ.")]


def tao_csdl(hau_to):
    """Tao database neu chua co (ket noi vao CSDL he thong 'postgres')."""
    ten = db.dsn(hau_to).rsplit("/", 1)[1]
    goc = db.dsn(hau_to).rsplit("/", 1)[0] + "/postgres"
    db.bat_may_chu()
    with psycopg.connect(goc, autocommit=True) as c:
        if not c.execute("SELECT 1 FROM pg_database WHERE datname=%s",
                         (ten,)).fetchone():
            c.execute('CREATE DATABASE "%s"' % ten)
            print("Tao CSDL", ten)


def copy_vao(cur, bang, cot, df):
    with cur.copy("COPY %s (%s) FROM STDIN" % (bang, ", ".join(cot))) as cp:
        for dong in df[cot].itertuples(index=False, name=None):
            cp.write_row(dong)


def nap_danh_muc(cur, hau_to):
    import geopandas as gpd
    luoi = gpd.read_file(cfg.GRID_FILE).to_crs(cfg.CRS_WGS84)
    for r in luoi.itertuples():
        cur.execute(
            "INSERT INTO o_luoi VALUES (%s,%s,%s,%s,%s,%s,%s,%s,"
            "ST_SetSRID(ST_GeomFromText(%s), 4326))",
            (r.id_o, r.ma_o, r.hang, r.cot, r.kinh_do_tam, r.vi_do_tam,
             r.dien_tich_km2, r.ty_le_trong, r.geometry.wkt))
    print("o_luoi          %8d dong" % len(luoi))

    for ma, c in cfg.CHI_SO.items():
        cur.execute("INSERT INTO chi_so VALUES (%s,%s,%s,%s,%s)",
                    (ma, c["ten"], c["don_vi"], c["collection"],
                     ma in cfg.CHI_SO_DU_BAO))

    f = cfg.PROCESSED / ("nguong%s.json" % hau_to)
    nguong = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    for ma, ng in nguong.items():
        moc = [None, ng["tot_duoi"], ng["trung_binh_duoi"], None]
        for i, (muc, mau, kc) in enumerate(MUC):
            cur.execute("INSERT INTO nguong_canh_bao VALUES "
                        "(%s,%s,%s,%s,%s,%s,%s)",
                        (ma, i + 1, muc, moc[i], moc[i + 1], mau, kc))
    print("nguong_canh_bao %8d dong" % (3 * len(nguong)))


def nap_quan_trac(cur, hau_to):
    bang = pd.read_parquet(cfg.PROCESSED / ("bang_ngay%s.parquet" % hau_to))
    f_ns = cfg.PROCESSED / ("co_noi_suy%s.parquet" % hau_to)
    ns = pd.read_parquet(f_ns) if f_ns.exists() else None

    co = [c for c in cfg.CHI_SO if c in bang.columns]
    dai = bang.melt(id_vars=["ngay", "id_o"], value_vars=co,
                    var_name="ma_chi_so", value_name="gia_tri").dropna()
    if ns is not None:
        ns = ns.melt(id_vars=["ngay", "id_o"], value_vars=co,
                     var_name="ma_chi_so", value_name="noi_suy")
        dai = dai.merge(ns, on=["ngay", "id_o", "ma_chi_so"], how="left")
        dai["noi_suy"] = dai["noi_suy"].fillna(False).astype(bool)
    else:
        dai["noi_suy"] = False
    dai["ngay"] = dai["ngay"].dt.date
    copy_vao(cur, "quan_trac",
             ["id_o", "ma_chi_so", "ngay", "gia_tri", "noi_suy"], dai)
    print("quan_trac       %8d dong (%.1f%% noi suy)"
          % (len(dai), 100 * dai.noi_suy.mean()))

    kt = bang[["id_o", "ngay", "nhiet_do", "toc_do_gio", "luong_mua"]]
    kt = kt.dropna(subset=["nhiet_do", "toc_do_gio", "luong_mua"], how="all")
    kt = kt.astype(object).where(kt.notna(), None)
    kt["ngay"] = pd.to_datetime(kt["ngay"]).dt.date
    copy_vao(cur, "khi_tuong",
             ["id_o", "ngay", "nhiet_do", "toc_do_gio", "luong_mua"], kt)
    print("khi_tuong       %8d dong" % len(kt))


def nap_mo_hinh(cur, hau_to):
    """Tra ve {(chi_so, loai, tam): id_mo_hinh} cua lan huan luyen nay."""
    f = cfg.MODELS / ("ket_qua%s.json" % hau_to)
    if not f.exists():
        return {}
    ngay = datetime.fromtimestamp(f.stat().st_mtime).replace(microsecond=0)
    ma = {}
    for chi, cac_loai in json.loads(f.read_text(encoding="utf-8")).items():
        for loai, cac_tam in cac_loai.items():
            tep = ("%s_%s.pt" % (loai, chi)) if loai != "xgboost" else None
            for k, s in cac_tam.items():
                tam = int(k.lstrip("t"))
                duong_dan = tep or "xgboost_%s_t%d.json" % (chi, tam)
                id_mh = cur.execute(
                    "INSERT INTO mo_hinh (ma_chi_so, loai, tam, ngay_huan_luyen,"
                    " rmse, mae, mape, r2, so_mau_test, duong_dan) VALUES"
                    " (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                    " ON CONFLICT (ma_chi_so, loai, tam, ngay_huan_luyen)"
                    " DO UPDATE SET r2 = EXCLUDED.r2 RETURNING id_mo_hinh",
                    (chi, loai, tam, ngay, s.get("rmse"), s.get("mae"),
                     s.get("mape"), s.get("r2"), s.get("n"),
                     "models/" + duong_dan)).fetchone()[0]
                ma[(chi, loai, tam)] = id_mh
    print("mo_hinh         %8d dong" % len(ma))
    return ma


def nap_du_bao(cur, hau_to, ma_mo_hinh):
    f = cfg.PROCESSED / ("du_bao%s.parquet" % hau_to)
    if not f.exists():
        print("du_bao          chua co (chay predict.py)")
        return
    d = pd.read_parquet(f)
    d["id_mo_hinh"] = [ma_mo_hinh.get((r.chi_so, r.mo_hinh, r.tam))
                       for r in d.itertuples()]
    # Chay lai cung ngay thi thay the, cac ngay khac giu lai lam lich su
    cur.execute("DELETE FROM du_bao WHERE ngay_chay = ANY(%s)",
                (sorted(d.ngay_chay.dt.date.unique()),))
    d = d.rename(columns={"chi_so": "ma_chi_so", "gia_tri_du_bao": "gia_tri",
                          "muc_canh_bao": "muc_canh_bao"})
    d["ngay_chay"] = d.ngay_chay.dt.date
    d["ngay_du_bao"] = d.ngay_du_bao.dt.date
    d["id_mo_hinh"] = d.id_mo_hinh.astype(object).where(d.id_mo_hinh.notna(), None)
    copy_vao(cur, "du_bao",
             ["id_o", "ma_chi_so", "ngay_chay", "ngay_du_bao", "tam",
              "gia_tri", "muc_canh_bao", "id_mo_hinh"], d)
    print("du_bao          %8d dong" % len(d))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hau-to", default="")
    ap.add_argument("--chi-du-bao", action="store_true",
                    help="khong tao lai bang, chi them mo_hinh + du_bao moi")
    a = ap.parse_args()

    t0 = time.time()
    tao_csdl(a.hau_to)
    with db.ket_noi(a.hau_to) as c, c.cursor() as cur:
        if not a.chi_du_bao:
            cur.execute((cfg.ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
            print("Tao lai bang theo sql/schema.sql")
            nap_danh_muc(cur, a.hau_to)
            nap_quan_trac(cur, a.hau_to)
        ma = nap_mo_hinh(cur, a.hau_to)
        nap_du_bao(cur, a.hau_to, ma)
    with db.ket_noi(a.hau_to, autocommit=True) as c:
        c.execute("VACUUM ANALYZE")
    print("Xong sau %.0f giay -> %s" % (time.time() - t0,
                                        db.dsn(a.hau_to).rsplit("@", 1)[1]))


if __name__ == "__main__":
    main()
