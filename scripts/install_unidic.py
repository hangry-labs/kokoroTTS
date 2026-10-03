#!/usr/bin/env python3
"""Install pinned UniDic from a verified local archive or explicit URL."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

import unidic


def verify(archive: Path, expected_sha256: str) -> None:
    digest = hashlib.sha256()
    with archive.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    actual_sha256 = digest.hexdigest()
    if actual_sha256 != expected_sha256:
        raise RuntimeError(
            f"UniDic checksum mismatch: expected {expected_sha256}, got {actual_sha256}"
        )


def download(url: str, destination: Path, expected_sha256: str) -> None:
    partial = destination.with_suffix(destination.suffix + ".part")
    partial.unlink(missing_ok=True)

    for attempt in range(1, 4):
        digest = hashlib.sha256()
        downloaded = 0
        started = time.monotonic()
        try:
            with urllib.request.urlopen(url, timeout=60) as response, partial.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
                    downloaded += len(chunk)
        except Exception:
            partial.unlink(missing_ok=True)
            if attempt == 3:
                raise
            print(f"UniDic download attempt {attempt} failed; retrying...", file=sys.stderr)
            time.sleep(attempt * 2)
            continue

        actual_sha256 = digest.hexdigest()
        if actual_sha256 != expected_sha256:
            partial.unlink(missing_ok=True)
            raise RuntimeError(
                f"UniDic checksum mismatch: expected {expected_sha256}, got {actual_sha256}"
            )
        partial.replace(destination)
        elapsed = max(time.monotonic() - started, 0.001)
        print(
            f"Downloaded {downloaded / 1024 / 1024:.1f} MiB in {elapsed:.1f}s "
            f"({downloaded / 1024 / 1024 / elapsed:.1f} MiB/s)",
            file=sys.stderr,
        )
        return


def install(archive: Path, version: str) -> None:
    package_dir = Path(unidic.__file__).resolve().parent
    dictionary_dir = package_dir / "dicdir"

    with tempfile.TemporaryDirectory(prefix="unidic-install-", dir=package_dir) as temp_name:
        extraction_dir = Path(temp_name)
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(extraction_dir)

        extracted_dictionary = extraction_dir / "unidic"
        if not extracted_dictionary.is_dir():
            raise RuntimeError("UniDic archive does not contain the expected unidic/ directory")

        if dictionary_dir.exists():
            shutil.rmtree(dictionary_dir)
        shutil.move(str(extracted_dictionary), dictionary_dir)

    (dictionary_dir / "version").write_text(f"unidic-{version}", encoding="utf-8")
    (dictionary_dir / "mecabrc").write_text("# This is a dummy file.", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()

    expected_sha256 = args.sha256.lower()
    if args.archive and args.archive.is_file():
        verify(args.archive, expected_sha256)
        print(f"Using cached UniDic archive {args.archive}", file=sys.stderr)
        install(args.archive, args.version)
        print(f"Installed UniDic {args.version} in {unidic.DICDIR}", file=sys.stderr)
        return

    package_dir = Path(unidic.__file__).resolve().parent
    archive = package_dir / "unidic.zip"
    try:
        download(args.url, archive, expected_sha256)
        install(archive, args.version)
    finally:
        archive.unlink(missing_ok=True)

    print(f"Installed UniDic {args.version} in {unidic.DICDIR}", file=sys.stderr)


if __name__ == "__main__":
    main()
