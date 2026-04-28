"""
Fix PocketBase collections for v0.37+
Uses PATCH to add fields to existing collections,
and creates the missing user-linked collections.
"""
import httpx
import json

PB_URL = "http://127.0.0.1:8090"
EMAIL = "imshubham7004@gmail.com"
PASSWORD = "Pulser@220"

# Login
r = httpx.post(f"{PB_URL}/api/collections/_superusers/auth-with-password",
               json={"identity": EMAIL, "password": PASSWORD})
token = r.json()["token"]
H = {"Authorization": token, "Content-Type": "application/json"}
print("✅ Logged in as admin\n")


def get_collection(name):
    resp = httpx.get(f"{PB_URL}/api/collections/{name}", headers=H)
    if resp.status_code == 200:
        return resp.json()
    return None


def delete_collection(name):
    resp = httpx.delete(f"{PB_URL}/api/collections/{name}", headers=H)
    if resp.status_code == 204:
        print(f"  🗑️  Deleted '{name}'")


def create_collection(payload):
    name = payload["name"]
    resp = httpx.post(f"{PB_URL}/api/collections", headers=H, json=payload)
    if resp.status_code == 200:
        print(f"  ✅ Created '{name}'")
        return resp.json()
    else:
        print(f"  ❌ Failed '{name}': {resp.text[:300]}")
        return None


# ============================================================
# Step 1: Fix the resources collection — add missing fields
# ============================================================
print("📦 Step 1: Fixing resources collection...")

res_col = get_collection("resources")
if res_col:
    existing_fields = res_col.get("fields", [])

    new_fields = existing_fields + [
        {"name": "title",       "type": "text",   "required": True},
        {"name": "description", "type": "text",   "required": True},
        {"name": "icon",        "type": "text",   "required": True},
        {"name": "color_class", "type": "text",   "required": True},
        {"name": "category",    "type": "select", "required": True,
         "values": ["crisis","mindfulness","therapy","self-care","physical","creative","tools"]},
        {"name": "order",       "type": "number", "required": True},
        {"name": "url",         "type": "url",    "required": False},
        {"name": "is_active",   "type": "bool",   "required": False},
    ]

    resp = httpx.patch(
        f"{PB_URL}/api/collections/resources",
        headers=H,
        json={"fields": new_fields, "listRule": "", "viewRule": ""},
    )
    if resp.status_code == 200:
        print("  ✅ Added fields to resources")
        # Check if data is now visible
        recs = httpx.get(f"{PB_URL}/api/collections/resources/records", headers=H)
        items = recs.json().get("items", [])
        if items and items[0].get("title"):
            print(f"  ✅ Data intact! Sample: {items[0]['title']}")
        else:
            print("  ⚠️  Fields added but existing data may need re-seeding")
    else:
        print(f"  ❌ Failed to patch resources: {resp.text[:300]}")


# ============================================================
# Step 2: Create user-linked collections
# ============================================================
print("\n📦 Step 2: Creating user-linked collections...")

# Delete any broken ones first
for name in ["mood_logs", "journal_entries", "ai_conversations"]:
    if get_collection(name):
        delete_collection(name)

# mood_logs
create_collection({
    "name": "mood_logs",
    "type": "base",
    "fields": [
        {"name": "user",     "type": "relation", "required": True,
         "collectionId": "_pb_users_auth_", "maxSelect": 1},
        {"name": "level",    "type": "number",   "required": True,
         "min": 1, "max": 10},
        {"name": "emotions", "type": "json",     "required": False},
        {"name": "note",     "type": "text",     "required": False},
    ],
    "listRule": "",
    "viewRule": "",
    "createRule": "",
    "updateRule": "",
    "deleteRule": "",
})

# journal_entries
create_collection({
    "name": "journal_entries",
    "type": "base",
    "fields": [
        {"name": "user",          "type": "relation", "required": True,
         "collectionId": "_pb_users_auth_", "maxSelect": 1},
        {"name": "prompt",        "type": "text",     "required": True},
        {"name": "content",       "type": "text",     "required": True},
        {"name": "ai_reflection", "type": "text",     "required": False},
    ],
    "listRule": "",
    "viewRule": "",
    "createRule": "",
    "updateRule": "",
    "deleteRule": "",
})

# ai_conversations
create_collection({
    "name": "ai_conversations",
    "type": "base",
    "fields": [
        {"name": "user",    "type": "relation", "required": True,
         "collectionId": "_pb_users_auth_", "maxSelect": 1},
        {"name": "messages","type": "json",     "required": False},
        {"name": "summary", "type": "text",     "required": False},
    ],
    "listRule": "",
    "viewRule": "",
    "createRule": "",
    "updateRule": "",
    "deleteRule": "",
})


# ============================================================
# Step 3: Verify everything
# ============================================================
print("\n🔍 Step 3: Verification...")
for name in ["resources", "mood_logs", "journal_entries", "ai_conversations"]:
    col = get_collection(name)
    if col:
        field_count = len([f for f in col.get("fields", []) if not f.get("system")])
        print(f"  ✅ {name}: {field_count} custom fields")
    else:
        print(f"  ❌ {name}: NOT FOUND")

# Verify resource data
recs = httpx.get(f"{PB_URL}/api/collections/resources/records", headers=H, params={"perPage": 1})
items = recs.json().get("items", [])
total = recs.json().get("totalItems", 0)
if items:
    sample = items[0]
    print(f"\n  📊 Resources: {total} records")
    print(f"     Sample: {sample.get('title', '???')} ({sample.get('category', '???')})")
else:
    print(f"\n  ⚠️  Resources: {total} records but no data visible")

print("\n✅ Done!")
