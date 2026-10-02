# -*- coding: utf-8 -*-
"""Backend API cho he thong WebGIS, doc du lieu tu PostgreSQL + PostGIS.

    python src/nap_csdl.py      # nap du lieu vao CSDL (lam mot lan)
    python src/api.py           # -> mo trinh duyet tai http://127.0.0.1:8000

Cac endpoint:
    GET /api/thong-tin              thong tin chung (khoang ngay, chi so, nguong)
    GET /api/luoi                   ranh gioi cac o luoi dang GeoJSON (PostGIS)
    GET /api/o-tai-diem?kinh_do=&vi_do=   toa do thuoc o luoi nao (ST_Contains)
    GET /api/ban-do?chi_so=&ngay=   gia tri tung o trong mot ngay (to mau ban do)
    GET /api/lich-su?id_o=&chi_so=  chuoi lich su cua mot o
    GET /api/du-bao?id_o=&chi_so=   du bao t+1..t+3 moi nhat cua mot o
    GET /api/danh-gia               bang so sanh sai so cac mo hinh
"""
import argparse
import threading

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
import psycopg
from psycopg.rows import dict_row

import config as cfg
import db

WEB = cfg.ROOT / "web"
app = FastAPI(title="Giám sát chất lượng không khí TP.HCM", version="1.1")

CSDL = {"hau_to": "", "ket_noi": None}
_khoa = threading.Lock()


def sql(cau, tham_so=(), mot=False):
    """Chay mot truy van doc. Dung chung mot ket noi, tu noi lai neu bi rot."""
    with _khoa:
        for lan in range(2):
            c = CSDL["ket_noi"]
            if c is None or c.closed:
                c = CSDL["ket_noi"] = db.ket_noi(CSDL["hau_to"], autocommit=True,
                                                  row_factory=dict_row)
            try:
                cur = c.execute(cau, tham_so)
                return cur.fetchone() if mot else cur.fetchall()
            except psycopg.OperationalError:
                # PostgreSQL vua khoi dong lai -> bo ket noi cu, thu lai mot lan
                CSDL["ket_noi"] = None
                if lan:
                    raise


def kiem_chi_so(chi_so):
    if not sql("SELECT 1 FROM chi_so WHERE ma_chi_so=%s", (chi_so,), mot=True):
        raise HTTPException(404, "Khong co chi so %s" % chi_so)
    return sql("SELECT don_vi FROM chi_so WHERE ma_chi_so=%s",
               (chi_so,), mot=True)["don_vi"]


@app.get("/api/thong-tin")
def thong_tin():
    pv = sql("SELECT min(ngay) dau, max(ngay) cuoi FROM quan_trac", mot=True)
    so_o = sql("SELECT count(*) n FROM o_luoi", mot=True)["n"]
    # ngay_cuoi rieng tung chi so: S5P thuong tre vai ngay so voi ERA5
    chi = sql("SELECT c.ma_chi_so ma, ten, don_vi, co_du_bao, "
              "       max(q.ngay)::text ngay_cuoi "
              "FROM chi_so c JOIN quan_trac q USING (ma_chi_so) "
              "GROUP BY c.ma_chi_so "
              "ORDER BY array_position(%s, c.ma_chi_so)", (list(cfg.CHI_SO),))
    nguong = {}
    for r in sql("SELECT ma_chi_so, thu_tu, den FROM nguong_canh_bao "
                 "WHERE thu_tu < 3"):
        k = "tot_duoi" if r["thu_tu"] == 1 else "trung_binh_duoi"
        nguong.setdefault(r["ma_chi_so"], {})[k] = r["den"]
    return {
        "ngay_dau": str(pv["dau"]), "ngay_cuoi": str(pv["cuoi"]),
        "so_o_luoi": so_o, "chi_so": chi, "nguong": nguong,
        "kich_thuoc_o_km": cfg.GRID_SIZE_M // 1000,
    }


@app.get("/api/luoi")
def luoi():
    # PostGIS dung luon GeoJSON, backend khong can xu ly hinh hoc
    r = sql("""
        SELECT json_build_object('type', 'FeatureCollection', 'features',
               json_agg(json_build_object(
                   'type', 'Feature',
                   'geometry', ST_AsGeoJSON(hinh_hoc, 6)::json,
                   'properties', json_build_object('id_o', id_o, 'ma_o', ma_o))
               ORDER BY id_o))::text AS gj
        FROM o_luoi""", mot=True)
    return Response(r["gj"], media_type="application/json")


@app.get("/api/o-tai-diem")
def o_tai_diem(kinh_do: float, vi_do: float):
    r = sql("SELECT id_o, ma_o FROM o_luoi "
            "WHERE ST_Contains(hinh_hoc, ST_SetSRID(ST_MakePoint(%s,%s), 4326))",
            (kinh_do, vi_do), mot=True)
    if not r:
        raise HTTPException(404, "Toa do nam ngoai vung luoi")
    return r


@app.get("/api/ban-do")
def ban_do(chi_so: str = Query("no2"), ngay: str = Query(None)):
    don_vi = kiem_chi_so(chi_so)
    if ngay is None:
        ngay = str(sql("SELECT max(ngay) m FROM quan_trac WHERE ma_chi_so=%s",
                       (chi_so,), mot=True)["m"])
    ds = sql("SELECT id_o, gia_tri FROM quan_trac "
             "WHERE ma_chi_so=%s AND ngay=%s", (chi_so, ngay))
    if not ds:
        raise HTTPException(404, "Khong co du lieu ngay %s" % ngay)
    gt = [r["gia_tri"] for r in ds]
    return {
        "ngay": ngay, "chi_so": chi_so, "don_vi": don_vi,
        "nho_nhat": min(gt), "lon_nhat": max(gt),
        "gia_tri": {r["id_o"]: r["gia_tri"] for r in ds},
    }


@app.get("/api/lich-su")
def lich_su(id_o: int, chi_so: str = "no2", so_ngay: int = 120):
    don_vi = kiem_chi_so(chi_so)
    o = sql("SELECT ma_o FROM o_luoi WHERE id_o=%s", (id_o,), mot=True)
    if not o:
        raise HTTPException(404, "Khong co o %d" % id_o)
    # Lay n ngay cuoi cua o nay (ke ca ngay trong) theo lich
    ds = sql("""
        WITH cuoi AS (SELECT max(ngay) m FROM quan_trac WHERE ma_chi_so=%(c)s)
        SELECT d::date AS ngay, q.gia_tri
        FROM cuoi, generate_series(cuoi.m - (%(n)s - 1), cuoi.m,
                                   interval '1 day') d
        LEFT JOIN quan_trac q
               ON q.id_o=%(o)s AND q.ma_chi_so=%(c)s AND q.ngay=d::date
        ORDER BY d""", {"c": chi_so, "n": so_ngay, "o": id_o})
    return {
        "id_o": id_o, "ma_o": o["ma_o"], "chi_so": chi_so, "don_vi": don_vi,
        "ngay": [str(r["ngay"]) for r in ds],
        "gia_tri": [r["gia_tri"] for r in ds],
    }


@app.get("/api/du-bao")
def du_bao(id_o: int, chi_so: str = "no2"):
    ds = sql("""
        SELECT ngay_chay, ngay_du_bao, tam, gia_tri, muc_canh_bao
        FROM du_bao
        WHERE id_o=%(o)s AND ma_chi_so=%(c)s
          AND ngay_chay = (SELECT max(ngay_chay) FROM du_bao
                           WHERE id_o=%(o)s AND ma_chi_so=%(c)s)
        ORDER BY tam""", {"o": id_o, "c": chi_so})
    if not ds:
        raise HTTPException(404, "Khong co du bao cho o %d / %s" % (id_o, chi_so))
    return {
        "id_o": id_o, "chi_so": chi_so, "ngay_chay": str(ds[0]["ngay_chay"]),
        "du_bao": [{"tam": r["tam"], "ngay": str(r["ngay_du_bao"]),
                    "gia_tri": r["gia_tri"], "muc": r["muc_canh_bao"]}
                   for r in ds],
    }


@app.get("/api/danh-gia")
def danh_gia():
    """Ket qua lan huan luyen moi nhat, cung dang voi models/ket_qua.json."""
    kq = {}
    for r in sql("""
            SELECT * FROM mo_hinh m
            WHERE ngay_huan_luyen = (SELECT max(ngay_huan_luyen) FROM mo_hinh
                                     WHERE ma_chi_so = m.ma_chi_so)
            ORDER BY ma_chi_so, id_mo_hinh"""):
        kq.setdefault(r["ma_chi_so"], {}).setdefault(r["loai"], {})[
            "t%d" % r["tam"]] = {"rmse": r["rmse"], "mae": r["mae"],
                                 "mape": r["mape"], "r2": r["r2"],
                                 "n": r["so_mau_test"]}
    return kq


@app.get("/")
def trang_chu():
    f = WEB / "index.html"
    if not f.exists():
        return {"loi": "Chua co web/index.html"}
    return FileResponse(f)


if (WEB / "static").exists():
    app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hau-to", default="")
    ap.add_argument("--cong", type=int, default=8000)
    a = ap.parse_args()

    CSDL["hau_to"] = a.hau_to
    n = sql("SELECT count(*) n FROM quan_trac", mot=True)["n"]
    if not n:
        raise SystemExit("CSDL trong. Chay truoc: python src/nap_csdl.py")
    print("Ket noi CSDL %s: %d dong quan trac"
          % (db.dsn(a.hau_to).rsplit("/", 1)[1], n))
    import uvicorn
    print("Mo trinh duyet: http://127.0.0.1:%d" % a.cong)
    uvicorn.run(app, host="127.0.0.1", port=a.cong, log_level="warning")
