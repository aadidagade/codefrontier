import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

openapi = app.openapi()
paths = openapi.get("paths", {})

categories = {
    '1. Authentication APIs': [],
    '2. User management APIs': [],
    '3. Project CRUD APIs': [],
    '4. Document upload APIs': [],
    '5. Document processing APIs': [],
    '6. Handover generation APIs': [],
    '7. Evidence verification APIs': [],
    '8. Contradiction detection APIs': [],
    '9. Conflict resolution APIs': [],
    '10. Member and permission APIs': [],
    '11. Audit log APIs': [],
    '12. Handover version APIs': [],
    '13. Version comparison APIs': [],
    '14. Incoming-member APIs': [],
    '15. Task management APIs': [],
}

uncategorized = []

for p, methods in sorted(paths.items()):
    for m, details in sorted(methods.items()):
        if m.lower() not in ["get", "post", "put", "patch", "delete"]:
            continue
        op = f"{m.upper():6} {p}"
        tags = details.get("tags", [])
        
        # Categorize logically into the 15 domains
        if "/api/v1/auth" in p:
            categories['1. Authentication APIs'].append(op)
        elif "/api/v1/users" in p:
            categories['2. User management APIs'].append(op)
        elif "/documents/upload" in p:
            categories['4. Document upload APIs'].append(op)
        elif "/documents" in p:
            categories['5. Document processing APIs'].append(op)
        elif "/evidence" in p:
            categories['7. Evidence verification APIs'].append(op)
        elif "/resolve" in p:
            categories['9. Conflict resolution APIs'].append(op)
        elif "/conflicts" in p:
            categories['8. Contradiction detection APIs'].append(op)
        elif "/members" in p or "/invitations" in p:
            categories['10. Member and permission APIs'].append(op)
        elif "/audit-logs" in p:
            categories['11. Audit log APIs'].append(op)
        elif "compare" in p:
            categories['13. Version comparison APIs'].append(op)
        elif "/versions" in p:
            categories['12. Handover version APIs'].append(op)
        elif any(k in p for k in ["shared-with-me", "/continuity", "/share", "/acknowledge"]):
            categories['14. Incoming-member APIs'].append(op)
        elif "/tasks" in p:
            categories['15. Task management APIs'].append(op)
        elif "/handovers" in p:
            categories['6. Handover generation APIs'].append(op)
        elif "/projects" in p or p == "/":
            categories['3. Project CRUD APIs'].append(op)
        else:
            uncategorized.append(op)

total = 0
for cat, items in categories.items():
    print(f"\n=== {cat} ({len(items)} endpoints) ===")
    for it in sorted(items):
        print(f"  {it}")
    total += len(items)

if uncategorized:
    print(f"\n=== Other / Uncategorized ({len(uncategorized)}) ===")
    for it in uncategorized:
        print(f"  {it}")

print(f"\nTotal categorized: {total}, uncategorized: {len(uncategorized)}, grand total: {total + len(uncategorized)}")
