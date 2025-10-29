"""Seed default companies for existing users

Revision ID: 20250916_170100
Revises: 20250916_170000_add_billing_system
Create Date: 2025-09-16 17:01:00.000000

This migration:
1. Creates a default company for each existing user
2. Assigns users to their respective companies
3. Assigns existing validation sessions to companies based on user

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers
revision = '20250916_170100'
down_revision = '20250916_170000_add_billing_system'
branch_labels = None
depends_on = None


def upgrade():
    """Seed default companies for existing users"""

    # Create a connection to execute raw SQL
    conn = op.get_bind()

    # Get all existing users
    result = conn.execute(sa.text("""
        SELECT id, email, full_name, role, created_at
        FROM users
        WHERE company_id IS NULL
        ORDER BY created_at
    """))

    users = result.fetchall()

    # Create default company for each user
    for user in users:
        user_id, email, full_name, role, created_at = user

        # Generate company name based on user info
        if full_name and full_name.strip():
            company_name = f"{full_name.strip()} - {role.title()}"
        else:
            company_name = f"{email.split('@')[0]} - {role.title()}"

        # Generate unique company ID
        company_id = str(uuid.uuid4())

        # Insert company
        conn.execute(sa.text("""
            INSERT INTO companies (
                id, name, contact_email, plan, status, created_at, updated_at
            ) VALUES (
                :company_id, :company_name, :contact_email, 'free', 'active',
                :created_at, :created_at
            )
        """), {
            'company_id': company_id,
            'company_name': company_name,
            'contact_email': email,
            'created_at': created_at
        })

        # Update user to reference the new company
        conn.execute(sa.text("""
            UPDATE users
            SET company_id = :company_id
            WHERE id = :user_id
        """), {
            'company_id': company_id,
            'user_id': str(user_id)
        })

        # Update validation sessions for this user to reference the company
        conn.execute(sa.text("""
            UPDATE validation_sessions
            SET company_id = :company_id
            WHERE user_id = :user_id
        """), {
            'company_id': company_id,
            'user_id': str(user_id)
        })

    # Count the results for verification
    companies_created = conn.execute(sa.text("SELECT COUNT(*) FROM companies")).scalar()
    users_updated = conn.execute(sa.text("SELECT COUNT(*) FROM users WHERE company_id IS NOT NULL")).scalar()
    sessions_updated = conn.execute(sa.text("SELECT COUNT(*) FROM validation_sessions WHERE company_id IS NOT NULL")).scalar()

    print(f"Migration completed:")
    print(f"  - Companies created: {companies_created}")
    print(f"  - Users assigned to companies: {users_updated}")
    print(f"  - Validation sessions assigned: {sessions_updated}")


def downgrade():
    """Remove seeded companies (WARNING: This will delete billing data)"""

    conn = op.get_bind()

    # Clear company associations
    conn.execute(sa.text("UPDATE validation_sessions SET company_id = NULL"))
    conn.execute(sa.text("UPDATE users SET company_id = NULL"))

    # Delete all companies (this will cascade to invoices and usage records)
    conn.execute(sa.text("DELETE FROM companies"))

    print("Downgrade completed - all companies and billing data removed")