from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from benchmarks.vram import run_benchmark


class VramBenchmarkTests(unittest.TestCase):
    def test_mib_conversion(self) -> None:
        self.assertEqual(run_benchmark._mib(1024 * 1024), 1.0)
        self.assertEqual(run_benchmark._mib(1536 * 1024), 1.5)

    def test_device_sampler_records_peak(self) -> None:
        values = iter((100.0, 125.0, 110.0, 105.0))

        def sample(_device: str) -> dict[str, float]:
            used = next(values, 105.0)
            return {"used_mib": used, "free_mib": 1000.0 - used, "total_mib": 1000.0}

        sampler = run_benchmark.DeviceMemorySampler("cuda:0", 0.001, sample)
        sampler.start()
        time.sleep(0.004)
        result = sampler.stop()

        self.assertGreaterEqual(result["samples"], 2)
        self.assertEqual(result["peak_used_mib"], 125.0)
        self.assertEqual(result["minimum_free_mib"], 875.0)

    def test_language_groups_report_highest_voice(self) -> None:
        results = [
            {
                "language": "English",
                "voice": "af_one",
                "process": {"peak_allocated_mib": 100.0, "peak_reserved_mib": 120.0},
                "device": {"peak_used_mib": 500.0},
            },
            {
                "language": "English",
                "voice": "af_two",
                "process": {"peak_allocated_mib": 110.0, "peak_reserved_mib": 140.0},
                "device": {"peak_used_mib": 490.0},
            },
        ]

        grouped = run_benchmark._group_languages(results)

        self.assertEqual(grouped[0]["voices"], 2)
        self.assertEqual(grouped[0]["peak_reserved_mib"], 140.0)
        self.assertEqual(grouped[0]["peak_reserved_voice"], "af_two")
        self.assertEqual(grouped[0]["device_peak_voice"], "af_one")

    def test_summary_escapes_comment(self) -> None:
        memory = {
            "allocated_mib": 0.0,
            "reserved_mib": 0.0,
            "peak_allocated_mib": 0.0,
            "peak_reserved_mib": 0.0,
        }
        output = {
            "version": "0.4-snapshot",
            "model": "hexgrad/Kokoro-82M",
            "gpu": None,
            "voices": 1,
            "sample_interval_ms": 50.0,
            "test_time": "03.10.2026 12:00:00",
            "stages": {
                "before_runtime": {
                    "process": memory,
                    "device": {"used_mib": 100.0, "total_mib": 16000.0},
                },
                "after_weights": {
                    "process": {**memory, "allocated_mib": 500.0, "reserved_mib": 600.0}
                },
            },
            "peaks": {
                "process_allocated_mib": 700.0,
                "process_reserved_mib": 800.0,
                "inference_reserved_increment_mib": 200.0,
                "device_used_mib": 1200.0,
                "device_increment_mib": 1100.0,
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.md"
            run_benchmark._append_summary(path, output, "clean | baseline")
            row = path.read_text(encoding="utf-8")

        self.assertIn("clean \\| baseline", row)
        self.assertIn("700.0 MiB", row)


if __name__ == "__main__":
    unittest.main()
