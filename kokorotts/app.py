"""ASGI application composition for the KokoroTTS UI and API."""

from kokorotts.api import api
from kokorotts.mcp_server import attach_mcp
from kokorotts.standalone_ui.server import create_app as create_ui_app
from kokorotts.standalone_ui.magic_api import attach_magic
from kokorotts.standalone_ui.script_api import attach_scripts
from kokorotts.api import RUNTIME

app = create_ui_app(api_app=attach_mcp(api_app=api))
attach_magic(app)
attach_scripts(app, RUNTIME.settings.path.parent / "scripts")

__all__ = ["app"]
