from __future__ import annotations

import unittest

import torch
import torch.nn.functional as F

from kokorotts.istftnet import SineGen


def _legacy_interpolated_sines(generator: SineGen, f0_values: torch.Tensor) -> torch.Tensor:
    """Reproduce the former non-pulse path, including its ineffective RNG draw."""
    rad_values = (f0_values / generator.sampling_rate) % 1
    rand_ini = torch.rand(
        f0_values.shape[0], f0_values.shape[2], device=f0_values.device
    )
    rand_ini[:, 0] = 0
    rad_values[:, 0, :] = rad_values[:, 0, :] + rand_ini
    rad_values = F.interpolate(
        rad_values.transpose(1, 2),
        scale_factor=1 / generator.upsample_scale,
        mode="linear",
    ).transpose(1, 2)
    phase = torch.cumsum(rad_values, dim=1) * 2 * torch.pi
    phase = F.interpolate(
        phase.transpose(1, 2) * generator.upsample_scale,
        scale_factor=generator.upsample_scale,
        mode="linear",
    ).transpose(1, 2)
    return torch.sin(phase)


class SineGenTest(unittest.TestCase):
    def setUp(self) -> None:
        self.f0_values = torch.full((1, 1_200, 3), 210.0)

    def test_interpolated_source_matches_legacy_output_exactly(self) -> None:
        generator = SineGen(24_000, 300, harmonic_num=2)

        torch.manual_seed(12_345)
        legacy = _legacy_interpolated_sines(generator, self.f0_values)
        torch.manual_seed(12_345)
        current = generator._f02sine(self.f0_values)

        self.assertTrue(torch.equal(current, legacy))

    def test_interpolated_source_does_not_advance_rng(self) -> None:
        generator = SineGen(24_000, 300, harmonic_num=2)
        torch.manual_seed(12_345)
        state_before = torch.random.get_rng_state()

        generator._f02sine(self.f0_values)

        self.assertTrue(torch.equal(torch.random.get_rng_state(), state_before))

    def test_pulse_source_retains_randomized_harmonic_phase(self) -> None:
        generator = SineGen(24_000, 300, harmonic_num=2, flag_for_pulse=True)

        torch.manual_seed(1)
        first = generator._f02sine(self.f0_values)
        torch.manual_seed(2)
        second = generator._f02sine(self.f0_values)

        self.assertFalse(torch.equal(first[..., 1:], second[..., 1:]))


if __name__ == "__main__":
    unittest.main()
