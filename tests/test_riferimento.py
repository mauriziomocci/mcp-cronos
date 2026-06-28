"""Tests for cronos_riferimento."""


def _reg(diario):
    (diario / "cronos.toml").write_text(
        "[cronos]\ngit = false\n\n"
        '[cronos.projects.SmarTicket]\nsistema = "Teseo"\n\n'
        '[cronos.projects.Infomobile]\nsistema = "Teseo"\n\n'
        "[cronos.projects.Goceano]\n",
        encoding="utf-8",
    )


def _day(diario, ymd, body):
    y, m, _ = ymd.split("-")
    p = diario / y / m / ymd
    p.mkdir(parents=True, exist_ok=True)
    (p / "raw.md").write_text(body, encoding="utf-8")


def test_riferimento_traces_ticket_across_projects(tmp_diario):
    _reg(tmp_diario)
    _day(
        tmp_diario,
        "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### SmarTicket - export\n\nlavoro su DVT-552 export.\n\n---\n\n"
        "### Goceano - altro\n\nniente di rilevante.\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
    )
    _day(
        tmp_diario,
        "2026-04-10",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### Infomobile - fix collegato\n\nfix per dvt-552 lato infomobile.\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.riferimento import traccia_riferimento

    _reset_config()
    r = traccia_riferimento("DVT-552", data_inizio="2026-04-01", data_fine="2026-04-30")

    assert r["num_voci"] == 2
    assert r["num_giorni"] == 2
    assert r["progetti"] == ["Infomobile", "SmarTicket"]
    assert r["sistemi"] == ["Teseo"]
    titoli = [v["titolo"] for v in r["timeline"]]
    assert "SmarTicket - export" in titoli
    assert "Infomobile - fix collegato" in titoli
    assert all("Goceano" not in t for t in titoli)
    assert r["timeline"] == sorted(r["timeline"], key=lambda v: v["data"])


def test_riferimento_empty_when_absent(tmp_diario):
    _reg(tmp_diario)
    _day(
        tmp_diario,
        "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n### SmarTicket - x\n\nniente.\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.riferimento import traccia_riferimento

    _reset_config()
    r = traccia_riferimento("NOPE-999", data_inizio="2026-04-01", data_fine="2026-04-30")
    assert r["num_voci"] == 0
    assert r["progetti"] == []
    assert r["sistemi"] == []
    assert r["timeline"] == []
    assert r["troncato"] is False


def test_riferimento_truncates(tmp_diario):
    _reg(tmp_diario)
    body = "# T\n\n## Cosa ho fatto ieri\n\n"
    for i in range(4):
        body += f"### SmarTicket - task {i}\n\ntocca DVT-1 qui.\n\n---\n\n"
    body += "## Bloccanti\n\nNessuno\n"
    _day(tmp_diario, "2026-04-08", body)
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.riferimento import traccia_riferimento

    _reset_config()
    r = traccia_riferimento("DVT-1", data_inizio="2026-04-01", data_fine="2026-04-30", max_voci=2)
    assert r["num_voci"] == 4
    assert len(r["timeline"]) == 2
    assert r["troncato"] is True


def test_cronos_riferimento_tool_registered():
    from mcp_cronos.server import TOOLS

    assert any(t.name == "cronos_riferimento" for t in TOOLS)


def test_riferimento_max_voci_zero_is_intentional(tmp_diario):
    # max_voci=0 -> empty timeline but num_voci/troncato still report the count.
    _reg(tmp_diario)
    _day(
        tmp_diario,
        "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n### SmarTicket - x\n\ntocca DVT-9 qui.\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.riferimento import traccia_riferimento

    _reset_config()
    r = traccia_riferimento("DVT-9", data_inizio="2026-04-01", data_fine="2026-04-30", max_voci=0)
    assert r["num_voci"] == 1
    assert r["timeline"] == []
    assert r["troncato"] is True
