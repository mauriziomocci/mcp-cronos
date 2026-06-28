"""Tests for cronos_statistiche."""


def _reg(diario):
    (diario / "cronos.toml").write_text(
        "[cronos]\ngit = false\n\n"
        "[cronos.projects.Teseo]\n\n"
        '[cronos.projects.SmarTicket]\nsistema = "Teseo"\n\n'
        '[cronos.projects.Infomobile]\nsistema = "Teseo"\n\n'
        "[cronos.projects.Goceano]\n",
        encoding="utf-8",
    )


def _day(diario, ymd, *headings):
    y, m, _ = ymd.split("-")
    p = diario / y / m / ymd
    p.mkdir(parents=True, exist_ok=True)
    body = "# T\n\n## Cosa ho fatto ieri\n\n"
    for h in headings:
        body += f"### {h}\n\nx\n\n---\n\n"
    body += "## Bloccanti\n\nNessuno\n"
    (p / "raw.md").write_text(body, encoding="utf-8")


def test_statistiche_distribution_and_rollup(tmp_diario):
    _reg(tmp_diario)
    _day(tmp_diario, "2026-04-08", "SmarTicket - a", "SmarTicket - b", "Goceano - c")
    _day(tmp_diario, "2026-05-09", "SmarTicket - d", "Infomobile - e")
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.statistiche import statistiche

    _reset_config()
    r = statistiche(data_inizio="2026-04-01", data_fine="2026-05-31")

    assert r["totali"]["voci"] == 5
    assert r["totali"]["giorni_attivi"] == 2
    assert r["totali"]["progetti"] == 3
    assert r["totali"]["sistemi"] == 1
    pp = {p["nome"]: p for p in r["per_progetto"]}
    assert pp["SmarTicket"]["voci"] == 3
    assert pp["SmarTicket"]["giorni"] == 2
    assert pp["SmarTicket"]["sistema"] == "Teseo"
    assert pp["Goceano"]["sistema"] is None
    ps = {s["sistema"]: s for s in r["per_sistema"]}
    assert ps["Teseo"]["voci"] == 4
    assert ps["Teseo"]["quota_pct"] == 80.0
    assert r["per_mese"] == {"2026-04": 3, "2026-05": 2}


def test_statistiche_empty_period_no_crash(tmp_diario):
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.statistiche import statistiche

    _reset_config()
    r = statistiche(data_inizio="2026-04-01", data_fine="2026-04-02")
    assert r["totali"]["voci"] == 0
    assert r["per_sistema"] == []
    assert r["per_progetto"] == []
    assert r["per_mese"] == {}
    assert r["troncato"] is False


def test_statistiche_truncates(tmp_diario):
    _reg(tmp_diario)
    _day(tmp_diario, "2026-04-08", "SmarTicket - a", "Infomobile - b", "Goceano - c")
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.statistiche import statistiche

    _reset_config()
    r = statistiche(data_inizio="2026-04-01", data_fine="2026-04-30", max_progetti=2)
    assert r["totali"]["progetti"] == 3
    assert len(r["per_progetto"]) == 2
    assert r["troncato"] is True


def test_cronos_statistiche_tool_registered():
    from mcp_cronos.server import TOOLS

    assert any(t.name == "cronos_statistiche" for t in TOOLS)


def test_statistiche_passthrough_no_registry(tmp_diario):
    # No cronos.toml -> pass-through: raw names counted, no system roll-up.
    _day(tmp_diario, "2026-04-08", "Backend API - a", "Mobile App - b")
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.statistiche import statistiche

    _reset_config()
    r = statistiche(data_inizio="2026-04-01", data_fine="2026-04-30")
    assert r["totali"]["voci"] == 2
    assert r["totali"]["sistemi"] == 0
    assert r["per_sistema"] == []
    nomi = {p["nome"] for p in r["per_progetto"]}
    assert nomi == {"Backend API", "Mobile App"}
    assert all(p["sistema"] is None for p in r["per_progetto"])


def test_statistiche_composite_counts_consistently(tmp_diario):
    _reg(tmp_diario)
    # one composite heading touching two Teseo components
    _day(tmp_diario, "2026-04-08", "SmarTicket / Infomobile - shared work")
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.statistiche import statistiche

    _reset_config()
    r = statistiche(data_inizio="2026-04-01", data_fine="2026-04-30")
    # composite counts for both projects
    assert r["totali"]["voci"] == 2
    pp = {p["nome"]: p["voci"] for p in r["per_progetto"]}
    assert pp == {"SmarTicket": 1, "Infomobile": 1}
    # per_mese is consistent with totali.voci
    assert sum(r["per_mese"].values()) == r["totali"]["voci"] == 2


def test_statistiche_system_includes_direct_tagged_work(tmp_diario):
    _reg(tmp_diario)
    # "Teseo" tagged directly (platform/infra work) + a component, same period
    _day(tmp_diario, "2026-04-08", "Teseo - infra rollout", "SmarTicket - fix")
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.statistiche import statistiche

    _reset_config()
    r = statistiche(data_inizio="2026-04-01", data_fine="2026-04-30")
    ps = {s["sistema"]: s for s in r["per_sistema"]}
    # Teseo system = direct "Teseo" work (1) + SmarTicket component (1) = 2
    assert ps["Teseo"]["voci"] == 2
    # "Teseo" still also appears as a top-level project entry (sistema=None) in per_progetto
    pp = {p["nome"]: p for p in r["per_progetto"]}
    assert pp["Teseo"]["sistema"] is None
    assert pp["Teseo"]["voci"] == 1


def test_statistiche_copertura_registro_popolato(tmp_diario):
    _reg(tmp_diario)
    # 2 mapped (SmarTicket, Goceano) + 1 unmapped heading
    _day(tmp_diario, "2026-04-08", "SmarTicket - a", "Goceano - b", "Sconosciuto - c")
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.statistiche import statistiche

    _reset_config()
    r = statistiche(data_inizio="2026-04-01", data_fine="2026-04-30")

    cop = r["copertura"]
    assert cop["registro_attivo"] is True
    assert cop["voci_totali"] == 3
    assert cop["voci_mappate"] == 2
    assert cop["voci_non_mappate"] == 1
    assert cop["percentuale"] == 66.7


def test_statistiche_copertura_registro_vuoto_e_cento(tmp_diario):
    # No registry -> pass-through: every heading maps, coverage 100%.
    (tmp_diario / "cronos.toml").write_text("[cronos]\ngit = false\n", encoding="utf-8")
    _day(tmp_diario, "2026-04-08", "Qualcosa - a", "Altro - b")
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.statistiche import statistiche

    _reset_config()
    r = statistiche(data_inizio="2026-04-01", data_fine="2026-04-30")

    cop = r["copertura"]
    assert cop["registro_attivo"] is False
    assert cop["voci_totali"] == 2
    assert cop["voci_mappate"] == 2
    assert cop["voci_non_mappate"] == 0
    assert cop["percentuale"] == 100.0
