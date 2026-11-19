"""Рушій синхронізації локальної папки з віддаленою (виконує план із core.sync)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from ..core.sync import (
    SyncAction,
    SyncActionKind,
    conflict_copy_name,
    load_base,
    plan_sync,
    save_base,
    scan_folder,
    sha256_bytes,
)
from .api_client import ApiClientProtocol


@dataclass
class SyncReport:
    actions: list[SyncAction] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.actions)

    def summary(self) -> str:
        if not self.actions and not self.errors:
            return "Папки синхронізовано, змін немає"
        counts: dict[str, int] = {}
        for a in self.actions:
            counts[a.kind.value] = counts.get(a.kind.value, 0) + 1
        labels = {
            "upload": "вивантажено",
            "download": "завантажено",
            "delete_remote": "видалено на сервері",
            "delete_local": "видалено локально",
            "conflict": "конфліктів (збережено обидві версії)",
        }
        parts = [f"{labels[k]}: {v}" for k, v in counts.items()]
        if self.errors:
            parts.append(f"помилок: {len(self.errors)}")
        return "; ".join(parts)


class SyncEngine:
    def __init__(self, api: ApiClientProtocol, folder: Path | str):
        self.api = api
        self.folder = Path(folder)

    def _write_local(self, name: str, data: bytes) -> None:
        target = self.folder / name
        tmp = self.folder / f".{name}.part"
        tmp.write_bytes(data)
        os.replace(tmp, target)

    def run_once(self) -> SyncReport:
        account = self.api.username or ""
        if not self.folder.is_dir():
            raise FileNotFoundError(f"Папку не знайдено: {self.folder}")
        local = scan_folder(self.folder)
        remote_records = {r.name: r for r in self.api.list_files()}
        remote = {name: r.sha256 for name, r in remote_records.items()}
        base = load_base(self.folder, account)
        plan = plan_sync(local, remote, base)

        report = SyncReport()
        new_base = {n: h for n, h in local.items() if remote.get(n) == h}
        for action in plan:
            name = action.name
            try:
                if action.kind is SyncActionKind.UPLOAD:
                    data = (self.folder / name).read_bytes()
                    rec = self.api.upload(name, data)
                    new_base[name] = rec.sha256
                elif action.kind is SyncActionKind.DOWNLOAD:
                    data = self.api.download(remote_records[name].id)
                    self._write_local(name, data)
                    new_base[name] = sha256_bytes(data)
                elif action.kind is SyncActionKind.DELETE_REMOTE:
                    self.api.delete(remote_records[name].id)
                    new_base.pop(name, None)
                elif action.kind is SyncActionKind.DELETE_LOCAL:
                    (self.folder / name).unlink(missing_ok=True)
                    new_base.pop(name, None)
                elif action.kind is SyncActionKind.CONFLICT:
                    # зберігаємо обидві версії: локальна -> копія «(конфлікт)», віддалена -> під основним іменем
                    copy = conflict_copy_name(name)
                    local_data = (self.folder / name).read_bytes()
                    self._write_local(copy, local_data)
                    rec = self.api.upload(copy, local_data)
                    new_base[copy] = rec.sha256
                    remote_data = self.api.download(remote_records[name].id)
                    self._write_local(name, remote_data)
                    new_base[name] = sha256_bytes(remote_data)
                report.actions.append(action)
            except Exception as exc:  # одна невдала дія не зупиняє решту циклу
                report.errors.append(f"{action}: {exc}")
                if name in base:
                    new_base[name] = base[name]
        save_base(self.folder, account, new_base)
        return report
