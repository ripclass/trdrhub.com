#!/usr/bin/env python3
"""
Quick script to create a test user for end-to-end testing.
Usage: python scripts/create_test_user.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User
from app.core.security import hash_password

def create_test_user():
    """Create exporter1@globalexports.com user if it doesn't exist."""
    db = SessionLocal()
    try:
        # Check if user exists
        existing_user = db.query(User).filter(
            User.email == "exporter1@globalexports.com"
        ).first()
        
        if existing_user:
            print(f"User already exists: {existing_user.email} (ID: {existing_user.id})")
            print(f"Role: {existing_user.role}, Active: {existing_user.is_active}")
            return existing_user
        
        # Create new user
        hashed_pw = hash_password("exporter123")
        new_user = User(
            email="exporter1@globalexports.com",
            hashed_password=hashed_pw,
            full_name="Exporter One",
            role="exporter",
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"✅ Created user: {new_user.email} (ID: {new_user.id})")
        print(f"Role: {new_user.role}, Active: {new_user.is_active}")
        return new_user
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating user: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()

