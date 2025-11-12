#!/usr/bin/env python3
"""Generate bcrypt_sha256 hash standalone (no app dependencies)."""

import hashlib
import bcrypt

def hash_password_bcrypt_sha256(password: str) -> str:
    """Generate bcrypt_sha256 hash (SHA256 pre-hash + bcrypt).
    
    Passlib format: $bcrypt-sha256$v=2,t=2b$<cost>$<hash>
    """
    # Pre-hash with SHA256 (this is what bcrypt_sha256 does)
    sha256_hash = hashlib.sha256(password.encode('utf-8')).digest()
    
    # Generate bcrypt hash of the SHA256 hash
    salt = bcrypt.gensalt()
    bcrypt_hash = bcrypt.hashpw(sha256_hash, salt).decode('utf-8')
    
    # Extract the cost and hash parts from bcrypt hash ($2b$12$...)
    # Format: $bcrypt-sha256$v=2,t=2b$<rest of bcrypt hash>
    parts = bcrypt_hash.split('$')
    if len(parts) >= 4:
        # parts[0] is empty, parts[1] is '2b', parts[2] is cost, parts[3] is hash
        cost_and_hash = '$'.join(parts[2:])  # Get '12$...hash'
        return f"$bcrypt-sha256$v=2,t=2b${cost_and_hash}"
    else:
        # Fallback
        return f"$bcrypt-sha256$v=2,t=2b${bcrypt_hash.split('$', 2)[-1]}"

if __name__ == "__main__":
    password = "exporter123"
    hash_val = hash_password_bcrypt_sha256(password)
    print(f"Password: {password}")
    print(f"Hash: {hash_val}")
    print(f"\nSQL to run in Supabase SQL Editor:")
    print(f"UPDATE users SET hashed_password = '{hash_val}' WHERE email = 'exporter1@globalexports.com';")

