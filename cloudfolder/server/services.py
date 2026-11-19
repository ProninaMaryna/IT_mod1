"""Сервісний шар: автентифікація та операції з файлами."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
from datetime import datetime, timedelta, timezone

import jwt

from ..core import variant
from ..core.models import FileRecord
from .db import FileRepo, UserRepo, row_to_record, utcnow
from .storage import FileStorage

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,32}$")
MAX_FILE_SIZE = 50 * 1024 * 1024


class ServiceError(Exception):
    status = 400

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        if status is not None:
            self.status = status


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"pbkdf2_sha256${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    candidate = hash_password(password, bytes.fromhex(salt_hex)).split("$")[2]
    return hmac.compare_digest(candidate, digest_hex)


class AuthService:
    TOKEN_TTL = timedelta(hours=12)

    def __init__(self, users: UserRepo, secret: str):
        self.users = users
        self.secret = secret

    def register(self, username: str, password: str) -> str:
        username = (username or "").strip()
        if not USERNAME_RE.match(username):
            raise ServiceError("Логін: 3–32 символи (латиниця, цифри, _ . -)")
        if len(password or "") < 6:
            raise ServiceError("Пароль має містити щонайменше 6 символів")
        if self.users.by_username(username):
            raise ServiceError("Користувач з таким логіном уже існує", 409)
        user_id = self.users.create(username, hash_password(password))
        return self._issue(user_id, username)

    def login(self, username: str, password: str) -> str:
        row = self.users.by_username((username or "").strip())
        if not row or not verify_password(password or "", row["password_hash"]):
            raise ServiceError("Невірний логін або пароль", 401)
        return self._issue(row["id"], row["username"])

    def _issue(self, user_id: int, username: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {"sub": str(user_id), "name": username, "iat": now, "exp": now + self.TOKEN_TTL}
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def authenticate(self, token: str) -> tuple[int, str]:
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise ServiceError("Сесія недійсна або завершилась — увійдіть знову", 401) from exc
        user = self.users.by_id(int(payload["sub"]))
        if not user:
            raise ServiceError("Користувача не знайдено", 401)
        return user["id"], user["username"]


def validate_file_name(name: str) -> str:
    name = (name or "").strip()
    name = name.replace("\\", "/").split("/")[-1]  # відкидаємо шлях, якщо браузер його передав
    if not name or name in (".", "..") or name.startswith(".") or len(name) > 255:
        raise ServiceError("Некоректне ім'я файлу")
    if any(c in name for c in '<>:"|?*') or any(ord(c) < 32 for c in name):
        raise ServiceError("Ім'я файлу містить заборонені символи")
    return name


class FileService:
    def __init__(self, files: FileRepo, storage: FileStorage):
        self.files = files
        self.storage = storage

    def list(
        self,
        owner_id: int,
        sort: str | None = None,
        order: str = "asc",
        type_filter: str | None = None,
    ) -> list[FileRecord]:
        records = [row_to_record(r) for r in self.files.list(owner_id)]
        try:
            records = variant.filter_files(records, type_filter)
            if sort:
                records = variant.sort_files(records, sort, order)
        except ValueError as exc:
            raise ServiceError(str(exc)) from exc
        return records

    def get(self, owner_id: int, file_id: int) -> FileRecord:
        row = self.files.get(owner_id, file_id)
        if not row:
            raise ServiceError("Файл не знайдено", 404)
        return row_to_record(row)

    def upload(self, owner_id: int, username: str, name: str, data: bytes, now: datetime | None = None) -> FileRecord:
        """Вивантаження. Якщо файл з таким іменем уже є — це редагування (нова версія вмісту)."""
        name = validate_file_name(name)
        if len(data) > MAX_FILE_SIZE:
            raise ServiceError("Файл завеликий (максимум 50 МБ)", 413)
        now = now or utcnow()
        sha = hashlib.sha256(data).hexdigest()
        with self.files.db.lock:
            existing = self.files.by_name(owner_id, name)
            if existing and existing["sha256"] == sha:
                return row_to_record(existing)  # вміст не змінився
            key = self.storage.save(data)
            if existing:
                self.files.update_content(existing["id"], len(data), sha, key, username, now)
                self.storage.delete(existing["storage_key"])
                file_id = existing["id"]
            else:
                file_id = self.files.insert(owner_id, name, len(data), sha, key, username, now)
        return self.get(owner_id, file_id)

    def content(self, owner_id: int, file_id: int) -> tuple[FileRecord, bytes]:
        row = self.files.get(owner_id, file_id)
        if not row:
            raise ServiceError("Файл не знайдено", 404)
        return row_to_record(row), self.storage.load(row["storage_key"])

    def delete(self, owner_id: int, file_id: int) -> None:
        with self.files.db.lock:
            row = self.files.get(owner_id, file_id)
            if not row:
                raise ServiceError("Файл не знайдено", 404)
            self.files.delete(file_id)
        self.storage.delete(row["storage_key"])
