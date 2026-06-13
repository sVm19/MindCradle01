import sys
from pathlib import Path

# Add backend to python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.services.supabase import _get_client

def main():
    try:
        client = _get_client()
        res = client.table("push_notification_tokens").select("*").limit(1).execute()
        print("Success! Table exists. Response data:", res.data)
    except Exception as e:
        print("Error/Table might not exist:", e)

if __name__ == "__main__":
    main()
