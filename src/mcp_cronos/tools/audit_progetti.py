"""Audit and bootstrap helper for the project registry.

Scans diary headings over a period, clusters the raw project tokens by their
normalized key, and emits a ready-to-edit [cronos.projects] draft so building
the registry is simple for any user. Read-only: it never writes cronos.toml.
"""

from datetime import timedelta
from typing import Optional

from mcp_cronos.utils.dates import get_date_range, get_file_path, get_today, parse_date
from mcp_cronos.utils.markdown import _split_entries_respecting_fences
from mcp_cronos.utils.projects import normalize_project, project_tokens


def audit_progetti(
    data_inizio: Optional[str] = None,
    data_fine: Optional[str] = None,
    ultimi_giorni: int = 180,
    max_voci: int = 200,
) -> dict:
    """Cluster raw project tokens over a period and draft a registry block."""
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

    clusters: dict[str, dict] = {}
    for d in get_date_range(start, end):
        file_path = get_file_path(d)
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        for part in _split_entries_respecting_fences(content):
            first_line = part.split("\n", 1)[0]
            if not first_line.startswith("### "):
                continue
            header = first_line[4:].strip()
            for token in project_tokens(header):
                key = normalize_project(token)
                if not key:
                    continue
                c = clusters.setdefault(key, {"varianti": {}, "occorrenze": 0})
                c["varianti"][token] = c["varianti"].get(token, 0) + 1
                c["occorrenze"] += 1

    ordered = sorted(clusters.items(), key=lambda kv: kv[1]["occorrenze"], reverse=True)
    troncato = len(ordered) > max_voci
    ordered = ordered[:max_voci]

    cluster_out = []
    draft_lines: list[str] = []
    for key, data in ordered:
        varianti = sorted(data["varianti"], key=lambda v: data["varianti"][v], reverse=True)
        canonical = varianti[0]
        cluster_out.append(
            {
                "chiave": key,
                "canonico_proposto": canonical,
                "varianti": varianti,
                "occorrenze": data["occorrenze"],
            }
        )
        draft_lines.append(f"[cronos.projects.{canonical!r}]")
        extra = [v for v in varianti if v != canonical]
        if extra:
            alias_repr = ", ".join(repr(v) for v in extra)
            draft_lines.append(f"alias = [{alias_repr}]")
        draft_lines.append("")

    return {
        "periodo": {"da": str(start), "a": str(end)},
        "totale_nomi_grezzi": len(clusters),
        "max_voci": max_voci,
        "troncato": troncato,
        "cluster": cluster_out,
        "bozza_toml": "\n".join(draft_lines).strip(),
        "nota": (
            "Bozza pronta da incollare in cronos.toml. Rivedi i canonici, "
            "accorpa con 'alias' i sinonimi veri, e aggiungi 'sistema = \"...\"' "
            "dove vuoi la gerarchia. Il tool non scrive il file."
        ),
    }
