from __future__ import annotations

import time
import unittest
import weakref
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import numpy as np

from kokorotts.runtime import InferenceRuntime


class FakePipeline:
    def load_voice(self, _voice):
        return [None] * 512

    def __call__(self, _text, _voice, _speed):
        yield "text", "abc", None


class FakeAudio:
    def numpy(self):
        return np.array([0.1, -0.1], dtype=np.float32)


class FakeModel:
    def __init__(self, device: str, error: RuntimeError | None = None):
        self.device = device
        self.error = error

    def __call__(self, _phonemes, _ref_s, _speed):
        if self.error:
            raise self.error
        return FakeAudio()


class InferenceRuntimeTest(unittest.TestCase):
    def runtime(self, model_factory):
        return InferenceRuntime(
            model_factory=model_factory,
            pipeline_factory=lambda _language: FakePipeline(),
            eager_voices=False,
        )

    def test_model_initialization_is_singleton_under_concurrency(self) -> None:
        calls = []

        def factory(device):
            calls.append(device)
            time.sleep(0.03)
            return FakeModel(device)

        runtime = self.runtime(factory)

        def acquire_model(_index):
            with runtime.use_model("cuda:0") as model:
                return id(model)

        with ThreadPoolExecutor(max_workers=8) as executor:
            model_ids = list(executor.map(acquire_model, range(8)))

        self.assertEqual(calls, ["cuda:0"])
        self.assertEqual(len(set(model_ids)), 1)

    def test_cuda_failure_falls_back_to_cpu_and_reports_it(self) -> None:
        def factory(device):
            if device == "cuda:0":
                return FakeModel(device, RuntimeError("CUDA out of memory"))
            return FakeModel(device)

        runtime = self.runtime(factory)
        result = runtime.synthesize("text", "af_heart", 1.0, "cuda:0")

        self.assertIsNotNone(result)
        self.assertEqual(result.inference_devices, ("cpu",))
        self.assertIn("CUDA out of memory", result.fallback_reason)
        self.assertEqual(runtime.last_fallback["inference_device"], "cpu")

    def test_non_cuda_runtime_error_is_not_hidden(self) -> None:
        runtime = self.runtime(
            lambda device: FakeModel(device, RuntimeError("invalid tensor shape"))
        )

        with self.assertRaisesRegex(RuntimeError, "invalid tensor shape"):
            runtime.synthesize("text", "af_heart", 1.0, "cuda:0")

    def test_purge_collects_objects_and_releases_cuda_cache(self) -> None:
        runtime = self.runtime(lambda device: FakeModel(device))
        with runtime.use_model("cuda:0") as model:
            model_reference = weakref.ref(model)
        del model

        with (
            patch("kokorotts.runtime.gc.collect") as collect,
            patch("kokorotts.runtime.torch.cuda.is_available", return_value=True),
            patch("kokorotts.runtime.torch.cuda.empty_cache") as empty_cache,
        ):
            purged, remaining = runtime.purge("cuda:0")

        self.assertEqual(purged, ["cuda:0"])
        self.assertEqual(remaining, [])
        self.assertIsNone(model_reference())
        collect.assert_called_once_with()
        empty_cache.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
