#!/usr/bin/env python3
"""
Script to reset admin user password in the database.

Usage:
    python scripts/reset_admin_password.py admin@trdrhub.com newpassword123

Or set environment variables:
    ADMIN_EMAIL=admin@trdrhub.com ADMIN_PASSWORD=newpassword123 python scripts/reset_admin_password.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.security import hash_password
from app.database import SessionLocal
from app.models import User


def reset_admin_password(email: str, new_password: str):
    """Reset password for an admin user."""
    db = SessionLocal()
    try:
        # Find user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ User not found: {email}")
            return False
        
        # Check if user is admin
        if user.role not in ('system_admin', 'tenant_admin'):
            print(f"⚠️  Warning: User {email} has role '{user.role}', not an admin role")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return False
        
        # Generate new password hash
        print(f"🔐 Generating password hash for {email}...")
        hashed_password = hash_password(new_password)
        
        # Update user
        user.hashed_password = hashed_password
        db.commit()
        db.refresh(user)
        
        print(f"✅ Password reset successful for {email}")
        print(f"   Role: {user.role}")
        print(f"   You can now log in at https://trdrhub.com/admin/login")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error resetting password: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    # Get email and password from command line or environment
    if len(sys.argv) >= 3:
        email = sys.argv[1]
        password = sys.argv[2]
    elif len(sys.argv) >= 2:
        email = sys.argv[1]
        password = os.getenv("ADMIN_PASSWORD")
        if not password:
            password = input(f"Enter new password for {email}: ")
    else:
        email = os.getenv("ADMIN_EMAIL", "admin@trdrhub.com")
        password = os.getenv("ADMIN_PASSWORD")
        if not password:
            print("Usage: python reset_admin_password.py <email> <password>")
            print("   Or: ADMIN_EMAIL=... ADMIN_PASSWORD=... python reset_admin_password.py")
            sys.exit(1)
    
    success = reset_admin_password(email, password)
    sys.exit(0 if success else 1)

