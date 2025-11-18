import ast
import os

versions_dir = os.path.join(os.path.dirname(__file__), "alembic", "versions")
infos = {}


def parse_value(line: str):
    value = line.split("=", 1)[1].strip()
    if "#" in value:
        value = value.split("#", 1)[0].strip()
    try:
        return ast.literal_eval(value)
    except Exception:
        stripped = value.strip("\"'")
        if stripped.lower() == "none":
            return None
        return stripped


for fname in os.listdir(versions_dir):
    if not fname.endswith(".py"):
        continue
    path = os.path.join(versions_dir, fname)
    rev = None
    down = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("revision ="):
                rev = parse_value(stripped)
            elif stripped.startswith("down_revision ="):
                down = parse_value(stripped)
    if rev:
        infos[rev] = {"file": fname, "down": down}

heads = set(infos)
for data in infos.values():
    down = data["down"]
    if not down:
        continue
    if isinstance(down, (tuple, list, set)):
        for parent in down:
            if parent in heads:
                heads.remove(parent)
    else:
        if down in heads:
            heads.remove(down)

print("Heads:", heads)
for h in heads:
    info = infos[h]
    print(f"- {h} (file={info['file']}, down={info['down']})")

