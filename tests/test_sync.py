"""Тести тристороннього узгодження та рушія синхронізації десктоп-клієнта."""
from cloudfolder.core.sync import (
    STATE_FILE_NAME,
    SyncAction,
    SyncActionKind as K,
    conflict_copy_name,
    load_base,
    plan_sync,
    scan_folder,
)
from cloudfolder.desktop.sync_engine import SyncEngine


def kinds(actions):
    return {a.name: a.kind for a in actions}


def test_plan_first_sync_uploads_local_and_downloads_remote():
    plan = plan_sync(local={"a.xml": "1"}, remote={"b.png": "2"}, base={})
    assert kinds(plan) == {"a.xml": K.UPLOAD, "b.png": K.DOWNLOAD}


def test_plan_identical_content_needs_nothing():
    assert plan_sync({"a": "1"}, {"a": "1"}, {}) == []


def test_plan_local_edit_is_uploaded_and_remote_edit_downloaded():
    plan = plan_sync(local={"a": "L", "b": "1"}, remote={"a": "1", "b": "R"}, base={"a": "1", "b": "1"})
    assert kinds(plan) == {"a": K.UPLOAD, "b": K.DOWNLOAD}


def test_plan_deletions_propagate_both_ways():
    plan = plan_sync(local={"b": "1"}, remote={"a": "1"}, base={"a": "1", "b": "1"})
    assert kinds(plan) == {"a": K.DELETE_REMOTE, "b": K.DELETE_LOCAL}


def test_plan_edit_wins_over_delete():
    plan = plan_sync(local={"b": "L"}, remote={"a": "R"}, base={"a": "1", "b": "1"})
    assert kinds(plan) == {"a": K.DOWNLOAD, "b": K.UPLOAD}


def test_plan_both_sides_changed_is_conflict():
    assert plan_sync({"a": "L"}, {"a": "R"}, {"a": "1"}) == [SyncAction(K.CONFLICT, "a")]
    assert plan_sync({"a": "L"}, {"a": "R"}, {}) == [SyncAction(K.CONFLICT, "a")]


def test_conflict_copy_name():
    assert conflict_copy_name("report.xml") == "report (конфлікт).xml"
    assert conflict_copy_name("README") == "README (конфлікт)"


def test_scan_folder_skips_hidden_and_state(tmp_path):
    (tmp_path / "a.xml").write_text("<a/>")
    (tmp_path / ".hidden").write_text("x")
    (tmp_path / STATE_FILE_NAME).write_text("{}")
    (tmp_path / "sub").mkdir()
    assert list(scan_folder(tmp_path)) == ["a.xml"]


def test_engine_full_round_trip(tmp_path, fake_api):
    (tmp_path / "local.xml").write_bytes(b"<local/>")
    fake_api.upload("remote.png", b"PNG")
    fake_api.calls.clear()

    report = SyncEngine(fake_api, tmp_path).run_once()
    assert not report.errors
    assert (tmp_path / "remote.png").read_bytes() == b"PNG"
    assert fake_api.store["local.xml"][1] == b"<local/>"
    assert set(load_base(tmp_path, "anna")) == {"local.xml", "remote.png"}

    # другий цикл без змін нічого не робить
    assert SyncEngine(fake_api, tmp_path).run_once().actions == []

    # локальне видалення -> видалення на сервері
    (tmp_path / "local.xml").unlink()
    report = SyncEngine(fake_api, tmp_path).run_once()
    assert [str(a) for a in report.actions] == ["delete_remote: local.xml"]
    assert "local.xml" not in fake_api.store


def test_engine_conflict_keeps_both_versions(tmp_path, fake_api):
    (tmp_path / "doc.xml").write_bytes(b"v1")
    SyncEngine(fake_api, tmp_path).run_once()
    (tmp_path / "doc.xml").write_bytes(b"local-v2")
    fake_api.upload("doc.xml", b"remote-v2")

    report = SyncEngine(fake_api, tmp_path).run_once()
    assert [a.kind for a in report.actions] == [K.CONFLICT]
    assert (tmp_path / "doc.xml").read_bytes() == b"remote-v2"
    assert (tmp_path / "doc (конфлікт).xml").read_bytes() == b"local-v2"
    assert fake_api.store["doc (конфлікт).xml"][1] == b"local-v2"
    assert SyncEngine(fake_api, tmp_path).run_once().actions == []
