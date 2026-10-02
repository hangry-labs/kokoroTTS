"""Lightweight Uvicorn launcher that leaves application import to Uvicorn."""

import os

import uvicorn


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "7860"))
    reload_enabled = os.getenv("UVICORN_RELOAD", "0").lower() in {"1", "true", "yes"}
    uvicorn.run("kokorotts.app:app", host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    main()
