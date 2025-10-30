# PowerShell script for Windows setup

Write-Host "🚀 Setting up TRDR Hub LCopilot Backend..." -ForegroundColor Green

# Check if Docker is installed
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "✅ Docker found. Using Docker setup..." -ForegroundColor Green
    
    # Start services with Docker Compose
    docker-compose up -d postgres redis
    
    Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    # Run migrations
    Write-Host "📊 Running database migrations..." -ForegroundColor Blue
    docker-compose exec api alembic upgrade head
    
    # Start the API
    Write-Host "🚀 Starting API server..." -ForegroundColor Green
    docker-compose up api
    
} else {
    Write-Host "❌ Docker not found. Please install Docker or use manual setup." -ForegroundColor Red
    Write-Host "📖 See setup-backend.md for manual setup instructions." -ForegroundColor Yellow
}
