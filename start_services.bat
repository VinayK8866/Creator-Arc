@echo off
echo ==================================================
echo   1. STARTING LOCAL SERVICES (POSTGRES & REDIS)   
echo ==================================================
echo.
docker compose up -d db redis
if %ERRORLEVEL% neq 0 (
    echo.
    echo [WARNING] Docker Compose command failed.
    echo Please make sure Docker Desktop is open and running!
) else (
    echo.
    echo [SUCCESS] PostgreSQL and Redis are running in the background.
)
echo.
pause
