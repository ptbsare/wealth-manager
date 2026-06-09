#!/bin/bash
# Wealth Manager Startup Script

set -e

echo "🚀 Starting Wealth Manager..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "📦 Installing dependencies..."
    uv sync
fi

# Create data directory
mkdir -p data

# Run database migrations (handled automatically on startup)
echo "🗄️  Database ready..."

# Start the application
echo "🌐 Starting server on http://localhost:8000"
echo ""
echo "📊 Access the application at: http://localhost:8000"
echo "📚 API documentation at: http://localhost:8000/docs"
echo ""

uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
