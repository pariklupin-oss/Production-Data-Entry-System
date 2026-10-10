@echo off
setlocal
title STARISH SQL TEST - READ ONLY
cd /d "D:\PRODUCTION AUTOMATION\EXCEL FILE\SQL_TEST"
if errorlevel 1 (
 echo SQL_TEST folder missing. No watcher started.
 pause
 exit /b 1
)
echo Read-only checks only. This does not start the ERP watcher.
py preflight.py
if errorlevel 1 (
 echo Setup check needs attention. Share the displayed check results.
 pause
 exit /b 1
)
py -m unittest discover -s . -v
if errorlevel 1 (
 echo Offline tests failed. Do not start ERP integration.
 pause
 exit /b 1
)
echo Offline checks passed. ERP adapter is not connected yet.
pause
