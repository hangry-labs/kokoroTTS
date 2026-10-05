from __future__ import annotations

import tempfile
import time
import unittest
import weakref
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import numpy as np

from kokorotts.catalog import CHINESE_V11_MODEL_FAMILY
from kokorotts.runtime import InferenceRuntime
from kokorotts.settings import RuntimeSettingsStore


class FakePipeline:
    def __init__(self, language: str = "a"):
        self.language = language
        self.voices = {}
        self.calls = []

    def load_voice(self, _voice):
        return [None] * 512

    def __call__(self, _text, _voice, _speed, **kwargs):
        self.calls.append({"voice": _voice, **kwargs})
        yield "text", f"{self.language}abc", None


class FakeAudio:
    def numpy(self):
        return np.array([0.1, -0.1], dtype=np.float32)


class FakeModel:
    def __init__(self, device: str, error: RuntimeError | None = None):
        self.device = device
        self.error = error
        self.speeds = []

    def __call__(self, _phonemes, _ref_s, _speed):
        self.speeds.append(_speed)
        if self.error:
            raise self.error
        return FakeAudio()


class InferenceRuntimeTest(unittest.TestCase):
    def runtime(self, model_factory):
        return InferenceRuntime(
            model_factory=model_factory,
            pipeline_factory=lambda language: FakePipeline(language),
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
            lambda _model_family, device: FakeModel(
                device, RuntimeError("invalid tensor shape")
            )
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
        self.assertEqual(result.phonemes, "aabc\naabc")

    def test_ssml_dialogue_switches_voice_and_model_family_in_order(self) -> None:
        model_calls = []

        def model_factory(model_family, device):
            model_calls.append((model_family, device))
            return FakeModel(device)

        runtime = self.runtime(model_factory)
        chunks = list(
            runtime.iter_synthesis(
                """<speak>
                  <voice name="af_heart">Hello.</voice>
                  <voice name="dm_martin">Guten Tag.</voice>
                  <voice name="af_heart">Welcome back.</voice>
                </speak>""",
                "af_heart",
                1.0,
                "cpu",
                "ssml",
            )
        )

        speech = [chunk for chunk in chunks if chunk.phonemes]
        self.assertEqual(
            [(chunk.voice, chunk.language) for chunk in speech],
            [("af_heart", "a"), ("dm_martin", "d"), ("af_heart", "a")],
        )
        self.assertEqual(
            model_calls,
            [("kokoro-v1.0", "cpu"), ("kikiri-german-martin", "cpu")],
        )

    def test_ssml_language_tag_preserves_selected_voice(self) -> None:
        runtime = self.runtime(lambda _model_family, device: FakeModel(device))

        units = runtime.prepare_synthesis(
            '<speak>你好。<lang xml:lang="en-US">Hello.</lang></speak>',
            "zf_xiaoxiao",
            "ssml",
        )

        self.assertEqual(
            [(unit.language, unit.voice) for unit in units],
            [("z", "zf_xiaoxiao"), ("a", "zf_xiaoxiao")],
        )

    def test_v11_chinese_voice_uses_family_specific_pipeline(self) -> None:
        family_pipeline_calls = []

        def family_pipeline_factory(model_family, language):
            family_pipeline_calls.append((model_family, language))
            return FakePipeline(language)

        runtime = InferenceRuntime(
            model_factory=lambda _family, device: FakeModel(device),
            pipeline_factory=lambda language: FakePipeline(language),
            family_pipeline_factory=family_pipeline_factory,
            eager_voices=False,
        )

        standard = runtime.prepare_synthesis("你好。", "zf_xiaoxiao")
        v11 = runtime.prepare_synthesis("你好。", "zf_001")
        repeated = runtime.prepare_synthesis("欢迎。", "zf_001")

        self.assertEqual(standard[0].phonemes, "zabc")
        self.assertEqual(v11[0].phonemes, "zabc")
        self.assertEqual(repeated[0].phonemes, "zabc")
        self.assertEqual(family_pipeline_calls, [(CHINESE_V11_MODEL_FAMILY, "z")])

    def test_ssml_prosody_speed_is_applied_per_speech_unit(self) -> None:
        model = FakeModel("cpu")
        runtime = self.runtime(lambda _model_family, _device: model)

        list(
            runtime.iter_synthesis(
                "<speak>Normal.<prosody speed='0.75'>Slower.</prosody></speak>",
                "af_heart",
                1.2,
                "cpu",
                "ssml",
            )
        )

        self.assertEqual(len(model.speeds), 2)
        self.assertAlmostEqual(model.speeds[0], 1.2)
        self.assertAlmostEqual(model.speeds[1], 0.9)

    def test_markdown_cleanup_is_limited_to_plain_text(self) -> None:
        pipeline = FakePipeline()
        runtime = InferenceRuntime(
            model_factory=lambda _model_family, device: FakeModel(device),
            pipeline_factory=lambda _language: pipeline,
            eager_voices=False,
        )

        runtime.phoneme_segments("You *shouldn't* panic.", "af_heart", "text")
        runtime.phoneme_segments(
            "<speak>You *shouldn't* panic.</speak>", "af_heart", "ssml"
        )

        self.assertEqual(
            [call["normalize_markdown_emphasis"] for call in pipeline.calls],
            [True, False],
        )

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

    def test_model_family_purge_preserves_other_loaded_checkpoints(self) -> None:
        runtime = self.runtime(lambda _model_family, device: FakeModel(device))
        with runtime.use_model("cuda:0", "kokoro-v1.0"):
            pass
        with runtime.use_model("cuda:0", "kikiri-german-martin"):
            pass

        with (
            patch("kokorotts.runtime.gc.collect") as collect,
            patch("kokorotts.runtime.torch.cuda.is_available", return_value=True),
            patch("kokorotts.runtime.torch.cuda.empty_cache") as empty_cache,
        ):
            remaining = runtime.purge_model_families({"kikiri-german-martin"})

        self.assertEqual(
            remaining,
            [{"model_family": "kokoro-v1.0", "device": "cuda:0"}],
        )
        self.assertEqual(runtime.loaded_models, remaining)
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

            selected = runtime.set_served_model_families(["kikiri-german-martin"])

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
