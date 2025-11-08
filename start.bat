@echo off
REM NinthOctopusMitten - Single Command Launcher for Windows
REM This script initializes dependencies and launches the full stack

echo 🚀 NinthOctopusMitten - Starting Full Stack...

REM Create required directories
echo 📁 Creating required directories...
mkdir var\storage\documents var\storage\graphs var\storage\telemetry var\models\huggingface var\models\whisper var\models\tts var\audio var\backups 2>nul

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker first.
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    exit /b 1
)

REM Check if backend dependencies exist
if not exist "backend\requirements.txt" (
    echo ❌ Backend requirements not found. Please check your installation.
    exit /b 1
)

REM Check if frontend dependencies exist
if not exist "frontend\package.json" (
    echo ❌ Frontend package.json not found. Please check your installation.
    exit /b 1
)

echo 🐳 Starting Docker services...
docker-compose up -d

echo ⏳ Waiting for services to start...
timeout /t 10 /nobreak >nul

echo 📋 Services started:
echo    🔹 API (Backend): http://localhost:8000
echo    🔹 Frontend: http://localhost:5173
echo    🔹 Neo4j: http://localhost:7474
echo    🔹 Qdrant: http://localhost:6333/dashboard
echo    🔹 STT Service: http://localhost:9000
echo    🔹 TTS Service: http://localhost:5002

echo ✅ NinthOctopusMitten is now running!
echo    Use 'docker-compose logs -f' to view logs
echo    Use 'docker-compose down' to stop services

pause