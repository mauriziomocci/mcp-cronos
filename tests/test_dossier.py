"""Tests for cronos_progetto (project dossier)."""


def _write_registry(diario):
    (diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n'
        '[cronos.projects.Teseo]\n\n'
        '[cronos.projects.SmarTicket]\nsistema = "Teseo"\n\n'
        '[cronos.projects.Infomobile]\nsistema = "Teseo"\n\n'
        '[cronos.projects.Goceano]\n',
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
        tmp_diario, "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### SmarTicket - Fix login\n\nFixed.\n\n**Riferimenti:**\n- Repository: st-backend\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
    )
    _write_day(
        tmp_diario, "2026-04-09",
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
        tmp_diario, "2026-04-09",
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
