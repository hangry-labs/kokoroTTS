#!/usr/bin/env python3
"""Verify the source and license bundle shipped in a KokoroTTS image."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import tarfile
from importlib.metadata import version
from pathlib import Path


EXPECTED_PACKAGES = {
    "espeakng-loader": "0.2.4",
    "phonemizer-fork": "3.3.2",
    "num2words": "0.5.14",
}

EXPECTED_DEBIAN_PACKAGES = (
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

EXPECTED_ARCHIVES = {
    "sources/phonemizer_fork-3.3.2.tar.gz": "phonemizer_fork-3.3.2/",
    "sources/num2words-0.5.14.tar.gz": "num2words-0.5.14/",
    "sources/espeakng-loader-0.2.4-146599e29be3.tar.gz": (
        "espeakng-loader-146599e29be31bf17d99f0bcb7dbb2f92aef3d95/"
    ),
    "sources/espeak-ng-1.52.0-4870adfa25b1.tar.gz": (
        "espeak-ng-4870adfa25b1a32b4361592f1be8a40337c58d6c/"
    ),
}

REQUIRED_FILES = {
    "README.md",
    "SOURCE_MANIFEST.md",
    "PYTHON_PACKAGES.md",
    "SHA256SUMS",
    "licenses/espeakng-loader/MIT.txt",
    "licenses/espeak-ng/COPYING",
    "licenses/espeak-ng/COPYING.UCD",
    "licenses/phonemizer-fork/GPL-3.0-or-later.txt",
    "licenses/num2words/LGPL-2.1.txt",
    "licenses/debian/espeak-ng-copyright",
    "licenses/debian/ffmpeg-copyright",
    "licenses/debian/GPL-3",
    "licenses/debian/GPL-2",
    "build/Dockerfile",
    "build/requirements.txt",
    "build/requirements.in",
    "build/pyproject.toml",
    "build/install_compliance_sources.py",
}


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            checksum.update(chunk)
    return checksum.hexdigest()


def verify_checksums(root: Path) -> int:
    count = 0
    for line in (root / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        expected, relative = line.split("  ", 1)
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f"checksummed file is missing: {relative}")
        actual = digest(path)
        if actual != expected:
            raise RuntimeError(
                f"checksum mismatch for {relative}: expected {expected}, got {actual}"
            )
        count += 1
    return count


def verify_debian_inventory(manifest: str) -> int:
    result = subprocess.run(
        [
            "dpkg-query",
            "-W",
            "-f=${binary:Package}\\t${Version}\\n",
            *EXPECTED_DEBIAN_PACKAGES,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    count = 0
    for line in result.stdout.splitlines():
        package, installed_version = line.split("\t")
        record = f"| `{package}` | `{installed_version}` |"
        if record not in manifest:
            raise RuntimeError(
                f"Debian inventory mismatch: {package} {installed_version} "
                "is not recorded in SOURCE_MANIFEST.md"
            )
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default="/app/third_party")
    args = parser.parse_args()
    root = args.root.resolve()

    missing = sorted(relative for relative in REQUIRED_FILES if not (root / relative).is_file())
    if missing:
        raise RuntimeError(f"compliance bundle is missing: {', '.join(missing)}")

    checksummed = verify_checksums(root)
    for relative, prefix in EXPECTED_ARCHIVES.items():
        with tarfile.open(root / relative, "r:gz") as archive:
            names = archive.getnames()
        if not names or not all(name == prefix.rstrip("/") or name.startswith(prefix) for name in names):
            raise RuntimeError(f"unexpected source archive layout: {relative}")

    for package, expected in EXPECTED_PACKAGES.items():
        actual = version(package)
        if actual != expected:
            raise RuntimeError(f"{package} version mismatch: expected {expected}, got {actual}")

    manifest = (root / "SOURCE_MANIFEST.md").read_text(encoding="utf-8")
    for required in ("espeak-ng", "ffmpeg", "sources.debian.org"):
        if required not in manifest:
            raise RuntimeError(f"source manifest does not mention {required}")
    debian_packages = verify_debian_inventory(manifest)

    inventory = (root / "PYTHON_PACKAGES.md").read_text(encoding="utf-8")
    for required in ("phonemizer-fork", "num2words", "espeakng-loader", "nvidia-cublas"):
        if required not in inventory:
            raise RuntimeError(f"Python license inventory does not mention {required}")

    print(
        f"Compliance bundle verified: {checksummed} checksums, "
        f"{len(EXPECTED_ARCHIVES)} source archives, "
        f"{len(EXPECTED_PACKAGES)} pinned Python packages, "
        f"{debian_packages} runtime Debian packages."
    )


if __name__ == "__main__":
    main()
