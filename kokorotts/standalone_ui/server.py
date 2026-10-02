from __future__ import annotations

import html
import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from kokorotts.standalone_ui.gpu import GPU_MONITOR


PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
REPO_ROOT = PACKAGE_DIR.parents[1]
BRAND_DIR = REPO_ROOT / "hangrylabs"


def _read_version_file() -> str:
    try:
        return (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        try:
            return version("kokorotts")
        except PackageNotFoundError:
            return "0+unknown"


def create_app(*, api_app: FastAPI) -> FastAPI:
    """Mount the standalone browser workspace on the existing TTS API."""
    development_assets = os.getenv("KOKOROTTS_UI_DEV", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    @api_app.middleware("http")
    async def disable_development_asset_cache(request, call_next):
        response = await call_next(request)
        if development_assets and (
            request.url.path == "/"
            or request.url.path.startswith("/static/")
            or request.url.path.startswith("/brand/")
        ):
            response.headers["Cache-Control"] = "no-store"
        return response

    api_app.mount("/static", StaticFiles(directory=STATIC_DIR), name="ui-static")
    if BRAND_DIR.is_dir():
        api_app.mount("/brand", StaticFiles(directory=BRAND_DIR), name="ui-brand")

    @api_app.get("/", include_in_schema=False)
    async def index() -> HTMLResponse:
        index_html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        rendered_html = index_html.replace("{{UI_VERSION}}", html.escape(_read_version_file()))
        return HTMLResponse(rendered_html, headers={"Cache-Control": "no-cache"})

    @api_app.get("/system/gpu", include_in_schema=False)
    def gpu() -> JSONResponse:
        return JSONResponse(GPU_MONITOR.request_snapshot(), headers={"Cache-Control": "no-store"})

    return api_app
