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

from .audio import to_int16_audio
from .catalog import (
    DEFAULT_MODEL_REPO_ID,
    LANGUAGE_CHOICES,
    VOICE_CHOICES,
    voice_language,
)
from .model import KModel
from .pipeline import KPipeline

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
        model_factory: Callable[[str], KModel] | None = None,
        pipeline_factory: Callable[[str], KPipeline] | None = None,
        eager_voices: bool = True,
    ) -> None:
        self.repo_id = repo_id or os.getenv("KOKORO_REPO_ID", DEFAULT_MODEL_REPO_ID)
        self._model_factory = model_factory or self._create_model
        self._pipeline_factory = pipeline_factory or self._create_pipeline
        self._models: dict[str, KModel] = {}
        self._active: dict[str, int] = {}
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

    def _create_model(self, device: str) -> KModel:
        return KModel(repo_id=self.repo_id).to(device).eval()

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
        for voice_id in VOICE_CHOICES.values():
            self.pipelines[voice_language(voice_id)].load_voice(voice_id)

    @property
    def loaded_model_devices(self) -> list[str]:
        with self._condition:
            return list(self._models)

    @property
    def last_fallback(self) -> dict[str, str] | None:
        with self._condition:
            return dict(self._last_fallback) if self._last_fallback else None

    @contextmanager
    def use_model(self, device: str) -> Iterator[KModel]:
        with self._condition:
            while self._purging_all or device in self._purging_devices:
                self._condition.wait()
            model = self._models.get(device)
            if model is None:
                model = self._model_factory(device)
                self._models[device] = model
            self._active[device] = self._active.get(device, 0) + 1
        try:
            yield model
        finally:
            with self._condition:
                self._active[device] -= 1
                if self._active[device] == 0:
                    del self._active[device]
                    self._condition.notify_all()

    def purge(self, device: str | None = None) -> tuple[list[str], list[str]]:
        removed: list[KModel] = []
        with self._condition:
            if device is None:
                self._purging_all = True
                while self._active:
                    self._condition.wait()
                purged = list(self._models)
                removed = list(self._models.values())
                self._models.clear()
                self._purging_all = False
            else:
                self._purging_devices.add(device)
                while self._active.get(device, 0):
                    self._condition.wait()
                purged = [device] if device in self._models else []
                model = self._models.pop(device, None)
                if model is not None:
                    removed.append(model)
                model = None
                self._purging_devices.remove(device)
            remaining = list(self._models)
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
    ) -> Iterator[SynthesisChunk]:
        pipeline = self.pipelines[voice_language(voice)]
        pack = pipeline.load_voice(voice)
        fallback_reason = None

        with ExitStack() as stack:
            model = stack.enter_context(self.use_model(device))
            inference_device = device
            for _, phonemes, _ in pipeline(text, voice, speed):
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
                    model = stack.enter_context(self.use_model("cpu"))
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
        self, text: str, voice: str, speed: float, device: str
    ) -> SynthesisResult | None:
        chunks = list(self.iter_synthesis(text, voice, speed, device))
        if not chunks:
            return None
        return SynthesisResult(
            audio=to_int16_audio(np.concatenate([chunk.audio for chunk in chunks])),
            phonemes="\n".join(chunk.phonemes for chunk in chunks),
            requested_device=device,
            inference_devices=tuple(
                dict.fromkeys(chunk.inference_device for chunk in chunks)
            ),
            fallback_reason=next(
                (chunk.fallback_reason for chunk in chunks if chunk.fallback_reason),
                None,
            ),
        )

    def phoneme_segments(self, text: str, voice: str) -> list[str]:
        pipeline = self.pipelines[voice_language(voice)]
        return [phonemes for _, phonemes, _ in pipeline(text, voice)]
