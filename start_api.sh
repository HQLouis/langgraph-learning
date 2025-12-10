#!/bin/bash

# Quick start script for Lingolino Backend API

echo "🚀 Starting Lingolino Backend API..."
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Make sure you have your Google API credentials configured"
    echo ""
fi

# Start the server
echo "📡 Server will start at http://localhost:8000"
echo "📖 API Documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd "$(dirname "$0")"
source .venv/bin/activate
python -m backend.main

