"""Encoding equivalence: which encodings are *also* a correct answer.

Manifest.csv assigns every file one declared encoding, which for a
round-trip corpus is exactly right - it records what produced the bytes.
As detection ground truth it is wrong, because a byte sequence is
frequently valid, and decodes identically, under many encodings at once.

Measured on the v2.0 corpus, 300 of 1,150 text files were byte-identical
to a file carrying a *different* declared encoding, and 27 byte sequences
appeared twice inside the corpus under contradictory labels - once in
01_ASCII as us-ascii and once in 00_Documentation as utf-8. No detector
can satisfy both rows; whichever it reports, the manifest marks 27 files
wrong. A detector answering "ascii" for pure-ASCII content - the more
precise answer - scored 65 false negatives against v2.0 for being right.

This module computes the full answer set for a file's bytes, so a
benchmark harness can score set membership instead of string equality.

The set is computed from the bytes themselves, not from which duplicates
the corpus happens to contain. Pure-ASCII content is valid as every
ASCII-superset encoding whether or not the corpus emits it in all of
them, and the ground truth should say so.
"""

from __future__ import annotations

from generator.encoder import all_specs

# Byte length above which the compatibility scan is skipped. The scan is
# O(bytes x codecs), but measured against the whole corpus - 14_LargeFiles
# included - it costs under a second, so the cap is set high enough to
# cover every file the corpus actually emits. A lower cap would leave the
# large files with an empty answer set, which a harness would read as
# "only the declared encoding is correct" and score against a detector
# that is right. Correctness beats a speed saving that does not exist.
_MAX_SCAN_BYTES = 16 << 20  # 16 MiB


def _candidate_labels() -> list[tuple[str, str]]:
    """Distinct (label, codec) pairs across every spec, in stable order."""
    seen: set[str] = set()
    candidates: list[tuple[str, str]] = []
    for spec in all_specs():
        if spec.label in seen:
            continue
        seen.add(spec.label)
        candidates.append((spec.label, spec.codec))
    return candidates


def compatible_encodings(
    payload: bytes,
    declared_label: str,
    expected_text: str,
) -> tuple[str, ...]:
    """Encodings other than `declared_label` that yield exactly `expected_text`.

    `payload` must already have had any BOM stripped, so the comparison
    is over the encoded text alone.

    An encoding qualifies only when decoding the bytes under it produces
    the *same characters* the declared encoding produces. Byte-level
    reversibility is not enough and must not be used: every single-byte
    codec, iso-8859-1 chief among them, decodes an arbitrary byte
    sequence without error and re-encodes it exactly. Judged on
    round-tripping alone, iso-8859-1 is "compatible" with every file in
    the corpus - it would have UTF-8 Japanese listed as also-valid-as
    iso-8859-1, which is mojibake, not an alternative reading.

    What makes ascii a legitimate answer for a pure-ASCII UTF-8 file is
    that both decoders return identical text. That is the test.

    Returns a sorted tuple, excluding the declared encoding itself.
    """
    if not payload or len(payload) > _MAX_SCAN_BYTES:
        return ()

    compatible: list[str] = []
    for label, codec in _candidate_labels():
        if label == declared_label:
            continue
        try:
            if payload.decode(codec) == expected_text:
                compatible.append(label)
        except UnicodeDecodeError:
            continue
    return tuple(sorted(compatible))


def format_also_valid_as(labels: tuple[str, ...]) -> str:
    """Render an equivalence set for the manifest's AlsoValidAs column.

    Semicolon-separated so the field survives CSV without quoting, and
    empty when the declared encoding is the only correct answer.
    """
    return ";".join(labels)
