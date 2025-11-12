#!/usr/bin/env python3
"""Generate password hash using the app's security module."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import hash_password

if __name__ == "__main__":
    password = "exporter123"
    hash_val = hash_password(password)
    print(f"Password: {password}")
    print(f"Hash: {hash_val}")
    print(f"\nSQL to run in Supabase:")
    print(f"UPDATE users SET hashed_password = '{hash_val}' WHERE email = 'exporter1@globalexports.com';")

