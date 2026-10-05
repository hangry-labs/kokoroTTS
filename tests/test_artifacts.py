from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kokorotts.artifacts import (
    ArtifactExpiredError,
    ArtifactNotFoundError,
    ArtifactStore,
)


class ArtifactStoreTests(unittest.TestCase):
    def test_artifact_is_resolved_before_expiry_without_exposing_input_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ArtifactStore(directory)
            artifact = store.create(
                b"audio",
                extension="mp3",
                ttl_seconds=300,
                format="mp3",
                mime_type="audio/mpeg",
                duration_seconds=1.25,
                sample_rate=24_000,
                voice="af_heart",
                language="a",
                voices=["af_heart"],
                languages=["a"],
                inference_devices=["cuda:0"],
                fallback_reason=None,
                now=1000,
            )

            resolved, path = store.resolve(artifact.token, now=1200)
            metadata = json.loads(
                (Path(directory) / f"{artifact.token}.json").read_text(encoding="utf-8")
            )
            audio = path.read_bytes()

        self.assertEqual(audio, b"audio")
        self.assertEqual(resolved.size_bytes, 5)
        self.assertNotIn("text", metadata)
        self.assertNotIn("audio", metadata)

    def test_expired_artifact_is_unavailable_and_removed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ArtifactStore(directory)
            artifact = store.create(
                b"audio",
                extension="wav",
                ttl_seconds=60,
                format="wav",
                mime_type="audio/wav",
                duration_seconds=1,
                sample_rate=24_000,
                voice="af_heart",
                language="a",
                voices=["af_heart"],
                languages=["a"],
                inference_devices=["cpu"],
                fallback_reason=None,
                now=1000,
            )
            with self.assertRaisesRegex(ArtifactExpiredError, "expired"):
                store.resolve(artifact.token, now=1060)

            self.assertFalse(any(Path(directory).iterdir()))

    def test_invalid_token_never_escapes_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ArtifactStore(directory)
            with self.assertRaisesRegex(ArtifactNotFoundError, "not found"):
                store.resolve("../settings", now=1000)


if __name__ == "__main__":
    unittest.main()
