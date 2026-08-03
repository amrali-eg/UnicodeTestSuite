"""SHA-256 hashing helpers.

File hashes are always computed by re-reading the file from disk after
it was written (never reused from the in-memory bytes that were
written), so a hash mismatch reflects a genuine round-trip failure.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 1024 * 1024  # 1 MiB


def sha256_bytes(data: bytes) -> str:
    """Return the hex SHA-256 digest of an in-memory byte string."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 digest of a file's on-disk contents."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
