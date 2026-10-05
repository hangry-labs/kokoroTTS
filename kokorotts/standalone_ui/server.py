from __future__ import annotations

import html
import json
import mimetypes
import os
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from kokorotts.standalone_ui.gpu import GPU_MONITOR


PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
LOCALES_DIR = STATIC_DIR / "locales"
LOCALE_MANIFEST_PATH = LOCALES_DIR / "manifest.json"
REPO_ROOT = PACKAGE_DIR.parents[1]
ASSET_DIR = REPO_ROOT / "assets"

mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("font/woff2", ".woff2")


def _read_version_file() -> str:
    try:
        return (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        try:
            return version("kokorotts")
        except PackageNotFoundError:
            return "0+unknown"


@lru_cache(maxsize=1)
def _locale_manifest() -> dict[str, object]:
    manifest = json.loads(LOCALE_MANIFEST_PATH.read_text(encoding="utf-8"))
    default_locale = str(manifest.get("defaultLocale") or "en")
    locales = manifest.get("locales")
    if not isinstance(locales, list) or not locales:
        raise ValueError("UI locale manifest must define at least one locale.")

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in locales:
        if not isinstance(item, dict):
            raise ValueError("Every UI locale manifest entry must be an object.")
        code = str(item.get("code") or "").strip().lower()
        if not code or code in seen or not (LOCALES_DIR / f"{code}.json").is_file():
            raise ValueError(f"Invalid or missing UI locale catalog: {code or '(empty)'}.json")
        seen.add(code)
        normalized.append(
            {
                "code": code,
                "name": str(item.get("name") or code),
                "path": f"/{code}",
                "direction": "rtl" if item.get("direction") == "rtl" else "ltr",
                "browserLanguage": str(item.get("browserLanguage") or code),
            }
        )
    if default_locale not in seen:
        raise ValueError(f"Default UI locale {default_locale!r} is not in the locale manifest.")
    return {"defaultLocale": default_locale, "locales": normalized}


@lru_cache(maxsize=16)
def _locale_catalog(locale: str) -> dict[str, str]:
    catalog = json.loads((LOCALES_DIR / f"{locale}.json").read_text(encoding="utf-8"))
    if not isinstance(catalog, dict) or not all(
        isinstance(key, str) and isinstance(value, str) and value
        for key, value in catalog.items()
    ):
        raise ValueError(f"UI locale catalog {locale}.json must contain non-empty string messages.")
    return catalog


def _index_response(locale: str) -> HTMLResponse:
    manifest = _locale_manifest()
    locale_entry = next(item for item in manifest["locales"] if item["code"] == locale)
    bootstrap = {
        "locale": locale,
        "defaultLocale": manifest["defaultLocale"],
        "locales": [
            {key: item[key] for key in ("code", "name", "path", "direction", "browserLanguage")}
            for item in manifest["locales"]
        ],
        "storageKey": "kokorotts-ui-locale-v1",
        "messages": _locale_catalog(locale),
    }
    bootstrap_json = json.dumps(bootstrap, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    index_html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    rendered_html = (
        index_html.replace("{{UI_VERSION}}", html.escape(_read_version_file()))
        .replace("{{UI_LOCALE}}", html.escape(locale))
        .replace("{{UI_DIRECTION}}", str(locale_entry["direction"]))
        .replace("{{UI_BOOTSTRAP}}", bootstrap_json)
    )
    return HTMLResponse(rendered_html, headers={"Cache-Control": "no-cache"})


def create_app(*, api_app: FastAPI) -> FastAPI:
    """Mount the standalone browser workspace on the existing TTS API."""
    development_assets = os.getenv("KOKOROTTS_UI_DEV", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    locale_manifest = _locale_manifest()
    locale_paths = {item["path"] for item in locale_manifest["locales"]}

    @api_app.middleware("http")
    async def disable_development_asset_cache(request, call_next):
        response = await call_next(request)
        if development_assets and (
            request.url.path == "/"
            or request.url.path in locale_paths
            or request.url.path.startswith("/static/")
            or request.url.path.startswith("/assets/")
        ):
            response.headers["Cache-Control"] = "no-store"
        return response

    api_app.mount("/static", StaticFiles(directory=STATIC_DIR), name="ui-static")
    if ASSET_DIR.is_dir():
        api_app.mount("/assets", StaticFiles(directory=ASSET_DIR), name="ui-assets")

    @api_app.get("/", include_in_schema=False)
    async def index() -> HTMLResponse:
        return _index_response(str(locale_manifest["defaultLocale"]))

    def locale_handler(locale: str):
        async def localized_index() -> HTMLResponse:
            return _index_response(locale)

        return localized_index

    for locale_entry in locale_manifest["locales"]:
        locale = str(locale_entry["code"])
        api_app.add_api_route(
            str(locale_entry["path"]),
            locale_handler(locale),
            methods=["GET"],
            include_in_schema=False,
            name=f"ui-{locale}",
        )

    @api_app.get("/system/gpu", include_in_schema=False)
    def gpu() -> JSONResponse:
        return JSONResponse(GPU_MONITOR.request_snapshot(), headers={"Cache-Control": "no-store"})

    return api_app
