import uuid
from app.config import SUPABASE_URL, SUPABASE_ANON_KEY
from supabase import create_client

def main():
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    email = f"test_{uuid.uuid4()}@example.com"
    password = "testpassword123"
    
    print(f"Signing up test user: {email}...")
    try:
        auth_res = client.auth.sign_up({"email": email, "password": password})
        user = auth_res.user
        if not user:
            print("Failed to sign up user.")
            return
        user_id = user.id
        print(f"User signed up successfully. ID: {user_id}")
        
        # Test inserting with 'created'
        print("\nAttempting to insert mood_log with 'created'...")
        try:
            res1 = client.table("mood_logs").insert({
                "user_id": user_id,
                "level": 5,
                "emotions": ["happy"],
                "note": "testing",
                "created": "2026-06-10T22:51:55Z"
            }).execute()
            print("Success inserting with 'created':", res1.data)
        except Exception as e:
            print("Failed inserting with 'created':", e)

        # Test inserting with 'created_at'
        print("\nAttempting to insert mood_log with 'created_at'...")
        try:
            res2 = client.table("mood_logs").insert({
                "user_id": user_id,
                "level": 5,
                "emotions": ["happy"],
                "note": "testing",
                "created_at": "2026-06-10T22:51:55Z"
            }).execute()
            print("Success inserting with 'created_at':", res2.data)
        except Exception as e:
            print("Failed inserting with 'created_at':", e)
            
        # Let's clean up user if possible (requires admin key, so we can't, but that's fine since it's a test db)
    except Exception as e:
        print("Error during test:", e)

if __name__ == "__main__":
    main()
