"""Inference lifecycle and synthesis orchestration."""

from __future__ import annotations

import gc
import logging
import os
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Condition, RLock

import numpy as np
import torch
from huggingface_hub import hf_hub_download

from .audio import SAMPLE_RATE, to_int16_audio
from .catalog import (
    CUSTOM_VOICE_ASSETS,
    DEFAULT_MODEL_REPO_ID,
    LANGUAGE_CHOICES,
    STANDARD_MODEL_FAMILY,
    model_families_for_voices,
    voice_language,
    voice_model_family,
    voices_for_model_families,
)
from .model import KModel
from .pipeline import KPipeline
from .settings import RuntimeSettingsStore
from .ssml import SSMLSynthesisUnit, SSMLValidationError, compile_ssml

logger = logging.getLogger(__name__)

CUDA_ERROR_MARKERS = (
    "cuda error",
    "cuda out of memory",
    "cublas",
    "cudnn",
    "cusparse",
    "device-side assert",
)


@dataclass(frozen=True)
class SynthesisChunk:
    audio: np.ndarray
    phonemes: str
    requested_device: str
    inference_device: str
    fallback_reason: str | None = None


@dataclass(frozen=True)
class SynthesisResult:
    audio: np.ndarray
    phonemes: str
    requested_device: str
    inference_devices: tuple[str, ...]
    fallback_reason: str | None = None


class InferenceRuntime:
    """Own pipelines, prepared voices, model instances, and their lifecycle."""

    def __init__(
        self,
        repo_id: str | None = None,
        *,
        model_factory: Callable[[str, str], KModel] | None = None,
        pipeline_factory: Callable[[str], KPipeline] | None = None,
        settings: RuntimeSettingsStore | None = None,
        eager_voices: bool = True,
    ) -> None:
        self.repo_id = repo_id or os.getenv("KOKORO_REPO_ID", DEFAULT_MODEL_REPO_ID)
        self._model_factory = model_factory or self._create_model
        self._pipeline_factory = pipeline_factory or self._create_pipeline
        self.settings = settings or RuntimeSettingsStore()
        self._served_voices = self.settings.served_voices()
        self._models: dict[tuple[str, str], KModel] = {}
        self._active: dict[tuple[str, str], int] = {}
        self._purging_devices: set[str] = set()
        self._purging_all = False
        self._last_fallback: dict[str, str] | None = None
        self._condition = Condition(RLock())
        self.pipelines = {
            language: self._pipeline_factory(language) for language in LANGUAGE_CHOICES
        }
        self._add_product_pronunciations()
        if eager_voices:
            self.prepare_voices()

    def _create_model(self, model_family: str, device: str) -> KModel:
        if model_family == STANDARD_MODEL_FAMILY:
            return KModel(repo_id=self.repo_id).to(device).eval()
        asset = next(
            value
            for value in CUSTOM_VOICE_ASSETS.values()
            if value["model_family"] == model_family
        )
        config_repo_id = asset.get(
            "config_repo_id",
            asset["repo_id"] if "config_file" in asset else self.repo_id,
        )
        config_path = hf_hub_download(
            repo_id=config_repo_id, filename=asset.get("config_file", "config.json")
        )
        model_path = hf_hub_download(
            repo_id=asset["repo_id"], filename=asset["model_file"]
        )
        return KModel(
            repo_id=asset["repo_id"], config=config_path, model=model_path
        ).to(device).eval()

    def _create_pipeline(self, language: str) -> KPipeline:
        return KPipeline(lang_code=language, repo_id=self.repo_id, model=False)

    def _add_product_pronunciations(self) -> None:
        for language, pronunciation in (("a", "kˈOkəɹO"), ("b", "kˈQkəɹQ")):
            pipeline = self.pipelines.get(language)
            lexicon = getattr(getattr(pipeline, "g2p", None), "lexicon", None)
            if lexicon is not None:
                lexicon.golds["kokoro"] = pronunciation

    def prepare_voices(self) -> None:
        """Prepare every advertised voice before the service reports ready."""
        for voice_id in self.served_voices:
            self._load_voice(voice_id)

    def _load_voice(self, voice_id: str):
        pipeline = self.pipelines[voice_language(voice_id)]
        voices = getattr(pipeline, "voices", {})
        if voice_id in voices:
            return pipeline.voices[voice_id]
        asset = CUSTOM_VOICE_ASSETS.get(voice_id)
        if asset is None:
            return pipeline.load_voice(voice_id)
        voice_path = hf_hub_download(
            repo_id=asset["repo_id"], filename=asset["voice_file"]
        )
        pack = torch.load(voice_path, map_location="cpu", weights_only=True)
        if not hasattr(pipeline, "voices"):
            pipeline.voices = {}
        pipeline.voices[voice_id] = pack
        return pack

    @property
    def served_voices(self) -> list[str]:
        with self._condition:
            return list(self._served_voices)

    def set_served_voices(self, voices: list[str]) -> list[str]:
        selected = self.settings.validate_served_voices(voices)
        return self._apply_served_voices(selected)

    @property
    def served_model_families(self) -> list[str]:
        return model_families_for_voices(self.served_voices)

    def set_served_model_families(self, families: list[str]) -> list[str]:
        selected_families = self.settings.validate_served_model_families(families)
        self._apply_served_voices(voices_for_model_families(selected_families))
        return selected_families

    def _apply_served_voices(self, selected: list[str]) -> list[str]:
        previous = self.served_voices
        for voice_id in selected:
            self._load_voice(voice_id)
        self.settings.set_served_voices(selected)
        with self._condition:
            self._served_voices = selected
        disabled = set(previous) - set(selected)
        for voice_id in disabled:
            pipeline = self.pipelines[voice_language(voice_id)]
            pipeline.voices.pop(voice_id, None)
        if disabled:
            self.purge()
        return list(selected)

    def serves_voice(self, voice_id: str) -> bool:
        with self._condition:
            return voice_id in self._served_voices

    @property
    def loaded_model_devices(self) -> list[str]:
        with self._condition:
            return list(dict.fromkeys(device for _, device in self._models))

    @property
    def loaded_models(self) -> list[dict[str, str]]:
        with self._condition:
            return [
                {"model_family": family, "device": device}
                for family, device in self._models
            ]

    @property
    def last_fallback(self) -> dict[str, str] | None:
        with self._condition:
            return dict(self._last_fallback) if self._last_fallback else None

    @contextmanager
    def use_model(
        self, device: str, model_family: str = STANDARD_MODEL_FAMILY
    ) -> Iterator[KModel]:
        key = (model_family, device)
        with self._condition:
            while self._purging_all or device in self._purging_devices:
                self._condition.wait()
            model = self._models.get(key)
            if model is None:
                model = self._model_factory(model_family, device)
                self._models[key] = model
            self._active[key] = self._active.get(key, 0) + 1
        try:
            yield model
        finally:
            with self._condition:
                self._active[key] -= 1
                if self._active[key] == 0:
                    del self._active[key]
                    self._condition.notify_all()

    def purge(self, device: str | None = None) -> tuple[list[str], list[str]]:
        removed: list[KModel] = []
        with self._condition:
            if device is None:
                self._purging_all = True
                while self._active:
                    self._condition.wait()
                purged = list(dict.fromkeys(key[1] for key in self._models))
                removed = list(self._models.values())
                self._models.clear()
                self._purging_all = False
            else:
                self._purging_devices.add(device)
                while any(key[1] == device for key in self._active):
                    self._condition.wait()
                matching = [key for key in self._models if key[1] == device]
                purged = [device] if matching else []
                removed.extend(self._models.pop(key) for key in matching)
                self._purging_devices.remove(device)
            remaining = list(dict.fromkeys(key[1] for key in self._models))
            self._condition.notify_all()

        del removed
        gc.collect()
        if torch.cuda.is_available() and (device is None or device.startswith("cuda")):
            torch.cuda.empty_cache()
        return purged, remaining

    @staticmethod
    def is_recoverable_cuda_error(error: RuntimeError) -> bool:
        if isinstance(error, torch.cuda.OutOfMemoryError):
            return True
        message = str(error).lower()
        return any(marker in message for marker in CUDA_ERROR_MARKERS)

    def iter_synthesis(
        self,
        text: str,
        voice: str,
        speed: float,
        device: str,
        input_type: str = "text",
        plan: list[SSMLSynthesisUnit] | None = None,
    ) -> Iterator[SynthesisChunk]:
        if plan is None:
            plan = self.prepare_synthesis(text, voice, input_type)
        pack = self._load_voice(voice)
        model_family = voice_model_family(voice)
        fallback_reason = None

        with ExitStack() as stack:
            model = stack.enter_context(self.use_model(device, model_family))
            inference_device = device
            for unit in plan:
                if unit.kind == "break":
                    yield SynthesisChunk(
                        audio=np.zeros(
                            round(unit.duration_ms * SAMPLE_RATE / 1000),
                            dtype=np.float32,
                        ),
                        phonemes="",
                        requested_device=device,
                        inference_device=inference_device,
                        fallback_reason=fallback_reason,
                    )
                    continue
                phonemes = unit.phonemes
                if unit.contains_phoneme_override and hasattr(model, "vocab"):
                    unsupported = sorted(
                        character
                        for character in unit.phoneme_override_characters
                        if character not in model.vocab
                    )
                    if unsupported:
                        rendered = ", ".join(repr(character) for character in unsupported[:12])
                        raise SSMLValidationError(
                            f"Phoneme override contains characters outside this model's vocabulary: {rendered}."
                        )
                ref_s = pack[len(phonemes) - 1]
                try:
                    generated = model(phonemes, ref_s, speed)
                except RuntimeError as error:
                    if (
                        inference_device != device
                        or not device.startswith("cuda")
                        or not self.is_recoverable_cuda_error(error)
                    ):
                        raise
                    fallback_reason = str(error)
                    logger.warning(
                        "CUDA inference failed on %s; continuing this request on CPU",
                        device,
                    )
                    with self._condition:
                        self._last_fallback = {
                            "requested_device": device,
                            "inference_device": "cpu",
                            "error": fallback_reason,
                            "timestamp": datetime.now(UTC).isoformat(),
                        }
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    model = stack.enter_context(self.use_model("cpu", model_family))
                    inference_device = "cpu"
                    generated = model(phonemes, ref_s, speed)
                yield SynthesisChunk(
                    audio=generated.numpy(),
                    phonemes=phonemes,
                    requested_device=device,
                    inference_device=inference_device,
                    fallback_reason=fallback_reason,
                )

    def synthesize(
        self,
        text: str,
        voice: str,
        speed: float,
        device: str,
        input_type: str = "text",
    ) -> SynthesisResult | None:
        chunks = list(self.iter_synthesis(text, voice, speed, device, input_type))
        if not chunks:
            return None
        return SynthesisResult(
            audio=to_int16_audio(np.concatenate([chunk.audio for chunk in chunks])),
            phonemes="\n".join(chunk.phonemes for chunk in chunks if chunk.phonemes),
            requested_device=device,
            inference_devices=tuple(
                dict.fromkeys(chunk.inference_device for chunk in chunks)
            ),
            fallback_reason=next(
                (chunk.fallback_reason for chunk in chunks if chunk.fallback_reason),
                None,
            ),
        )

    def prepare_synthesis(
        self, text: str, voice: str, input_type: str = "text"
    ) -> list[SSMLSynthesisUnit]:
        pipeline = self.pipelines[voice_language(voice)]

        def phonemize(value: str) -> Iterator[str]:
            for _, phonemes, _ in pipeline(
                value,
                voice,
                1.0,
                normalize_markdown_emphasis=input_type == "text",
            ):
                yield phonemes

        if input_type == "text":
            return [
                SSMLSynthesisUnit("speech", phonemes=phonemes)
                for phonemes in phonemize(text)
            ]
        if input_type == "ssml":
            return compile_ssml(text, voice_language(voice), phonemize)
        raise ValueError("input_type must be 'text' or 'ssml'")

    def phoneme_segments(
        self, text: str, voice: str, input_type: str = "text"
    ) -> list[str]:
        return [
            unit.phonemes
            for unit in self.prepare_synthesis(text, voice, input_type)
            if unit.kind == "speech"
        ]
