"""Інтеграційні тести REST API (FastAPI TestClient) та сховища."""
import time

import pytest
from fastapi.testclient import TestClient

from cloudfolder.desktop.api_client import ApiClient, ApiError
from cloudfolder.server.app import create_app
from cloudfolder.server.storage import LocalFileStorage


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / "data", web_dist=tmp_path / "no-dist")
    with TestClient(app) as c:
        yield c


def auth(client, username="anna", password="secret1", register=True):
    path = "/api/auth/register" if register else "/api/auth/login"
    r = client.post(path, json={"username": username, "password": password})
    assert r.status_code in (200, 201), r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def upload(client, headers, name, data):
    r = client.post("/api/files", headers=headers, files={"file": (name, data)})
    assert r.status_code == 201, r.text
    return r.json()


def test_register_login_and_validation(client):
    auth(client)
    assert client.post("/api/auth/register", json={"username": "anna", "password": "secret1"}).status_code == 409
    assert client.post("/api/auth/register", json={"username": "x", "password": "secret1"}).status_code == 400
    assert client.post("/api/auth/login", json={"username": "anna", "password": "wrong!"}).status_code == 401
    h = auth(client, register=False)
    assert client.get("/api/files", headers=h).status_code == 200


def test_files_require_auth(client):
    assert client.get("/api/files").status_code == 401
    assert client.get("/api/files", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_upload_list_download_delete(client):
    h = auth(client)
    rec = upload(client, h, "config.xml", b"<cfg/>")
    assert rec["uploaded_by"] == rec["edited_by"] == "anna"
    assert rec["extension"] == ".xml"
    files = client.get("/api/files", headers=h).json()
    assert [f["name"] for f in files] == ["config.xml"]
    r = client.get(f"/api/files/{rec['id']}/content", headers=h)
    assert r.content == b"<cfg/>" and r.headers["content-type"].startswith("text/plain")
    assert client.delete(f"/api/files/{rec['id']}", headers=h).status_code == 204
    assert client.get("/api/files", headers=h).json() == []


def test_reupload_same_name_is_edit(client):
    h = auth(client)
    first = upload(client, h, "a.java", b"v1")
    time.sleep(1.1)
    second = upload(client, h, "a.java", b"v2")
    assert second["id"] == first["id"]
    assert second["created_at"] == first["created_at"]
    assert second["modified_at"] > first["modified_at"]


def test_users_have_isolated_spaces(client):
    h1 = auth(client, "anna")
    h2 = auth(client, "bohdan")
    rec = upload(client, h1, "secret.png", b"PNG")
    assert client.get("/api/files", headers=h2).json() == []
    assert client.get(f"/api/files/{rec['id']}/content", headers=h2).status_code == 404
    assert client.delete(f"/api/files/{rec['id']}", headers=h2).status_code == 404


def test_server_side_sort_and_filter(client):
    h = auth(client)
    for name in ["b.png", "a.java", "c.xml"]:
        upload(client, h, name, name.encode())
        time.sleep(1.1)
    asc = client.get("/api/files", headers=h, params={"sort": "modified_at", "order": "asc"}).json()
    assert [f["name"] for f in asc] == ["b.png", "a.java", "c.xml"]
    desc = client.get("/api/files", headers=h, params={"sort": "modified_at", "order": "desc", "type": ".png"}).json()
    assert [f["name"] for f in desc] == ["b.png"]
    assert client.get("/api/files", headers=h, params={"type": ".txt"}).status_code == 400


def test_rejects_bad_file_names(client):
    h = auth(client)
    r = client.post("/api/files", headers=h, files={"file": ("x", b"1")}, data={"name": "../.env"})
    assert r.status_code == 400


def test_desktop_api_client_against_real_app(client):
    api = ApiClient("http://testserver", transport=client._transport)
    api.register("Maryna", "secret1")
    rec = api.upload("pic.png", b"\x89PNG")
    assert [f.name for f in api.list_files()] == ["pic.png"]
    assert api.download(rec.id) == b"\x89PNG"
    api.delete(rec.id)
    with pytest.raises(ApiError) as err:
        api.delete(rec.id)
    assert err.value.status == 404


def test_local_storage_round_trip(tmp_path):
    st = LocalFileStorage(tmp_path)
    key = st.save(b"data")
    assert st.load(key) == b"data"
    st.delete(key)
    st.delete(key)  # повторне видалення не падає
    with pytest.raises(ValueError):
        st.load("../evil")
