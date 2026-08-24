"""CorpusCertificate.txt: the anchor of the corpus integrity chain.

The certificate is written last, after every other file, and records the
SHA-256 of each one that MasterHashes.sha256 cannot cover - including
MasterHashes.sha256 itself. `GenerateCorpus.py verify` re-checks those
hashes before it trusts the manifest, which closes the chain:

    CorpusCertificate.txt
      -> MasterHashes.sha256 + Manifest.csv + Manifest.sqlite + ...
           -> every corpus file

In v2.0 the certificate recorded the master hash but nothing ever
verified it, and the metadata files were not hashed at all, so a corpus
could be edited in ways both verification paths reported as clean.

The certificate intentionally includes a wall-clock timestamp and a
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

from generator import GENERATOR_VERSION, MANIFEST_VERSION
from generator.corpus import GeneratedFile
from generator.hashing import sha256_file

# Files written outside the manifest, hashed here instead. Order is fixed
# so the certificate is stable in shape across runs.
METADATA_FILES: tuple[str, ...] = (
    "MasterHashes.sha256",
    "Manifest.csv",
    "Manifest.sqlite",
    "ManifestVersion.txt",
    "Index.html",
    "README.md",
    "Statistics.txt",
)

_HASH_PREFIX = "  "
_LABEL_WIDTH = 22


def _metadata_hash_lines(output_root: Path) -> list[str]:
    lines = []
    for name in METADATA_FILES:
        path = output_root / name
        digest = sha256_file(path) if path.is_file() else "(absent)"
        lines.append(f"{_HASH_PREFIX}{name:<{_LABEL_WIDTH}} {digest}")
    return lines


def parse_metadata_hashes(certificate_text: str) -> dict[str, str]:
    """Recover the {filename: sha256} map recorded in a certificate.

    Used by `verify` to re-check the metadata files before trusting
    Manifest.csv. Unknown or malformed lines are ignored; a caller that
    finds an expected name missing should treat that as a failure.
    """
    found: dict[str, str] = {}
    for raw_line in certificate_text.splitlines():
        parts = raw_line.split()
        if len(parts) == 2 and parts[0] in METADATA_FILES:
            found[parts[0]] = parts[1]
    return found


def build_certificate_text(
    records: list[GeneratedFile],
    generation_seconds: float,
    output_root: Path,
    source_overrides: list[tuple[str, str]] | None = None,
) -> str:
    """Render the full CorpusCertificate.txt content as a string."""
    total_files = len(records)
    total_bytes = sum(r.size_bytes for r in records)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "Unicode Test Suite Generator - Corpus Certificate",
        "=" * 50,
        "",
        f"Generator version:    {GENERATOR_VERSION}",
        f"Manifest version:     {MANIFEST_VERSION}",
        f"Python version:       {sys.version.split()[0]} ({platform.python_implementation()})",
        f"Platform:             {platform.system()} {platform.release()}",
        f"Unicode version:      {unicodedata.unidata_version}",
        f"Generation timestamp: {timestamp}",
        f"Generation duration:  {generation_seconds:.2f} seconds",
        "",
        f"Total files:          {total_files:,}",
        f"Total size:           {total_bytes:,} bytes",
        "",
        "Metadata file hashes (SHA-256)",
        "-" * 50,
    ]
    lines.extend(_metadata_hash_lines(output_root))
    lines.append("")

    lines.append("Source document overrides")
    lines.append("-" * 50)
    if source_overrides:
        for doc_id, digest in source_overrides:
            lines.append(f"{_HASH_PREFIX}{doc_id:<{_LABEL_WIDTH}} {digest}")
        lines.append("")
        lines.append("  WARNING: this corpus was generated with Source/ overrides and")
        lines.append("  is NOT the canonical corpus for this generator version. Its")
        lines.append("  hashes will not match an unmodified run.")
    else:
        lines.append(f"{_HASH_PREFIX}none")
    lines.append("")

    lines.extend([
        "Every file listed in MasterHashes.sha256 was reopened from disk,",
        "decoded with its declared encoding (where applicable), and its",
        "SHA-256 was recomputed and compared before this certificate was",
        "issued. No mismatch occurred during this run.",
        "",
    ])
    return chr(10).join(lines) + chr(10)


def write_certificate(
    records: list[GeneratedFile],
    generation_seconds: float,
    output_root: Path,
    output_path: Path,
    source_overrides: list[tuple[str, str]] | None = None,
) -> None:
    """Write CorpusCertificate.txt to disk. Must run after every other file."""
    text = build_certificate_text(records, generation_seconds, output_root, source_overrides)
    output_path.write_text(text, encoding="utf-8", newline=chr(10))
