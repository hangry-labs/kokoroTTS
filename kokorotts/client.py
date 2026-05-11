"""Small dependency-free client for the KokoroTTS HTTP API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class KokoroTTSClientError(RuntimeError):
    """Raised when the KokoroTTS API returns an error or cannot be reached."""


@dataclass(frozen=True)
class AudioResponse:
    """Audio bytes returned by a KokoroTTS synthesis endpoint."""

    content: bytes
    media_type: str
    headers: dict[str, str]

    @property
    def filename(self) -> str | None:
        disposition = self.headers.get("content-disposition", "")
        for part in disposition.split(";"):
            part = part.strip()
            if part.startswith("filename="):
                return part.split("=", 1)[1].strip('"')
        return None

    def save(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.write_bytes(self.content)
        return output_path


class KokoroTTSClient:
    """Python client for a running KokoroTTS UI/API server."""

    def __init__(self, base_url: str = "http://localhost:7860", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def ping(self) -> dict[str, Any]:
        return self._json("GET", "/tts/ping")

    def status(self) -> dict[str, Any]:
        return self._json("GET", "/tts/status")

    def defaults(self) -> dict[str, Any]:
        return self._json("GET", "/tts/defaults")

    def formats(self) -> dict[str, Any]:
        return self._json("GET", "/tts/formats")

    def stream_formats(self) -> dict[str, Any]:
        return self._json("GET", "/tts/stream-formats")

    def languages(self) -> dict[str, Any]:
        return self._json("GET", "/tts/languages")

    def speakers(self, language: str = "a") -> dict[str, Any]:
        return self._json("GET", f"/tts/speakers?{urlencode({'language': language})}")

    def voices(self) -> dict[str, Any]:
        return self._json("GET", "/tts/voices")

    def metrics(self, text: str, voice: str = "af_heart") -> dict[str, Any]:
        return self._json("POST", "/tts/metrics", {"text": text, "voice": voice})

    def purge(self, device: str | None = None) -> dict[str, Any]:
        payload = {} if device is None else {"device": device}
        return self._json("POST", "/tts/purge", payload)

    def generate(
        self,
        text: str,
        voice: str = "af_heart",
        speed: float = 1.0,
        device: str = "auto",
        output_format: str = "wav",
        pitch_semitones: float = 0.0,
        tempo: float = 1.0,
        volume: float = 1.0,
        normalize: bool = False,
    ) -> AudioResponse:
        return self._audio(
            "/tts/generate",
            self._tts_payload(
                text,
                voice,
                speed,
                device,
                output_format,
                pitch_semitones,
                tempo,
                volume,
                normalize,
            ),
        )

    def convert(
        self,
        text: str,
        voice: str = "af_heart",
        speed: float = 1.0,
        device: str = "auto",
        output_format: str = "wav",
        pitch_semitones: float = 0.0,
        tempo: float = 1.0,
        volume: float = 1.0,
        normalize: bool = False,
    ) -> AudioResponse:
        return self._audio(
            "/tts/convert",
            self._tts_payload(
                text,
                voice,
                speed,
                device,
                output_format,
                pitch_semitones,
                tempo,
                volume,
                normalize,
            ),
        )

    def stream(
        self,
        text: str,
        voice: str = "af_heart",
        speed: float = 1.0,
        device: str = "auto",
        stream_format: str = "pcm_s16le",
        pitch_semitones: float = 0.0,
        tempo: float = 1.0,
        volume: float = 1.0,
        normalize: bool = False,
    ) -> AudioResponse:
        payload = self._tts_payload(
            text,
            voice,
            speed,
            device,
            "wav",
            pitch_semitones,
            tempo,
            volume,
            normalize,
        )
        payload["stream_format"] = stream_format
        return self._audio("/tts/stream", payload)

    def _tts_payload(
        self,
        text: str,
        voice: str,
        speed: float,
        device: str,
        output_format: str,
        pitch_semitones: float,
        tempo: float,
        volume: float,
        normalize: bool,
    ) -> dict[str, Any]:
        return {
            "text": text,
            "voice": voice,
            "speed": speed,
            "device": device,
            "output_format": output_format,
            "pitch_semitones": pitch_semitones,
            "tempo": tempo,
            "volume": volume,
            "normalize": normalize,
        }

    def _json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._request(method, path, payload)
        if not response:
            return {}
        return json.loads(response.decode("utf-8"))

    def _audio(self, path: str, payload: dict[str, Any]) -> AudioResponse:
        content, media_type, headers = self._request_with_headers("POST", path, payload)
        return AudioResponse(content=content, media_type=media_type, headers=headers)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> bytes:
        content, _, _ = self._request_with_headers(method, path, payload)
        return content

    def _request_with_headers(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> tuple[bytes, str, dict[str, str]]:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "*/*"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_headers = {key.lower(): value for key, value in response.headers.items()}
                media_type = response_headers.get("content-type", "application/octet-stream").split(";", 1)[0]
                return response.read(), media_type, response_headers
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise KokoroTTSClientError(f"KokoroTTS API error {exc.code}: {detail}") from exc
        except URLError as exc:
            raise KokoroTTSClientError(f"Could not reach KokoroTTS API at {url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise KokoroTTSClientError(f"Timed out waiting for KokoroTTS API at {url}") from exc
