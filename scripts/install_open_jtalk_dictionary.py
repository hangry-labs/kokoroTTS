#!/usr/bin/env python3
"""Install the pinned Open JTalk dictionary with integrity verification."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

import pyopenjtalk


def verify(archive: Path, expected_sha256: str) -> None:
    digest = hashlib.sha256()
    with archive.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    actual_sha256 = digest.hexdigest()
    if actual_sha256 != expected_sha256:
        raise RuntimeError(
            f"Open JTalk dictionary checksum mismatch: expected {expected_sha256}, "
            f"got {actual_sha256}"
        )


def download(url: str, destination: Path, expected_sha256: str) -> None:
    for attempt in range(1, 4):
        started = time.monotonic()
        try:
            with (
                urllib.request.urlopen(url, timeout=60) as response,
                destination.open("wb") as output,
            ):
                shutil.copyfileobj(response, output)
            verify(destination, expected_sha256)
        except Exception:
            destination.unlink(missing_ok=True)
            if attempt == 3:
                raise
            print(
                f"Open JTalk dictionary download attempt {attempt} failed; retrying...",
                file=sys.stderr,
            )
            time.sleep(attempt * 2)
            continue

        elapsed = max(time.monotonic() - started, 0.001)
        size_mib = destination.stat().st_size / 1024 / 1024
        print(
            f"Downloaded {size_mib:.1f} MiB in {elapsed:.1f}s "
            f"({size_mib / elapsed:.1f} MiB/s)",
            file=sys.stderr,
        )
        return


def install(archive: Path, version: str) -> Path:
    package_dir = Path(pyopenjtalk.__file__).resolve().parent
    directory_name = f"open_jtalk_dic_utf_8-{version}"
    destination = package_dir / directory_name

    with tempfile.TemporaryDirectory(
        prefix="open-jtalk-install-", dir=package_dir
    ) as temp_name:
        extraction_dir = Path(temp_name)
        with tarfile.open(archive, mode="r:gz") as compressed:
            members = compressed.getmembers()
            if not members or any(
                member.name.split("/", 1)[0] != directory_name
                or member.issym()
                or member.islnk()
                for member in members
            ):
                raise RuntimeError("Open JTalk archive has an unexpected layout")
            compressed.extractall(extraction_dir, filter="data")

        extracted = extraction_dir / directory_name
        required_files = {"char.bin", "matrix.bin", "sys.dic", "unk.dic", "COPYING"}
        missing = sorted(
            name for name in required_files if not (extracted / name).is_file()
        )
        if missing:
            raise RuntimeError(f"Open JTalk dictionary is missing: {', '.join(missing)}")

        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(extracted), destination)

    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="open-jtalk-download-") as temp_name:
        archive = Path(temp_name) / "dictionary.tar.gz"
        download(args.url, archive, args.sha256.lower())
        destination = install(archive, args.version)

    print(
        f"Installed Open JTalk {args.version} dictionary in {destination}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
