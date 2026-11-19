"""Абстракція сховища вмісту файлів (метадані зберігаються окремо, у SQLite)."""
from __future__ import annotations

import contextlib
import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path


class FileStorage(ABC):
    @abstractmethod
    def save(self, data: bytes) -> str:
        """Зберігає вміст і повертає ключ сховища."""

    @abstractmethod
    def load(self, key: str) -> bytes: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class LocalFileStorage(FileStorage):
    """Зберігає вміст у каталозі на диску сервера під випадковими іменами (UUID)."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        if not key or "/" in key or "\\" in key or key.startswith("."):
            raise ValueError("Некоректний ключ сховища")
        return self.root / key

    def save(self, data: bytes) -> str:
        key = uuid.uuid4().hex
        tmp = self.root / f".{key}.tmp"
        tmp.write_bytes(data)
        os.replace(tmp, self._path(key))  # атомарний запис
        return key

    def load(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        with contextlib.suppress(FileNotFoundError):
            self._path(key).unlink()
