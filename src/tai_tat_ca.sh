#!/usr/bin/env bash
# Tai toan bo du lieu tu Google Earth Engine.
#
#   (ma project GEE doc tu src/ee_project.txt, hoac dat bien EE_PROJECT)
#   bash src/tai_tat_ca.sh
#
# Thu tu uu tien: NO2 va Aerosol Index (co du bao) + khi tuong truoc,
# roi moi den CO / SO2 / O3 (chi hien thi ban do).
# Script chay theo tung thang va tu bo qua thang da tai, nen dung giua
# chung roi chay lai van tiep tuc duoc.
set -u

TU=${TU:-2018-07}
DEN=${DEN:-2026-09}
cd "$(dirname "$0")"

chay() {
  echo ""
  echo "############ $* ############"
  python fetch_gee.py "$@" --tu "$TU" --den "$DEN"
}

echo "Bat dau: $(date)"
chay --chi-so no2
chay --chi-so aer_ai
chay --khi-tuong
chay --chi-so o3
chay --chi-so co
chay --chi-so so2
echo ""
echo "Xong luc: $(date)"
echo "So file da tai: $(ls ../data/raw/*.csv 2>/dev/null | wc -l)"
