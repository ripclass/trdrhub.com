"""
Quick verification script for org isolation.

Checks that org filtering is working correctly at the API level.

Usage:
    python scripts/verify_org_isolation.py <org1_id> <org2_id> <user1_token> <user2_token>
"""

import sys
import requests
import json

API_BASE_URL = "http://localhost:8000"  # Update for staging/prod

def verify_org_isolation(org1_id, org2_id, user1_token, user2_token):
    """Verify org isolation by checking API responses."""
    
    headers1 = {"Authorization": f"Bearer {user1_token}"}
    headers2 = {"Authorization": f"Bearer {user2_token}"}
    
    print("🔍 Verifying Org Isolation...\n")
    
    # Test 1: Results endpoint
    print("Test 1: Results endpoint")
    print("-" * 50)
    
    # User 1 with Org 1
    r1_org1 = requests.get(
        f"{API_BASE_URL}/bank/results?org={org1_id}",
        headers=headers1
    )
    print(f"User 1 + Org 1: {r1_org1.status_code}")
    if r1_org1.status_code == 200:
        data1_org1 = r1_org1.json()
        lc_numbers_1 = [r.get('lc_number') for r in data1_org1.get('results', [])]
        print(f"  LC Numbers: {lc_numbers_1[:5]}...")
        print(f"  Total: {len(data1_org1.get('results', []))}")
    
    # User 1 with Org 2 (should fail or return empty)
    r1_org2 = requests.get(
        f"{API_BASE_URL}/bank/results?org={org2_id}",
        headers=headers1
    )
    print(f"User 1 + Org 2: {r1_org2.status_code}")
    if r1_org2.status_code == 200:
        data1_org2 = r1_org2.json()
        print(f"  Total: {len(data1_org2.get('results', []))}")
        if len(data1_org2.get('results', [])) > 0:
            print("  ⚠️  WARNING: User 1 can see Org 2 data!")
    
    # User 2 with Org 2
    r2_org2 = requests.get(
        f"{API_BASE_URL}/bank/results?org={org2_id}",
        headers=headers2
    )
    print(f"User 2 + Org 2: {r2_org2.status_code}")
    if r2_org2.status_code == 200:
        data2_org2 = r2_org2.json()
        lc_numbers_2 = [r.get('lc_number') for r in data2_org2.get('results', [])]
        print(f"  LC Numbers: {lc_numbers_2[:5]}...")
        print(f"  Total: {len(data2_org2.get('results', []))}")
    
    # User 2 with Org 1 (should fail or return empty)
    r2_org1 = requests.get(
        f"{API_BASE_URL}/bank/results?org={org1_id}",
        headers=headers2
    )
    print(f"User 2 + Org 1: {r2_org1.status_code}")
    if r2_org1.status_code == 200:
        data2_org1 = r2_org1.json()
        print(f"  Total: {len(data2_org1.get('results', []))}")
        if len(data2_org1.get('results', [])) > 0:
            print("  ⚠️  WARNING: User 2 can see Org 1 data!")
    
    # Check for overlap
    if r1_org1.status_code == 200 and r2_org2.status_code == 200:
        lc1_set = set(lc_numbers_1)
        lc2_set = set(lc_numbers_2)
        overlap = lc1_set & lc2_set
        if overlap:
            print(f"\n  ❌ DATA LEAKAGE DETECTED!")
            print(f"  Overlapping LC numbers: {overlap}")
        else:
            print(f"\n  ✅ No data leakage - LC numbers are isolated")
    
    print("\n" + "=" * 50)
    
    # Test 2: Approvals endpoint
    print("\nTest 2: Approvals endpoint")
    print("-" * 50)
    
    r1_approvals = requests.get(
        f"{API_BASE_URL}/bank/workflow/approvals?org={org1_id}",
        headers=headers1
    )
    print(f"User 1 + Org 1 Approvals: {r1_approvals.status_code}")
    if r1_approvals.status_code == 200:
        data = r1_approvals.json()
        print(f"  Total: {len(data.get('approvals', []))}")
    
    r2_approvals = requests.get(
        f"{API_BASE_URL}/bank/workflow/approvals?org={org2_id}",
        headers=headers2
    )
    print(f"User 2 + Org 2 Approvals: {r2_approvals.status_code}")
    if r2_approvals.status_code == 200:
        data = r2_approvals.json()
        print(f"  Total: {len(data.get('approvals', []))}")
    
    print("\n" + "=" * 50)
    
    # Test 3: Duplicates endpoint
    print("\nTest 3: Duplicates endpoint")
    print("-" * 50)
    
    # Get a session ID from Org 1
    if r1_org1.status_code == 200 and len(data1_org1.get('results', [])) > 0:
        session_id_org1 = data1_org1['results'][0]['jobId']
        
        r1_duplicates = requests.get(
            f"{API_BASE_URL}/bank/duplicates/candidates/{session_id_org1}?org={org1_id}",
            headers=headers1
        )
        print(f"User 1 + Org 1 Duplicates: {r1_duplicates.status_code}")
        if r1_duplicates.status_code == 200:
            data = r1_duplicates.json()
            print(f"  Candidates: {len(data.get('candidates', []))}")
    
    print("\n✅ Verification complete!")
    print("\nNext steps:")
    print("1. Review the results above")
    print("2. If any warnings appear, investigate the issue")
    print("3. Run manual UI tests (see docs/BANK_LAUNCH_TESTS.md)")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python verify_org_isolation.py <org1_id> <org2_id> <user1_token> <user2_token>")
        sys.exit(1)
    
    org1_id = sys.argv[1]
    org2_id = sys.argv[2]
    user1_token = sys.argv[3]
    user2_token = sys.argv[4]
    
    verify_org_isolation(org1_id, org2_id, user1_token, user2_token)

