import os

versions_dir = os.path.join(os.path.dirname(__file__), "alembic", "versions")
revisions = set()
down_refs = {}

for fname in os.listdir(versions_dir):
    if not fname.endswith(".py"):
        continue
    path = os.path.join(versions_dir, fname)
    revision = None
    down_revision = None
    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if line.startswith("revision ="):
                revision = line.split("=", 1)[1].strip().split()[0].strip("\"'")
            elif line.startswith("down_revision ="):
                down_revision = line.split("=", 1)[1].strip().split()[0].strip("\"'")
    if revision:
        revisions.add(revision)
        down_refs[revision] = (down_revision, fname)

missing = []
for rev, (down, fname) in down_refs.items():
    if down and down not in revisions:
        missing.append((rev, down, fname))

print("Missing down_revision targets:")
for rev, down, fname in missing:
    print(f"- {rev} (file {fname}) -> down_revision '{down}' not found.")

