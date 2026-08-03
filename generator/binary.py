"""Synthetic binary-format-signature fixtures for 13_Binary.

These are NOT real, valid instances of each format - they are small,
deterministic byte streams that begin with the format's real magic
number/signature (so a signature-sniffing detector recognizes them)
followed by deterministic filler. This is standard practice for an
encoding/format-detector test corpus: the goal is exercising signature
recognition and binary-vs-text classification, not producing files
that actually open in a real application.

Every fixture is fully deterministic (no OS randomness) so the corpus
stays byte-identical across runs.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable

from generator.categories import BINARY_CATEGORIES

# Fixed seed so every "random" byte in this module is reproducible.
_SEED = 20260101


def _deterministic_stream(seed_label: str, length: int) -> bytes:
    """Deterministic pseudo-random-looking bytes via a chained SHA-256.

    Not cryptographically meaningful - just a reproducible, uniformly
    distributed-looking filler stream with no external randomness.
    """
    out = bytearray()
    block = f"{_SEED}:{seed_label}".encode("utf-8")
    while len(out) < length:
        block = hashlib.sha256(block).digest()
        out.extend(block)
    return bytes(out[:length])


def _magic_stub(signature: bytes, seed_label: str, total_size: int) -> bytes:
    """Signature bytes followed by deterministic filler up to total_size."""
    filler_len = max(0, total_size - len(signature))
    return signature + _deterministic_stream(seed_label, filler_len)


# One or more (variant_name, signature_bytes) pairs per binary category.
# Signatures are the real, publicly documented magic numbers for each
# format; everything after the signature is synthetic filler.
_FORMAT_SIGNATURES: dict[str, list[tuple[str, bytes]]] = {
    "EXE": [
        ("Small", b"MZ\x90\x00\x03\x00\x00\x00"),
        ("Medium", b"MZ\x90\x00\x03\x00\x00\x00"),
        ("Large", b"MZ\x90\x00\x03\x00\x00\x00"),
    ],
    "DLL": [
        ("Small", b"MZ\x90\x00\x03\x00\x00\x00"),
        ("Medium", b"MZ\x90\x00\x03\x00\x00\x00"),
        ("Large", b"MZ\x90\x00\x03\x00\x00\x00"),
    ],
    "PNG": [
        ("Small", b"\x89PNG\r\n\x1a\n"),
        ("Medium", b"\x89PNG\r\n\x1a\n"),
        ("Large", b"\x89PNG\r\n\x1a\n"),
    ],
    "JPG": [
        ("Small", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"),
        ("Medium", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"),
        ("Large", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"),
    ],
    "GIF": [
        ("GIF87a", b"GIF87a"),
        ("GIF89a", b"GIF89a"),
        ("Large", b"GIF89a"),
    ],
    "ZIP": [
        ("Small", b"PK\x03\x04\x14\x00\x00\x00\x08\x00"),
        ("Empty", b"PK\x05\x06" + b"\x00" * 18),
        ("Large", b"PK\x03\x04\x14\x00\x00\x00\x08\x00"),
    ],
    "PDF": [
        ("Small", b"%PDF-1.7\n"),
        ("Medium", b"%PDF-1.4\n"),
        ("Large", b"%PDF-2.0\n"),
    ],
    "Office": [
        ("OOXML_Zip", b"PK\x03\x04\x14\x00\x00\x00\x08\x00"),
        ("LegacyOLE", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),
        ("OOXML_Large", b"PK\x03\x04\x14\x00\x00\x00\x08\x00"),
    ],
    "Audio": [
        ("WAV", b"RIFF\x00\x00\x00\x00WAVEfmt "),
        ("MP3_ID3", b"ID3\x03\x00\x00\x00\x00\x00\x00"),
        ("FLAC", b"fLaC\x00\x00\x00\x22"),
    ],
    "Video": [
        ("MP4", b"\x00\x00\x00\x18ftypmp42"),
        ("AVI", b"RIFF\x00\x00\x00\x00AVI LIST"),
        ("Matroska", b"\x1a\x45\xdf\xa3"),
    ],
    "SQLite": [
        ("Header", b"SQLite format 3\x00"),
        ("Large", b"SQLite format 3\x00"),
    ],
    "Random": [
        ("Uniform4KB", b""),
        ("Uniform16KB", b""),
        ("Uniform64KB", b""),
    ],
}

_VARIANT_SIZES: dict[str, int] = {
    "Small": 512,
    "Medium": 4096,
    "Large": 32768,
    "GIF87a": 512,
    "GIF89a": 512,
    "Empty": 22,
    "OOXML_Zip": 2048,
    "LegacyOLE": 2048,
    "OOXML_Large": 32768,
    "WAV": 1024,
    "MP3_ID3": 1024,
    "FLAC": 1024,
    "MP4": 2048,
    "AVI": 2048,
    "Matroska": 2048,
    "Header": 4096,
    "Uniform4KB": 4096,
    "Uniform16KB": 16384,
    "Uniform64KB": 65536,
}


def generate_binary_fixtures(
    root: Path,
    binary_folder: str,
    verify_binary_file: Callable[[Path, str, int], None],
    sha256_bytes: Callable[[bytes], str],
    generated_file_cls,
) -> list:
    """Write every binary-format-stub fixture under `binary_folder`.

    Returns a list of `generated_file_cls` records (duck-typed as
    generator.corpus.GeneratedFile to avoid a circular import).
    """
    results = []
    for category in BINARY_CATEGORIES:
        for variant_name, signature in _FORMAT_SIGNATURES.get(category, []):
            size = _VARIANT_SIZES.get(variant_name, 1024)
            data = _magic_stub(signature, f"{category}:{variant_name}", size)
            filename = f"{category}_{variant_name}.bin"
            relative_path = "/".join([binary_folder, category, filename])
            full_path = root.joinpath(*relative_path.split("/"))
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(data)
            digest = sha256_bytes(data)
            verify_binary_file(full_path, digest, len(data))
            results.append(generated_file_cls(
                doc_id="N/A", category=category, encoding_label="Binary",
                bom="N/A", line_ending="N/A", characters=0,
                size_bytes=len(data), sha256=digest, relative_path=relative_path,
            ))

    mostly_ascii_with_nuls = bytearray()
    sentence = b"Mostly ASCII text with occasional embedded NUL bytes. " * 4
    for i, byte in enumerate(sentence):
        mostly_ascii_with_nuls.append(byte)
        if i % 17 == 0:
            mostly_ascii_with_nuls.append(0x00)

    edge_fixtures = {
        "ZeroBytes.bin": b"\x00" * 2048,
        "AllOnesBytes.bin": b"\xff" * 2048,
        "EmbeddedUtf8Bom.bin": b"before\n\xef\xbb\xbfmiddle\nafter\n",
        "OnlyBomUtf8.bin": b"\xef\xbb\xbf",
        "OnlyBomUtf16LE.bin": b"\xff\xfe",
        "OnlyBomUtf16BE.bin": b"\xfe\xff",
        "OnlyBomUtf32LE.bin": b"\xff\xfe\x00\x00",
        "OnlyBomUtf32BE.bin": b"\x00\x00\xfe\xff",
        "MostlyAsciiWithNuls.bin": bytes(mostly_ascii_with_nuls),
        "SingleByte.bin": b"\x41",
        "AlternatingBytes.bin": bytes((i % 2) * 0xFF for i in range(2048)),
        "AllPossibleByteValues.bin": bytes(range(256)),
        "HighEntropy.bin": _deterministic_stream("HighEntropy", 4096),
        "RepeatingPattern.bin": (b"\xde\xad\xbe\xef" * 512),
        "NearlyAllNul.bin": (b"\x00" * 1023 + b"\x01"),
    }
    for filename, data in edge_fixtures.items():
        relative_path = "/".join([binary_folder, "Random", filename])
        full_path = root.joinpath(*relative_path.split("/"))
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        digest = sha256_bytes(data)
        verify_binary_file(full_path, digest, len(data))
        results.append(generated_file_cls(
            doc_id="N/A", category="Random", encoding_label="Binary",
            bom="N/A", line_ending="N/A", characters=0,
            size_bytes=len(data), sha256=digest, relative_path=relative_path,
        ))

    return results
