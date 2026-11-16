import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

openapi = app.openapi()
paths = openapi.get("paths", {})
print(f"Total Unique Paths: {len(paths)}")

inventory = []
for p, methods in sorted(paths.items()):
    for m, details in sorted(methods.items()):
        if m.lower() in ["get", "post", "put", "patch", "delete"]:
            inventory.append({
                "method": m.upper(),
                "path": p,
                "tags": details.get("tags", []),
                "summary": details.get("summary", details.get("operationId", "")),
                "parameters": [param.get("name") for param in details.get("parameters", [])],
                "has_body": "requestBody" in details,
            })

print(f"Total Operations: {len(inventory)}")
print("=" * 110)
for item in inventory:
    tags = ",".join(item["tags"])
    print(f"{item['method']:6} {item['path']:65} [{tags}]")
