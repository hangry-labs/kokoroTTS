from __future__ import annotations

import unittest

from kokorotts.ssml import (
    MAX_BREAK_MS,
    SSMLValidationError,
    compile_ssml,
    parse_ssml,
)


class SsmlTest(unittest.TestCase):
    @staticmethod
    def phonemize(text: str):
        yield text.strip().lower()

    def test_supported_elements_compile_into_speech_and_break_units(self) -> None:
        document = """<speak version="1.0">
          Hello <sub alias="World Wide Web Consortium">W3C</sub>.
          <break time="500ms"/>
          Attempt <say-as interpret-as="ordinal">3</say-as> by
          <say-as interpret-as="characters">SQL</say-as>.
        </speak>"""

        units = compile_ssml(document, "a", self.phonemize)

        self.assertEqual([unit.kind for unit in units], ["speech", "break", "speech"])
        self.assertIn("world wide web consortium", units[0].phonemes)
        self.assertEqual(units[1].duration_ms, 500)
        self.assertIn("3rd", units[2].phonemes)
        self.assertIn("s q l", units[2].phonemes)

    def test_phoneme_override_bypasses_phonemizer(self) -> None:
        units = compile_ssml(
            '<speak>Hello <phoneme alphabet="ipa" ph="wˈɜːld">world</phoneme>.</speak>',
            "a",
            self.phonemize,
        )

        self.assertEqual(len(units), 1)
        self.assertIn("wˈɜːld", units[0].phonemes)
        self.assertTrue(units[0].contains_phoneme_override)
        self.assertEqual(units[0].phoneme_override_characters, frozenset("wˈɜːld"))

    def test_standard_ssml_namespace_is_accepted(self) -> None:
        segments = parse_ssml(
            '<speak xmlns="http://www.w3.org/2001/10/synthesis">Hello.</speak>',
            "a",
        )

        self.assertEqual(segments[0].value, "Hello.")

    def test_ssml_requires_explicit_speak_root(self) -> None:
        with self.assertRaisesRegex(SSMLValidationError, "<speak> root"):
            parse_ssml("<voice>Hello world.</voice>", "a")

    def test_unknown_and_nested_elements_are_rejected(self) -> None:
        with self.assertRaisesRegex(SSMLValidationError, "Unsupported SSML element"):
            parse_ssml("<speak><prosody rate='slow'>Hello</prosody></speak>", "a")
        with self.assertRaisesRegex(SSMLValidationError, "Nested tags"):
            parse_ssml(
                "<speak><sub alias='API'><say-as interpret-as='characters'>API</say-as></sub></speak>",
                "a",
            )

    def test_unsafe_xml_declarations_are_rejected(self) -> None:
        document = '<!DOCTYPE speak [<!ENTITY x "hello">]><speak>&x;</speak>'

        with self.assertRaisesRegex(SSMLValidationError, "Invalid or unsafe SSML"):
            parse_ssml(document, "a")
        with self.assertRaisesRegex(SSMLValidationError, "Invalid or unsafe SSML"):
            parse_ssml("<!DOCTYPE speak><speak>Hello.</speak>", "a")

    def test_break_limits_are_enforced(self) -> None:
        with self.assertRaisesRegex(SSMLValidationError, "Each <break>"):
            parse_ssml(
                f'<speak><break time="{MAX_BREAK_MS + 1}ms"/></speak>', "a"
            )
        with self.assertRaisesRegex(SSMLValidationError, "Total SSML break"):
            parse_ssml(
                "<speak>"
                "<break time='10s'/><break time='10s'/>"
                "<break time='10s'/><break time='1ms'/>"
                "</speak>",
                "a",
            )
        with self.assertRaisesRegex(SSMLValidationError, "Each <break>"):
            parse_ssml(f'<speak><break time="{"9" * 400}ms"/></speak>', "a")

    def test_ordinal_is_explicitly_limited_to_english(self) -> None:
        with self.assertRaisesRegex(SSMLValidationError, "English voices only"):
            parse_ssml(
                "<speak><say-as interpret-as='ordinal'>3</say-as></speak>", "f"
            )
        with self.assertRaisesRegex(SSMLValidationError, "18 digits"):
            parse_ssml(
                "<speak><say-as interpret-as='ordinal'>1234567890123456789</say-as></speak>",
                "a",
            )


if __name__ == "__main__":
    unittest.main()
