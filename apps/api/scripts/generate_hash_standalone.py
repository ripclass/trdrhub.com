#!/usr/bin/env python3
"""Generate bcrypt_sha256 hash standalone (no app dependencies)."""

import hashlib
import bcrypt

def hash_password_bcrypt_sha256(password: str) -> str:
    """Generate bcrypt_sha256 hash (SHA256 pre-hash + bcrypt)."""
    # Pre-hash with SHA256 (this is what bcrypt_sha256 does)
    sha256_hash = hashlib.sha256(password.encode('utf-8')).digest()
    
    # Generate bcrypt hash of the SHA256 hash
    salt = bcrypt.gensalt()
    bcrypt_hash = bcrypt.hashpw(sha256_hash, salt)
    
    # Format as bcrypt_sha256: $bcrypt-sha256$ + bcrypt hash
    return f"$bcrypt-sha256${bcrypt_hash.decode('utf-8')}"

if __name__ == "__main__":
    password = "exporter123"
    hash_val = hash_password_bcrypt_sha256(password)
    print(f"Password: {password}")
    print(f"Hash: {hash_val}")
    print(f"\nSQL to run in Supabase SQL Editor:")
    print(f"UPDATE users SET hashed_password = '{hash_val}' WHERE email = 'exporter1@globalexports.com';")

