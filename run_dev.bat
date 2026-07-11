@echo off
echo ==================================================
echo   2. CREATOR-ARC ONE-CLICK DEVELOPER RUNNER       
echo ==================================================
echo.

:: Step 1: Initialize Backend Dependencies & Seed
echo [1/3] Checking Backend Python Dependencies...
cd apps\backend
python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install Python dependencies.
    goto error
)
echo.
echo Database Seeding Check...
python -c "from app.core.database import SessionLocal; from app.services.rewriter.migration import seed_style_references; seed_style_references(SessionLocal(), force_reseed=False)"
cd ..\..
echo.

:: Step 2: Initialize Frontend NPM Packages
echo [2/3] Checking Frontend Node.js Dependencies...
cd apps\frontend
call npm install
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install Node dependencies.
    goto error
)
cd ..\..
echo.

:: Step 3: Run FastAPI, Celery, and Next.js in Parallel
echo [3/3] Launching local servers in parallel...

:: A. Start Backend FastAPI
start "Creator-Arc Backend (FastAPI)" cmd /c "cd apps\backend && python -m uvicorn app.main:app --reload --port 8000"

:: B. Start Celery Worker
start "Creator-Arc Background Worker (Celery)" cmd /c "python -m celery -A workers.main worker --loglevel=info -P threads"

:: C. Start Frontend Next.js Dev Server
start "Creator-Arc Frontend (Next.js)" cmd /c "cd apps\frontend && npm run dev"

echo.
echo ==================================================
echo   SUCCESS: All servers are starting up in separate tabs!
echo   - Backend API URL:  http://localhost:8000
echo   - Frontend App URL: http://localhost:3000
echo ==================================================
echo.
pause
exit

:error
echo.
echo [FAIL] Setup failed. Please check the error logs above.
pause
