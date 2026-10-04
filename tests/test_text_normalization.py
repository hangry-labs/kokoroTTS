from __future__ import annotations

import unittest

from kokorotts.catalog import DEFAULT_MODEL_REPO_ID
from kokorotts.pipeline import KPipeline
from kokorotts.text_normalization import (
    expand_english_eras,
    expand_english_large_units,
    expand_english_measurements,
    expand_english_roman_numerals,
    normalize_english_text,
    strip_english_markdown_emphasis,
)


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


class EnglishIssue108NormalizationTest(unittest.TestCase):
    def test_expands_issue_measurements_with_correct_pluralization(self) -> None:
        self.assertEqual(
            expand_english_measurements("1m, 10 m, 32ft, 40cm, 1 in, 1.5km"),
            "1 meter, 10 meters, 32 feet, 40 centimeters, 1 inch, 1.5 kilometers",
        )

    def test_measurements_preserve_identifiers_and_unrelated_units(self) -> None:
        text = "64MB, timer10m, 5ms, 10 M, 10m_value, 10m², CSS32ftRule, and room 2B"
        self.assertEqual(expand_english_measurements(text), text)

    def test_expands_year_adjacent_eras_only(self) -> None:
        self.assertEqual(
            expand_english_eras("1479 BC, 300 BCE, AD 1066, and 2026 CE"),
            "1479 before Christ, 300 before common era, anno Domini 1066, and 2026 common era",
        )
        self.assertEqual(
            expand_english_eras("BC Ferries and an AD campaign"),
            "BC Ferries and an AD campaign",
        )

    def test_expands_contextual_roman_numerals(self) -> None:
        self.assertEqual(
            expand_english_roman_numerals(
                "World War II, Chapter XI, Type II, Model IV, Thutmose II, Henry VIII, and Pope John Paul II"
            ),
            "World War 2, Chapter 11, Type 2, Model 4, Thutmose 2nd, Henry 8th, and Pope John Paul 2nd",
        )

    def test_preserves_invalid_or_context_free_capitals(self) -> None:
        text = "API IVR uses MIX tools; I agree with XML, and Chapter IIX is invalid."
        self.assertEqual(expand_english_roman_numerals(text), text)

    def test_normalizes_complete_issue_example(self) -> None:
        text = (
            "Thutmose II was an ancestor whose reign lasted from 1493 to 1479 BC. "
            "The passage had a 10m tunnel, a 32ft chamber, and a 40cm gap."
        )
        self.assertEqual(
            normalize_english_text(text),
            "Thutmose 2nd was an ancestor whose reign lasted from 1493 to 1479 before Christ. "
            "The passage had a 10 meters tunnel, a 32 feet chamber, and a 40 centimeters gap.",
        )

    def test_english_pipeline_applies_complete_normalization_before_g2p(self) -> None:
        pipeline = KPipeline.__new__(KPipeline)
        pipeline.lang_code = "a"
        pipeline.model = None
        pipeline.g2p = RecordingG2P()

        self.assertEqual(
            list(pipeline("Thutmose II crossed 10m in 1479 BC.", model=False)), []
        )
        self.assertEqual(
            pipeline.g2p.inputs,
            ["Thutmose 2nd crossed 10 meters in 1479 before Christ."],
        )

    def test_non_english_pipeline_preserves_issue_108_forms(self) -> None:
        pipeline = KPipeline.__new__(KPipeline)
        pipeline.lang_code = "f"
        pipeline.model = None
        pipeline.g2p = RecordingG2P()

        results = list(pipeline("Thutmose II, 10m, 1479 BC", model=False))

        self.assertEqual(pipeline.g2p.inputs, ["Thutmose II, 10m, 1479 BC"])
        self.assertEqual(results[0].phonemes, "Thutmose II, 10m, 1479 BC")


class EnglishIssue217NormalizationTest(unittest.TestCase):
    def test_strips_balanced_emphasis_around_contractions(self) -> None:
        self.assertEqual(
            strip_english_markdown_emphasis("You *shouldn't* and *don't* panic."),
            "You shouldn't and don't panic.",
        )

    def test_strips_single_double_and_triple_emphasis(self) -> None:
        self.assertEqual(
            strip_english_markdown_emphasis(
                "This is *important*, **very important**, and ***urgent***."
            ),
            "This is important, very important, and urgent.",
        )

    def test_preserves_literal_asterisk_uses(self) -> None:
        text = (
            "Use 2 * 3, 2*x*3, *.txt, \\*literal\\*, and * unmatched.\n"
            "* First item\n* Second item\nUse * as a symbol and * again."
        )
        self.assertEqual(strip_english_markdown_emphasis(text), text)

    def test_plain_english_pipeline_strips_emphasis_before_g2p(self) -> None:
        pipeline = KPipeline.__new__(KPipeline)
        pipeline.lang_code = "a"
        pipeline.model = None
        pipeline.g2p = RecordingG2P()

        self.assertEqual(list(pipeline("You *shouldn't* panic.", model=False)), [])
        self.assertEqual(pipeline.g2p.inputs, ["You shouldn't panic."])

    def test_explicit_ssml_pipeline_can_preserve_asterisks(self) -> None:
        pipeline = KPipeline.__new__(KPipeline)
        pipeline.lang_code = "a"
        pipeline.model = None
        pipeline.g2p = RecordingG2P()

        self.assertEqual(
            list(
                pipeline(
                    "You *shouldn't* panic.",
                    model=False,
                    normalize_markdown_emphasis=False,
                )
            ),
            [],
        )
        self.assertEqual(pipeline.g2p.inputs, ["You *shouldn't* panic."])


class EnglishPronunciationRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.american = KPipeline(
            lang_code="a", repo_id=DEFAULT_MODEL_REPO_ID, model=False
        )
        cls.british = KPipeline(
            lang_code="b", repo_id=DEFAULT_MODEL_REPO_ID, model=False
        )

    @staticmethod
    def phonemes(pipeline: KPipeline, text: str) -> str:
        return "".join(result.phonemes for result in pipeline(text, model=False))

    def test_pinned_frontend_pronounces_midair_in_both_english_variants(self) -> None:
        text = "The planes collided in midair."
        american_phonemes = self.phonemes(self.american, text)
        british_phonemes = self.phonemes(self.british, text)

        self.assertIn("mˌɪdˈɛɹ", american_phonemes)
        self.assertIn("mɪdˈAə", british_phonemes)

    def test_arithmetic_uses_noun_pronunciation_outside_noun_modifiers(self) -> None:
        cases = (
            "arithmetic",
            "Basic arithmetic is useful.",
            "She teaches arithmetic.",
            "Check the arithmetic.",
        )
        for text in cases:
            with self.subTest(dialect="us", text=text):
                self.assertIn(
                    "əɹˈɪθmətˌɪk", self.phonemes(self.american, text)
                )
            with self.subTest(dialect="gb", text=text):
                self.assertIn("əɹˈɪθmətɪk", self.phonemes(self.british, text))

    def test_arithmetic_uses_adjective_pronunciation_before_nouns(self) -> None:
        cases = (
            "This arithmetic operation is simple.",
            "Calculate the arithmetic mean.",
            "The arithmetic logic unit is ready.",
        )
        for text in cases:
            with self.subTest(dialect="us", text=text):
                self.assertIn(
                    "ˌɛɹɪθmˈɛTɪk", self.phonemes(self.american, text)
                )
            with self.subTest(dialect="gb", text=text):
                self.assertIn("ˌaɹɪθmˈɛtɪk", self.phonemes(self.british, text))


if __name__ == "__main__":
    unittest.main()
