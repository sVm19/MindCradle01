import json
import httpx
from app.config import SUPABASE_URL, SUPABASE_ANON_KEY

def main():
    url = f"{SUPABASE_URL}/rest/v1/"
    headers = {"apikey": SUPABASE_ANON_KEY}
    res = httpx.get(url, headers=headers)
    if res.status_code == 200:
        spec = res.json()
        print("Tables found in OpenAPI spec:")
        for table in spec.get("paths", {}).keys():
            if table.strip('/') in ["mood_logs", "morning_rituals"]:
                print(f"Table path: {table}")
        
        definitions = spec.get("definitions", {})
        for name in ["mood_logs", "morning_rituals"]:
            if name in definitions:
                print(f"\nTable '{name}' properties:")
                for prop_name, prop_val in definitions[name].get("properties", {}).items():
                    print(f"  - {prop_name}: {prop_val.get('type')}")
    else:
        print(f"Failed to fetch OpenAPI: {res.status_code} - {res.text}")

if __name__ == "__main__":
    main()
