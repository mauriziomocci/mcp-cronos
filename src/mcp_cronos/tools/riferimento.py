"""Cross-reference search: the thread of a ticket / MR / repo across the diary.

Read-only. Scans the diary over a period and returns every entry that mentions a
given reference (case-insensitive substring), tagged with its canonical project,
plus the projects and systems the reference spans. Capped output.
"""

from datetime import timedelta
from typing import Optional

from mcp_cronos.utils.dates import get_date_range, get_file_path, get_today, parse_date
from mcp_cronos.utils.markdown import split_entries_respecting_fences
from mcp_cronos.utils.projects import canonical_projects, system_of


def traccia_riferimento(
    riferimento: str,
    data_inizio: Optional[str] = None,
    data_fine: Optional[str] = None,
    ultimi_giorni: int = 180,
    max_voci: int = 50,
) -> dict:
    """Trace every diary entry that mentions a reference, project-aware."""
    if not riferimento or not riferimento.strip():
        return {"errore": "riferimento vuoto"}
    needle = riferimento.strip().lower()

    today = get_today()
    if data_inizio and data_fine:
        try:
            start = parse_date(data_inizio)
            end = parse_date(data_fine)
            if start > end:
                return {"errore": "data_inizio deve essere precedente a data_fine"}
        except ValueError as e:
            return {"errore": str(e)}
    else:
        start = today - timedelta(days=ultimi_giorni - 1)
        end = today

    timeline: list[dict] = []
    progetti: set[str] = set()
    giorni: set[str] = set()

    for d in get_date_range(start, end):
        file_path = get_file_path(d)
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        for part in split_entries_respecting_fences(content):
            # Match the reference anywhere in the entry (heading or body),
            # case-insensitive.
            if needle not in part.lower():
                continue
            head_body = part.split("\n", 1)
            first = head_body[0]
            if not first.startswith("### "):
                continue
            heading = first[4:].strip()
            projs = canonical_projects(heading)
            body = head_body[1] if len(head_body) > 1 else ""
            timeline.append(
                {
                    "data": str(d),
                    "progetto": projs,
                    "titolo": heading,
                    "snippet": body.strip()[:200],
                }
            )
            progetti.update(projs)
            giorni.add(str(d))

    timeline.sort(key=lambda v: v["data"])
    max_voci = max(0, max_voci)
    troncato = len(timeline) > max_voci
    timeline_out = timeline[len(timeline) - max_voci :] if troncato else timeline
    sistemi = sorted({s for p in progetti if (s := system_of(p)) is not None})
    date_all = sorted(giorni)

    return {
        "riferimento": riferimento,
        "periodo": {"da": str(start), "a": str(end)},
        "num_voci": len(timeline),
        "num_giorni": len(giorni),
        "prima_data": date_all[0] if date_all else None,
        "ultima_data": date_all[-1] if date_all else None,
        "progetti": sorted(progetti),
        "sistemi": sistemi,
        "timeline": timeline_out,
        "max_voci": max_voci,
        "troncato": troncato,
    }
