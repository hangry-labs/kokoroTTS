# KokoroTTS SSML-H and Magic Studio

Magic is the visual dialogue editor adapted from Hangry Labs Qwen3-TTS Studio.
It edits real SSML-H documents: choose a voice for each turn, add pauses and
transformations, preview or regenerate individual turns, lock good takes, and
assemble the result. Undo/redo, pronunciation substitutions, import/export,
folders, search and explicit workspace saving are available without a frontend
build step or external browser services.

See the [Magic Studio and dialogue showcase](../examples/ssml.html#magic-studio)
for the editor screenshot and a Bella/Isabella conversation available as Opus audio.

## Processor Profile

The [SSML-H specification](https://hangrylabs.app/ns/ssml-h/1.0) is maintained
separately. This processor uses `ssml-h-tools==0.3.1` and advertises its exact
subset at `GET /tts/ssml/capabilities`. It does not claim full W3C conformance.

Native generation, streaming, metrics and token inspection accept explicit
`input_type="ssml-h"`. Plain text remains the API default; markup is never
auto-detected. Existing `input_type="ssml"` keeps its original parser, direct
IPA support, and `speed`/`tempo` semantics. OpenAI compatibility remains plain
text only.

```xml
<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis"
       xmlns:h="https://hangrylabs.app/ns/ssml-h/1.0">
  <voice name="af_heart">Is the release ready?</voice>
  <break time="150ms"/>
  <voice name="am_michael">
    <prosody rate="slow" pitch="-1st" volume="soft">After one more test!</prosody>
  </voice>
</speak>
```

Supported standard elements: `speak`, `metadata`, `p`, `s`, `token`, `w`,
`voice`, `lang`, `break`, `prosody`, `sub`, `say-as`. Standard rate/pitch/volume
presets and numeric percentages/semitones are accepted. Rate is an audio tempo
effect; the native request's `speed` still controls Kokoro model delivery.
Nested rates/volumes multiply and pitch adds. Effective request plus per-turn
values must stay within tempo 0.5-2, pitch -12 to +12 semitones and volume 0-2.
Normalization applies once to the assembled recording, not to individual takes.

`voice` selects an enabled native voice and its checkpoint/native language;
an explicit `lang` overrides the text frontend without changing voice identity.
Do not expect native bilingual quality from a voice trained for one language.
Adjacent turns have the same conservative 100 ms handoff as existing SSML;
explicit breaks replace it, including `0ms`. Outer recording padding is retained.
Long turns are split into model-safe chunks but remain one editable Magic take.

Kokoro has no neural voice design, cloning or instruction-following model.
SSML-H voice definitions, saved voice profiles and `h:direction` are therefore
unsupported, hidden in Magic and rejected explicitly by the server. Select
native voices and use prosody instead. Remote audio, lexicons and SSML-H direct
phonemes are unsupported; existing legacy SSML remains available for IPA.

Limits: 50000 source characters, 300 XML elements, nesting 12, 200 semantic
units, 64 speech turns, 10 seconds per break and 60 seconds total explicit
breaks. Magic render/assembly additionally caps audio at 300 seconds. Unsafe
XML, DTDs, entities, external references and unknown markup fail validation.
More complex valid documents can stay in the raw SSML-H editor when the visual
editor cannot preserve their structure; it does not silently simplify them.

## Endpoints

| Endpoint | Contract |
| --- | --- |
| `GET /tts/ssml/capabilities` | Supported tags, extensions, controls and limits; no model inference. |
| `POST /tts/plan` | Native generation JSON; returns semantic turns and phoneme chunks without synthesis. Legacy text/SSML return token-inspection data. |
| `POST /tts/magic/take` | JSON `{"payload": {...native request...}, "speech_index": 0}`; returns one complete mono 24 kHz PCM16 WAV take. Index counts speech turns, not pauses or model chunks. |
| `POST /tts/magic/render` | Multipart `payload` (native JSON with `ssml-h`), `speech_ids` (unique string array), `retained` (array of `{id, seed}`), optional repeated `takes` WAV uploads. Generates only missing takes, then returns the shared binary take bundle. |
| `POST /tts/magic/assemble-upload` | Multipart `options` (`items`, `output_format`, `normalize_loudness`), `take_metadata`, repeated `takes`. Items use `type="speech", id` or `type="break", milliseconds`. No model inference. |
| `GET/POST /tts/dialogue-scripts` | List/create saved scripts. Retrieve/update/delete through `/{id}`, download through `/{id}/download`. |
| `POST /tts/dialogue-workspaces` | Explicit-save multipart `metadata` and optional repeated `takes`, `output`, `processed` audio. Update with `PUT /tts/dialogue-workspaces/{id}`. |
| `POST/DELETE /tts/dialogue-script-folders[/{id}]` | Create/remove library folders. Removing a folder retains its scripts in Ungrouped. |

The bundle media type is `application/vnd.hangrylabs.magic-takes`. It contains
a four-byte little-endian JSON-manifest length, UTF-8 JSON manifest, then binary
audio payloads. Each take and the assembled output have bounded payload-relative
`offset` and `length`, plus media type and extension. It never embeds base64
audio in JSON. Bundle version is 1; the studio client decodes this contract.
Seed fields are compatibility metadata only: Kokoro does not promise seeded
regeneration or alter process-global RNG state. A locked take preserves the
actual audio, not a recipe to recreate it.

Take uploads must be non-empty mono PCM16 WAV at 24000 Hz. Limits are 64 files,
20 MB per file, 40 MB total and 300 seconds decoded audio. Workspace audio is
decoded from uploaded bytes only, with no URL fetch or network protocols.
Cross-origin browser writes to studio/library endpoints are blocked. These
local-first endpoints are not an authenticated public multi-tenant service.

## Persistence and Cancellation

Only clicking Save or calling a save endpoint persists user content. Scripts,
folders, generation settings and explicitly saved takes/output live beside
`settings.json` in `app/scripts`, inside `/app/persistent`. The existing
`kokorotts_data` volume retains them across image replacement. No volume is
required; without it, storage is local to the container and ephemeral.

Magic cancellation stops further model chunks after the active model call
returns and releases runtime leases. A generation or preview never saves a
workspace automatically. Request-wide controls invalidate existing takes in
the UI; changing just one turn invalidates that turn. Normalization is not baked
into individual takes, so assembly does not normalize them twice.
