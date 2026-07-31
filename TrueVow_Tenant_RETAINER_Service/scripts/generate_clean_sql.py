"""Generate clean SQL from alembic --sql output."""
import subprocess, sys, re

subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "base:head", "--sql"],
    stdout=open("infra/database/retainer_tables_raw.sql", "w"),
    stderr=subprocess.DEVNULL,
    check=True,
)

with open("infra/database/retainer_tables_raw.sql") as f:
    lines = f.readlines()

out = []
in_alembic = False
in_enum = False
paren_count = 0

for line in lines:
    s = line.strip()

    # Skip alembic log lines
    if s.startswith("INFO"):
        continue
    if s.startswith("-- Running"):
        continue

    # Skip CREATE SCHEMA
    if "CREATE SCHEMA" in s:
        continue

    # Track alembic_version table block
    if "CREATE TABLE retainer.alembic_version" in s:
        in_alembic = True
        paren_count = 0
        continue
    if in_alembic:
        paren_count += s.count("(") - s.count(")")
        if paren_count <= 0:
            in_alembic = False
        continue

    # Track engagement_state type block
    if "CREATE TYPE retainer.engagement_state" in s:
        in_enum = True
        continue
    if in_enum:
        if ");" in s:
            in_enum = False
        continue

    # Skip alembic_version DML
    if "alembic_version" in s.lower():
        continue

    out.append(line)

text = "".join(out)
text = re.sub(r'\n{3,}', '\n\n', text)

with open("infra/database/retainer_tables.sql", "w") as f:
    f.write(text)

print(f"Lines: {len(out)}")
# Quick sanity
with open("infra/database/retainer_tables.sql") as f:
    first = f.readlines()[:5]
    for fl in first:
        print(fl.rstrip())
