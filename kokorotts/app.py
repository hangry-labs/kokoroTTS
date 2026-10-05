"""ASGI application composition for the KokoroTTS UI and API."""

from kokorotts.api import api
from kokorotts.mcp_server import attach_mcp
from kokorotts.standalone_ui.server import create_app as create_ui_app

app = create_ui_app(api_app=attach_mcp(api_app=api))

__all__ = ["app"]
