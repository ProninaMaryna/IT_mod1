"""Доменні моделі, спільні для сервера та десктоп-клієнта."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class FileRecord:
    """Метадані одного файлу у віддаленій папці користувача."""

    id: int
    name: str
    size: int
    sha256: str
    created_at: datetime
    modified_at: datetime
    uploaded_by: str
    edited_by: str

    @property
    def extension(self) -> str:
        dot = self.name.rfind(".")
        return self.name[dot:].lower() if dot > 0 else ""

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["modified_at"] = self.modified_at.isoformat()
        data["extension"] = self.extension
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "FileRecord":
        return cls(
            id=int(data["id"]),
            name=data["name"],
            size=int(data["size"]),
            sha256=data["sha256"],
            created_at=datetime.fromisoformat(data["created_at"]),
            modified_at=datetime.fromisoformat(data["modified_at"]),
            uploaded_by=data["uploaded_by"],
            edited_by=data["edited_by"],
        )
