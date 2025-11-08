#!/bin/bash

# Co-Counsel - Single Command Launcher
# This script initializes dependencies and launches the full stack

echo "🚀 Co-Counsel - Starting Full Stack..."

# Create required directories
echo "📁 Creating required directories..."
mkdir -p var/storage/documents var/storage/graphs var/storage/telemetry var/models/huggingface var/models/whisper var/models/tts var/audio var/backups

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if backend dependencies need to be installed
if [ ! -f "backend/requirements.txt" ]; then
    echo "❌ Backend requirements not found. Please check your installation."
    exit 1
fi

# Check if frontend dependencies need to be installed
if [ ! -f "frontend/package.json" ]; then
    echo "❌ Frontend package.json not found. Please check your installation."
    exit 1
fi

echo "🐳 Starting Docker services..."
docker-compose up -d

echo "⏳ Waiting for services to start..."
sleep 10

echo "📋 Services started:"
echo "   🔹 API (Backend): http://localhost:8000"
echo "   🔹 Frontend: http://localhost:5173"
echo "   🔹 Neo4j: http://localhost:7474"
echo "   🔹 Qdrant: http://localhost:6333/dashboard"
echo "   🔹 STT Service: http://localhost:9000"
echo "   🔹 TTS Service: http://localhost:5002"

echo "✅ NinthOctopusMitten is now running!"
echo "   Use 'docker-compose logs -f' to view logs"
echo "   Use 'docker-compose down' to stop services"