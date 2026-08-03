"""Manifest output: Manifest.csv, Manifest.sqlite, and MasterHashes.sha256.

All three are derived from the same in-memory list of GeneratedFile
records and are written in a fixed, sorted order (by relative_path) so
re-running the generator with unchanged inputs produces byte-identical
output files.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from generator.corpus import GeneratedFile

CSV_HEADER = (
    "DocumentID", "Category", "Encoding", "BOM", "LineEnding",
    "Characters", "Bytes", "SHA256", "RelativePath",
)


def _sorted_records(records: list[GeneratedFile]) -> list[GeneratedFile]:
    return sorted(records, key=lambda r: r.relative_path)


def write_manifest_csv(records: list[GeneratedFile], path: Path) -> None:
    """Write Manifest.csv with one row per generated file."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_HEADER)
        for record in _sorted_records(records):
            writer.writerow([
                record.doc_id,
                record.category,
                record.encoding_label,
                record.bom,
                record.line_ending,
                record.characters,
                record.size_bytes,
                record.sha256,
                record.relative_path,
            ])


def write_manifest_sqlite(records: list[GeneratedFile], path: Path) -> None:
    """Write Manifest.sqlite with the same metadata as Manifest.csv."""
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(str(path))
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE files (
                document_id TEXT NOT NULL,
                category TEXT NOT NULL,
                encoding TEXT NOT NULL,
                bom TEXT NOT NULL,
                line_ending TEXT NOT NULL,
                characters INTEGER NOT NULL,
                bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                relative_path TEXT NOT NULL PRIMARY KEY
            )
            """
        )
        rows = [
            (
                r.doc_id, r.category, r.encoding_label, r.bom, r.line_ending,
                r.characters, r.size_bytes, r.sha256, r.relative_path,
            )
            for r in _sorted_records(records)
        ]
        cursor.executemany(
            "INSERT INTO files VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows
        )
        cursor.execute("CREATE INDEX idx_category ON files(category)")
        cursor.execute("CREATE INDEX idx_encoding ON files(encoding)")
        connection.commit()
    finally:
        connection.close()


def read_manifest_csv(path: Path) -> list[dict[str, str]]:
    """Read Manifest.csv back into a list of plain string dicts."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_master_hashes(records: list[GeneratedFile], path: Path) -> None:
    """Write MasterHashes.sha256 in standard 'sha256  path' format.

    This format is compatible with the `sha256sum -c` verification tool
    on Linux/macOS, in addition to being read by this project itself.
    """
    lines = [
        f"{record.sha256}  {record.relative_path}"
        for record in _sorted_records(records)
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_html_index(records: list[GeneratedFile]) -> str:
    """Render Index.html: every generated file grouped by top-level folder."""
    groups: dict[str, list[GeneratedFile]] = {}
    for record in _sorted_records(records):
        folder = record.relative_path.split("/", 1)[0]
        groups.setdefault(folder, []).append(record)

    total_files = len(records)
    total_bytes = sum(r.size_bytes for r in records)

    html_parts: list[str] = []
    html_parts.append("<!DOCTYPE html>")
    html_parts.append("<html lang=\"en\">")
    html_parts.append("<head>")
    html_parts.append("<meta charset=\"utf-8\">")
    html_parts.append("<title>UnicodeTestSuite Index</title>")
    html_parts.append(
        "<style>"
        "body{font-family:monospace;margin:2em;}"
        "h1{font-size:1.4em;} h2{font-size:1.1em;margin-top:2em;"
        "border-bottom:1px solid #ccc;padding-bottom:0.2em;}"
        "table{border-collapse:collapse;width:100%;margin-bottom:1em;}"
        "th,td{border:1px solid #ddd;padding:2px 6px;font-size:0.85em;"
        "text-align:left;white-space:nowrap;}"
        "th{background:#f0f0f0;} tr:nth-child(even){background:#fafafa;}"
        "</style>")
    html_parts.append("</head>")
    html_parts.append("<body>")
    html_parts.append("<h1>UnicodeTestSuite - Corpus Index</h1>")
    html_parts.append(f"<p>Total files: {total_files:,} &mdash; Total size: {total_bytes:,} bytes</p>")

    for folder in sorted(groups):
        folder_records = groups[folder]
        html_parts.append(f"<h2>{_escape_html(folder)} ({len(folder_records):,} files)</h2>")
        html_parts.append("<table>")
        html_parts.append(
            "<tr><th>DocumentID</th><th>Category</th><th>Encoding</th><th>BOM</th>"
            "<th>LineEnding</th><th>Bytes</th><th>SHA-256</th><th>Path</th></tr>"
        )
        for record in folder_records:
            html_parts.append(
                "<tr>"
                f"<td>{_escape_html(record.doc_id)}</td>"
                f"<td>{_escape_html(record.category)}</td>"
                f"<td>{_escape_html(record.encoding_label)}</td>"
                f"<td>{_escape_html(record.bom)}</td>"
                f"<td>{_escape_html(record.line_ending)}</td>"
                f"<td>{record.size_bytes:,}</td>"
                f"<td>{record.sha256[:12]}&hellip;</td>"
                f"<td><a href=\"{_escape_html(record.relative_path)}\">{_escape_html(record.relative_path)}</a></td>"
                "</tr>"
            )
        html_parts.append("</table>")

    html_parts.append("</body>")
    html_parts.append("</html>")
    return "\n".join(html_parts) + "\n"


def write_html_index(records: list[GeneratedFile], path: Path) -> None:
    """Write Index.html to disk."""
    path.write_text(build_html_index(records), encoding="utf-8", newline="\n")
