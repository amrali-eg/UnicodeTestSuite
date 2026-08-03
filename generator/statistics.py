"""Statistics.txt: aggregate counts and sizes across the whole corpus."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from generator.corpus import GeneratedFile


def _format_bytes(size: int) -> str:
    return f"{size:,} bytes"


def build_statistics_text(records: list[GeneratedFile], generation_seconds: float) -> str:
    """Render the full Statistics.txt content as a string."""
    total_files = len(records)
    total_bytes = sum(r.size_bytes for r in records)

    per_encoding: Counter[str] = Counter(r.encoding_label for r in records)
    per_category: Counter[str] = Counter(r.category for r in records)

    average_size = total_bytes / total_files if total_files else 0
    largest = max(records, key=lambda r: r.size_bytes) if records else None
    smallest = min(records, key=lambda r: r.size_bytes) if records else None

    lines: list[str] = []
    lines.append("Unicode Test Suite Generator - Statistics")
    lines.append("=" * 42)
    lines.append("")
    lines.append(f"Total files:        {total_files:,}")
    lines.append(f"Total bytes:        {_format_bytes(total_bytes)}")
    lines.append(f"Average file size:  {_format_bytes(round(average_size))}")
    lines.append(f"Generation time:    {generation_seconds:.2f} seconds")
    lines.append("")

    if largest is not None:
        lines.append(f"Largest file:       {largest.relative_path} ({_format_bytes(largest.size_bytes)})")
    if smallest is not None:
        lines.append(f"Smallest file:      {smallest.relative_path} ({_format_bytes(smallest.size_bytes)})")
    lines.append("")

    lines.append("Files per encoding")
    lines.append("-" * 42)
    for encoding_label, count in sorted(per_encoding.items()):
        lines.append(f"  {encoding_label:<20} {count:>6,}")
    lines.append("")

    lines.append("Files per category")
    lines.append("-" * 42)
    for category, count in sorted(per_category.items()):
        lines.append(f"  {category:<20} {count:>6,}")
    lines.append("")

    return "\n".join(lines) + "\n"


def write_statistics(records: list[GeneratedFile], generation_seconds: float, path: Path) -> None:
    """Write Statistics.txt to disk."""
    path.write_text(build_statistics_text(records, generation_seconds), encoding="utf-8", newline="\n")
