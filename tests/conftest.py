import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cloudfolder.core.models import FileRecord  # noqa: E402
from cloudfolder.core.sync import sha256_bytes  # noqa: E402

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


def make_record(id_, name, minutes=0, uploaded_by="anna", edited_by="anna", created_minutes=0, data=b""):
    return FileRecord(
        id=id_,
        name=name,
        size=len(data),
        sha256=sha256_bytes(data or name.encode()),
        created_at=T0 + timedelta(minutes=created_minutes),
        modified_at=T0 + timedelta(minutes=minutes),
        uploaded_by=uploaded_by,
        edited_by=edited_by,
    )


class FakeApi:
    """In-memory заміна REST API для тестів view-моделі та рушія синхронізації."""

    def __init__(self, username="anna"):
        self.username = username
        self.store: dict[str, tuple[int, bytes]] = {}
        self._next = 1
        self.calls: list[tuple[str, str]] = []

    def _record(self, name):
        id_, data = self.store[name]
        return FileRecord(id_, name, len(data), sha256_bytes(data), T0, T0, self.username, self.username)

    def list_files(self):
        return [self._record(n) for n in self.store]

    def upload(self, name, data):
        self.calls.append(("upload", name))
        id_ = self.store[name][0] if name in self.store else self._next
        if name not in self.store:
            self._next += 1
        self.store[name] = (id_, data)
        return self._record(name)

    def _name(self, file_id):
        return next(n for n, (i, _) in self.store.items() if i == file_id)

    def download(self, file_id):
        name = self._name(file_id)
        self.calls.append(("download", name))
        return self.store[name][1]

    def delete(self, file_id):
        name = self._name(file_id)
        self.calls.append(("delete", name))
        del self.store[name]


@pytest.fixture
def fake_api():
    return FakeApi()
