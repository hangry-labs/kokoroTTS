from __future__ import annotations

import unittest

from kokorotts.pipeline import KPipeline
from kokorotts.text_normalization import expand_english_large_units


class RecordingG2P:
    def __init__(self) -> None:
        self.inputs: list[str] = []

    def __call__(self, text: str):
        self.inputs.append(text)
        return text, []


class EnglishLargeUnitNormalizationTest(unittest.TestCase):
    def test_expands_supported_units(self) -> None:
        self.assertEqual(
            expand_english_large_units("20K, 3M, 4B, and 5T"),
            "20 thousand, 3 million, 4 billion, and 5 trillion",
        )

    def test_preserves_currency_and_decimal_values(self) -> None:
        self.assertEqual(
            expand_english_large_units("$1.5M, £2B, and $1,200K"),
            "$1.5 million, £2 billion, and $1,200 thousand",
        )

    def test_ignores_ambiguous_or_identifier_suffixes(self) -> None:
        text = "10m, 64MB, ABC12M, v2B, and 3_k"
        self.assertEqual(expand_english_large_units(text), text)

    def test_english_pipeline_normalizes_before_g2p(self) -> None:
        pipeline = KPipeline.__new__(KPipeline)
        pipeline.lang_code = "a"
        pipeline.model = None
        pipeline.g2p = RecordingG2P()

        self.assertEqual(list(pipeline("The file has 20K rows.", model=False)), [])
        self.assertEqual(pipeline.g2p.inputs, ["The file has 20 thousand rows."])

    def test_non_english_pipeline_does_not_apply_english_expansion(self) -> None:
        pipeline = KPipeline.__new__(KPipeline)
        pipeline.lang_code = "f"
        pipeline.model = None
        pipeline.g2p = RecordingG2P()

        results = list(pipeline("Le fichier contient 20K lignes.", model=False))

        self.assertEqual(pipeline.g2p.inputs, ["Le fichier contient 20K lignes."])
        self.assertEqual(results[0].phonemes, "Le fichier contient 20K lignes.")


if __name__ == "__main__":
    unittest.main()
