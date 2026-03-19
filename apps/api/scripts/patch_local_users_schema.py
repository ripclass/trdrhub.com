import sqlite3

db = r'H:\.openclaw\workspace\trdrhub.com\apps\api\test_lcopilot.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

stmts = [
    "ALTER TABLE users ADD COLUMN auth_user_id VARCHAR(255)",
    "ALTER TABLE users ADD COLUMN role VARCHAR(50)",
    "ALTER TABLE users ADD COLUMN company_id UUID",
    "ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT 0",
    "ALTER TABLE users ADD COLUMN onboarding_data TEXT",
    "ALTER TABLE users ADD COLUMN onboarding_step INTEGER",
    "ALTER TABLE users ADD COLUMN status VARCHAR(50)",
    "ALTER TABLE users ADD COLUMN kyc_required BOOLEAN DEFAULT 0",
    "ALTER TABLE users ADD COLUMN kyc_status VARCHAR(50)",
    "ALTER TABLE users ADD COLUMN approver_id UUID",
    "ALTER TABLE users ADD COLUMN approved_at DATETIME",
]

for stmt in stmts:
    try:
        cur.execute(stmt)
        print('applied:', stmt)
    except Exception as exc:
        print('skip:', stmt, '=>', exc)

conn.commit()
conn.close()
print('done')
