#!/usr/bin/env python3
"""
Create test users for all roles in Supabase/database.
This script creates users directly in the database with hashed passwords.
"""

import sys
import os
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User
from app.core.security import hash_password

# Test users to create
TEST_USERS = [
    {
        "email": "exporter1@globalexports.com",
        "password": "exporter123",
        "full_name": "Exporter One",
        "role": "exporter"
    },
    {
        "email": "importer1@globalexports.com",
        "password": "importer123",
        "full_name": "Importer One",
        "role": "importer"
    },
    {
        "email": "bank1@globalexports.com",
        "password": "bank123",
        "full_name": "Bank Officer One",
        "role": "bank_officer"
    },
    {
        "email": "bankadmin@globalexports.com",
        "password": "bankadmin123",
        "full_name": "Bank Admin One",
        "role": "bank_admin"
    },
    {
        "email": "admin@trdrhub.com",
        "password": "admin123",
        "full_name": "System Admin",
        "role": "system_admin"
    }
]

def create_test_users():
    """Create all test users if they don't exist."""
    db = SessionLocal()
    created_count = 0
    existing_count = 0
    
    try:
        for user_data in TEST_USERS:
            # Check if user exists
            existing_user = db.query(User).filter(
                User.email == user_data["email"]
            ).first()
            
            if existing_user:
                print(f"⚠️  User already exists: {user_data['email']} (Role: {existing_user.role})")
                existing_count += 1
                continue
            
            # Create new user
            hashed_pw = hash_password(user_data["password"])
            new_user = User(
                email=user_data["email"],
                hashed_password=hashed_pw,
                full_name=user_data["full_name"],
                role=user_data["role"],
                is_active=True
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            print(f"✅ Created user: {new_user.email}")
            print(f"   Role: {new_user.role}, ID: {new_user.id}")
            created_count += 1
            
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating users: {e}")
        raise
    finally:
        db.close()
    
    print(f"\n📊 Summary: Created {created_count} users, {existing_count} already existed")
    return created_count, existing_count

if __name__ == "__main__":
    create_test_users()

