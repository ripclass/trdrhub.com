#!/usr/bin/env python3
"""
Quick script to fix exporter1 password hash.
Run this on Render via shell or create a one-time endpoint.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User
from app.core.security import hash_password, verify_password

def fix_exporter_password():
    """Fix password hash for exporter1@globalexports.com"""
    db = SessionLocal()
    
    try:
        email = "exporter1@globalexports.com"
        password = "exporter123"
        
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"❌ User not found: {email}")
            return False
        
        print(f"📋 Current hash prefix: {user.hashed_password[:30]}...")
        
        # Test current password verification
        current_works = verify_password(password, user.hashed_password)
        print(f"🔍 Current password verification: {'✅ WORKS' if current_works else '❌ FAILS'}")
        
        if not current_works:
            # Generate new hash using bcrypt_sha256
            new_hash = hash_password(password)
            print(f"🔄 New hash prefix: {new_hash[:30]}...")
            
            user.hashed_password = new_hash
            db.commit()
            
            # Verify new hash works
            if verify_password(password, new_hash):
                print(f"✅ Password updated and verified for: {email}")
                return True
            else:
                print(f"❌ New password hash verification failed!")
                db.rollback()
                return False
        else:
            print(f"✅ Password already works, no update needed")
            return True
            
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = fix_exporter_password()
    sys.exit(0 if success else 1)

