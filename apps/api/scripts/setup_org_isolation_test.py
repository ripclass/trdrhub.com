"""
Helper script to set up test data for Org Isolation Test.

Run this script to create:
- 2 test organizations
- 2 test users (one per org)
- Test validation sessions for each org

Usage:
    python scripts/setup_org_isolation_test.py
"""

import os
import sys
import uuid
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import User, Company
from app.models.bank_orgs import BankOrg, UserOrgAccess, OrgKind, OrgAccessRole
from app.models.sessions import ValidationSession, SessionStatus

def setup_test_data():
    """Set up test data for org isolation testing."""
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        print("🔧 Setting up Org Isolation Test Data...")
        
        # Find a bank company (or create one)
        bank_company = db.query(Company).filter(
            Company.company_type == 'bank'
        ).first()
        
        if not bank_company:
            print("❌ No bank company found. Please create one first.")
            return
        
        print(f"✅ Using bank company: {bank_company.name} (ID: {bank_company.id})")
        
        # Create Org 1: APAC
        org1_id = uuid.uuid4()
        org1 = BankOrg(
            id=org1_id,
            bank_company_id=bank_company.id,
            parent_id=None,
            kind=OrgKind.REGION.value,
            name="Test Bank - APAC",
            code="APAC",
            path=f"/{org1_id}",
            level=0,
            sort_order=1,
            is_active=True,
        )
        db.add(org1)
        db.flush()
        print(f"✅ Created Org 1: {org1.name} (ID: {org1_id})")
        
        # Create Org 2: EMEA
        org2_id = uuid.uuid4()
        org2 = BankOrg(
            id=org2_id,
            bank_company_id=bank_company.id,
            parent_id=None,
            kind=OrgKind.REGION.value,
            name="Test Bank - EMEA",
            code="EMEA",
            path=f"/{org2_id}",
            level=0,
            sort_order=2,
            is_active=True,
        )
        db.add(org2)
        db.flush()
        print(f"✅ Created Org 2: {org2.name} (ID: {org2_id})")
        
        # Find existing bank users (use any bank user for testing)
        bank_users = db.query(User).filter(
            User.company_id == bank_company.id,
            User.role.in_(['bank_admin', 'bank_officer'])
        ).limit(2).all()
        
        user1_id = None
        user2_id = None
        
        if len(bank_users) >= 1:
            user1_id = bank_users[0].id
            print(f"✅ Using existing User 1: {bank_users[0].email} (ID: {user1_id})")
        
        if len(bank_users) >= 2:
            user2_id = bank_users[1].id
            print(f"✅ Using existing User 2: {bank_users[1].email} (ID: {user2_id})")
        elif len(bank_users) == 1:
            # Use same user for both orgs (for testing)
            user2_id = bank_users[0].id
            print(f"✅ Using same user for both orgs: {bank_users[0].email} (ID: {user2_id})")
        
        if not bank_users:
            print("⚠️  No bank users found. Orgs will be created but no user assignments.")
            print("   You can assign users later via API or SQL.")
        
        # Assign users to orgs
        if user1_id:
            # Check if access already exists
            existing_access1 = db.query(UserOrgAccess).filter(
                UserOrgAccess.user_id == user1_id,
                UserOrgAccess.org_id == org1_id
            ).first()
            if not existing_access1:
                access1 = UserOrgAccess(
                    user_id=user1_id,
                    org_id=org1_id,
                    role=OrgAccessRole.ADMIN.value,  # Use ADMIN role for testing
                )
                db.add(access1)
                print(f"✅ Assigned User 1 to Org 1")
            else:
                print(f"✅ User 1 already has access to Org 1")
        
        if user2_id and user2_id != user1_id:  # Only if different user
            # Check if access already exists
            existing_access2 = db.query(UserOrgAccess).filter(
                UserOrgAccess.user_id == user2_id,
                UserOrgAccess.org_id == org2_id
            ).first()
            if not existing_access2:
                access2 = UserOrgAccess(
                    user_id=user2_id,
                    org_id=org2_id,
                    role=OrgAccessRole.ADMIN.value,  # Use ADMIN role for testing
                )
                db.add(access2)
                print(f"✅ Assigned User 2 to Org 2")
            else:
                print(f"✅ User 2 already has access to Org 2")
        
        # If same user, assign to both orgs
        if user1_id and user2_id == user1_id:
            existing_access2 = db.query(UserOrgAccess).filter(
                UserOrgAccess.user_id == user1_id,
                UserOrgAccess.org_id == org2_id
            ).first()
            if not existing_access2:
                access2 = UserOrgAccess(
                    user_id=user1_id,
                    org_id=org2_id,
                    role=OrgAccessRole.ADMIN.value,
                )
                db.add(access2)
                print(f"✅ Assigned same user to Org 2 (for testing)")
        
        # Create test validation sessions
        print("\n📝 Creating test validation sessions...")
        
        # Get existing sessions to tag
        existing_sessions = db.query(ValidationSession).filter(
            ValidationSession.company_id == bank_company.id,
            ValidationSession.deleted_at.is_(None)
        ).limit(10).all()
        
        if len(existing_sessions) < 10:
            print(f"⚠️  Only {len(existing_sessions)} sessions found. Need at least 10 for proper testing.")
        
        # Tag first half as Org 1, second half as Org 2
        mid_point = len(existing_sessions) // 2
        
        for i, session in enumerate(existing_sessions[:mid_point]):
            # Tag as Org 1
            if session.extracted_data:
                import json
                data = session.extracted_data if isinstance(session.extracted_data, dict) else json.loads(session.extracted_data)
            else:
                data = {}
            
            if 'bank_metadata' not in data:
                data['bank_metadata'] = {}
            
            data['bank_metadata']['org_id'] = str(org1_id)
            data['bank_metadata']['client_name'] = f"APAC Client {i+1}"
            data['bank_metadata']['lc_number'] = f"LC-APAC-{i+1:03d}"
            
            session.extracted_data = data
            print(f"  ✅ Tagged session {session.id} as Org 1 (LC-APAC-{i+1:03d})")
        
        for i, session in enumerate(existing_sessions[mid_point:]):
            # Tag as Org 2
            if session.extracted_data:
                import json
                data = session.extracted_data if isinstance(session.extracted_data, dict) else json.loads(session.extracted_data)
            else:
                data = {}
            
            if 'bank_metadata' not in data:
                data['bank_metadata'] = {}
            
            data['bank_metadata']['org_id'] = str(org2_id)
            data['bank_metadata']['client_name'] = f"EMEA Client {i+1}"
            data['bank_metadata']['lc_number'] = f"LC-EMEA-{i+1:03d}"
            
            session.extracted_data = data
            print(f"  ✅ Tagged session {session.id} as Org 2 (LC-EMEA-{i+1:03d})")
        
        db.commit()
        
        print("\n✅ Test data setup complete!")
        print("\n📋 Test Configuration:")
        print(f"  Org 1 ID: {org1_id}")
        print(f"  Org 1 Name: {org1.name}")
        print(f"  Org 2 ID: {org2_id}")
        print(f"  Org 2 Name: {org2.name}")
        if user1_id:
            print(f"  User 1 ID: {user1_id}")
        if user2_id:
            print(f"  User 2 ID: {user2_id}")
        print(f"\n  Sessions tagged: {len(existing_sessions)}")
        print(f"    - Org 1: {mid_point} sessions")
        print(f"    - Org 2: {len(existing_sessions) - mid_point} sessions")
        
        print("\n🧪 Ready to run Org Isolation Test!")
        print("   See docs/BANK_LAUNCH_TESTS.md for test steps")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error setting up test data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    setup_test_data()

