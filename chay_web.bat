@echo off
chcp 65001 >nul
rem Bam dup de mo trang web. Dong cua so nay la tat web.
cd /d "%~dp0src"
python -c "import fastapi, uvicorn, psycopg, pandas, xgboost" 2>nul
if errorlevel 1 (
  echo Chua cai du thu vien. Mo PowerShell trong thu muc du an va chay:
  echo     pip install -r requirements-web.txt
  pause
  exit /b
)
rem Cho web san sang roi moi mo trinh duyet (PostgreSQL co the can 1-2 phut de khoi dong)
start "" /b powershell -NoProfile -Command "for($i=0;$i -lt 240;$i++){try{Invoke-WebRequest http://127.0.0.1:8000/api/thong-tin -UseBasicParsing -TimeoutSec 5 | Out-Null; Start-Process http://127.0.0.1:8000; break}catch{Start-Sleep 1}}"
python api.py
pause
