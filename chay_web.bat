@echo off
rem Bam dup de mo trang web. Dong cua so nay la tat web.
cd /d "%~dp0src"
start "" /b powershell -NoProfile -Command "Start-Sleep 6; Start-Process http://127.0.0.1:8000"
python api.py
pause
