"""HTTP-клієнт REST API для десктоп-застосунку."""
from __future__ import annotations

from typing import Protocol

import httpx

from ..core.models import FileRecord


class ApiError(Exception):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


class ApiClientProtocol(Protocol):
    """Інтерфейс, від якого залежать view-модель і рушій синхронізації (у тестах — заглушка)."""

    username: str | None

    def list_files(self) -> list[FileRecord]: ...
    def upload(self, name: str, data: bytes) -> FileRecord: ...
    def download(self, file_id: int) -> bytes: ...
    def delete(self, file_id: int) -> None: ...


class ApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", transport: httpx.BaseTransport | None = None):
        self.base_url = base_url.rstrip("/")
        self.token: str | None = None
        self.username: str | None = None
        self._http = httpx.Client(base_url=self.base_url, timeout=30.0, transport=transport)

    # ---------------------------------------------------------------- helpers
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _check(self, resp: httpx.Response) -> httpx.Response:
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail")
            except ValueError:
                detail = None
            if isinstance(detail, list):  # помилка валідації FastAPI
                detail = "; ".join(str(d.get("msg", d)) for d in detail)
            raise ApiError(detail or f"HTTP {resp.status_code}", resp.status_code)
        return resp

    def _request(self, method: str, url: str, **kw) -> httpx.Response:
        try:
            return self._check(self._http.request(method, url, headers=self._headers(), **kw))
        except httpx.TransportError as exc:
            raise ApiError(f"Сервер недоступний ({self.base_url}): {exc}") from exc

    # ---------------------------------------------------------------- auth
    def _auth(self, path: str, username: str, password: str) -> str:
        data = self._request("POST", path, json={"username": username, "password": password}).json()
        self.token, self.username = data["access_token"], data["username"]
        return self.username

    def register(self, username: str, password: str) -> str:
        return self._auth("/api/auth/register", username, password)

    def login(self, username: str, password: str) -> str:
        return self._auth("/api/auth/login", username, password)

    def logout(self) -> None:
        self.token = self.username = None

    # ---------------------------------------------------------------- files
    def list_files(self) -> list[FileRecord]:
        return [FileRecord.from_json(item) for item in self._request("GET", "/api/files").json()]

    def upload(self, name: str, data: bytes) -> FileRecord:
        resp = self._request("POST", "/api/files", files={"file": (name, data)}, data={"name": name})
        return FileRecord.from_json(resp.json())

    def download(self, file_id: int) -> bytes:
        return self._request("GET", f"/api/files/{file_id}/content", params={"download": "true"}).content

    def delete(self, file_id: int) -> None:
        self._request("DELETE", f"/api/files/{file_id}")
