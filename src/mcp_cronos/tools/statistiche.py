"""Work statistics over the diary: distribution by project and system.

Read-only. Counts entries (each H3 heading resolving to a canonical project)
and distinct days per project over a period, rolls up to systems with a share
percentage, and reports a per-month activity trend. Effort is a proxy (entries
and days), not manual time-tracking.

per_mese counts project-attributions per month (consistent with totali.voci).
quota_pct is each system's share of total entries; shares may not sum to
exactly 100 due to 1-decimal rounding, and exclude standalone projects (which
have no system), so they sum to less than 100 when standalone work exists.

per_sistema roll-up includes both component work (project with sistema = X)
and directly-tagged system work (heading resolved to a system name itself),
matching the dossier's members_of semantics. The system's own entries also
appear in per_progetto with sistema=None (they are the system's direct work
line, not a component of another system).
"""

from datetime import timedelta
from typing import Optional

from mcp_cronos.config import load_config
from mcp_cronos.utils.dates import get_date_range, get_file_path, get_today, parse_date
from mcp_cronos.utils.markdown import split_entries_respecting_fences
from mcp_cronos.utils.projects import canonical_projects, system_of


def statistiche(
    data_inizio: Optional[str] = None,
    data_fine: Optional[str] = None,
    ultimi_giorni: int = 90,
    max_progetti: int = 50,
) -> dict:
    """Aggregate work statistics by project and system over a period."""
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

    voci: dict[str, int] = {}
    giorni: dict[str, set[str]] = {}
    per_mese: dict[str, int] = {}
    giorni_attivi: set[str] = set()

    for d in get_date_range(start, end):
        file_path = get_file_path(d)
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        mese = str(d)[:7]
        for part in split_entries_respecting_fences(content):
            first = part.split("\n", 1)[0]
            if not first.startswith("### "):
                continue
            projects = canonical_projects(first[4:].strip())
            if not projects:
                continue
            giorni_attivi.add(str(d))
            for p in projects:
                voci[p] = voci.get(p, 0) + 1
                giorni.setdefault(p, set()).add(str(d))
                per_mese[mese] = per_mese.get(mese, 0) + 1

    totale_voci = sum(voci.values())

    systems = set(load_config().project_system.values())
    sys_voci: dict[str, int] = {}
    sys_giorni: dict[str, set[str]] = {}
    for p, n in voci.items():
        # A component rolls into its parent system; a project whose own name is a
        # system rolls into that system (its directly-tagged platform-level work),
        # matching the dossier's members_of semantics.
        s = system_of(p)
        if s is None and p in systems:
            s = p
        if s:
            sys_voci[s] = sys_voci.get(s, 0) + n
            sys_giorni.setdefault(s, set()).update(giorni[p])

    per_sistema = [
        {
            "sistema": s,
            "voci": n,
            "giorni": len(sys_giorni[s]),
            "quota_pct": round(n / totale_voci * 100, 1) if totale_voci else 0.0,
        }
        for s, n in sorted(sys_voci.items(), key=lambda kv: kv[1], reverse=True)
    ]

    ordinati = sorted(voci.items(), key=lambda kv: kv[1], reverse=True)
    troncato = len(ordinati) > max_progetti
    per_progetto = [
        {"nome": p, "sistema": system_of(p), "voci": n, "giorni": len(giorni[p])}
        for p, n in ordinati[:max_progetti]
    ]

    return {
        "periodo": {"da": str(start), "a": str(end), "giorni_analizzati": (end - start).days + 1},
        "totali": {
            "voci": totale_voci,
            "giorni_attivi": len(giorni_attivi),
            "progetti": len(voci),
            "sistemi": len(sys_voci),
        },
        "per_sistema": per_sistema,
        "per_progetto": per_progetto,
        "per_mese": dict(sorted(per_mese.items())),
        "max_progetti": max_progetti,
        "troncato": troncato,
    }
