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

import sys
try:
    from loguru import logger
except ImportError:
    import logging

    logger = logging.getLogger("kokorotts")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(asctime)s | %(name)s:%(lineno)d | %(levelname)s | %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
else:
    # Replace the default logger format with concise module:line context.
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <cyan>{module:>16}:{line}</cyan> | <level>{level: >8}</level> | <level>{message}</level>",
        colorize=True,
        level="INFO",
    )

if hasattr(logger, "disable"):
    logger.disable("kokorotts")

from .client import AudioResponse, KokoroTTSClient, KokoroTTSClientError

__all__ = [
    "AudioResponse",
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
