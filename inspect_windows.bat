@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist output mkdir output
set "PY="
for %%D in ("%USERPROFILE%\anaconda3" "C:\anaconda3" "D:\anaconda3" "D:\Anaconda3") do (
  if not defined PY if exist "%%~D\python.exe" set "PY=%%~D\python.exe"
)
if not defined PY for /f "delims=" %%P in ('where python 2^>nul') do if not defined PY set "PY=%%P"
"%PY%" -u src\inspect_zip.py > output\inspect_log.txt 2>&1
echo DONE >> output\inspect_log.txt
