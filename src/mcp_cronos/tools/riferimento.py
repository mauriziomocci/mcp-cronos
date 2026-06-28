"""Cross-reference search: the thread of a ticket / MR / repo across the diary.

Read-only. Scans the diary over a period and returns every entry that mentions a
given reference (case-insensitive substring), tagged with its canonical project,
plus the projects and systems the reference spans. Capped output.
"""

from datetime import timedelta
from typing import Optional

from mcp_cronos.utils.dates import get_today, parse_date
from mcp_cronos.utils.projects import canonical_projects, system_of
from mcp_cronos.utils.scan import iter_diary_days


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

    for d, _content, entries in iter_diary_days(start, end):
        for heading, body in entries:
            # Match the reference anywhere in the entry (heading or body),
            # case-insensitive.
            if needle not in heading.lower() and needle not in body.lower():
                continue
            projs = canonical_projects(heading)
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
