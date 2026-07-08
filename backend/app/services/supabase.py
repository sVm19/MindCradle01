import os
import json
import base64
import asyncio
import logging
from typing import Any, Optional, Dict, List
import httpx
from supabase import create_client, ClientOptions
from app.config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_JWT_SECRET
from app.core.security import (
    extract_user_id_verified,
    verify_custom_access_token,
    get_supabase_token_for_user,
)

logger = logging.getLogger(__name__)

# Global HTTP client to avoid the overhead of creating one per request
shared_httpx_client = httpx.Client()

def _get_client(token: Optional[str] = None):
    headers = {}
    if token:
        clean_token = token.removeprefix("Bearer ").strip()
        # Intercept and translate custom JWTs to Supabase JWTs on the fly
        try:
            custom_payload = verify_custom_access_token(clean_token)
            if custom_payload:
                # Extract email from custom token if present
                email = extract_user_email(clean_token)
                clean_token = get_supabase_token_for_user(custom_payload.sub, email)
        except Exception:
            # Ignore errors and fall back to the original token
            pass
            
        headers["Authorization"] = f"Bearer {clean_token}"
    
    options = ClientOptions(
        httpx_client=shared_httpx_client,
        headers=headers
    )
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY, options=options)


def extract_user_id(token: Optional[str]) -> Optional[str]:
    """
    Verify the Supabase JWT signature and return the user UUID (sub claim).

    Replaces the previous unsafe implementation that only base64-decoded the
    payload without verifying the signature — which allowed token forgery.
    Now delegates to app.core.security.extract_user_id_verified which:
      - Verifies the HS256 signature against SUPABASE_JWT_SECRET
      - Checks token expiry
      - Validates the issuer matches the configured Supabase project
    """
    return extract_user_id_verified(token)


def extract_user_email(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    try:
        clean_token = token.removeprefix("Bearer ").strip()
        parts = clean_token.split(".")
        if len(parts) < 2:
            return None
        payload_part = parts[1]
        padded = payload_part + "=" * (-len(payload_part) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        data_dict = json.loads(decoded)
        return data_dict.get("email")
    except Exception:
        return None

def _apply_filter(query, filter_str: str):
    if not filter_str:
        return query
    
    parts = [p.strip() for p in filter_str.split("&&")]
    for part in parts:
        if part == "is_active=true":
            query = query.eq("is_active", True)
        elif part == "is_active=false":
            query = query.eq("is_active", False)
        elif part.startswith("category="):
            cat_val = part.split("=", 1)[1].strip('"\'')
            query = query.eq("category", cat_val)
        elif ">=" in part:
            field, val = [x.strip() for x in part.split(">=")]
            val = val.strip('"\'')
            query = query.gte(field, val)
        elif "=" in part:
            field, val = [x.strip() for x in part.split("=", 1)]
            val = val.strip('"\'')
            if val.lower() == "true":
                query = query.eq(field, True)
            elif val.lower() == "false":
                query = query.eq(field, False)
            else:
                query = query.eq(field, val)
    return query

def _execute_query(query):
    try:
        return query.execute()
    except Exception as e:
        err_str = str(e)
        if "PGRST301" in err_str or "wrong key type" in err_str or "decode the JWT" in err_str:
            raise Exception(
                "SUPABASE_JWT_SECRET is configured incorrectly in your backend .env file. "
                "Please check your Supabase Settings -> API -> JWT Secret."
            )
        raise

class JWTExpiredError(Exception):
    """Raised when a Supabase call fails due to an expired JWT."""
    pass


class SupabaseService:
    """Wrapper around Supabase API to match PocketBase Client interface."""
    
    async def auth_with_password(self, email: str, password: str) -> dict:
        def _call():
            client = _get_client()
            res = client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return {
                "token": res.session.access_token,
                "refresh_token": res.session.refresh_token,
                "record": {
                    "id": res.user.id,
                    "email": res.user.email,
                    "name": res.user.user_metadata.get("name", "")
                }
            }
        return await asyncio.to_thread(_call)

    async def refresh_session(self, refresh_token: str) -> dict:
        """Exchange a refresh token for a new access + refresh token pair."""
        def _call():
            client = _get_client()
            res = client.auth.refresh_session(refresh_token)
            return {
                "token": res.session.access_token,
                "refresh_token": res.session.refresh_token,
                "record": {
                    "id": res.user.id,
                    "email": res.user.email,
                    "name": res.user.user_metadata.get("name", "")
                }
            }
        return await asyncio.to_thread(_call)

    async def create_user(self, data: dict) -> dict:
        def _call():
            client = _get_client()
            res = client.auth.sign_up({
                "email": data["email"],
                "password": data["password"],
                "options": {
                    "data": {
                        "name": data.get("name", "")
                    }
                }
            })
            return {"id": res.user.id if res.user else ""}
        return await asyncio.to_thread(_call)

    async def list_records(
        self,
        collection: str,
        token: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> dict:
        def _call():
            client = _get_client(token)
            query = client.table(collection).select("*")
            
            p = params or {}
            
            # Apply pocketbase-style filter
            if "filter" in p:
                query = _apply_filter(query, p["filter"])
                
            # Apply sorting
            if "sort" in p:
                sort_field = p["sort"]
                descending = False
                if sort_field.startswith("-"):
                    descending = True
                    sort_field = sort_field[1:]
                query = query.order(sort_field, desc=descending)
                
            # Apply pagination/limit
            if "perPage" in p:
                query = query.limit(int(p["perPage"]))
                
            res = _execute_query(query)
            return {
                "items": res.data or [],
                "totalItems": len(res.data) if res.data else 0
            }
        try:
            return await asyncio.to_thread(_call)
        except Exception as e:
            err_str = str(e)
            if "JWT expired" in err_str or "PGRST303" in err_str:
                logger.warning("JWT expired when querying %s — returning empty result", collection)
                raise JWTExpiredError(f"JWT expired when querying {collection}")
            raise

    async def get_record(
        self, collection: str, record_id: str, token: Optional[str] = None
    ) -> dict:
        def _call():
            client = _get_client(token)
            res = _execute_query(client.table(collection).select("*").eq("id", record_id))
            if not res.data:
                raise Exception(f"Record {record_id} not found in {collection}")
            return res.data[0]
        return await asyncio.to_thread(_call)

    async def create_record(
        self, collection: str, data: dict, token: Optional[str] = None
    ) -> dict:
        def _call():
            client = _get_client(token)
            insert_data = dict(data)
            if "user" in insert_data:
                insert_data["user_id"] = insert_data.pop("user")
            
            res = _execute_query(client.table(collection).insert(insert_data))
            if not res.data:
                raise Exception(f"Failed to create record in {collection}")
            return res.data[0]
        return await asyncio.to_thread(_call)

    async def update_record(
        self,
        collection: str,
        record_id: str,
        data: dict,
        token: Optional[str] = None,
    ) -> dict:
        def _call():
            client = _get_client(token)
            update_data = dict(data)
            if "user" in update_data:
                update_data["user_id"] = update_data.pop("user")
                
            res = _execute_query(client.table(collection).update(update_data).eq("id", record_id))
            if not res.data:
                raise Exception(f"Failed to update record {record_id} in {collection}")
            return res.data[0]
        return await asyncio.to_thread(_call)

    async def upsert_records(
        self,
        collection: str,
        records: List[dict],
        token: Optional[str] = None,
        on_conflict: Optional[str] = None,
    ) -> List[dict]:
        """
        Bulk upsert multiple records.  When `on_conflict` is provided (comma-separated
        column names) it is passed directly to Supabase's upsert ignore-duplicates logic.
        Falls back to a regular insert if on_conflict is not supported.
        """
        def _call():
            client = _get_client(token)
            query = client.table(collection).upsert(records, ignore_duplicates=True)
            if on_conflict:
                # supabase-py >=2.0 supports `on_conflict` kwarg in upsert()
                try:
                    query = client.table(collection).upsert(records, on_conflict=on_conflict)
                except TypeError:
                    # older SDK — fall back to ignore_duplicates
                    query = client.table(collection).upsert(records, ignore_duplicates=True)
            res = _execute_query(query)
            return res.data or []
        return await asyncio.to_thread(_call)

    async def delete_record(
        self, collection: str, record_id: str, token: Optional[str] = None
    ) -> None:
        def _call():
            client = _get_client(token)
            client.table(collection).delete().eq("id", record_id).execute()
        return await asyncio.to_thread(_call)

    async def call_rpc(
        self,
        function_name: str,
        params: dict,
        token: Optional[str] = None,
    ) -> Any:
        """
        Call a Supabase PostgreSQL function via the PostgREST RPC endpoint.
        Returns the raw data from the response (list for set-returning functions).
        """
        def _call():
            client = _get_client(token)
            res = client.rpc(function_name, params).execute()
            return res.data
        return await asyncio.to_thread(_call)

    async def upsert_user_profile(self, token: str, payload: dict) -> dict:


        auth_token = token.removeprefix("Bearer ").strip()
        if not auth_token:
            raise ValueError("Missing auth token for profile sync")
            
        parts = auth_token.split(".")
        if len(parts) < 2:
            raise ValueError("Invalid JWT token structure")
            
        payload_part = parts[1]
        padded = payload_part + "=" * (-len(payload_part) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        data_dict = json.loads(decoded)
        user_id = data_dict["sub"]
        
        def _call():
            client = _get_client(auth_token)
            res = client.table("user_profiles").select("*").eq("user_id", user_id).execute()
            
            profile_data = dict(payload)
            profile_data["user_id"] = user_id
            
            if res.data:
                profile_id = res.data[0]["id"]
                upd_res = client.table("user_profiles").update(profile_data).eq("id", profile_id).execute()
                return upd_res.data[0]
            else:
                ins_res = client.table("user_profiles").insert(profile_data).execute()
                return ins_res.data[0]
                
        return await asyncio.to_thread(_call)

    async def update_user(self, token: str, data: dict) -> dict:
        """Update user credentials (e.g. password) in Supabase Auth."""
        def _call():
            clean_token = token.removeprefix("Bearer ").strip()
            client = _get_client(clean_token)
            res = client.auth.update_user(data)
            return {"id": res.user.id if res.user else ""}
        return await asyncio.to_thread(_call)

    async def delete_user_account(self, token: str) -> None:
        def _call():
            client = _get_client(token)
            client.rpc("delete_user").execute()
        return await asyncio.to_thread(_call)

    async def get_user_email(self, token: str) -> str:
        # Try extracting from JWT first
        email = extract_user_email(token)
        if email:
            return email
            
        # Fallback to Supabase auth API
        def _call():
            clean_token = token.removeprefix("Bearer ").strip()
            client = _get_client(clean_token)
            res = client.auth.get_user(clean_token)
            if res and res.user:
                return res.user.email
            raise Exception("Failed to retrieve user email from Supabase Auth")
        return await asyncio.to_thread(_call)

    async def create_password_reset_token(self, email: str, token: str, expiry_seconds: int) -> bool:
        """Call RPC to securely generate and store password reset token for user email."""
        def _call():
            client = _get_client()
            res = client.rpc(
                "create_password_reset_token_for_email",
                {
                    "email_address": email,
                    "reset_token": token,
                    "expiry_seconds": expiry_seconds
                }
            ).execute()
            return res.data is True
        return await asyncio.to_thread(_call)

    async def get_password_history_by_token(self, reset_token: str) -> list:
        """Call RPC to securely fetch password history for validation prior to reset."""
        def _call():
            client = _get_client()
            res = client.rpc(
                "get_password_history_by_token",
                {"reset_token": reset_token}
            ).execute()
            return res.data or []
        return await asyncio.to_thread(_call)

    async def reset_password_with_token(
        self, reset_token: str, new_encrypted_password: str, new_history_hash: str
    ) -> bool:
        """Call RPC to securely update user password in auth.users and record history."""
        def _call():
            client = _get_client()
            res = client.rpc(
                "reset_password_with_token",
                {
                    "reset_token": reset_token,
                    "new_encrypted_password": new_encrypted_password,
                    "new_history_hash": new_history_hash
                }
            ).execute()
            return res.data is True
        return await asyncio.to_thread(_call)

    async def create_magic_login_token(self, email: str, token: str, expiry_seconds: int) -> bool:
        """Call RPC to securely generate and store magic login token for user email."""
        def _call():
            client = _get_client()
            res = client.rpc(
                "create_magic_login_token_for_email",
                {
                    "email_address": email,
                    "magic_token": token,
                    "expiry_seconds": expiry_seconds
                }
            ).execute()
            return res.data is True
        return await asyncio.to_thread(_call)

    async def consume_magic_login_token(self, magic_token: str) -> Optional[dict]:
        """Call RPC to securely verify and consume a magic login token, returning user details."""
        def _call():
            client = _get_client()
            res = client.rpc(
                "consume_magic_login_token",
                {"magic_token": magic_token}
            ).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
            return None
        return await asyncio.to_thread(_call)

    async def check_expired_trials(self) -> bool:
        """Call RPC to check and deactivate expired trials in the database."""
        def _call():
            client = _get_client()
            client.rpc("check_expired_trials").execute()
            return True
        return await asyncio.to_thread(_call)

pb = SupabaseService()


