from __future__ import annotations

import unittest

import numpy as np

from kokorotts.audio import (
    audio_to_wav_bytes,
    build_audio_effect_filters,
    normalize_output_format,
    normalize_stream_format,
)


class AudioTest(unittest.TestCase):
    def test_format_aliases_preserve_compatibility(self) -> None:
        self.assertEqual(normalize_output_format(".mp3"), "mp3")
        self.assertEqual(normalize_output_format(None), "wav")
        self.assertEqual(normalize_stream_format("raw"), "pcm_s16le")

    def test_audio_controls_build_expected_filter_chain(self) -> None:
        filters = build_audio_effect_filters(
            24_000, pitch_semitones=2, tempo=1.1, volume=0.9, normalize=True
        )

        self.assertTrue(filters[0].startswith("asetrate="))
        self.assertIn("atempo=1.100000", filters)
        self.assertIn("volume=0.900000", filters)
        self.assertTrue(filters[-1].startswith("loudnorm="))

    def test_wav_encoder_produces_pcm_container(self) -> None:
        encoded = audio_to_wav_bytes(np.array([0, 100, -100], dtype=np.int16))

        self.assertEqual(encoded[:4], b"RIFF")
        self.assertEqual(encoded[8:12], b"WAVE")


if __name__ == "__main__":
    unittest.main()
