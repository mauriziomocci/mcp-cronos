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

copertura reports how much of the written work the statistics actually see:
voci_totali counts every H3 entry, voci_mappate those resolving to a registered
project. With an empty registry everything passes through (100%). voci_non_mappate
includes both untagged work and sub-section headings written as H3, so the
percentage is a lower bound on real coverage, not an accusation.
"""

from datetime import timedelta
from typing import Optional

from mcp_cronos.config import load_config
from mcp_cronos.utils.dates import get_today, parse_date
from mcp_cronos.utils.projects import canonical_projects, system_of
from mcp_cronos.utils.scan import iter_diary_days


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

    config = load_config()
    voci: dict[str, int] = {}
    giorni: dict[str, set[str]] = {}
    per_mese: dict[str, int] = {}
    giorni_attivi: set[str] = set()
    entries_count = 0
    entries_mapped = 0

    for d, _content, entries in iter_diary_days(start, end):
        mese = str(d)[:7]
        for heading, _body in entries:
            entries_count += 1
            projects = canonical_projects(heading)
            if not projects:
                continue
            entries_mapped += 1
            giorni_attivi.add(str(d))
            for p in projects:
                voci[p] = voci.get(p, 0) + 1
                giorni.setdefault(p, set()).add(str(d))
                per_mese[mese] = per_mese.get(mese, 0) + 1

    totale_voci = sum(voci.values())

    systems = set(config.project_system.values())
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

    copertura = {
        "registro_attivo": config.projects_registered,
        "voci_totali": entries_count,
        "voci_mappate": entries_mapped,
        "voci_non_mappate": entries_count - entries_mapped,
        "percentuale": round(entries_mapped / entries_count * 100, 1) if entries_count else 0.0,
    }

    return {
        "periodo": {"da": str(start), "a": str(end), "giorni_analizzati": (end - start).days + 1},
        "totali": {
            "voci": totale_voci,
            "giorni_attivi": len(giorni_attivi),
            "progetti": len(voci),
            "sistemi": len(sys_voci),
        },
        "copertura": copertura,
        "per_sistema": per_sistema,
        "per_progetto": per_progetto,
        "per_mese": dict(sorted(per_mese.items())),
        "max_progetti": max_progetti,
        "troncato": troncato,
    }
