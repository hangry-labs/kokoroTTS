"""KokoroTTS application package (UI + API)."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def _read_version() -> str:
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except OSError:
        try:
            return version("kokorotts")
        except PackageNotFoundError:
            return "0+unknown"


__version__ = _read_version()

from .client import AudioResponse, AudioStream, KokoroTTSClient, KokoroTTSClientError

__all__ = [
    "AudioResponse",
    "AudioStream",
    "KModel",
    "KPipeline",
    "KokoroTTSClient",
    "KokoroTTSClientError",
    "__version__",
]


def __getattr__(name: str):
    if name == "KModel":
        from .model import KModel

        return KModel
    if name == "KPipeline":
        from .pipeline import KPipeline

        return KPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
