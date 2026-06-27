"""Tests for cronos_progetto (project dossier)."""


def _write_registry(diario):
    (diario / "cronos.toml").write_text(
        "[cronos]\ngit = false\n\n"
        "[cronos.projects.Teseo]\n\n"
        '[cronos.projects.SmarTicket]\nsistema = "Teseo"\n\n'
        '[cronos.projects.Infomobile]\nsistema = "Teseo"\n\n'
        "[cronos.projects.Goceano]\n",
        encoding="utf-8",
    )


def _write_day(diario, ymd, body):
    y, m, _ = ymd.split("-")
    d = diario / y / m / ymd
    d.mkdir(parents=True, exist_ok=True)
    (d / "raw.md").write_text(body, encoding="utf-8")


def test_dossier_system_rolls_up_components(tmp_diario):
    _write_registry(tmp_diario)
    _write_day(
        tmp_diario,
        "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### SmarTicket - Fix login\n\nFixed.\n\n**Riferimenti:**\n- Repository: st-backend\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
    )
    _write_day(
        tmp_diario,
        "2026-04-09",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### Infomobile — GTFS import\n\nImported.\n\n---\n\n"
        "### Goceano - other\n\nx\n\n---\n\n"
        "## Bloccanti\n\nAttesa credenziali vendor\n",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.dossier import dossier_progetto

    _reset_config()
    r = dossier_progetto("Teseo", data_inizio="2026-04-08", data_fine="2026-04-09")

    assert r["e_sistema"] is True
    assert set(r["membri"]) == {"Teseo", "SmarTicket", "Infomobile"}
    titoli = [v["titolo"] for v in r["timeline"]]
    assert any("SmarTicket" in t for t in titoli)
    assert any("Infomobile" in t for t in titoli)
    assert all("Goceano" not in t for t in titoli)
    assert r["num_voci"] == 2
    assert r["per_progetto"].get("SmarTicket") == 1
    assert r["per_progetto"].get("Infomobile") == 1
    assert "st-backend" in r["riferimenti"].get("repository", [])
    assert any(b["data"] == "2026-04-09" and "credenziali" in b["testo"] for b in r["bloccanti"])
    assert r["timeline"] == sorted(r["timeline"], key=lambda v: v["data"])


def test_dossier_single_component(tmp_diario):
    _write_registry(tmp_diario)
    _write_day(
        tmp_diario,
        "2026-04-09",
        "# T\n\n## Cosa ho fatto ieri\n\n### SmarTicket - x\n\na\n\n---\n\n"
        "### Infomobile - y\n\nb\n\n---\n\n## Bloccanti\n\nNessuno\n",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.dossier import dossier_progetto

    _reset_config()
    r = dossier_progetto("SmarTicket", data_inizio="2026-04-09", data_fine="2026-04-09")
    assert r["e_sistema"] is False
    assert r["num_voci"] == 1
    assert [v["titolo"] for v in r["timeline"]] == ["SmarTicket - x"]


def test_dossier_truncates(tmp_diario):
    _write_registry(tmp_diario)
    body = "# T\n\n## Cosa ho fatto ieri\n\n"
    for i in range(5):
        body += f"### SmarTicket - task {i}\n\nwork {i}\n\n---\n\n"
    body += "## Bloccanti\n\nNessuno\n"
    _write_day(tmp_diario, "2026-04-09", body)
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.dossier import dossier_progetto

    _reset_config()
    r = dossier_progetto("SmarTicket", data_inizio="2026-04-09", data_fine="2026-04-09", max_voci=2)
    assert r["num_voci"] == 5
    assert len(r["timeline"]) == 2
    assert r["troncato"] is True


def test_cronos_progetto_tool_registered():
    from mcp_cronos.server import TOOLS

    assert any(t.name == "cronos_progetto" for t in TOOLS)


def test_dossier_passthrough_without_registry(tmp_diario):
    # No cronos.toml -> pass-through: a raw project name still collects its entries.
    y = tmp_diario / "2026" / "04" / "2026-04-09"
    y.mkdir(parents=True, exist_ok=True)
    (y / "raw.md").write_text(
        "# T\n\n## Cosa ho fatto ieri\n\n### Backend API - x\n\na\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.dossier import dossier_progetto

    _reset_config()
    r = dossier_progetto("Backend API", data_inizio="2026-04-09", data_fine="2026-04-09")
    assert r["e_sistema"] is False
    assert r["num_voci"] == 1
    assert r["timeline"][0]["titolo"] == "Backend API - x"


def test_dossier_empty_result_no_crash(tmp_diario):
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.dossier import dossier_progetto

    _reset_config()
    r = dossier_progetto("Nonexistent", data_inizio="2026-04-09", data_fine="2026-04-09")
    assert r["num_voci"] == 0
    assert r["num_giorni"] == 0
    assert r["prima_data"] is None
    assert r["ultima_data"] is None
    assert r["timeline"] == []
    assert r["troncato"] is False


def test_dossier_max_voci_zero(tmp_diario):
    y = tmp_diario / "2026" / "04" / "2026-04-09"
    y.mkdir(parents=True, exist_ok=True)
    (y / "raw.md").write_text(
        "# T\n\n## Cosa ho fatto ieri\n\n### Backend API - x\n\na\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.dossier import dossier_progetto

    _reset_config()
    r = dossier_progetto(
        "Backend API", data_inizio="2026-04-09", data_fine="2026-04-09", max_voci=0
    )
    assert r["num_voci"] == 1
    assert r["timeline"] == []
    assert r["troncato"] is True


def test_dossier_composite_partial_match(tmp_diario):
    (tmp_diario / "cronos.toml").write_text(
        "[cronos]\ngit = false\n\n[cronos.projects.SmarTicket]\n\n[cronos.projects.Infomobile]\n",
        encoding="utf-8",
    )
    y = tmp_diario / "2026" / "04" / "2026-04-09"
    y.mkdir(parents=True, exist_ok=True)
    (y / "raw.md").write_text(
        "# T\n\n## Cosa ho fatto ieri\n\n### SmarTicket / Infomobile - shared\n\na\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.dossier import dossier_progetto

    _reset_config()
    r = dossier_progetto("SmarTicket", data_inizio="2026-04-09", data_fine="2026-04-09")
    assert r["num_voci"] == 1
    # only SmarTicket counted, not Infomobile, even though the heading is composite
    assert r["timeline"][0]["progetto"] == ["SmarTicket"]
    assert r["per_progetto"] == {"SmarTicket": 1}
