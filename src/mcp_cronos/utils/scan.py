"""Shared day-by-day diary scanner used by the read/analysis tools.

Yields, for each day in a range that has a diary file, the date, the raw file
content, and the list of (heading, body) pairs for the top-level '### ' entries
(fence-aware). Centralises the scan loop that lista/dossier/statistiche/audit/
riferimento would otherwise each re-implement.
"""

from collections.abc import Iterator
from datetime import date

from mcp_cronos.utils.dates import get_date_range, get_file_path
from mcp_cronos.utils.markdown import split_entries_respecting_fences


def iter_diary_days(start: date, end: date) -> Iterator[tuple[date, str, list[tuple[str, str]]]]:
    """Yield (day, content, entries) for each existing diary file in [start, end].

    entries is a list of (heading, body): heading is the text after '### ' of a
    top-level entry; body is the rest of that entry chunk. Segmentation is
    fence-aware (fenced code blocks are opaque).
    """
    for d in get_date_range(start, end):
        file_path = get_file_path(d)
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        entries: list[tuple[str, str]] = []
        for part in split_entries_respecting_fences(content):
            head_body = part.split("\n", 1)
            first = head_body[0]
            if not first.startswith("### "):
                continue
            heading = first[4:].strip()
            body = head_body[1] if len(head_body) > 1 else ""
            entries.append((heading, body))
        yield d, content, entries
