# -*- coding: utf-8 -*-
"""Ket noi PostgreSQL. Tu bat may chu neu no chua chay (vi du sau khi tat may)."""
import subprocess
import time

import psycopg

import config as cfg


def dsn(hau_to=""):
    """Hau to (neu co) duoc gan vao ten CSDL."""
    return cfg.PG_DSN + hau_to.replace("-", "_")


def bat_may_chu():
    """Chay pg_ctl start neu cong 5433 chua mo. Khong lam gi neu da chay."""
    if subprocess.run([str(cfg.PG_BIN / "pg_isready.exe"), "-q", "-p", "5433"]).returncode == 0:
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
        if subprocess.run([str(cfg.PG_BIN / "pg_isready.exe"), "-q", "-p", "5433"]).returncode == 0:
            return
    raise SystemExit("Khong bat duoc PostgreSQL, xem %s"
                     % (cfg.PG_DATA / "server.log"))


def ket_noi(hau_to="", **kw):
    bat_may_chu()
    return psycopg.connect(dsn(hau_to), **kw)
