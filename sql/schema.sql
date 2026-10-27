-- Luoc do co so du lieu - Giam sat chat luong khong khi TP.HCM
-- PostgreSQL 16 + PostGIS, 7 bang.
-- Chay lai file nay se XOA TOAN BO du lieu cu va tao lai bang rong.

CREATE EXTENSION IF NOT EXISTS postgis;

DROP TABLE IF EXISTS du_bao, mo_hinh, khi_tuong, quan_trac, o_luoi,
                     nguong_canh_bao, chi_so CASCADE;

-- =============================================================== Danh muc

CREATE TABLE chi_so (
    ma_chi_so   VARCHAR(10) PRIMARY KEY,           -- no2, co, so2, o3, aer_ai
    ten         TEXT        NOT NULL,
    don_vi      VARCHAR(20) NOT NULL,
    nguon       TEXT        NOT NULL,              -- collection tren GEE
    co_du_bao   BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE TABLE nguong_canh_bao (
    ma_chi_so   VARCHAR(10) REFERENCES chi_so,
    thu_tu      SMALLINT    NOT NULL,              -- 1 Tot, 2 Trung binh, 3 Xau
    muc         VARCHAR(20) NOT NULL,
    tu          DOUBLE PRECISION,                  -- NULL = am vo cung
    den         DOUBLE PRECISION,                  -- NULL = duong vo cung
    mau         CHAR(7)     NOT NULL,
    khuyen_cao  TEXT,
    PRIMARY KEY (ma_chi_so, thu_tu)
);

CREATE TABLE o_luoi (
    id_o          INTEGER PRIMARY KEY,
    ma_o          VARCHAR(10) UNIQUE NOT NULL,     -- O_hang_cot
    hang          SMALLINT,
    cot           SMALLINT,
    kinh_do_tam   DOUBLE PRECISION,
    vi_do_tam     DOUBLE PRECISION,
    dien_tich_km2 REAL,
    ty_le_trong   REAL,                            -- phan dien tich nam trong TP
    hinh_hoc      geometry(Polygon, 4326) NOT NULL
);
CREATE INDEX o_luoi_gist ON o_luoi USING GIST (hinh_hoc);

-- ========================================================== Du lieu chinh

CREATE TABLE quan_trac (
    id_o       INTEGER     NOT NULL REFERENCES o_luoi,
    ma_chi_so  VARCHAR(10) NOT NULL REFERENCES chi_so,
    ngay       DATE        NOT NULL,
    gia_tri    DOUBLE PRECISION NOT NULL,
    noi_suy    BOOLEAN     NOT NULL DEFAULT FALSE, -- TRUE = gia tri noi suy
    PRIMARY KEY (id_o, ma_chi_so, ngay)            -- lich su mot o
);

CREATE TABLE khi_tuong (
    id_o        INTEGER NOT NULL REFERENCES o_luoi,
    ngay        DATE    NOT NULL,
    nhiet_do    REAL,                              -- do C
    toc_do_gio  REAL,                              -- m/s
    luong_mua   REAL,                              -- mm/ngay
    PRIMARY KEY (id_o, ngay)
);

CREATE TABLE mo_hinh (
    id_mo_hinh       SERIAL PRIMARY KEY,
    ma_chi_so        VARCHAR(10) NOT NULL REFERENCES chi_so,
    loai             VARCHAR(20) NOT NULL,         -- xgboost / lstm / gru
    tam              SMALLINT    NOT NULL,         -- du bao t+1..t+3
    ngay_huan_luyen  TIMESTAMP   NOT NULL,
    rmse             DOUBLE PRECISION,
    mae              DOUBLE PRECISION,
    mape             DOUBLE PRECISION,
    r2               DOUBLE PRECISION,
    so_mau_test      INTEGER,
    duong_dan        TEXT,                         -- tep mo hinh trong models/
    UNIQUE (ma_chi_so, loai, tam, ngay_huan_luyen)
);

CREATE TABLE du_bao (
    id_du_bao     BIGSERIAL PRIMARY KEY,
    id_o          INTEGER     NOT NULL REFERENCES o_luoi,
    ma_chi_so     VARCHAR(10) NOT NULL REFERENCES chi_so,
    ngay_chay     DATE        NOT NULL,
    ngay_du_bao   DATE        NOT NULL,
    tam           SMALLINT    NOT NULL,
    gia_tri       DOUBLE PRECISION NOT NULL,
    muc_canh_bao  VARCHAR(20),
    id_mo_hinh    INTEGER REFERENCES mo_hinh,
    UNIQUE (id_o, ma_chi_so, ngay_chay, tam)       -- giu lich su cac lan chay
);

-- ================================================================ Chi muc
-- Ve ban do mot ngay: loc theo (chi so, ngay)
CREATE INDEX quan_trac_chi_so_ngay ON quan_trac (ma_chi_so, ngay);
CREATE INDEX du_bao_moi_nhat ON du_bao (ma_chi_so, id_o, ngay_chay DESC);
