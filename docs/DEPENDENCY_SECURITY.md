# Dependency Security Review

Reviewed on 2026-10-28 against 26 open Dependabot alerts across seven packages.
Several alerts describe the same advisory in both Python lockfiles. Decisions
below apply to the maintained Docker UI/API product, not arbitrary uses of the
underlying libraries. This is not a claim that the distribution is vulnerability-free.

## Targeted Fixes

| Package | Change | Purpose |
| --- | --- | --- |
| Certifi | 2026.7.22 to **2026.10.18** | Removes compromised emSign certificate authorities. Relevant to HTTPS downloads, especially tiny-image startup. [Advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2). |
| Filelock | 4.0.9 to **4.2.1** in Docker; 4.0.12 to 4.2.1 in `uv.lock` | Fixes SQLite-backed read/write lock file attacks and two Windows lock issues. Hugging Face uses file locking; keep that integration tested. [Read/write lock advisory](https://github.com/tox-dev/filelock/security/advisories/GHSA-v4x8-3wr5-3wq8), [Windows SQLite](https://github.com/tox-dev/filelock/security/advisories/GHSA-9vhv-jxww-xfm5), [Windows soft lock](https://github.com/tox-dev/filelock/security/advisories/GHSA-567q-5qvw-pf92). |
| OpenTelemetry API | 1.45.0 to **1.45.1** in Docker | Bounds hostile `tracestate` parsing. It is a transitive MCP dependency; `uv.lock` already contained the fixed release. [Advisory](https://github.com/open-telemetry/opentelemetry-python/security/advisories/GHSA-xcq7-p3pf-p88h). |
| Rubyzip | Removed from the local website builder | Replaced the broad `github-pages` metapackage with the same Jekyll 3.10 and six rendering-plugin versions actually used here. This removes the unused remote-theme ZIP downloader rather than forcing incompatible Rubyzip 3 into a `<3` dependency. The local theme and safe mode are unchanged. [Advisory](https://github.com/advisories/GHSA-47m2-wp7j-p9vc). |

The three Python fixes are pinned in `requirements.in`, the optional `server`
extra, `requirements.txt`, and `uv.lock`. The default HTTP-client installation
remains dependency-free. No inference kernels, models, language frontends, CUDA
libraries, or synthesis defaults were changed. The website bundle controls the
local preview build, not GitHub's separately maintained branch-based Pages service.

## Retained Model-Stack Dependencies

These dependencies still match advisory version ranges. Their alerts are not
suppressed, and the packages must not be described as patched. Revisit when a
compatible upgrade can be qualified on the full language/model/API matrix.

| Dependency / advisory | Current product exposure and decision |
| --- | --- |
| Setuptools 79.0.1: [macOS manifest normalization](https://github.com/pypa/setuptools/security/advisories/GHSA-h35f-9h28-mq5c), [Windows legacy wheel installation](https://github.com/pypa/setuptools/security/advisories/GHSA-xmj3-9gf7-h52w) | Fixes require 83.0.0/84.1.0, but Torch 2.11 declares `setuptools<82`. Do not override that requirement. Docker runs on Linux, project packaging uses Hatchling, and API/MCP requests do not install wheels or build source distributions. This does not cover arbitrary package installation by an operator. |
| Torch 2.11.0: [`torch.jit.script` memory corruption](https://github.com/advisories/GHSA-rrmf-rvhw-rf47) | Fixed in 2.13.0. Product inference uses eager PyTorch and does not expose scripting attacker-supplied Python. Retain the qualified CUDA stack rather than upgrading it for an unused scripting path. |
| Transformers 4.57.6: [`Trainer` RNG loading](https://github.com/advisories/GHSA-69w3-r845-3855) | No training or `Trainer` checkpoint restoration in the product. The advisory also describes older Torch behavior; this is not a reason to advertise all of Transformers as safe. |
| Transformers 4.57.6: [automatic attention-kernel loading](https://github.com/advisories/GHSA-29pf-2h5f-8g72) | The server constructs ALBERT from product-owned configuration and catalog-selected assets, not user-selected `AutoModelForCausalLM` repositories/configurations. Arbitrary model/configuration imports are not a supported endpoint. |
| Transformers 4.57.6: [LightGlue model loading](https://github.com/advisories/GHSA-fgcw-684q-jj6r) | No LightGlue model or automatic nested configuration loading in product inference. |
| Transformers 4.57.6: [custom generation code download](https://github.com/advisories/GHSA-x9r9-c232-4q39) | No custom-generation repository input in the product. Normal English uses the packaged eSpeak fallback, not Misaki's optional neural generation fallback. The advisory lists no patched release in the reviewed feed. |
| Transformers 4.57.6: [chat-template save traversal](https://github.com/advisories/GHSA-xrqw-3rrv-vx5w) | No chat templates, tokenizer export, or `save_pretrained` route. Keep the qualified ALBERT dependency until a model-facing upgrade is separately justified and tested. |

## Operating Boundary

Use only trusted catalog model assets and trusted package sources. Do not load
community checkpoints, custom repositories, Python scripts, or model configuration
files into the serving process. Existing checkpoints and voice tensors are loaded
with `weights_only=True`; that does not make every possible untrusted tensor file safe.

Full images support offline inference. Tiny images need HTTPS access for initial
asset downloads. Offline flags reduce network exposure but do not turn vulnerable
libraries into patched versions. Keep the native UI/API and optional MCP on a
trusted network, or put authentication/access controls in front of them; OpenAI
route authentication alone does not protect the native operator controls.

## Validation

Run the targeted pin guard, complete unit suite, native client, official OpenAI
client, Magic Studio checks, all-language synthesis, and dependency consistency
checks after rebuilding the image. Validate real Hugging Face downloads/locking
for tiny startup and network-disabled synthesis for the baked image. Use
`task deps-test` for the pin guard, and `task pages-test` and `task pages-build`
for the website dependency change.

The 2026-10-28 qualification passed both image builds, 178 unit/runtime/UI tests,
44 native client tests, four official OpenAI SDK tests, six live Magic Studio
tests, the live MCP linked-audio/package-eviction test, and all-language/model-family
checks. A no-volume, network-disabled baked container generated on CUDA for all
11 languages and five model families. Both images passed `pip check` and the
compliance verifier. Real concurrent Hugging Face HTTPS downloads passed with a
fresh temporary cache. The website built with the reduced bundle and passed its
staging, language-routing, and browser checks.

A paired short-text check warmed 13 voice cases and measured five rounds per
case. All 65 requests passed before and after, with identical audio durations.
Mean latency was 0.297 s before and 0.256 s after; no slowdown was observed. This
shared-machine check is not an official throughput baseline or evidence that
the security patches improve inference speed.

Lockfile edits do not update an already running container or a published image.
Dependabot alerts change only after the user publishes the reviewed source;
retained dependencies will continue to produce their advisory alerts.
