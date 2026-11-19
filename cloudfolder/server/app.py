"""REST API сервера «Хмарне сховище» (FastAPI).

Запуск:  python -m cloudfolder.server  (див. __main__.py)
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, Header, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..core import variant
from .db import Database, FileRepo, UserRepo
from .services import AuthService, FileService, ServiceError
from .storage import LocalFileStorage

ROOT = Path(__file__).resolve().parents[2]


class Credentials(BaseModel):
    username: str
    password: str


def _secret(data_dir: Path) -> str:
    env = os.environ.get("CLOUDFOLDER_SECRET")
    if env:
        return env
    path = data_dir / "secret.key"
    if not path.exists():
        path.write_text(secrets.token_hex(32), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


def create_app(data_dir: Path | str | None = None, web_dist: Path | str | None = None) -> FastAPI:
    data_dir = Path(data_dir or os.environ.get("CLOUDFOLDER_DATA", ROOT / "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    db = Database(data_dir / "cloudfolder.sqlite3")
    auth = AuthService(UserRepo(db), _secret(data_dir))
    files = FileService(FileRepo(db), LocalFileStorage(data_dir / "blobs"))

    app = FastAPI(title="Хмарне сховище API", version="1.0")
    app.state.db, app.state.auth, app.state.files = db, auth, files

    @app.exception_handler(ServiceError)
    async def _service_error(_: Request, exc: ServiceError):
        return JSONResponse({"detail": str(exc)}, status_code=exc.status)

    def current_user(authorization: str | None = Header(default=None)) -> tuple[int, str]:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise ServiceError("Потрібна автентифікація", 401)
        return auth.authenticate(authorization.split(" ", 1)[1])

    # ------------------------------------------------------------------ auth
    @app.post("/api/auth/register", status_code=201)
    def register(body: Credentials):
        token = auth.register(body.username, body.password)
        return {"access_token": token, "username": body.username.strip()}

    @app.post("/api/auth/login")
    def login(body: Credentials):
        token = auth.login(body.username, body.password)
        _, username = auth.authenticate(token)
        return {"access_token": token, "username": username}

    @app.get("/api/variant")
    def variant_info():
        return {
            "variant": variant.VARIANT,
            "preview_text": list(variant.PREVIEW_TEXT_EXTENSIONS),
            "preview_image": list(variant.PREVIEW_IMAGE_EXTENSIONS),
            "filter_extensions": list(variant.FILTER_EXTENSIONS),
            "sort_attribute": variant.VARIANT_SORT_ATTRIBUTE,
        }

    # ------------------------------------------------------------------ files
    @app.get("/api/files")
    def list_files(
        sort: str | None = Query(default=None),
        order: str = Query(default="asc", pattern="^(asc|desc|none)$"),
        type: str | None = Query(default=None),
        user=Depends(current_user),
    ):
        return [f.to_json() for f in files.list(user[0], sort, order, type)]

    @app.post("/api/files", status_code=201)
    async def upload(
        file: UploadFile = File(...),
        name: str | None = Form(default=None),
        user=Depends(current_user),
    ):
        data = await file.read()
        record = files.upload(user[0], user[1], name or file.filename or "", data)
        return record.to_json()

    @app.get("/api/files/{file_id}/content")
    def file_content(file_id: int, download: bool = False, user=Depends(current_user)):
        record, data = files.content(user[0], file_id)
        kind = variant.preview_kind(record.name)
        media = {"text": "text/plain; charset=utf-8", "image": "image/png"}.get(kind.value, "application/octet-stream")
        disposition = "attachment" if download else "inline"
        return Response(
            data,
            media_type=media,
            headers={"Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(record.name)}"},
        )

    @app.delete("/api/files/{file_id}", status_code=204)
    def delete_file(file_id: int, user=Depends(current_user)):
        files.delete(user[0], file_id)
        return Response(status_code=204)

    # ------------------------------------------------------------------ web SPA (монолітне розгортання)
    dist = Path(web_dist or ROOT / "web" / "dist")
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            target = (dist / path).resolve()
            if path and target.is_file() and dist.resolve() in target.parents:
                return FileResponse(target)
            return FileResponse(dist / "index.html")

    return app
