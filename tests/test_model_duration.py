from __future__ import annotations

import unittest

import torch

from kokorotts.model import _scale_speech_token_durations


class ModelDurationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.duration = torch.tensor([[19.0, 2.0, 6.0, 10.0]])

    def test_slow_speed_scales_only_speech_tokens(self) -> None:
        scaled = _scale_speech_token_durations(self.duration, 0.5)

        self.assertTrue(
            torch.equal(scaled, torch.tensor([[19.0, 4.0, 12.0, 10.0]]))
        )

    def test_fast_speed_scales_only_speech_tokens(self) -> None:
        scaled = _scale_speech_token_durations(self.duration, 2.0)

        self.assertTrue(
            torch.equal(scaled, torch.tensor([[19.0, 1.0, 3.0, 10.0]]))
        )

    def test_default_speed_is_exact_and_does_not_mutate_input(self) -> None:
        original = self.duration.clone()

        scaled = _scale_speech_token_durations(self.duration, 1.0)

        self.assertTrue(torch.equal(scaled, original))
        self.assertTrue(torch.equal(self.duration, original))


if __name__ == "__main__":
    unittest.main()
