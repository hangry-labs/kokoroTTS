from __future__ import annotations

import unittest

import numpy as np

from kokorotts.audio import (
    SSML_IMPLICIT_PAUSE_MS,
    audio_to_wav_bytes,
    build_audio_effect_filters,
    compact_ssml_speech_audio,
    encode_audio_bytes,
    get_supported_output_formats,
    normalize_output_format,
    normalize_stream_format,
    trim_silent_audio_edges,
)


class AudioTest(unittest.TestCase):
    def test_format_aliases_preserve_compatibility(self) -> None:
        self.assertEqual(normalize_output_format(".mp3"), "mp3")
        self.assertEqual(normalize_output_format("raw"), "pcm")
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

    def test_openai_compatibility_encoders_produce_expected_containers(self) -> None:
        audio = np.array([0, 1000, -1000] * 800, dtype=np.int16)

        opus = encode_audio_bytes(audio, "opus")
        aac = encode_audio_bytes(audio, "aac")
        pcm = encode_audio_bytes(audio, "pcm")

        self.assertEqual(opus[:4], b"OggS")
        self.assertEqual(aac[0], 0xFF)
        self.assertIn(aac[1] & 0xF6, (0xF0, 0xF2, 0xF4, 0xF6))
        self.assertEqual(pcm, audio.astype("<i2", copy=False).tobytes())

    def test_raw_pcm_is_marked_non_playable_for_browser_ui(self) -> None:
        formats = get_supported_output_formats()

        self.assertFalse(formats["pcm"]["browser_playback"])
        self.assertTrue(formats["opus"]["browser_playback"])

    def test_silent_audio_edges_trim_only_requested_outer_frames(self) -> None:
        audio = np.concatenate(
            (
                np.zeros(4_800, dtype=np.float32),
                np.full(2_400, 0.25, dtype=np.float32),
                np.zeros(7_200, dtype=np.float32),
            )
        )

        leading = trim_silent_audio_edges(audio, leading=True)
        trailing = trim_silent_audio_edges(audio, trailing=True)
        both = trim_silent_audio_edges(audio, leading=True, trailing=True)

        self.assertEqual(len(leading), 9_600)
        self.assertEqual(len(trailing), 7_200)
        self.assertEqual(len(both), 2_400)
        self.assertTrue(np.all(both == 0.25))

    def test_ssml_speech_compaction_adds_100ms_implicit_pause(self) -> None:
        audio = np.concatenate(
            (
                np.zeros(4_800, dtype=np.int16),
                np.full(2_400, 8_000, dtype=np.int16),
                np.zeros(7_200, dtype=np.int16),
            )
        )

        compacted = compact_ssml_speech_audio(
            audio,
            trim_leading=True,
            trim_trailing=True,
            append_implicit_pause=True,
        )

        pause_samples = round(SSML_IMPLICIT_PAUSE_MS * 24_000 / 1000)
        self.assertEqual(len(compacted), 2_400 + pause_samples)
        self.assertTrue(np.all(compacted[:2_400] == 8_000))
        self.assertTrue(np.all(compacted[2_400:] == 0))


if __name__ == "__main__":
    unittest.main()
