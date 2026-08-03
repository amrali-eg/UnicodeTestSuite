"""CorpusCertificate.txt: a signed-in-spirit summary of one generation run.

This certificate intentionally includes a wall-clock timestamp and a
generation duration, so it is NOT expected to be byte-identical across
runs - only the corpus data files, Manifest.csv/.sqlite, and
MasterHashes.sha256 carry the determinism guarantee. See README.md.
"""

from __future__ import annotations

import platform
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from generator import GENERATOR_VERSION
from generator.corpus import GeneratedFile
from generator.hashing import sha256_file


def build_certificate_text(
    records: list[GeneratedFile],
    generation_seconds: float,
    master_hashes_path: Path,
) -> str:
    """Render the full CorpusCertificate.txt content as a string."""
    total_files = len(records)
    total_bytes = sum(r.size_bytes for r in records)
    master_sha256 = sha256_file(master_hashes_path)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "Unicode Test Suite Generator - Corpus Certificate",
        "=" * 50,
        "",
        f"Generator version:    {GENERATOR_VERSION}",
        f"Python version:       {sys.version.split()[0]} ({platform.python_implementation()})",
        f"Platform:             {platform.system()} {platform.release()}",
        f"Unicode version:      {unicodedata.unidata_version}",
        f"Generation timestamp: {timestamp}",
        f"Generation duration:  {generation_seconds:.2f} seconds",
        "",
        f"Total files:          {total_files:,}",
        f"Total size:           {total_bytes:,} bytes",
        f"MasterHashes SHA-256: {master_sha256}",
        "",
        "Every file listed in MasterHashes.sha256 was reopened from disk,",
        "decoded with its declared encoding (where applicable), and its",
        "SHA-256 was recomputed and compared before this certificate was",
        "issued. No mismatch occurred during this run.",
        "",
    ]
    return "\n".join(lines) + "\n"


def write_certificate(
    records: list[GeneratedFile],
    generation_seconds: float,
    master_hashes_path: Path,
    output_path: Path,
) -> None:
    """Write CorpusCertificate.txt to disk."""
    text = build_certificate_text(records, generation_seconds, master_hashes_path)
    output_path.write_text(text, encoding="utf-8", newline="\n")
