#!/usr/bin/env python3
"""
Database setup script for LCopilot.
Handles database creation, migrations, and initial setup.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Command failed: {cmd}")
            print(f"Error: {result.stderr}")
            return False
        else:
            print(f"✅ {cmd}")
            if result.stdout.strip():
                print(f"   {result.stdout.strip()}")
            return True
    except Exception as e:
        print(f"❌ Exception running {cmd}: {e}")
        return False

def check_postgresql():
    """Check if PostgreSQL is running."""
    print("🔍 Checking PostgreSQL...")
    
    # Try to connect to default postgres database
    cmd = "psql -h localhost -U postgres -d postgres -c 'SELECT version();'"
    if run_command(cmd):
        return True
    
    # Try with different common setups
    alternatives = [
        "psql -h localhost -d postgres -c 'SELECT version();'",
        "docker exec -it postgres psql -U postgres -c 'SELECT version();'",
    ]
    
    for alt in alternatives:
        if run_command(alt):
            return True
    
    print("❌ PostgreSQL not accessible. Please ensure PostgreSQL is running.")
    print("   Options:")
    print("   1. Install locally: brew install postgresql (Mac) or apt-get install postgresql (Linux)")
    print("   2. Use Docker: docker run -d --name postgres -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:15")
    return False

def create_database():
    """Create the LCopilot database if it doesn't exist."""
    print("🔍 Creating database...")
    
    # Try to create database
    cmd = "psql -h localhost -U postgres -c 'CREATE DATABASE lcopilot;'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Database 'lcopilot' created")
        return True
    elif "already exists" in result.stderr:
        print("✅ Database 'lcopilot' already exists")
        return True
    else:
        print(f"❌ Failed to create database: {result.stderr}")
        return False

def setup_alembic():
    """Set up Alembic migrations."""
    api_dir = Path(__file__).parent / "apps" / "api"
    
    print("🔍 Setting up Alembic...")
    
    # Check if alembic.ini exists
    if not (api_dir / "alembic.ini").exists():
        print("❌ alembic.ini not found")
        return False
    
    # Run initial migration
    if run_command("alembic upgrade head", cwd=api_dir):
        print("✅ Database tables created")
        return True
    else:
        print("❌ Failed to run migrations")
        return False

def create_env_file():
    """Create .env file from example if it doesn't exist."""
    api_dir = Path(__file__).parent / "apps" / "api"
    env_file = api_dir / ".env"
    env_example = api_dir / ".env.example"
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    if env_example.exists():
        print("🔍 Creating .env from .env.example...")
        try:
            content = env_example.read_text()
            env_file.write_text(content)
            print("✅ .env file created")
            print("📝 Please review and update apps/api/.env with your settings")
            return True
        except Exception as e:
            print(f"❌ Failed to create .env: {e}")
            return False
    else:
        print("❌ .env.example not found")
        return False

def main():
    """Main setup function."""
    print("🚀 LCopilot Database Setup")
    print("=" * 50)
    
    steps = [
        ("Check PostgreSQL", check_postgresql),
        ("Create database", create_database), 
        ("Create .env file", create_env_file),
        ("Run migrations", setup_alembic),
    ]
    
    for name, func in steps:
        print(f"\n📋 {name}")
        if not func():
            print(f"\n❌ Setup failed at: {name}")
            print("Please fix the issue above and run this script again.")
            sys.exit(1)
    
    print("\n🎉 Database setup complete!")
    print("\n📋 Next steps:")
    print("1. Review apps/api/.env file")
    print("2. Start the backend: cd apps/api && uvicorn main:app --reload")
    print("3. Start the frontend: cd apps/web && npm run dev")

if __name__ == "__main__":
    main()