"""PocketBase HTTP client wrapper.

Centralizes all PocketBase REST API interactions so that
router modules never construct raw HTTP calls.
"""

import base64
import json
from typing import Any, Optional

import httpx
from app.config import POCKETBASE_URL


class PocketBaseClient:
    """Async wrapper around the PocketBase REST API."""

    def __init__(self, base_url: str = POCKETBASE_URL):
        self.base_url = base_url.rstrip("/")

    def _headers(self, token: Optional[str] = None) -> dict:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = token
        return headers

    # --- Auth ---
    async def auth_with_password(self, email: str, password: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/collections/users/auth-with-password",
                json={"identity": email, "password": password},
            )
            resp.raise_for_status()
            return resp.json()

    async def create_user(self, data: dict) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/collections/users/records",
                json=data,
            )
            resp.raise_for_status()
            return resp.json()

    # --- Generic CRUD ---
    async def list_records(
        self,
        collection: str,
        token: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/collections/{collection}/records",
                headers=self._headers(token),
                params=params or {},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_record(
        self, collection: str, record_id: str, token: Optional[str] = None
    ) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/collections/{collection}/records/{record_id}",
                headers=self._headers(token),
            )
            resp.raise_for_status()
            return resp.json()

    async def create_record(
        self, collection: str, data: dict, token: Optional[str] = None
    ) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/collections/{collection}/records",
                headers=self._headers(token),
                json=data,
            )
            resp.raise_for_status()
            return resp.json()

    async def update_record(
        self,
        collection: str,
        record_id: str,
        data: dict,
        token: Optional[str] = None,
    ) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{self.base_url}/api/collections/{collection}/records/{record_id}",
                headers=self._headers(token),
                json=data,
            )
            resp.raise_for_status()
            return resp.json()

    async def delete_record(
        self, collection: str, record_id: str, token: Optional[str] = None
    ) -> None:
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{self.base_url}/api/collections/{collection}/records/{record_id}",
                headers=self._headers(token),
            )
            resp.raise_for_status()

    async def upsert_user_profile(self, token: str, payload: dict) -> dict:
        auth_token = token.removeprefix("Bearer ").strip()
        if not auth_token:
            raise ValueError("Missing auth token for milestone sync")

        payload_part = auth_token.split(".")[1]
        decoded = base64.urlsafe_b64decode(payload_part + "==")
        data_dict = json.loads(decoded)
        user_id = data_dict["id"]

        result = await self.list_records(
            "user_profiles",
            token=auth_token,
            params={"perPage": 1, "sort": "-created"},
        )
        items = result.get("items", [])
        if items:
            return await self.update_record(
                "user_profiles",
                items[0]["id"],
                payload,
                token=auth_token,
            )
        payload["user"] = user_id
        return await self.create_record("user_profiles", payload, token=auth_token)


# Singleton
pb = PocketBaseClient()
