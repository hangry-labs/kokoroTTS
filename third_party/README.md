# Docker Compliance Bundle

Published KokoroTTS Docker images contain `/app/third_party` so recipients can
inspect the licenses and corresponding source for copyleft runtime components
without relying only on package metadata or mutable external documentation.

The bundle contains:

- exact, checksum-verified source archives for `phonemizer-fork`, `num2words`,
  `espeakng-loader`, and the eSpeak NG library bundled by the loader;
- the GPL, LGPL, MIT, Unicode-data, and Debian copyright notices relevant to
  those artifacts;
- exact installed Debian package versions and immutable source directions for
  the system eSpeak NG and FFmpeg packages;
- a generated version/license inventory for every installed Python
  distribution, including entries whose upstream metadata remains incomplete;
- the Dockerfile, dependency locks, package manifest, and installer scripts
  used to construct the runtime; and
- `SHA256SUMS` plus a verifier retained inside the image.

Run the repository task after building either image:

```bash
task compliance-test
```

The project-owned KokoroTTS source remains under Apache License 2.0. The
server and Docker images are mixed-license distributions; consult
`THIRD_PARTY_NOTICES.md` for component-level details. These records are
factual provenance and are not legal advice.
