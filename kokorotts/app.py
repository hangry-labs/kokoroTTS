"""ASGI application composition for the KokoroTTS UI and API."""

from kokorotts.api import api
from kokorotts.standalone_ui.server import create_app as create_ui_app

app = create_ui_app(api_app=api)

__all__ = ["app"]
