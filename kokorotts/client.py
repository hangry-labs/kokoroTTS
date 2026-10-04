"""Small dependency-free client for the KokoroTTS HTTP API."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Self
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


class AudioStream:
    """Incremental audio response that owns the underlying HTTP connection."""

    def __init__(
        self,
        response: BinaryIO,
        media_type: str,
        headers: dict[str, str],
        chunk_size: int,
    ) -> None:
        self._response = response
        self.media_type = media_type
        self.headers = headers
        self.chunk_size = chunk_size

    def __iter__(self) -> Iterator[bytes]:
        read_chunk = getattr(self._response, "read1", self._response.read)
        while chunk := read_chunk(self.chunk_size):
            yield chunk

    def read(self) -> bytes:
        return self._response.read()

    def close(self) -> None:
        self._response.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


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

    def sample(
        self, language: str = "a", random_sample: bool = False
    ) -> dict[str, Any]:
        query = urlencode({"language": language, "random": str(random_sample).lower()})
        return self._json("GET", f"/tts/samples?{query}")

    def speakers(self, language: str = "a") -> dict[str, Any]:
        return self._json("GET", f"/tts/speakers?{urlencode({'language': language})}")

    def voices(self) -> dict[str, Any]:
        return self._json("GET", "/tts/voices")

    def deployment_settings(self) -> dict[str, Any]:
        return self._json("GET", "/system/settings")

    def set_served_voices(self, voices: list[str]) -> dict[str, Any]:
        return self._json("PUT", "/system/settings/voices", {"voices": voices})

    def set_served_model_families(self, model_families: list[str]) -> dict[str, Any]:
        return self._json(
            "PUT",
            "/system/settings/model-families",
            {"model_families": model_families},
        )

    def metrics(
        self, text: str, voice: str = "af_heart", input_type: str = "text"
    ) -> dict[str, Any]:
        return self._json(
            "POST",
            "/tts/metrics",
            {"text": text, "voice": voice, "input_type": input_type},
        )

    def tokenize(
        self, text: str, voice: str = "af_heart", input_type: str = "text"
    ) -> dict[str, Any]:
        return self._json(
            "POST",
            "/tts/tokenize",
            {"text": text, "voice": voice, "input_type": input_type},
        )

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
        input_type: str = "text",
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
                input_type,
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
        input_type: str = "text",
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
                input_type,
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
        input_type: str = "text",
    ) -> AudioResponse:
        with self.iter_stream(
            text=text,
            voice=voice,
            speed=speed,
            device=device,
            stream_format=stream_format,
            pitch_semitones=pitch_semitones,
            tempo=tempo,
            volume=volume,
            normalize=normalize,
            input_type=input_type,
        ) as stream:
            return AudioResponse(
                content=b"".join(stream),
                media_type=stream.media_type,
                headers=stream.headers,
            )

    def iter_stream(
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
        chunk_size: int = 64 * 1024,
        input_type: str = "text",
    ) -> AudioStream:
        """Open a streaming request and yield bytes as they arrive."""
        if chunk_size < 1:
            raise ValueError("chunk_size must be at least 1")
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
            input_type,
        )
        payload["stream_format"] = stream_format
        response, media_type, headers = self._open_with_headers(
            "POST", "/tts/stream", payload
        )
        return AudioStream(response, media_type, headers, chunk_size)

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
        input_type: str,
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
            "input_type": input_type,
        }

    def _json(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        response = self._request(method, path, payload)
        if not response:
            return {}
        return json.loads(response.decode("utf-8"))

    def _audio(self, path: str, payload: dict[str, Any]) -> AudioResponse:
        content, media_type, headers = self._request_with_headers("POST", path, payload)
        return AudioResponse(content=content, media_type=media_type, headers=headers)

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> bytes:
        content, _, _ = self._request_with_headers(method, path, payload)
        return content

    def _request_with_headers(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> tuple[bytes, str, dict[str, str]]:
        response, media_type, response_headers = self._open_with_headers(
            method, path, payload
        )
        with response:
            return response.read(), media_type, response_headers

    def _open_with_headers(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> tuple[BinaryIO, str, dict[str, str]]:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "*/*"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(url, data=data, headers=headers, method=method)
        try:
            response = urlopen(request, timeout=self.timeout)
            response_headers = {
                key.lower(): value for key, value in response.headers.items()
            }
            media_type = response_headers.get(
                "content-type", "application/octet-stream"
            ).split(";", 1)[0]
            return response, media_type, response_headers
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise KokoroTTSClientError(
                f"KokoroTTS API error {exc.code}: {detail}"
            ) from exc
        except URLError as exc:
            raise KokoroTTSClientError(
                f"Could not reach KokoroTTS API at {url}: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise KokoroTTSClientError(
                f"Timed out waiting for KokoroTTS API at {url}"
            ) from exc
