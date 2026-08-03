"""Round-trip verification.

Every text file the corpus writes is reopened, its BOM (if any) is
checked, it is decoded with the exact encoding it was written with,
and the decoded text is compared character-for-character against the
original document. Size and SHA-256 are re-verified from disk bytes,
never from the in-memory buffer that was written.

Any mismatch raises CorpusIntegrityError, which the orchestrator
treats as fatal - generation aborts immediately per the reliability
requirement.
"""

from __future__ import annotations

from pathlib import Path

from generator.encoder import EncodingSpec, strip_bom
from generator.hashing import sha256_file


class CorpusIntegrityError(RuntimeError):
    """Raised when a generated file fails round-trip verification."""


def verify_text_file(
    path: Path,
    spec: EncodingSpec,
    expected_text: str,
    expected_sha256: str,
    expected_size: int,
) -> None:
    """Verify a text-based corpus file matches its expected content exactly."""
    if not path.is_file():
        raise CorpusIntegrityError(f"File missing after write: {path}")

    data = path.read_bytes()

    if len(data) != expected_size:
        raise CorpusIntegrityError(
            f"Size mismatch for {path}: expected {expected_size}, got {len(data)}"
        )

    actual_sha256 = sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise CorpusIntegrityError(
            f"SHA-256 mismatch for {path}: expected {expected_sha256}, got {actual_sha256}"
        )

    if spec.has_bom and not data.startswith(spec.bom_bytes):
        raise CorpusIntegrityError(f"Expected BOM missing in {path}")
    if not spec.has_bom and spec.codec == "utf-8" and data.startswith(b"\xef\xbb\xbf"):
        raise CorpusIntegrityError(f"Unexpected UTF-8 BOM found in {path}")

    payload = strip_bom(data, spec)
    try:
        decoded = payload.decode(spec.codec)
    except UnicodeDecodeError as exc:
        raise CorpusIntegrityError(f"Decode failure for {path}: {exc}") from exc

    if decoded != expected_text:
        raise CorpusIntegrityError(f"Decoded text mismatch for {path}")


def verify_binary_file(path: Path, expected_sha256: str, expected_size: int) -> None:
    """Verify a non-text corpus file's size and hash only (no decoding)."""
    if not path.is_file():
        raise CorpusIntegrityError(f"File missing after write: {path}")

    data = path.read_bytes()
    if len(data) != expected_size:
        raise CorpusIntegrityError(
            f"Size mismatch for {path}: expected {expected_size}, got {len(data)}"
        )

    actual_sha256 = sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise CorpusIntegrityError(
            f"SHA-256 mismatch for {path}: expected {expected_sha256}, got {actual_sha256}"
        )


def verify_archived_file(
    full_path: Path,
    encoding_label: str,
    bom_label: str,
    expected_size: int,
    expected_sha256: str,
) -> None:
    """Post-hoc verification of a file already on disk, from Manifest.csv alone.

    Unlike verify_text_file (used during generation, which also checks
    the decoded text against the live source document), this only has
    the manifest row to work with: it re-checks size and SHA-256 from
    disk, and - for anything with a real text encoding - confirms the
    bytes still decode cleanly under that encoding. Used by
    `GenerateCorpus.py verify` to re-check an existing corpus directory
    without regenerating it.
    """
    from generator.encoder import find_spec  # local import: avoids a cycle at module load

    if not full_path.is_file():
        raise CorpusIntegrityError(f"File missing: {full_path}")

    data = full_path.read_bytes()
    if len(data) != expected_size:
        raise CorpusIntegrityError(
            f"Size mismatch for {full_path}: expected {expected_size}, got {len(data)}"
        )

    actual_sha256 = sha256_file(full_path)
    if actual_sha256 != expected_sha256:
        raise CorpusIntegrityError(
            f"SHA-256 mismatch for {full_path}: expected {expected_sha256}, got {actual_sha256}"
        )

    spec = find_spec(encoding_label, bom_label)
    if spec is None:
        return  # binary / invalid-unicode fixture: size + hash already confirmed above

    if spec.has_bom and not data.startswith(spec.bom_bytes):
        raise CorpusIntegrityError(f"Expected BOM missing in {full_path}")

    payload = strip_bom(data, spec)
    try:
        payload.decode(spec.codec)
    except UnicodeDecodeError as exc:
        raise CorpusIntegrityError(f"Decode failure for {full_path}: {exc}") from exc
