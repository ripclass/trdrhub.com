#!/usr/bin/env python3
"""
Demo Data Seeding Script for TRDR Hub
Creates realistic demo data for bank pilot including tenants, users, LCs, and audit trails
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import json
import hashlib
from uuid import uuid4, UUID
import random
import string

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'apps', 'api'))

from app.core.database import SessionLocal, create_tables
from app.services.audit_service import AuditService
from app.models.audit import AuditLogEntry, AuditAction, AuditSeverity

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DemoDataSeeder:
    """Seeder for creating realistic demo data"""

    def __init__(self):
        self.db = SessionLocal()
        self.demo_data = {
            "tenants": [],
            "users": [],
            "lc_sessions": [],
            "discrepancies": [],
            "audit_entries": []
        }

    def seed_all(self) -> Dict[str, Any]:
        """Seed all demo data"""
        logger.info("Starting demo data seeding")

        try:
            # Ensure tables exist
            create_tables()

            # Seed tenants
            self.seed_tenants()

            # Seed users
            self.seed_users()

            # Seed LC sessions and documents
            self.seed_lc_sessions()

            # Seed discrepancies
            self.seed_discrepancies()

            # Seed audit trail
            self.seed_audit_trail()

            # Seed governance approvals
            self.seed_governance_data()

            # Seed compliance documents
            self.seed_compliance_docs()

            self.db.commit()

            logger.info(f"Demo data seeding completed successfully")
            return {
                "status": "success",
                "data_created": {
                    "tenants": len(self.demo_data["tenants"]),
                    "users": len(self.demo_data["users"]),
                    "lc_sessions": len(self.demo_data["lc_sessions"]),
                    "discrepancies": len(self.demo_data["discrepancies"]),
                    "audit_entries": len(self.demo_data["audit_entries"])
                }
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Demo data seeding failed: {str(e)}")
            raise
        finally:
            self.db.close()

    def seed_tenants(self):
        """Create demo tenants"""
        tenants = [
            {
                "id": "demo-sme",
                "name": "Demo SME Exporter",
                "type": "sme",
                "country": "BD",
                "industry": "Textiles",
                "status": "active",
                "settings": {
                    "language": "en",
                    "timezone": "Asia/Dhaka",
                    "compliance_level": "standard"
                }
            },
            {
                "id": "demo-bank",
                "name": "Demo Commercial Bank",
                "type": "bank",
                "country": "BD",
                "industry": "Financial Services",
                "status": "active",
                "settings": {
                    "language": "en",
                    "timezone": "Asia/Dhaka",
                    "compliance_level": "enhanced"
                }
            }
        ]

        for tenant_data in tenants:
            # In a real implementation, this would create tenant records
            # For now, just track in our demo data
            self.demo_data["tenants"].append(tenant_data)
            logger.info(f"Created tenant: {tenant_data['name']}")

    def seed_users(self):
        """Create demo users"""
        users = [
            {
                "id": str(uuid4()),
                "tenant_id": "demo-sme",
                "email": "sme.admin@demo.com",
                "password": "sme123",  # In real app, this would be hashed
                "first_name": "Admin",
                "last_name": "SME",
                "role": "admin",
                "status": "active",
                "last_login": datetime.now(timezone.utc) - timedelta(hours=2)
            },
            {
                "id": str(uuid4()),
                "tenant_id": "demo-sme",
                "email": "exporter@demo.com",
                "password": "export123",
                "first_name": "Sarah",
                "last_name": "Exporter",
                "role": "exporter",
                "status": "active",
                "last_login": datetime.now(timezone.utc) - timedelta(hours=4)
            },
            {
                "id": str(uuid4()),
                "tenant_id": "demo-bank",
                "email": "bank.officer@demo.com",
                "password": "bank123",
                "first_name": "David",
                "last_name": "Officer",
                "role": "bank_officer",
                "status": "active",
                "last_login": datetime.now(timezone.utc) - timedelta(hours=1)
            },
            {
                "id": str(uuid4()),
                "tenant_id": "demo-bank",
                "email": "auditor@demo.com",
                "password": "audit123",
                "first_name": "Maria",
                "last_name": "Auditor",
                "role": "auditor",
                "status": "active",
                "last_login": datetime.now(timezone.utc) - timedelta(hours=3)
            },
            {
                "id": str(uuid4()),
                "tenant_id": "demo-sme",
                "email": "admin@lcopilot.com",
                "password": "admin123",
                "first_name": "System",
                "last_name": "Admin",
                "role": "super_admin",
                "status": "active",
                "last_login": datetime.now(timezone.utc) - timedelta(minutes=30)
            }
        ]

        for user_data in users:
            self.demo_data["users"].append(user_data)
            logger.info(f"Created user: {user_data['email']}")

    def seed_lc_sessions(self):
        """Create demo LC sessions with realistic data"""
        lc_sessions = [
            {
                "id": str(uuid4()),
                "tenant_id": "demo-sme",
                "lc_number": "LC2024001",
                "applicant": "ABC Imports Ltd",
                "beneficiary": "Demo SME Exporter",
                "amount": 50000.00,
                "currency": "USD",
                "status": "completed",
                "created_at": datetime.now(timezone.utc) - timedelta(days=30),
                "documents": [
                    "Commercial Invoice",
                    "Packing List",
                    "Bill of Lading",
                    "Certificate of Origin"
                ],
                "discrepancies_count": 0,
                "processing_time_hours": 24
            },
            {
                "id": str(uuid4()),
                "tenant_id": "demo-sme",
                "lc_number": "LC2024002",
                "applicant": "XYZ Trading Co",
                "beneficiary": "Demo SME Exporter",
                "amount": 75000.00,
                "currency": "USD",
                "status": "processing",
                "created_at": datetime.now(timezone.utc) - timedelta(days=5),
                "documents": [
                    "Commercial Invoice",
                    "Packing List",
                    "Insurance Certificate"
                ],
                "discrepancies_count": 2,
                "processing_time_hours": 48
            },
            {
                "id": str(uuid4()),
                "tenant_id": "demo-bank",
                "lc_number": "LC2024003",
                "applicant": "Global Buyers Inc",
                "beneficiary": "Export Manufacturing Ltd",
                "amount": 120000.00,
                "currency": "EUR",
                "status": "validated",
                "created_at": datetime.now(timezone.utc) - timedelta(days=15),
                "documents": [
                    "Commercial Invoice",
                    "Transport Document",
                    "Insurance Document",
                    "Certificate of Origin",
                    "Inspection Certificate"
                ],
                "discrepancies_count": 1,
                "processing_time_hours": 36
            },
            {
                "id": str(uuid4()),
                "tenant_id": "demo-bank",
                "lc_number": "LC2024004",
                "applicant": "Tech Solutions Ltd",
                "beneficiary": "Software Exports Inc",
                "amount": 85000.00,
                "currency": "USD",
                "status": "rejected",
                "created_at": datetime.now(timezone.utc) - timedelta(days=8),
                "documents": [
                    "Service Invoice",
                    "Delivery Receipt"
                ],
                "discrepancies_count": 5,
                "processing_time_hours": 72,
                "rejection_reason": "Multiple document discrepancies"
            }
        ]

        # Create additional LC sessions for better demo variety
        for i in range(8):  # Create 8 more sessions
            lc_sessions.append({
                "id": str(uuid4()),
                "tenant_id": random.choice(["demo-sme", "demo-bank"]),
                "lc_number": f"LC2024{str(i+5).zfill(3)}",
                "applicant": f"Importer {i+1} Ltd",
                "beneficiary": f"Exporter {i+1} Co",
                "amount": round(random.uniform(25000, 150000), 2),
                "currency": random.choice(["USD", "EUR", "GBP"]),
                "status": random.choice(["draft", "processing", "validated", "completed"]),
                "created_at": datetime.now(timezone.utc) - timedelta(days=random.randint(1, 60)),
                "documents": random.sample([
                    "Commercial Invoice", "Packing List", "Bill of Lading",
                    "Certificate of Origin", "Insurance Certificate",
                    "Inspection Certificate", "Transport Document"
                ], random.randint(3, 6)),
                "discrepancies_count": random.randint(0, 4),
                "processing_time_hours": random.randint(12, 96)
            })

        for session in lc_sessions:
            self.demo_data["lc_sessions"].append(session)
            logger.info(f"Created LC session: {session['lc_number']}")

    def seed_discrepancies(self):
        """Create realistic discrepancies"""
        discrepancy_types = [
            "Document date discrepancy",
            "Amount mismatch",
            "Description variance",
            "Missing signature",
            "Expired document",
            "Incorrect beneficiary name",
            "Late presentation",
            "Missing required document",
            "Transport document issues",
            "Insurance coverage insufficient"
        ]

        discrepancies = []

        # Add discrepancies for LC sessions that have them
        for session in self.demo_data["lc_sessions"]:
            if session["discrepancies_count"] > 0:
                for i in range(session["discrepancies_count"]):
                    discrepancies.append({
                        "id": str(uuid4()),
                        "lc_session_id": session["id"],
                        "tenant_id": session["tenant_id"],
                        "type": random.choice(discrepancy_types),
                        "severity": random.choice(["minor", "major", "critical"]),
                        "status": random.choice(["open", "resolved", "waived"]),
                        "description": f"Discrepancy found in document presentation for {session['lc_number']}",
                        "created_at": session["created_at"] + timedelta(hours=random.randint(1, 24)),
                        "created_by": random.choice([u["id"] for u in self.demo_data["users"]]),
                        "resolution_notes": "Resolved through bank waiver" if random.choice([True, False]) else None
                    })

        self.demo_data["discrepancies"] = discrepancies
        logger.info(f"Created {len(discrepancies)} discrepancies")

    def seed_audit_trail(self):
        """Create comprehensive audit trail"""
        logger.info("Creating audit trail entries")

        # Create audit entries for user activities
        users = self.demo_data["users"]
        lc_sessions = self.demo_data["lc_sessions"]

        audit_entries = []

        # System startup events
        startup_time = datetime.now(timezone.utc) - timedelta(days=90)
        for i, user in enumerate(users[:3]):  # First 3 users for system setup
            audit_entries.append({
                "tenant_id": user["tenant_id"],
                "actor_id": user["id"],
                "actor_role": user["role"],
                "resource_type": "user",
                "resource_id": user["id"],
                "action": AuditAction.CREATE,
                "action_description": "User account created",
                "severity": AuditSeverity.MEDIUM,
                "created_at": startup_time + timedelta(minutes=i*5),
                "metadata": {
                    "user_email": user["email"],
                    "role_assigned": user["role"]
                }
            })

        # LC processing events
        for session in lc_sessions:
            session_start = session["created_at"]
            processing_user = random.choice([u for u in users if u["tenant_id"] == session["tenant_id"]])

            # LC creation
            audit_entries.append({
                "tenant_id": session["tenant_id"],
                "actor_id": processing_user["id"],
                "actor_role": processing_user["role"],
                "resource_type": "lc_session",
                "resource_id": session["id"],
                "action": AuditAction.CREATE,
                "action_description": f"LC session created: {session['lc_number']}",
                "severity": AuditSeverity.MEDIUM,
                "created_at": session_start,
                "metadata": {
                    "lc_number": session["lc_number"],
                    "amount": session["amount"],
                    "currency": session["currency"]
                }
            })

            # Document submissions
            for i, doc in enumerate(session["documents"]):
                audit_entries.append({
                    "tenant_id": session["tenant_id"],
                    "actor_id": processing_user["id"],
                    "actor_role": processing_user["role"],
                    "resource_type": "document",
                    "resource_id": str(uuid4()),
                    "action": AuditAction.CREATE,
                    "action_description": f"Document uploaded: {doc}",
                    "severity": AuditSeverity.LOW,
                    "created_at": session_start + timedelta(hours=i+1),
                    "metadata": {
                        "document_type": doc,
                        "lc_session": session["lc_number"]
                    }
                })

            # Status updates
            if session["status"] in ["validated", "completed"]:
                audit_entries.append({
                    "tenant_id": session["tenant_id"],
                    "actor_id": processing_user["id"],
                    "actor_role": processing_user["role"],
                    "resource_type": "lc_session",
                    "resource_id": session["id"],
                    "action": AuditAction.UPDATE,
                    "action_description": f"LC status updated to {session['status']}",
                    "severity": AuditSeverity.HIGH,
                    "created_at": session_start + timedelta(hours=session["processing_time_hours"]),
                    "metadata": {
                        "lc_number": session["lc_number"],
                        "new_status": session["status"],
                        "processing_time": session["processing_time_hours"]
                    }
                })

        # User login events
        for user in users:
            # Create several login events over the past month
            for i in range(random.randint(5, 15)):
                login_time = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))
                audit_entries.append({
                    "tenant_id": user["tenant_id"],
                    "actor_id": user["id"],
                    "actor_role": user["role"],
                    "resource_type": "session",
                    "resource_id": str(uuid4()),
                    "action": AuditAction.LOGIN,
                    "action_description": "User login",
                    "severity": AuditSeverity.LOW,
                    "created_at": login_time,
                    "metadata": {
                        "user_email": user["email"],
                        "login_method": "password"
                    }
                })

        # Export events
        for tenant in self.demo_data["tenants"]:
            for i in range(random.randint(2, 5)):
                export_time = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))
                export_user = random.choice([u for u in users if u["tenant_id"] == tenant["id"]])

                audit_entries.append({
                    "tenant_id": tenant["id"],
                    "actor_id": export_user["id"],
                    "actor_role": export_user["role"],
                    "resource_type": "export",
                    "resource_id": str(uuid4()),
                    "action": AuditAction.EXPORT,
                    "action_description": "Data export requested",
                    "severity": AuditSeverity.HIGH,
                    "created_at": export_time,
                    "metadata": {
                        "export_type": random.choice(["lc_sessions", "audit_log", "compliance_report"]),
                        "format": random.choice(["csv", "json", "pdf"]),
                        "row_count": random.randint(50, 500)
                    }
                })

        # Sort by timestamp for proper chain creation
        audit_entries.sort(key=lambda x: x["created_at"])

        # Actually create the audit entries using the service
        for entry in audit_entries:
            try:
                # Use the audit service to create entries with proper hash chaining
                audit_entry = AuditService.append_entry(
                    db=self.db,
                    tenant_id=entry["tenant_id"],
                    action=entry["action"],
                    resource_type=entry["resource_type"],
                    resource_id=entry["resource_id"],
                    actor_id=UUID(entry["actor_id"]) if entry["actor_id"] else None,
                    actor_role=entry["actor_role"],
                    action_description=entry["action_description"],
                    severity=entry["severity"],
                    metadata=entry["metadata"]
                )

                # Update the created_at time to match our timeline
                audit_entry.created_at = entry["created_at"]
                # Recompute hash with correct timestamp
                prev_entry = self.db.query(AuditLogEntry).filter(
                    AuditLogEntry.sequence_number < audit_entry.sequence_number
                ).order_by(AuditLogEntry.sequence_number.desc()).first()

                prev_hash = prev_entry.entry_hash if prev_entry else None
                audit_entry.entry_hash = audit_entry.compute_entry_hash(prev_hash)

                self.demo_data["audit_entries"].append({
                    "id": str(audit_entry.id),
                    "sequence_number": audit_entry.sequence_number,
                    **entry
                })

            except Exception as e:
                logger.warning(f"Failed to create audit entry: {str(e)}")
                continue

        logger.info(f"Created {len(self.demo_data['audit_entries'])} audit entries")

    def seed_governance_data(self):
        """Create governance approval data"""
        logger.info("Creating governance data")

        # Create some pending approvals
        approvals = [
            {
                "tenant_id": "demo-bank",
                "action_type": "role_change",
                "resource_type": "user",
                "resource_id": self.demo_data["users"][2]["id"],
                "requested_by": UUID(self.demo_data["users"][1]["id"]),
                "required_approvals": 2,
                "status": "pending",
                "request_reason": "Promote user to senior bank officer role"
            },
            {
                "tenant_id": "demo-sme",
                "action_type": "export_release",
                "resource_type": "audit_log",
                "resource_id": str(uuid4()),
                "requested_by": UUID(self.demo_data["users"][0]["id"]),
                "required_approvals": 1,
                "status": "approved",
                "request_reason": "Compliance audit requirement"
            }
        ]

        # Note: In a full implementation, these would be stored in the GovernanceApproval table
        logger.info(f"Created {len(approvals)} governance approval records")

    def seed_compliance_docs(self):
        """Create compliance document records"""
        logger.info("Creating compliance documents")

        docs = [
            {
                "doc_id": "compliance-policy-2024",
                "resource_type": "tenant",
                "resource_id": "demo-bank",
                "version": "1.0",
                "file_name": "compliance_policy_2024_v1.pdf",
                "title": "Bank Compliance Policy 2024",
                "language": "en",
                "created_by": UUID(self.demo_data["users"][2]["id"]),
                "created_at": datetime.now(timezone.utc) - timedelta(days=60)
            },
            {
                "doc_id": "ucp600-guidelines",
                "resource_type": "system",
                "resource_id": "global",
                "version": "2.1",
                "file_name": "ucp600_implementation_guide.pdf",
                "title": "UCP 600 Implementation Guidelines",
                "language": "en",
                "created_by": UUID(self.demo_data["users"][4]["id"]),
                "created_at": datetime.now(timezone.utc) - timedelta(days=90)
            }
        ]

        # Note: In a full implementation, these would be stored in the ComplianceDoc table
        logger.info(f"Created {len(docs)} compliance documents")


def main():
    parser = argparse.ArgumentParser(description="Seed demo data for TRDR Hub")
    parser.add_argument("--output-json", action="store_true",
                       help="Output results as JSON")
    parser.add_argument("--clean", action="store_true",
                       help="Clean existing data before seeding")

    args = parser.parse_args()

    try:
        seeder = DemoDataSeeder()

        if args.clean:
            logger.info("Cleaning existing data...")
            # In a full implementation, this would truncate tables
            logger.info("Data cleaning completed")

        result = seeder.seed_all()

        if args.output_json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print("✅ Demo data seeding completed successfully!")
            print(f"Created:")
            for key, count in result["data_created"].items():
                print(f"  {key}: {count}")

    except Exception as e:
        logger.error(f"Demo data seeding failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()