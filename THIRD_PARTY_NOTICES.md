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

### phonemizer-fork

- Project: [bootphon/phonemizer](https://github.com/bootphon/phonemizer)
- Package: [phonemizer-fork on PyPI](https://pypi.org/project/phonemizer-fork/)
- Version currently used: 3.3.2
- License: GNU General Public License v3 or later
- Use here: Python interface to eSpeak NG, reached through Misaki for the
  English out-of-dictionary fallback and for the eSpeak-backed German,
  Spanish, French, Hindi, Italian, and Portuguese frontends.

The installed wheel includes the GNU GPL v3 license text in its distribution
metadata.

These phonemization components are server-runtime dependencies. They are
installed by the Docker images and the `kokorotts[server]` extra; the default
dependency-free `kokorotts` HTTP client installation does not install them.

### espeakng-loader and bundled eSpeak NG

- Project: [thewh1teagle/espeakng-loader](https://github.com/thewh1teagle/espeakng-loader)
- Version currently used: 0.2.4
- Loader source license: MIT
- Bundled component: eSpeak NG 1.52.0 shared library and data
- Bundled component license: GNU General Public License v3 or later, with
  additional notices for Unicode data
- Use here: supplies the eSpeak NG library and data selected by Misaki's
  phonemizer integration.

The pinned Misaki runtime explicitly configures `phonemizer-fork` to use the
library and data paths returned by `espeakng-loader`. This bundled copy is
therefore an active runtime dependency, not an unused installation. Matching
eSpeak NG source and license material are available from the upstream
[eSpeak NG 1.52.0 source tree](https://github.com/espeak-ng/espeak-ng/tree/1.52.0),
including [`COPYING`](https://github.com/espeak-ng/espeak-ng/blob/1.52.0/COPYING)
and [`COPYING.UCD`](https://github.com/espeak-ng/espeak-ng/blob/1.52.0/COPYING.UCD).

At the time this notice was reviewed, the `espeakng-loader` 0.2.4 wheel did
not declare a license in its package metadata or include the relevant license
files. Upstream correction is being tracked in
[espeakng-loader pull request #9](https://github.com/thewh1teagle/espeakng-loader/pull/9).
This notice records the licenses and exact corresponding source independently
of that packaging omission.

### num2words

- Project: [savoirfairelinux/num2words](https://github.com/savoirfairelinux/num2words)
- Version currently used: 0.5.14
- License: GNU Lesser General Public License 2.1
- Use here: number-to-word conversion used transitively by language
  normalization.

The installed wheel includes its LGPL 2.1 text. The Docker compliance bundle
also contains the exact source distribution and a separate copy of that
license.

### defusedxml

- Project: [tiran/defusedxml](https://github.com/tiran/defusedxml)
- Copyright: Christian Heimes and contributors
- License: Python Software Foundation License Version 2
- Use here: hardened parsing for explicitly selected experimental SSML input,
  including rejection of DTD and entity-based XML attacks.

### Model Context Protocol Python SDK

- Project: [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)
- Version currently used: 2.3.0
- Copyright: the Model Context Protocol authors and contributors
- License: MIT
- Use here: opt-in Streamable HTTP MCP server and protocol types for local AI
  agent integration.

The installed distribution includes its MIT license text in package metadata.

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
| Kokoro v1.1 Chinese model, configuration, and 103 voices | [hexgrad/Kokoro-82M-v1.1-zh](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh) | Apache License 2.0 |

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

- **System eSpeak NG:** a separate Debian installation in addition to the
  library bundled by `espeakng-loader`; primarily GNU General Public License
  v3 or later, with additional notices for specific files. The Debian package
  preserves its detailed copyright and license record at
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

## Docker License and Source Bundle

Both full and tiny images include `/app/third_party` with:

- complete GPL, LGPL, MIT, Unicode-data, and Debian copyright notices for the
  components identified above;
- checksum-verified corresponding-source archives for `phonemizer-fork`
  3.3.2, `num2words` 0.5.14, `espeakng-loader` 0.2.4, and the exact eSpeak NG
  1.52.0 revision used to build the loader's bundled library;
- loader build scripts, KokoroTTS Docker/dependency build inputs, and a
  generated manifest recording the installed Debian binary/source versions;
  and
- `SHA256SUMS` plus an offline verifier.

`PYTHON_PACKAGES.md` records every installed Python distribution, version,
declared license, and upstream URL. It intentionally reports incomplete
metadata as `UNKNOWN` instead of guessing. NVIDIA CUDA runtime wheels used by
PyTorch retain the proprietary license files supplied in their package
metadata; use and redistribution of those components remain subject to their
respective NVIDIA terms.

The generated manifest provides exact Debian source locations for the
unmodified system eSpeak NG and FFmpeg packages. Run
`/app/third_party/build/verify_compliance_bundle.py` inside an image, or
`task compliance-test` after a local tiny-image build, to verify the bundle.

KokoroTTS-owned source remains under Apache License 2.0. The server runtime and
Docker images are mixed-license distributions and must also be used and
redistributed under the applicable third-party terms described here. The
default dependency-free `kokorotts` HTTP client does not install these server
runtime dependencies.
