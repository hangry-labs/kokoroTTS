---
layout: default
title: Examples guide
permalink: /examples/guide/
---
# KokoroTTS examples

[Listen to the voice gallery](https://hangry-labs.github.io/kokoroTTS/examples/)
or [open the SSML dialogue showcase](https://hangry-labs.github.io/kokoroTTS/examples/ssml.html).

## Voice gallery

The gallery contains 173 MP3 recordings across 11 language groups. Choose a
language to filter speakers and translate the gallery text. Select a card or
press Enter or Space to play, seek within the waveform, or adjust the shared
volume control. `voices.js` contains the voice IDs, sample text and file names;
`player.js` supplies the existing playback and language controls.

## Dialogue showcase

The SSML page includes five multi-voice recordings and their exact scripts,
including a mixed-language conversation. Native audio controls handle playback;
copy buttons copy the SSML or API request for use in KokoroTTS. SSML is an
explicit, experimental native API and Studio mode; plain text remains the default.

## Preview and files

Run `task pages` from the repository root to preview the complete website,
including the README, translated documentation entry points and both galleries.
`task pages-build` builds without starting a server; `task pages-test` checks
public-file staging and language routing without loading speech models.

`index.md` and `ssml.md` integrate the corresponding standalone HTML files into
the shared website. The MP3 files and player scripts are shared by both views.
The standalone files use local CSS and JavaScript and can also be opened directly
from a downloaded checkout. For clipboard support, serve the checkout locally:

```powershell
python -m http.server 9000
```

Then open <http://localhost:9000/examples/index.html> or
<http://localhost:9000/examples/ssml.html>.
