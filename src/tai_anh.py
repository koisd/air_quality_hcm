# -*- coding: utf-8 -*-
"""Tai anh vê tinh mau that (Sentinel-2) cho tung o luoi de hien tren web.

    python src/tai_anh.py                       # mua kho 12/2025 - 3/2026
    python src/tai_anh.py --tu 2025-01-01 --den 2025-04-30

Moi o luoi lay mot anh tong hop trung vi (median) cac canh Sentinel-2 L2A it
may trong khoang thoi gian chon, cat theo khung o 5x5 km, luu thanh
web/static/anh/o_<id_o>.jpg. Trang web chi doc file tinh nay, khong goi GEE.
"""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor

import requests

import config as cfg

THU_MUC = cfg.ROOT / "web" / "static" / "anh"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tu", default="2025-12-01")
    ap.add_argument("--den", default="2026-03-31")
    ap.add_argument("--co", type=int, default=400, help="canh anh (pixel)")
    a = ap.parse_args()

    import ee
    ee.Initialize(project=cfg.EE_PROJECT)

    def che_may(anh):
        # SCL: 3 bong may, 8-9 may, 10 may ti, 11 tuyet
        scl = anh.select("SCL")
        tot = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
        return anh.updateMask(tot)

    s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
          .filterDate(a.tu, a.den)
          .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
          .map(che_may)
          .median()
          .visualize(bands=["B4", "B3", "B2"], min=0, max=2800, gamma=1.2))

    THU_MUC.mkdir(parents=True, exist_ok=True)
    luoi = json.loads(cfg.GRID_FILE.read_text(encoding="utf-8"))["features"]

    def tai(f):
        id_o = f["properties"]["id_o"]
        out = THU_MUC / ("o_%d.jpg" % id_o)
        if out.exists():
            return id_o, "co san"
        vung = ee.Geometry.Polygon(f["geometry"]["coordinates"]).bounds()
        url = s2.getThumbURL({"region": vung, "dimensions": a.co,
                              "format": "jpg"})
        for lan in range(3):
            try:
                r = requests.get(url, timeout=120)
                r.raise_for_status()
                out.write_bytes(r.content)
                return id_o, "ok"
            except Exception as e:      # GEE doi khi tra 429 / het gio
                loi = e
        return id_o, "loi: %s" % loi

    with ThreadPoolExecutor(8) as pool:
        for i, (id_o, kq) in enumerate(pool.map(tai, luoi), 1):
            if kq != "ok" or i % 50 == 0:
                print("%3d/%d  o %d: %s" % (i, len(luoi), id_o, kq))
    (THU_MUC / "nguon.json").write_text(json.dumps(
        {"ve_tinh": "Sentinel-2 L2A (COPERNICUS/S2_SR_HARMONIZED)",
         "tu": a.tu, "den": a.den, "cach_ghep": "median, che may theo SCL"},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print("Xong -> %s" % THU_MUC)


if __name__ == "__main__":
    main()
