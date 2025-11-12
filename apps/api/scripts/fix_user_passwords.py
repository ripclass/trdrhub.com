#!/usr/bin/env python3
"""
Fix user passwords - update to bcrypt_sha256 format.
Run this on Render after deployment.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User
from app.auth import get_password_hash

USERS = [
    ("exporter1@globalexports.com", "exporter123"),
    ("importer1@globalexports.com", "importer123"),
    ("bank1@globalexports.com", "bank123"),
    ("bankadmin@globalexports.com", "bankadmin123"),
    ("admin@trdrhub.com", "admin123"),
]

def fix_passwords():
    db = SessionLocal()
    try:
        for email, password in USERS:
            user = db.query(User).filter(User.email == email).first()
            if user:
                user.hashed_password = get_password_hash(password)
                print(f"✅ Updated {email}")
            else:
                print(f"⚠️  User not found: {email}")
        db.commit()
        print("\n✅ All passwords updated!")
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    fix_passwords()

