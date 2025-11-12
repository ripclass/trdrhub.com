#!/usr/bin/env python3
"""
Update user passwords to use bcrypt_sha256 format (compatible with passlib).
This script updates existing users with the correct password hash format.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User
from app.auth import hash_password

# Test users and their passwords
TEST_USERS = [
    {"email": "exporter1@globalexports.com", "password": "exporter123"},
    {"email": "importer1@globalexports.com", "password": "importer123"},
    {"email": "bank1@globalexports.com", "password": "bank123"},
    {"email": "bankadmin@globalexports.com", "password": "bankadmin123"},
    {"email": "admin@trdrhub.com", "password": "admin123"},
]

def update_user_passwords():
    """Update passwords for test users to use bcrypt_sha256 format."""
    db = SessionLocal()
    updated_count = 0
    
    try:
        for user_data in TEST_USERS:
            user = db.query(User).filter(User.email == user_data["email"]).first()
            
            if not user:
                print(f"⚠️  User not found: {user_data['email']}")
                continue
            
            # Generate new hash using bcrypt_sha256 (passlib format)
            new_hash = hash_password(user_data["password"])
            user.hashed_password = new_hash
            
            db.commit()
            print(f"✅ Updated password for: {user.email} (Role: {user.role})")
            updated_count += 1
            
    except Exception as e:
        db.rollback()
        print(f"❌ Error updating passwords: {e}")
        raise
    finally:
        db.close()
    
    print(f"\n📊 Updated {updated_count} user passwords")
    return updated_count

if __name__ == "__main__":
    update_user_passwords()

