"""Project dossier: the full story of a project or system from the diary.

Read-only. Scans the diary over a period, matches entries to a target project
(or system, with component roll-up) using canonical identity, and assembles a
chronological timeline, aggregated references, a per-component breakdown, and
the day-level blockers seen on days the project was worked. Output is capped.
"""

from datetime import timedelta
from typing import Optional

from mcp_cronos.config import load_config
from mcp_cronos.utils.dates import get_today, parse_date
from mcp_cronos.utils.markdown import extract_references, parse_diary_content
from mcp_cronos.utils.projects import canonical_projects, members_of, normalize_project
from mcp_cronos.utils.scan import iter_diary_days

_DEFAULT_NO_BLOCKERS = {"nessuno", "none"}


def _ref_bucket(label: str) -> Optional[str]:
    """Map a free-form reference label to one of the structured buckets.

    Returns "repository", "branch", "jira", or "gitlab_mr" for recognised
    label families (handling variants like "repo accounts", "jira task",
    "mr epic"), or None for everything else (which goes to the "altri" bucket).
    """
    low = label.strip().lower()
    if low.startswith("repo"):
        return "repository"
    if low.startswith("branch"):
        return "branch"
    if low == "mr" or low.startswith("mr ") or "gitlab" in low:
        return "gitlab_mr"
    if "jira" in low or "ticket" in low or "subtask" in low or low.endswith("task"):
        return "jira"
    return None


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

        The ``riferimenti`` value groups references into structured buckets:
        ``repository``, ``branch``, ``jira``, ``gitlab_mr``.  Label variants
        such as "repo accounts", "jira task", and "mr epic" are normalised into
        the corresponding bucket.  All other free-form labels are preserved
        under an ``altri`` sub-dict instead of flooding the top level.
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

    for d, content, entries in iter_diary_days(start, end):
        day_has_project = False
        for heading, body in entries:
            matched = [p for p in canonical_projects(heading) if p in target_set]
            if not matched:
                continue
            day_has_project = True
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

    strutturati: dict[str, set] = {}
    altri: dict[str, set] = {}
    for label, vals in refs_acc.items():
        bucket = _ref_bucket(label)
        if bucket:
            strutturati.setdefault(bucket, set()).update(vals)
        else:
            altri.setdefault(label, set()).update(vals)
    riferimenti: dict = {k: sorted(v) for k, v in sorted(strutturati.items())}
    if altri:
        riferimenti["altri"] = {k: sorted(v) for k, v in sorted(altri.items())}

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
        "riferimenti": riferimenti,
        "bloccanti": bloccanti,
        "max_voci": max_voci,
        "troncato": troncato,
    }
