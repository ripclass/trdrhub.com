#!/usr/bin/env python3
"""
Script to verify user registration data is stored correctly in the database.

Usage:
    python verify_user_data.py <email>
    python verify_user_data.py ripexpimp@gmail.com
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, Company
import json
from uuid import UUID


def verify_user_data(email: str):
    """Verify all registration data for a user."""
    db: Session = SessionLocal()
    
    try:
        print(f"\n{'='*60}")
        print(f"🔍 Verifying data for user: {email}")
        print(f"{'='*60}\n")
        
        # 1. Check if user exists
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ User not found in database!")
            return False
        
        print(f"✅ User found:")
        print(f"   - ID: {user.id}")
        print(f"   - Email: {user.email}")
        print(f"   - Full Name: {user.full_name}")
        print(f"   - Role: {user.role}")
        print(f"   - Is Active: {user.is_active}")
        print(f"   - Created At: {user.created_at}")
        
        # 2. Check company_id
        print(f"\n📋 Company Linkage:")
        if user.company_id:
            print(f"   ✅ company_id: {user.company_id}")
        else:
            print(f"   ❌ company_id: NULL (user not linked to company)")
        
        # 3. Check if company exists
        company = None
        if user.company_id:
            company = db.query(Company).filter(Company.id == user.company_id).first()
            if company:
                print(f"   ✅ Company record found by company_id")
            else:
                print(f"   ⚠️  Company ID exists but company record not found!")
        
        # 4. Try to find company by email
        if not company:
            company = db.query(Company).filter(Company.contact_email == email).first()
            if company:
                print(f"   ✅ Company record found by contact_email")
                print(f"   ⚠️  BUT user.company_id is NULL - needs linking!")
            else:
                print(f"   ❌ No company record found (by ID or email)")
        
        # 5. Display company data
        if company:
            print(f"\n🏢 Company Data:")
            print(f"   - ID: {company.id}")
            print(f"   - Name: {company.name}")
            print(f"   - Contact Email: {company.contact_email}")
            print(f"   - Legal Name: {company.legal_name or 'N/A'}")
            print(f"   - Registration Number: {company.registration_number or 'N/A'}")
            print(f"   - Country: {company.country or 'N/A'}")
            
            # Check event_metadata
            event_metadata = company.event_metadata or {}
            print(f"\n   📊 Event Metadata:")
            if event_metadata:
                print(f"      - business_type: {event_metadata.get('business_type', 'N/A')}")
                print(f"      - company_type: {event_metadata.get('company_type', 'N/A')}")
                print(f"      - company_size: {event_metadata.get('company_size', 'N/A')}")
                print(f"      - auto_created: {event_metadata.get('auto_created', False)}")
            else:
                print(f"      ⚠️  event_metadata is empty or NULL")
        
        # 6. Check onboarding_data
        print(f"\n📦 Onboarding Data (users.onboarding_data JSONB):")
        onboarding_data = user.onboarding_data or {}
        
        if onboarding_data:
            print(f"   ✅ onboarding_data exists")
            print(f"\n   📋 Contents:")
            
            # Company info
            company_info = onboarding_data.get('company', {})
            if company_info:
                print(f"      ✅ company:")
                print(f"         - name: {company_info.get('name', 'N/A')}")
                print(f"         - type: {company_info.get('type', 'N/A')}")
                print(f"         - size: {company_info.get('size', 'N/A')}")
                print(f"         - legal_name: {company_info.get('legal_name', 'N/A')}")
                print(f"         - registration_number: {company_info.get('registration_number', 'N/A')}")
                print(f"         - country: {company_info.get('country', 'N/A')}")
            else:
                print(f"      ❌ company: MISSING")
            
            # Business types
            business_types = onboarding_data.get('business_types', [])
            if business_types:
                print(f"      ✅ business_types: {business_types}")
            else:
                print(f"      ❌ business_types: MISSING or empty")
            
            # Contact person
            contact_person = onboarding_data.get('contact_person')
            if contact_person:
                print(f"      ✅ contact_person: {contact_person}")
            else:
                print(f"      ⚠️  contact_person: MISSING")
            
            # Full JSON dump
            print(f"\n   📄 Full JSON:")
            print(json.dumps(onboarding_data, indent=6, default=str))
        else:
            print(f"   ❌ onboarding_data is empty or NULL")
        
        # 7. Summary and recommendations
        print(f"\n{'='*60}")
        print(f"📊 SUMMARY")
        print(f"{'='*60}")
        
        issues = []
        if not user.company_id:
            issues.append("❌ User has no company_id")
        if not company:
            issues.append("❌ No company record found")
        if not onboarding_data:
            issues.append("❌ No onboarding_data")
        elif not onboarding_data.get('company'):
            issues.append("❌ onboarding_data.company is missing")
        elif not onboarding_data.get('business_types'):
            issues.append("❌ onboarding_data.business_types is missing")
        
        if issues:
            print(f"\n⚠️  ISSUES FOUND:")
            for issue in issues:
                print(f"   {issue}")
            print(f"\n💡 RECOMMENDATIONS:")
            if not user.company_id and company:
                print(f"   - Link user to company: UPDATE users SET company_id = '{company.id}' WHERE id = '{user.id}';")
            if not company:
                print(f"   - Company needs to be created (or restored from onboarding_data)")
            if not onboarding_data or not onboarding_data.get('company'):
                print(f"   - Onboarding data needs to be restored from company record")
        else:
            print(f"\n✅ ALL DATA PRESENT AND CORRECT!")
            print(f"   - User has company_id: {user.company_id}")
            print(f"   - Company record exists: {company.name if company else 'N/A'}")
            print(f"   - Onboarding data complete: Yes")
        
        print(f"\n{'='*60}\n")
        
        return len(issues) == 0
        
    except Exception as e:
        print(f"\n❌ Error verifying user data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_user_data.py <email>")
        print("Example: python verify_user_data.py ripexpimp@gmail.com")
        sys.exit(1)
    
    email = sys.argv[1]
    success = verify_user_data(email)
    sys.exit(0 if success else 1)

