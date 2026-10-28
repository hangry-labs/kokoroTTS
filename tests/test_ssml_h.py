from __future__ import annotations

import unittest

from kokorotts.ssml import SSMLValidationError, compile_ssml
from kokorotts.ssml_h import capabilities, compile_dialogue, parse_dialogue


def document(body):
    return (
        '<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:h="https://hangrylabs.app/ns/ssml-h/1.0">'
        + body
        + "</speak>"
    )


class SsmlHTests(unittest.TestCase):
    def parse(self, body):
        return parse_dialogue(
            document(body),
            "af_heart",
            lambda v: v in {"af_heart", "am_michael", "dm_martin", "zf_xiaoxiao"},
        )

    def test_same_voice_turn_identity_and_zero_break_are_preserved(self):
        turns = self.parse(
            '<voice name="af_heart">One.</voice><voice name="af_heart">Two.</voice><break time="0ms"/><s>Three.</s>'
        )
        self.assertEqual(
            [t.kind for t in turns], ["speech", "speech", "break", "speech"]
        )
        self.assertEqual(turns[2].duration_ms, 0)

    def test_language_switch_preserves_voice_and_voice_switch_uses_native_language(
        self,
    ):
        turns = self.parse(
            '<voice name="dm_martin">Guten Morgen.</voice><lang xml:lang="zh-CN">你好！</lang>'
        )
        self.assertEqual(
            [(t.voice, t.language) for t in turns],
            [("dm_martin", "d"), ("af_heart", "z")],
        )

    def test_standard_prosody_uses_tempo_not_model_speed(self):
        turns = self.parse(
            '<prosody rate="slow" pitch="high" volume="soft">Hello!</prosody>'
        )
        self.assertEqual(turns[0].prosody.speed, 1)
        self.assertEqual(turns[0].prosody.tempo, 0.75)
        self.assertEqual(turns[0].prosody.pitch_semitones, 2)
        self.assertEqual(turns[0].prosody.volume, 0.7)

    def test_standard_substitutions_numbers_and_strengths(self):
        turns = self.parse(
            '<s><sub alias="World Wide Web">WWW</sub> <say-as interpret-as="ordinal">3</say-as></s><break strength="weak"/>'
        )
        self.assertIn("World Wide Web", turns[0].text)
        self.assertIn("3rd", turns[0].text)
        self.assertEqual(turns[1].duration_ms, 200)

    def test_unsafe_xml_unknown_markup_design_direction_and_disabled_voice_fail(self):
        invalid = [
            '<audio src="http://example.com"/>',
            '<voice name="disabled">No.</voice>',
            '<voice name="af_heart" h:direction="angry">No.</voice>',
            '<metadata><h:extensions version="1.0"><h:voice-definition name="Bob" gender="male"/></h:extensions></metadata><voice name="Bob">No.</voice>',
            '<prosody speed="1.1">No.</prosody>',
            '<prosody rate="400%">No.</prosody>',
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(SSMLValidationError):
                self.parse(value)
        with self.assertRaises(SSMLValidationError):
            parse_dialogue(
                '<!DOCTYPE speak [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
                + document("&x;"),
                "af_heart",
            )

    def test_global_limits_cannot_be_bypassed_by_turn_splitting(self):
        with self.assertRaises(SSMLValidationError):
            self.parse('<break time="10000ms"/>' * 7)
        with self.assertRaises(SSMLValidationError):
            self.parse("<s>One.</s>" * 65)

    def test_long_turn_chunks_keep_one_take_group_and_never_truncate(self):
        groups = compile_dialogue(
            self.parse("<s>Hello.</s>"), lambda *_: iter(["a" * 400, "b" * 300])
        )
        self.assertEqual(len(groups), 1)
        self.assertEqual([len(u.phonemes) for u in groups[0]], [400, 300])
        with self.assertRaises(SSMLValidationError):
            compile_dialogue(self.parse("<s>Hello.</s>"), lambda *_: ["x" * 511])

    def test_legacy_ssml_contract_and_capabilities_are_honest(self):
        units = compile_ssml(
            '<speak><prosody speed="0.9" tempo="1.1">Hi.</prosody></speak>',
            "a",
            lambda *_: ["hi"],
        )
        self.assertEqual(units[0].prosody.speed, 0.9)
        self.assertEqual(units[0].prosody.tempo, 1.1)
        self.assertFalse(capabilities()["ssml_h"]["voice_definitions_supported"])
        self.assertFalse(capabilities()["magic"]["seed_supported"])


if __name__ == "__main__":
    unittest.main()
