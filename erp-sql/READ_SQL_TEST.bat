@echo off
setlocal
title STARISH SQL READ ONLY
cd /d "D:\PRODUCTION AUTOMATION\EXCEL FILE\SQL_TEST"
if errorlevel 1 exit /b 1
py sql_reader.py
pause
