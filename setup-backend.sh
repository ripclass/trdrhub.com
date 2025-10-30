#!/bin/bash

echo "🚀 Setting up TRDR Hub LCopilot Backend..."

# Check if Docker is installed
if command -v docker &> /dev/null; then
    echo "✅ Docker found. Using Docker setup..."
    
    # Start services with Docker Compose
    docker-compose up -d postgres redis
    
    echo "⏳ Waiting for services to be ready..."
    sleep 10
    
    # Run migrations
    echo "📊 Running database migrations..."
    docker-compose exec api alembic upgrade head
    
    # Start the API
    echo "🚀 Starting API server..."
    docker-compose up api
    
else
    echo "❌ Docker not found. Please install Docker or use manual setup."
    echo "📖 See setup-backend.md for manual setup instructions."
fi
