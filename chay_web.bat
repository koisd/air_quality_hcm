@echo off
chcp 65001 >nul
rem Bam dup de mo ung dung. Dong cua so nay la tat ung dung.
title Giam sat chat luong khong khi TP.HCM
set "PY=python"
if exist "%~dp0runtime\venv\Scripts\python.exe" set "PY=%~dp0runtime\venv\Scripts\python.exe"
cd /d "%~dp0src"
"%PY%" -c "import fastapi, uvicorn, psycopg, pandas, xgboost, sklearn" 2>nul
if errorlevel 1 (
  echo Ung dung chua duoc cai dat. Bam dup cai_dat.bat truoc.
  pause
  exit /b
)
rem Cho may chu san sang roi moi mo trinh duyet (PostgreSQL co the can 1-2 phut de khoi dong)
start "" /b powershell -NoProfile -Command "for($i=0;$i -lt 240;$i++){try{Invoke-WebRequest http://127.0.0.1:8000/api/thong-tin -UseBasicParsing -TimeoutSec 5 | Out-Null; Start-Process http://127.0.0.1:8000; break}catch{Start-Sleep 1}}"
"%PY%" api.py
pause
