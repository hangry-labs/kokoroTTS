from __future__ import annotations

import io
import tempfile
import unittest
import wave
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from benchmarks.tts import run_benchmark


class BenchmarkTests(unittest.TestCase):
    def test_voice_examples_cover_all_voices_and_languages(self) -> None:
        cases = run_benchmark._load_voice_cases(Path("examples/voices.js"))

        self.assertEqual(len(cases), 54)
        self.assertEqual(len({case["voice"] for case in cases}), 54)
        self.assertEqual(
            {case["language"] for case in cases},
            {
                "American English",
                "British English",
                "Japanese",
                "Mandarin Chinese",
                "Spanish",
                "French",
                "Hindi",
                "Italian",
                "Brazilian Portuguese",
            },
        )
        self.assertTrue(all(case["text"] for case in cases))

    def test_voice_examples_reject_duplicate_voices(self) -> None:
        source = (
            'window.VOICE_EXAMPLES = ['
            '{"name":"One","voice":"af_test","language":"English","text":"Hello"},'
            '{"name":"Two","voice":"af_test","language":"English","text":"Hello"}'
            '];\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "voices.js"
            path.write_text(source, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate voice"):
                run_benchmark._load_voice_cases(path)

    def test_warmup_selects_one_voice_per_language(self) -> None:
        cases = [
            {"voice": "a1", "language": "A"},
            {"voice": "a2", "language": "A"},
            {"voice": "b1", "language": "B"},
        ]

        warmups = run_benchmark._warmup_cases(cases)

        self.assertEqual([case["voice"] for case in warmups], ["a1", "b1"])

    def test_gpu_detection_selects_requested_device(self) -> None:
        output = (
            "0, NVIDIA GeForce RTX 5070 Ti, 16303, 610.88\n"
            "1, NVIDIA RTX 6000 Ada Generation, 49140, 610.88\n"
        )
        with patch.object(
            run_benchmark.subprocess,
            "run",
            return_value=CompletedProcess([], 0, stdout=output, stderr=""),
        ):
            gpu = run_benchmark._detect_gpu(1)

        self.assertEqual(gpu["index"], 1)
        self.assertEqual(gpu["name"], "NVIDIA RTX 6000 Ada Generation")
        self.assertEqual(gpu["memory_total_mib"], 49140)

    def test_wav_duration(self) -> None:
        target = io.BytesIO()
        with wave.open(target, "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(24_000)
            output.writeframes(b"\x00\x00" * 48_000)

        self.assertEqual(run_benchmark._wav_duration_seconds(target.getvalue()), 2.0)

    def test_performance_metrics_report_latency_and_realtime_speed(self) -> None:
        metrics = run_benchmark._performance_metrics(
            [
                {"characters": 10, "elapsed_sec": 0.1, "audio_duration_sec": 2.0, "error": ""},
                {"characters": 20, "elapsed_sec": 0.2, "audio_duration_sec": 3.0, "error": ""},
                {"characters": 30, "elapsed_sec": 0.3, "audio_duration_sec": 5.0, "error": ""},
            ]
        )

        self.assertEqual(metrics["requests"], 3)
        self.assertEqual(metrics["successful"], 3)
        self.assertEqual(metrics["characters"], 60)
        self.assertEqual(metrics["elapsed_sec"], 0.6)
        self.assertEqual(metrics["audio_duration_sec"], 10.0)
        self.assertEqual(metrics["mean_request_sec"], 0.2)
        self.assertEqual(metrics["p95_request_sec"], 0.29)
        self.assertEqual(metrics["realtime_factor"], 0.06)
        self.assertEqual(metrics["realtime_speed"], 16.67)

    def test_group_metrics_preserve_language_and_voice_metadata(self) -> None:
        results = [
            {
                "language": "English",
                "voice": "af_one",
                "name": "One",
                "characters": 10,
                "elapsed_sec": 0.2,
                "audio_duration_sec": 2.0,
                "error": "",
            },
            {
                "language": "English",
                "voice": "af_two",
                "name": "Two",
                "characters": 10,
                "elapsed_sec": 0.3,
                "audio_duration_sec": 2.0,
                "error": "",
            },
        ]

        languages = run_benchmark._group_metrics(results, "language")
        voices = run_benchmark._group_metrics(results, "voice")

        self.assertEqual(languages[0]["voices"], 2)
        self.assertEqual(languages[0]["requests"], 2)
        self.assertEqual(voices[0]["language"], "English")
        self.assertEqual(voices[0]["name"], "One")

    def test_failed_requests_do_not_distort_successful_metrics(self) -> None:
        metrics = run_benchmark._performance_metrics(
            [
                {"characters": 10, "elapsed_sec": 1.0, "audio_duration_sec": None, "error": "failed"},
                {"characters": 10, "elapsed_sec": 0.5, "audio_duration_sec": 2.0, "error": ""},
            ]
        )

        self.assertEqual(metrics["requests"], 2)
        self.assertEqual(metrics["successful"], 1)
        self.assertEqual(metrics["characters"], 10)
        self.assertEqual(metrics["elapsed_sec"], 0.5)
        self.assertEqual(metrics["realtime_factor"], 0.25)

    def test_summary_row_escapes_comment(self) -> None:
        output = {
            "version": "0.4-snapshot",
            "model": "hexgrad/Kokoro-82M",
            "gpu": None,
            "device": "auto",
            "voices": 1,
            "repetitions": 5,
            "metrics": {
                "requests": 5,
                "characters": 50,
                "audio_duration_sec": 10.0,
                "elapsed_sec": 1.0,
                "mean_request_sec": 0.2,
                "p95_request_sec": 0.3,
                "realtime_factor": 0.1,
                "realtime_speed": 10.0,
            },
            "test_time": "02.10.2026 12:00:00",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.md"
            run_benchmark._append_summary(path, output, "before | after")
            row = path.read_text(encoding="utf-8")

        self.assertIn("before \\| after", row)
        self.assertIn("0.4-snapshot", row)


if __name__ == "__main__":
    unittest.main()
