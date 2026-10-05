#!/usr/bin/env python3
"""Install license material and corresponding-source archives into an image."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from importlib.metadata import distribution, distributions
from pathlib import Path


@dataclass(frozen=True)
class Download:
    path: str
    url: str
    sha256: str
    size: int
    component: str


DOWNLOADS = (
    Download(
        path="sources/phonemizer_fork-3.3.2.tar.gz",
        url=(
            "https://files.pythonhosted.org/packages/42/fa/"
            "9294d2f11890ca49d0bdac7a4da60cbe5686629bfd4987cae0ad75e051cc/"
            "phonemizer_fork-3.3.2.tar.gz"
        ),
        sha256="10e16e827d0443b087062e21b55e805c00989cf1343b2e81e734cae5f6c0cf69",
        size=300_989,
        component="phonemizer-fork 3.3.2 (GPL-3.0-or-later)",
    ),
    Download(
        path="sources/num2words-0.5.14.tar.gz",
        url=(
            "https://files.pythonhosted.org/packages/f6/58/"
            "ad645bd38b4b648eb2fc2ba1b909398e54eb0cbb6a7dbd2b4953e38c9621/"
            "num2words-0.5.14.tar.gz"
        ),
        sha256="b066ec18e56b6616a3b38086b5747daafbaa8868b226a36127e0451c0cf379c6",
        size=218_213,
        component="num2words 0.5.14 (LGPL-2.1)",
    ),
    Download(
        path="sources/espeakng-loader-0.2.4-146599e29be3.tar.gz",
        url=(
            "https://codeload.github.com/thewh1teagle/espeakng-loader/tar.gz/"
            "146599e29be31bf17d99f0bcb7dbb2f92aef3d95"
        ),
        sha256="d6496114cd0608988f5291f54d2d15b50cb37b7f007af00bb62cf93be1b3ceca",
        size=3_935,
        component="espeakng-loader 0.2.4 source and build scripts (MIT)",
    ),
    Download(
        path="sources/espeak-ng-1.52.0-4870adfa25b1.tar.gz",
        url=(
            "https://codeload.github.com/espeak-ng/espeak-ng/tar.gz/"
            "4870adfa25b1a32b4361592f1be8a40337c58d6c"
        ),
        sha256="cd83f84c4e495f281ac14e919aecf2834306ec1ea1b498de8ef6000f3a0f90de",
        size=17_747_711,
        component="eSpeak NG 1.52.0 corresponding source (GPL-3.0-or-later)",
    ),
    Download(
        path="licenses/espeakng-loader/MIT.txt",
        url=(
            "https://raw.githubusercontent.com/thewh1teagle/espeakng-loader/"
            "0ddc87adf77e5850d7eeb542ac8a87d421b64daa/LICENSE"
        ),
        sha256="b05c73bb1335b4320ec97edff106b3991c12d0acdc6e899c96f061a15039119f",
        size=1_069,
        component="espeakng-loader MIT license",
    ),
    Download(
        path="licenses/espeak-ng/COPYING",
        url=(
            "https://raw.githubusercontent.com/espeak-ng/espeak-ng/"
            "4870adfa25b1a32b4361592f1be8a40337c58d6c/COPYING"
        ),
        sha256="8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903",
        size=35_147,
        component="eSpeak NG GPL-3.0 license",
    ),
    Download(
        path="licenses/espeak-ng/COPYING.UCD",
        url=(
            "https://raw.githubusercontent.com/espeak-ng/espeak-ng/"
            "4870adfa25b1a32b4361592f1be8a40337c58d6c/COPYING.UCD"
        ),
        sha256="be029c50df83105a810e391778b6edcb522d6cb4b4e142332aca54437a499bf7",
        size=2_788,
        component="eSpeak NG Unicode data notice",
    ),
)

DEBIAN_PACKAGES = (
    "espeak-ng",
    "espeak-ng-data",
    "libespeak-ng1",
    "ffmpeg",
    "libavcodec61",
    "libavdevice61",
    "libavfilter10",
    "libavformat61",
    "libavutil59",
    "libpostproc58",
    "libswresample5",
    "libswscale8",
)


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            checksum.update(chunk)
    return checksum.hexdigest()


def download(item: Download, output: Path) -> None:
    destination = output / item.path
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        item.url, headers={"User-Agent": "HangryLabs-KokoroTTS-license-bundle"}
    )

    for attempt in range(1, 4):
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.unlink(missing_ok=True)
        try:
            with (
                urllib.request.urlopen(request, timeout=120) as response,
                temporary.open("wb") as target,
            ):
                shutil.copyfileobj(response, target)
            actual_size = temporary.stat().st_size
            actual_digest = digest(temporary)
            if actual_size != item.size or actual_digest != item.sha256:
                raise RuntimeError(
                    f"integrity mismatch for {item.path}: expected "
                    f"{item.size}/{item.sha256}, got {actual_size}/{actual_digest}"
                )
            temporary.replace(destination)
            print(f"Installed {item.component}: {item.path}", file=sys.stderr)
            return
        except Exception:
            temporary.unlink(missing_ok=True)
            if attempt == 3:
                raise
            time.sleep(attempt * 2)


def copy_distribution_license(
    package: str, suffix: str, destination: Path
) -> None:
    package_distribution = distribution(package)
    matches = [
        entry
        for entry in package_distribution.files or ()
        if str(entry).replace("\\", "/").endswith(suffix)
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one {suffix!r} license in {package}, found {len(matches)}"
        )
    source = Path(package_distribution.locate_file(matches[0]))
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise RuntimeError(f"required compliance file is missing: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def debian_inventory() -> list[tuple[str, str, str, str]]:
    result = subprocess.run(
        [
            "dpkg-query",
            "-W",
            "-f=${binary:Package}\\t${Version}\\t${source:Package}\\t${source:Version}\\n",
            *DEBIAN_PACKAGES,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    inventory = []
    for line in result.stdout.splitlines():
        binary, version, source, source_version = line.split("\t")
        inventory.append(
            (
                binary,
                version,
                source or binary.split(":", 1)[0],
                source_version or version,
            )
        )
    return inventory


def write_manifest(output: Path, inventory: list[tuple[str, str, str, str]]) -> None:
    lines = [
        "# Corresponding Source Manifest",
        "",
        "This directory accompanies the KokoroTTS Docker server distribution.",
        "It records and carries source and license material for copyleft runtime",
        "components. It does not change the licenses of those components.",
        "",
        "## Source Included in the Image",
        "",
        "| Component | Archive | SHA-256 | Upstream |",
        "| --- | --- | --- | --- |",
    ]
    for item in DOWNLOADS:
        if not item.path.startswith("sources/"):
            continue
        lines.append(
            f"| {item.component} | `{item.path}` | `{item.sha256}` | "
            f"[source]({item.url}) |"
        )

    lines.extend(
        [
            "",
            "The eSpeak NG archive is the exact commit behind tag `1.52.0`.",
            "The loader archive is the commit that published version `0.2.4` and",
            "contains `build.sh` plus its GitHub build workflow. The complete",
            "KokoroTTS Python source is installed at `/app/kokorotts`; reproducible",
            "build inputs are retained under `/app/third_party/build`, and the OCI",
            "revision label identifies the corresponding public repository commit.",
            "",
            "## Debian Runtime Packages",
            "",
            "| Binary package | Installed version | Source package | Exact source |",
            "| --- | --- | --- | --- |",
        ]
    )
    seen_sources: set[tuple[str, str]] = set()
    for binary, version, source, source_version in inventory:
        key = (source, source_version)
        encoded_version = urllib.parse.quote(source_version, safe="")
        url = f"https://sources.debian.org/src/{source}/{encoded_version}/"
        label = "[Debian source]" if key not in seen_sources else "same source"
        link = f"{label}({url})" if label.startswith("[") else label
        lines.append(
            f"| `{binary}` | `{version}` | `{source}` `{source_version}` | {link} |"
        )
        seen_sources.add(key)

    lines.extend(
        [
            "",
            "Debian copyright records and common GPL texts are copied into",
            "`licenses/debian`. The exact Debian source pages above remain the",
            "network source offer for those unmodified operating-system packages.",
            "",
            "## Verification",
            "",
            "Run `/app/third_party/build/verify_compliance_bundle.py` inside the",
            "image. `SHA256SUMS` covers every bundled source archive and license",
            "file. This manifest is factual provenance, not legal advice.",
            "",
        ]
    )
    (output / "SOURCE_MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")


def table_cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")


def write_python_inventory(output: Path) -> None:
    lines = [
        "# Installed Python Package License Inventory",
        "",
        "Generated from the metadata installed in this Docker image. `UNKNOWN`",
        "means the distribution did not declare useful license metadata; consult",
        "`THIRD_PARTY_NOTICES.md` and the bundled files before drawing conclusions.",
        "",
        "| Package | Version | Declared license | Project |",
        "| --- | --- | --- | --- |",
    ]
    package_rows = []
    for package_distribution in distributions():
        metadata = package_distribution.metadata
        name = metadata.get("Name", "UNKNOWN")
        expression = metadata.get("License-Expression")
        classifiers = [
            value.removeprefix("License :: ")
            for value in metadata.get_all("Classifier", [])
            if value.startswith("License :: ")
        ]
        declared = expression or "; ".join(classifiers)
        if not declared:
            raw_license = metadata.get("License", "").strip()
            declared = raw_license if len(raw_license) <= 160 else raw_license.splitlines()[0]
        declared = declared or "UNKNOWN"

        project_url = metadata.get("Home-page", "").strip()
        if not project_url:
            for entry in metadata.get_all("Project-URL", []):
                _, separator, candidate = entry.partition(",")
                if separator and candidate.strip().startswith(("http://", "https://")):
                    project_url = candidate.strip()
                    break
        project = f"[upstream]({project_url})" if project_url else "UNKNOWN"
        package_rows.append(
            (
                name.casefold(),
                f"| `{table_cell(name)}` | `{package_distribution.version}` | "
                f"{table_cell(declared)} | {project} |",
            )
        )
    lines.extend(row for _, row in sorted(package_rows))
    lines.append("")
    (output / "PYTHON_PACKAGES.md").write_text("\n".join(lines), encoding="utf-8")


def write_checksums(output: Path) -> None:
    files = sorted(
        path
        for directory in (output / "sources", output / "licenses")
        for path in directory.rglob("*")
        if path.is_file()
    )
    lines = [f"{digest(path)}  {path.relative_to(output).as_posix()}" for path in files]
    (output / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    for item in DOWNLOADS:
        download(item, output)

    copy_distribution_license(
        "phonemizer-fork",
        "phonemizer_fork-3.3.2.dist-info/licenses/LICENSE",
        output / "licenses/phonemizer-fork/GPL-3.0-or-later.txt",
    )
    copy_distribution_license(
        "num2words",
        "num2words-0.5.14.dist-info/COPYING",
        output / "licenses/num2words/LGPL-2.1.txt",
    )
    copy_file(
        Path("/usr/share/doc/espeak-ng/copyright"),
        output / "licenses/debian/espeak-ng-copyright",
    )
    copy_file(
        Path("/usr/share/doc/ffmpeg/copyright"),
        output / "licenses/debian/ffmpeg-copyright",
    )
    copy_file(
        Path("/usr/share/common-licenses/GPL-3"),
        output / "licenses/debian/GPL-3",
    )
    copy_file(
        Path("/usr/share/common-licenses/GPL-2"),
        output / "licenses/debian/GPL-2",
    )

    inventory = debian_inventory()
    write_manifest(output, inventory)
    write_python_inventory(output)
    write_checksums(output)


if __name__ == "__main__":
    main()
