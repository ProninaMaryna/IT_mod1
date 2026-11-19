"""Тристороннє узгодження (three-way reconcile) локальної та віддаленої папок.

Порівнюються три знімки «ім'я -> SHA-256»:

* ``local``  — поточний вміст локальної папки;
* ``remote`` — поточний список файлів на сервері;
* ``base``   — стан після попередньої успішної синхронізації (зберігається у ``.cloudfolder-sync.json``).

Функція :func:`plan_sync` є чистою (без вводу/виводу), тому повністю покривається модульними тестами;
виконання дій виконує клієнт.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping

STATE_FILE_NAME = ".cloudfolder-sync.json"


class SyncActionKind(str, Enum):
    UPLOAD = "upload"            # локальний файл новий/змінений -> вивантажити на сервер
    DOWNLOAD = "download"        # віддалений файл новий/змінений -> завантажити в папку
    DELETE_REMOTE = "delete_remote"  # файл видалено локально -> видалити на сервері
    DELETE_LOCAL = "delete_local"    # файл видалено на сервері -> видалити локально
    CONFLICT = "conflict"        # змінено з обох боків -> зберегти обидві версії


@dataclass(frozen=True)
class SyncAction:
    kind: SyncActionKind
    name: str

    def __str__(self) -> str:  # для журналу синхронізації
        return f"{self.kind.value}: {self.name}"


def conflict_copy_name(name: str, suffix: str = "конфлікт") -> str:
    """``report.xml`` -> ``report (конфлікт).xml``."""
    dot = name.rfind(".")
    if dot > 0:
        return f"{name[:dot]} ({suffix}){name[dot:]}"
    return f"{name} ({suffix})"


def plan_sync(
    local: Mapping[str, str],
    remote: Mapping[str, str],
    base: Mapping[str, str],
) -> list[SyncAction]:
    actions: list[SyncAction] = []
    for name in sorted(set(local) | set(remote) | set(base)):
        l, r, b = local.get(name), remote.get(name), base.get(name)
        if l == r:
            continue  # однакові або обидва відсутні
        if b is None:
            if r is None:
                actions.append(SyncAction(SyncActionKind.UPLOAD, name))
            elif l is None:
                actions.append(SyncAction(SyncActionKind.DOWNLOAD, name))
            else:
                actions.append(SyncAction(SyncActionKind.CONFLICT, name))
            continue
        local_changed, remote_changed = l != b, r != b
        if local_changed and not remote_changed:
            kind = SyncActionKind.DELETE_REMOTE if l is None else SyncActionKind.UPLOAD
        elif remote_changed and not local_changed:
            kind = SyncActionKind.DELETE_LOCAL if r is None else SyncActionKind.DOWNLOAD
        elif l is None:  # локально видалено, але на сервері змінено -> віддалена версія важливіша
            kind = SyncActionKind.DOWNLOAD
        elif r is None:  # на сервері видалено, але локально змінено -> зберегти локальну
            kind = SyncActionKind.UPLOAD
        else:
            kind = SyncActionKind.CONFLICT
        actions.append(SyncAction(kind, name))
    return actions


# --------------------------------------------------------------------------- локальна папка

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scan_folder(folder: Path) -> dict[str, str]:
    """Плаский (нерекурсивний) маніфест папки; приховані файли та файл стану пропускаються."""
    manifest: dict[str, str] = {}
    for entry in sorted(Path(folder).iterdir()):
        if not entry.is_file() or entry.name.startswith(".") or entry.name == STATE_FILE_NAME:
            continue
        manifest[entry.name] = sha256_of(entry)
    return manifest


def load_base(folder: Path, account: str) -> dict[str, str]:
    path = Path(folder) / STATE_FILE_NAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if data.get("account") != account:
        return {}  # папка раніше синхронізувалась з іншим обліковим записом
    return dict(data.get("files", {}))


def save_base(folder: Path, account: str, files: Mapping[str, str]) -> None:
    path = Path(folder) / STATE_FILE_NAME
    path.write_text(
        json.dumps({"account": account, "files": dict(sorted(files.items()))}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
