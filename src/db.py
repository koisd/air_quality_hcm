# -*- coding: utf-8 -*-
"""Ket noi PostgreSQL. Tu bat may chu neu no chua chay (vi du sau khi tat may).

Chi tu bat khi PostgreSQL cai dang giai nen (co thu muc PG_DATA, nhu D:\\pgsql).
Neu cai bang bo cai dat thong thuong thi PostgreSQL chay san dang service,
khong can bat.
"""
import subprocess
import time
from urllib.parse import urlparse

import psycopg

import config as cfg


def dsn(hau_to=""):
    """Hau to (neu co) duoc gan vao ten CSDL."""
    return cfg.PG_DSN + hau_to.replace("-", "_")


def _cong():
    return str(urlparse(cfg.PG_DSN).port or 5432)


def _dang_chay():
    return subprocess.run([str(cfg.PG_BIN / "pg_isready.exe"), "-q", "-p", _cong()]
                          ).returncode == 0


def bat_may_chu():
    """Chay pg_ctl start neu PostgreSQL ban giai nen chua chay."""
    if not ((cfg.PG_BIN / "pg_ctl.exe").exists() and (cfg.PG_DATA / "PG_VERSION").exists()):
        return          # cai dang service -> de psycopg tu ket noi
    if _dang_chay():
        return
    print("PostgreSQL chua chay -> dang bat ...")
    subprocess.Popen(
        [str(cfg.PG_BIN / "pg_ctl.exe"), "-D", str(cfg.PG_DATA),
         "-l", str(cfg.PG_DATA / "server.log"), "start"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.DETACHED_PROCESS
        | subprocess.CREATE_NEW_PROCESS_GROUP)
    for _ in range(30):
        time.sleep(0.5)
        if _dang_chay():
            return
    raise SystemExit("Khong bat duoc PostgreSQL, xem %s"
                     % (cfg.PG_DATA / "server.log"))


def ket_noi(hau_to="", **kw):
    bat_may_chu()
    return psycopg.connect(dsn(hau_to), **kw)
