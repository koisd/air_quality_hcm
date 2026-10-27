@echo off
chcp 65001 >nul
rem Bam dup de cai dat. Chay lai nhieu lan duoc, buoc da xong se bo qua.
title Cai dat - Giam sat chat luong khong khi TP.HCM
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0cai_dat.ps1"
echo.
pause
