"""Run OpenAI SDK compatibility tests with compact verbose output."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class CompactTextResult(unittest.TextTestResult):
    def getDescription(self, test):
        return test._testMethodName


class CompactTextRunner(unittest.TextTestRunner):
    resultclass = CompactTextResult


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_openai_client")
    runner = CompactTextRunner(verbosity=2)
    raise SystemExit(not runner.run(suite).wasSuccessful())
