"""Fix PocketBase collections — uses the v0.37+ `fields` format instead of `schema`."""
import httpx
import json

PB_URL = "http://127.0.0.1:8090"
EMAIL = "imshubham7004@gmail.com"
PASSWORD = "Pulser@220"

# Login
r = httpx.post(f"{PB_URL}/api/collections/_superusers/auth-with-password",
               json={"identity": EMAIL, "password": PASSWORD})
token = r.json()["token"]
headers = {"Authorization": token, "Content-Type": "application/json"}
print("Logged in")

# Check resources collection structure
rc = httpx.get(f"{PB_URL}/api/collections/resources", headers=headers)
data = rc.json()
print(f"Resources collection fields: {len(data.get('fields', []))}")
for f in data.get("fields", []):
    name = f.get("name", "?")
    ftype = f.get("type", "?")
    sys = f.get("system", False)
    print(f"  {name}: {ftype} (system={sys})")

# Check records
recs = httpx.get(f"{PB_URL}/api/collections/resources/records", headers=headers)
print(f"Total resource records: {recs.json().get('totalItems', 0)}")

# Show one record
items = recs.json().get("items", [])
if items:
    print(f"Sample record keys: {list(items[0].keys())}")
    print(f"Sample: {items[0].get('title', 'NO TITLE')} | {items[0].get('icon', 'NO ICON')}")
