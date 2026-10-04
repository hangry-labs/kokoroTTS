from __future__ import annotations

import unittest

from kokorotts.catalog import resolve_language_code
from kokorotts.ssml import (
    MAX_BREAK_MS,
    MAX_SSML_NESTING,
    SSMLValidationError,
    compile_ssml,
    parse_ssml,
)


class SsmlTest(unittest.TestCase):
    @staticmethod
    def phonemize(text: str, language: str, voice: str):
        if text.strip():
            yield f"{language}:{voice}:{text.strip().lower()}"

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

    def test_zero_break_is_preserved_as_an_explicit_boundary(self) -> None:
        units = compile_ssml(
            '<speak><voice name="af_heart">One.</voice><break time="0ms"/><voice name="am_michael">Two.</voice></speak>',
            "a",
            self.phonemize,
        )

        self.assertEqual([unit.kind for unit in units], ["speech", "break", "speech"])
        self.assertEqual(units[1].duration_ms, 0)

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

    def test_language_segments_route_g2p_without_changing_voice(self) -> None:
        units = compile_ssml(
            """<speak>你好，<lang xml:lang="en-US">Hello world.</lang>再见。</speak>""",
            "z",
            self.phonemize,
            default_voice="zf_xiaoxiao",
            resolve_language=lambda value: {"en-US": "a"}[value],
        )

        self.assertEqual(
            [(unit.language, unit.voice) for unit in units],
            [("z", "zf_xiaoxiao"), ("a", "zf_xiaoxiao"), ("z", "zf_xiaoxiao")],
        )
        self.assertIn("a:zf_xiaoxiao:hello world.", units[1].phonemes)

    def test_voice_segments_compile_as_ordered_dialogue_units(self) -> None:
        voice_languages = {"af_heart": "a", "am_michael": "a", "jf_alpha": "j"}
        units = compile_ssml(
            """<speak>
              <voice name="af_heart">Good morning.</voice>
              <voice name="am_michael">Coffee first.</voice>
              <voice name="jf_alpha"><say-as interpret-as="characters">AI</say-as></voice>
            </speak>""",
            "a",
            self.phonemize,
            default_voice="af_heart",
            resolve_voice_language=voice_languages.__getitem__,
        )

        dialogue = [unit for unit in units if unit.phonemes.strip()]
        self.assertEqual(
            [(unit.voice, unit.language) for unit in dialogue],
            [("af_heart", "a"), ("am_michael", "a"), ("jf_alpha", "j")],
        )
        self.assertIn("j:jf_alpha:a i", dialogue[2].phonemes)

    def test_language_can_be_nested_inside_voice(self) -> None:
        units = compile_ssml(
            """<speak><voice name="zf_xiaoxiao">你好，<lang xml:lang="en-US"><sub alias="Kokoro text to speech">KokoroTTS</sub></lang>。</voice></speak>""",
            "z",
            self.phonemize,
            default_voice="zf_xiaoxiao",
            resolve_language=lambda _value: "a",
            resolve_voice_language=lambda _voice: "z",
        )

        self.assertEqual([unit.language for unit in units], ["z", "a", "z"])
        self.assertTrue(all(unit.voice == "zf_xiaoxiao" for unit in units))

    def test_prosody_is_optional_inherited_and_composed(self) -> None:
        units = compile_ssml(
            """<speak>
              Plain.
              <prosody speed="0.9" pitch="+2st" tempo="1.1" volume="0.8">
                Styled.
                <prosody speed="" pitch="-1st" tempo="" volume="1.25">Nested.</prosody>
                Styled again.
              </prosody>
              <prosody>Neutral.</prosody>
            </speak>""",
            "a",
            self.phonemize,
        )

        self.assertEqual(len(units), 5)
        self.assertTrue(units[0].prosody.is_neutral)
        self.assertEqual(
            (
                units[1].prosody.speed,
                units[1].prosody.pitch_semitones,
                units[1].prosody.tempo,
                units[1].prosody.volume,
            ),
            (0.9, 2.0, 1.1, 0.8),
        )
        self.assertEqual(
            (
                units[2].prosody.speed,
                units[2].prosody.pitch_semitones,
                units[2].prosody.tempo,
                units[2].prosody.volume,
            ),
            (0.9, 1.0, 1.1, 1.0),
        )
        self.assertEqual(units[3].prosody, units[1].prosody)
        self.assertTrue(units[4].prosody.is_neutral)

    def test_prosody_rejects_invalid_or_out_of_range_values(self) -> None:
        invalid_documents = (
            '<speak><prosody speed="slow">No.</prosody></speak>',
            '<speak><prosody pitch="high">No.</prosody></speak>',
            '<speak><prosody tempo="0.4">No.</prosody></speak>',
            '<speak><prosody volume="2.1">No.</prosody></speak>',
            '<speak><prosody speed="1.5"><prosody speed="1.5">No.</prosody></prosody></speak>',
        )

        for document in invalid_documents:
            with self.subTest(document=document):
                with self.assertRaisesRegex(SSMLValidationError, "prosody"):
                    parse_ssml(document, "a")

    def test_voice_resolver_rejects_unavailable_voice(self) -> None:
        def reject_voice(voice: str) -> str:
            raise ValueError(f"Voice '{voice}' is not served by this deployment.")

        with self.assertRaisesRegex(SSMLValidationError, "not served"):
            compile_ssml(
                '<speak><voice name="missing">Hello.</voice></speak>',
                "a",
                self.phonemize,
                default_voice="af_heart",
                resolve_voice_language=reject_voice,
            )

    def test_language_aliases_accept_common_bcp47_forms(self) -> None:
        self.assertEqual(resolve_language_code("en-US"), "a")
        self.assertEqual(resolve_language_code("en_GB"), "b")
        self.assertEqual(resolve_language_code("zh-CN"), "z")
        self.assertEqual(resolve_language_code("ja-JP"), "j")
        self.assertEqual(resolve_language_code("de-DE"), "d")
        self.assertEqual(resolve_language_code("vi-VN"), "v")
        with self.assertRaisesRegex(ValueError, "Unsupported language"):
            resolve_language_code("ru-RU")

    def test_dialogue_nesting_limit_is_enforced(self) -> None:
        content = "Hello."
        for _ in range(MAX_SSML_NESTING + 1):
            content = f'<lang xml:lang="en-US">{content}</lang>'

        with self.assertRaisesRegex(SSMLValidationError, "nesting is limited"):
            parse_ssml(
                f"<speak>{content}</speak>",
                "a",
                resolve_language=resolve_language_code,
            )

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
            parse_ssml("<speak><emphasis>Hello</emphasis></speak>", "a")
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
