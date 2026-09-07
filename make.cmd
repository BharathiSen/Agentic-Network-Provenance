@echo off
rem Windows shim so the Makefile targets are runnable without GNU make.
rem Keep every target in sync with the Makefile.
setlocal
if /i "%~1"=="up"   goto up
if /i "%~1"=="down" goto down
if /i "%~1"=="test" goto test
if /i "%~1"=="lint" goto lint
if /i "%~1"=="fmt"  goto fmt
if /i "%~1"=="schema" goto schema
if not "%~1"=="" echo make.cmd: unknown target "%~1"
echo usage: make ^<up^|down^|test^|lint^|fmt^|schema^>
exit /b 2

:up
docker compose up -d
exit /b %errorlevel%

:down
docker compose down
exit /b %errorlevel%

:test
uv run pytest
exit /b %errorlevel%

:lint
uv run ruff check .
exit /b %errorlevel%

:fmt
uv run black .
exit /b %errorlevel%

:schema
uv run python scripts/export_schema.py
exit /b %errorlevel%
