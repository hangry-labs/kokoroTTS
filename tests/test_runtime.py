from __future__ import annotations

import time
import tempfile
import unittest
import weakref
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import numpy as np

from kokorotts.runtime import InferenceRuntime
from kokorotts.settings import RuntimeSettingsStore


class FakePipeline:
    def __init__(self):
        self.voices = {}

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

        def factory(model_family, device):
            calls.append((model_family, device))
            time.sleep(0.03)
            return FakeModel(device)

        runtime = self.runtime(factory)

        def acquire_model(_index):
            with runtime.use_model("cuda:0") as model:
                return id(model)

        with ThreadPoolExecutor(max_workers=8) as executor:
            model_ids = list(executor.map(acquire_model, range(8)))

        self.assertEqual(calls, [("kokoro-v1.0", "cuda:0")])
        self.assertEqual(len(set(model_ids)), 1)

    def test_cuda_failure_falls_back_to_cpu_and_reports_it(self) -> None:
        def factory(_model_family, device):
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
            lambda _model_family, device: FakeModel(device, RuntimeError("invalid tensor shape"))
        )

        with self.assertRaisesRegex(RuntimeError, "invalid tensor shape"):
            runtime.synthesize("text", "af_heart", 1.0, "cuda:0")

    def test_ssml_synthesis_inserts_exact_silence_samples(self) -> None:
        runtime = self.runtime(lambda _model_family, device: FakeModel(device))

        result = runtime.synthesize(
            "<speak>Hello.<break time='500ms'/>World.</speak>",
            "af_heart",
            1.0,
            "cpu",
            "ssml",
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(result.audio), 12_004)
        self.assertEqual(result.phonemes, "abc\nabc")

    def test_purge_collects_objects_and_releases_cuda_cache(self) -> None:
        runtime = self.runtime(lambda _model_family, device: FakeModel(device))
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

    def test_different_voice_families_use_different_models_on_same_device(self) -> None:
        calls = []

        def factory(model_family, device):
            calls.append((model_family, device))
            return FakeModel(device)

        runtime = self.runtime(factory)
        with runtime.use_model("cpu", "kikiri-german-martin") as martin:
            pass
        with runtime.use_model("cpu", "kikiri-german-victoria") as victoria:
            pass

        self.assertIsNot(martin, victoria)
        self.assertEqual(len(calls), 2)
        self.assertEqual(runtime.loaded_model_devices, ["cpu"])
        self.assertEqual(len(runtime.loaded_models), 2)

    def test_served_voices_are_persisted_and_applied(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = RuntimeSettingsStore(Path(directory) / "settings.json")
            runtime = InferenceRuntime(
                model_factory=lambda _family, device: FakeModel(device),
                pipeline_factory=lambda _language: FakePipeline(),
                settings=settings,
                eager_voices=False,
            )

            selected = runtime.set_served_voices(["af_heart"])

            self.assertIn("af_heart", selected)
            self.assertIn("bf_emma", selected)
            self.assertTrue(runtime.serves_voice("af_heart"))
            self.assertTrue(runtime.serves_voice("bf_emma"))
            self.assertFalse(runtime.serves_voice("dm_martin"))
            self.assertFalse(runtime.serves_voice("df_victoria"))
            self.assertEqual(settings.served_voices(), selected)

    def test_model_family_setting_keeps_shared_voices_together(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = InferenceRuntime(
                model_factory=lambda _family, device: FakeModel(device),
                pipeline_factory=lambda _language: FakePipeline(),
                settings=RuntimeSettingsStore(Path(directory) / "settings.json"),
                eager_voices=False,
            )

            selected = runtime.set_served_model_families(
                ["kikiri-german-martin"]
            )

            self.assertEqual(selected, ["kikiri-german-martin"])
            self.assertEqual(runtime.served_voices, ["dm_martin"])
            self.assertEqual(runtime.served_model_families, selected)

    def test_reducing_served_voices_releases_cached_models(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = InferenceRuntime(
                model_factory=lambda _family, device: FakeModel(device),
                pipeline_factory=lambda _language: FakePipeline(),
                settings=RuntimeSettingsStore(Path(directory) / "settings.json"),
                eager_voices=False,
            )
            with runtime.use_model("cpu", "kikiri-german-martin"):
                pass

            runtime.set_served_voices(["af_heart"])

            self.assertEqual(runtime.loaded_models, [])


if __name__ == "__main__":
    unittest.main()
