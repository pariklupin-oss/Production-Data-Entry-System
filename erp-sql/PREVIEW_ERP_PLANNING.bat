@echo off
setlocal
title STARISH ERP Planning Preview
cd /d "%~dp0"
set /p "STARISH_PLAN_DATE=Planning date (DD-MM-YYYY): "
py erp_planning_to_sql.py --date "%STARISH_PLAN_DATE%"
echo This run previews planning only. It does not submit production or write SQL.
pause
