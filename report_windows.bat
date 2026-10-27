@echo off
REM Rebuilds statistics, charts and report from the existing output\tables (no data reload).
cd /d "%~dp0"
set PYTHONUTF8=1
set "PY="
for %%D in ("%USERPROFILE%\anaconda3" "C:\anaconda3" "D:\anaconda3" "D:\Anaconda3") do (
  if not defined PY if exist "%%~D\python.exe" set "PY=%%~D\python.exe"
)
if not defined PY for /f "delims=" %%P in ('where python 2^>nul') do if not defined PY set "PY=%%P"
"%PY%" -u -c "import sys; sys.path.insert(0, 'src'); from pathlib import Path; from stats_tests import run_tests; from make_report import build; o = Path('output'); run_tests(o); build(o); print('REPORT_OK')" > output\report_log.txt 2>&1
