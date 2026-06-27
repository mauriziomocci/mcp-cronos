"""Project dossier: the full story of a project or system from the diary.

Read-only. Scans the diary over a period, matches entries to a target project
(or system, with component roll-up) using canonical identity, and assembles a
chronological timeline, aggregated references, a per-component breakdown, and
the day-level blockers seen on days the project was worked. Output is capped.
"""

from datetime import timedelta
from typing import Optional

from mcp_cronos.config import load_config
from mcp_cronos.utils.dates import get_date_range, get_file_path, get_today, parse_date
from mcp_cronos.utils.markdown import (
    extract_references,
    parse_diary_content,
    split_entries_respecting_fences,
)
from mcp_cronos.utils.projects import canonical_projects, members_of, normalize_project

_DEFAULT_NO_BLOCKERS = {"nessuno", "none"}


def dossier_progetto(
    progetto: str,
    data_inizio: Optional[str] = None,
    data_fine: Optional[str] = None,
    ultimi_giorni: int = 180,
    max_voci: int = 50,
) -> dict:
    """Assemble the dossier for a project or system over a period.

    Args:
        progetto: Project or system name to query (resolved via registry if configured).
        data_inizio: Start date in YYYY-MM-DD format. Requires data_fine when provided.
        data_fine: End date in YYYY-MM-DD format. Requires data_inizio when provided.
        ultimi_giorni: Fallback window in days when no explicit date range given.
        max_voci: Maximum number of timeline entries returned. Excess entries are
            truncated from the front (oldest first) and flagged via ``troncato``.
            Each timeline entry's ``progetto`` field is a LIST of matched canonical
            project names (a composite heading can match more than one).

    Returns:
        Dict with keys: progetto, e_sistema, membri, periodo, num_voci, num_giorni,
        prima_data, ultima_data, per_progetto, timeline, riferimenti, bloccanti,
        max_voci, troncato. On validation error, returns {"errore": "<message>"}.
    """
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

    config = load_config()
    resolved = config.project_canonical.get(normalize_project(progetto), progetto)
    e_sistema = resolved in set(config.project_system.values())
    target_set = members_of(progetto)

    timeline: list[dict] = []
    per_progetto: dict[str, int] = {}
    refs_acc: dict[str, set] = {}
    bloccanti: list[dict] = []
    giorni: set[str] = set()

    for d in get_date_range(start, end):
        file_path = get_file_path(d)
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        day_has_project = False
        for part in split_entries_respecting_fences(content):
            head_body = part.split("\n", 1)
            first = head_body[0]
            if not first.startswith("### "):
                continue
            heading = first[4:].strip()
            matched = [p for p in canonical_projects(heading) if p in target_set]
            if not matched:
                continue
            day_has_project = True
            body = head_body[1] if len(head_body) > 1 else ""
            timeline.append(
                {
                    "data": str(d),
                    "progetto": matched,
                    "titolo": heading,
                    "snippet": body.strip()[:200],
                }
            )
            for p in matched:
                per_progetto[p] = per_progetto.get(p, 0) + 1
            refs = extract_references(body)
            if refs:
                for k, v in refs.items():
                    refs_acc.setdefault(k, set()).add(v)
        if day_has_project:
            giorni.add(str(d))
            diary = parse_diary_content(content)
            if diary and diary.bloccanti.strip().lower() not in _DEFAULT_NO_BLOCKERS:
                bloccanti.append({"data": str(d), "testo": diary.bloccanti.strip()[:300]})

    timeline.sort(key=lambda v: v["data"])
    max_voci = max(0, max_voci)
    troncato = len(timeline) > max_voci
    # Slice from an absolute index to avoid the timeline[-0:] == full-list trap.
    timeline_out = timeline[len(timeline) - max_voci :] if troncato else timeline
    date_all = sorted(giorni)

    return {
        "progetto": progetto,
        "e_sistema": e_sistema,
        "membri": sorted(target_set) if e_sistema else None,
        "periodo": {"da": str(start), "a": str(end)},
        "num_voci": len(timeline),
        "num_giorni": len(giorni),
        "prima_data": date_all[0] if date_all else None,
        "ultima_data": date_all[-1] if date_all else None,
        "per_progetto": dict(sorted(per_progetto.items(), key=lambda kv: kv[1], reverse=True)),
        "timeline": timeline_out,
        "riferimenti": {k: sorted(v) for k, v in sorted(refs_acc.items())},
        "bloccanti": bloccanti,
        "max_voci": max_voci,
        "troncato": troncato,
    }
