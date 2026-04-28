"""PocketBase HTTP client wrapper.

Centralizes all PocketBase REST API interactions so that
router modules never construct raw HTTP calls.
"""

import httpx
from typing import Any, Optional
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


# Singleton
pb = PocketBaseClient()
