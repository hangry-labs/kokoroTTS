# Third-Party Notices

KokoroTTS includes, adapts, downloads, or depends on third-party software and
model assets. Each component remains subject to its own license. This file is
informational and does not replace or modify those licenses.

The complete Apache License 2.0 text for this project and the Apache-licensed
components below is available in [`LICENSE`](LICENSE).

## Kokoro Runtime and Language Processing

### Kokoro

- Project: [hexgrad/kokoro](https://github.com/hexgrad/kokoro)
- Copyright: the Kokoro authors and contributors
- License: Apache License 2.0
- Use here: Kokoro model and inference implementation on which this fork is
  based. Hangry Labs has modified and extended the original implementation for
  Docker deployment, its standalone UI, APIs, additional languages, audio
  formats, runtime management, and related tooling.

### Misaki

- Project: [hexgrad/misaki](https://github.com/hexgrad/misaki)
- Copyright: the Misaki authors and contributors
- License: Apache License 2.0
- Use here: grapheme-to-phoneme processing and language support.

### defusedxml

- Project: [tiran/defusedxml](https://github.com/tiran/defusedxml)
- Copyright: Christian Heimes and contributors
- License: Python Software Foundation License Version 2
- Use here: hardened parsing for explicitly selected experimental SSML input,
  including rejection of DTD and entity-based XML attacks.

### Kokoro Vietnamese Integration

- Project: [iamdinhthuan/Kokoro-Vietnamese](https://github.com/iamdinhthuan/Kokoro-Vietnamese)
- Author: iamdinhthuan
- License: Apache License 2.0
- Use here: reference implementation and behavior for Vietnamese Kokoro
  inference.

### sea-g2p

- Project: [pnnbao97/sea-g2p](https://github.com/pnnbao97/sea-g2p)
- Copyright: Pham Nguyen Ngoc Bao and contributors
- License: Apache License 2.0
- Use here: Vietnamese text-to-phoneme conversion used through `vig2p`.

### vig2p

- Package: [vig2p on PyPI](https://pypi.org/project/vig2p/)
- PyPI owner: `DinhThuan` (`iamdinthhuan` on the PyPI profile)
- Version currently used: 0.1.2
- Use here: Kokoro-compatible Vietnamese phoneme adaptation around `sea-g2p`.

The `vig2p` package is maintained by the same identified maintainer who
authored the Apache-2.0 Kokoro-Vietnamese project, and that project explicitly
depends on `vig2p`. At the time this notice was reviewed, however, the
standalone PyPI package metadata and wheel did not declare or include a
license. KokoroTTS does not infer or assign a license to that separately
distributed package. On 2026-10-04, the KokoroTTS maintainers requested
explicit license metadata, a bundled license file, and a source-project link in
[Kokoro-Vietnamese issue #5](https://github.com/iamdinhthuan/Kokoro-Vietnamese/issues/5).
Upstream confirmation remains pending.

## Model and Voice Assets

The full Docker image prefetched these assets for offline inference. The tiny
image downloads an enabled model family on demand. The same licenses apply in
either distribution mode.

| Component | Source | License |
| --- | --- | --- |
| Kokoro-82M model and standard voices | [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) | Apache License 2.0 |
| Kikiri German Martin model and voice | [kikiri-tts/kikiri-german-martin](https://huggingface.co/kikiri-tts/kikiri-german-martin) | Apache License 2.0 |
| Kikiri German Victoria model and voice | [kikiri-tts/kikiri-german-victoria](https://huggingface.co/kikiri-tts/kikiri-german-victoria) | Apache License 2.0 |
| Kokoro Vietnamese model, configuration, and voices | [contextboxai/Kokoro-Vietnamese](https://huggingface.co/contextboxai/Kokoro-Vietnamese) | Apache License 2.0 |

## Browser Libraries

### WaveSurfer.js

- Project: [katspaugh/wavesurfer.js](https://github.com/katspaugh/wavesurfer.js)
- Copyright: 2012-2023 katspaugh and contributors
- License: BSD 3-Clause
- Bundled license: [`kokorotts/standalone_ui/static/vendor/wavesurfer/LICENSE`](kokorotts/standalone_ui/static/vendor/wavesurfer/LICENSE)

### Lucide and Feather Icons

- Project: [lucide-icons/lucide](https://github.com/lucide-icons/lucide)
- Copyright: Lucide Icons and contributors
- License: ISC
- Some Lucide icons are derived from Feather Icons, copyright Cole Bemis,
  under the MIT License.
- Bundled licenses: [`kokorotts/standalone_ui/static/vendor/lucide/LICENSE`](kokorotts/standalone_ui/static/vendor/lucide/LICENSE)

## Docker Runtime Components

The published Docker images also contain operating-system packages and
language data installed during the build:

- **eSpeak NG:** primarily GNU General Public License v3 or later, with
  additional notices for specific files. The Debian package preserves its
  detailed copyright and license record at
  `/usr/share/doc/espeak-ng/copyright` and the GPL text under
  `/usr/share/common-licenses/GPL-3`.
- **FFmpeg:** the default Debian binaries are distributed under GNU General
  Public License v2 or later, with individual components under compatible
  licenses. The installed package preserves its complete record at
  `/usr/share/doc/ffmpeg/copyright` and the corresponding license texts under
  `/usr/share/common-licenses/`.
- **Open JTalk Dictionary 1.11:** includes work copyright Nara Institute of
  Science and Technology, the UniDic Consortium, and Nagoya Institute of
  Technology, distributed under three-clause BSD-style terms. The complete
  combined notice is retained at
  `pyopenjtalk/open_jtalk_dic_utf_8-1.11/COPYING` inside the Python runtime.

Python packages installed into the image retain the metadata and license files
supplied by their distributions. Transitive packages remain governed by their
respective upstream terms.
