"""Tests for cronos_igiene."""

from datetime import date


def _reg(diario):
    (diario / "cronos.toml").write_text(
        "[cronos]\ngit = false\n\n"
        '[cronos.projects.SmarTicket]\nsistema = "Teseo"\n\n'
        "[cronos.projects.Goceano]\n",
        encoding="utf-8",
    )


def _no_reg(diario):
    (diario / "cronos.toml").write_text("[cronos]\ngit = false\n", encoding="utf-8")


def _day(diario, ymd, body, fine=False):
    y, m, _ = ymd.split("-")
    p = diario / y / m / ymd
    p.mkdir(parents=True, exist_ok=True)
    (p / "raw.md").write_text(body, encoding="utf-8")
    if fine:
        (p / "fine-giornata.md").write_text("# chiusura\n", encoding="utf-8")


def test_voci_non_mappate_aggregato(tmp_diario):
    """Una sola voce aggregata (tipo voci_non_mappate) per tutte le voci fuori registro."""
    _reg(tmp_diario)
    _day(
        tmp_diario,
        "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### SmarTicket - ok\n\nlavoro registrato.\n\n---\n\n"
        "### SconosciutoA - y\n\nniente.\n\n---\n\n"
        "### SconosciutoB - y\n\nniente.\n\n---\n\n"
        "### SconosciutoC - y\n\nniente.\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        fine=True,
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.igiene import igiene_diario

    _reset_config()
    result = igiene_diario(data_inizio="2026-04-08", data_fine="2026-04-08")

    # Exactly ONE aggregated finding
    voci_probs = [p for p in result["problemi"] if p["tipo"] == "voci_non_mappate"]
    assert len(voci_probs) == 1

    prob = voci_probs[0]
    assert prob["gravita"] == "avviso"
    assert prob["voci"] == 3
    assert prob["giorni"] == 1
    assert len(prob["esempi"]) >= 1

    # SmarTicket is registered — must NOT appear in esempi
    assert not any("SmarTicket" in e for e in prob["esempi"])

    # conteggi counts list items per tipo: one aggregated item = 1
    assert result["conteggi"]["voci_non_mappate"] == 1

    # riepilogo should mention voci fuori registro
    assert "voci fuori registro" in result["riepilogo"]


def test_nessuna_voce_non_mappata_quando_tutto_registrato(tmp_diario):
    """Nessun problema voci_non_mappate quando tutte le voci sono nel registro."""
    _reg(tmp_diario)
    _day(
        tmp_diario,
        "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### SmarTicket - x\n\nlavoro.\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        fine=True,
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.igiene import igiene_diario

    _reset_config()
    result = igiene_diario(data_inizio="2026-04-08", data_fine="2026-04-08")

    voci_probs = [p for p in result["problemi"] if p["tipo"] == "voci_non_mappate"]
    assert len(voci_probs) == 0


def test_registro_vuoto_salta_check(tmp_diario):
    _no_reg(tmp_diario)
    _day(
        tmp_diario,
        "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### Sconosciuto - y\n\nniente.\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        fine=True,
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.igiene import igiene_diario

    _reset_config()
    result = igiene_diario(data_inizio="2026-04-08", data_fine="2026-04-08")

    # No voci_non_mappate when registry is empty
    assert result["conteggi"]["voci_non_mappate"] == 0
    assert result["registro_attivo"] is False
    # Note should mention skipped check
    assert any("registro vuoto" in n for n in result["note"])


def test_fence_non_chiusa_critico(tmp_diario):
    _reg(tmp_diario)
    # Day with unclosed fence
    _day(
        tmp_diario,
        "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### SmarTicket - x\n\n```\ncode without close\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        fine=True,
    )
    # Clean day (no fence issues)
    _day(
        tmp_diario,
        "2026-04-09",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### SmarTicket - y\n\nniente.\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        fine=True,
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.igiene import igiene_diario

    _reset_config()

    # Test the unclosed-fence day
    r1 = igiene_diario(data_inizio="2026-04-08", data_fine="2026-04-08")
    fence_probs = [p for p in r1["problemi"] if p["tipo"] == "fence_non_chiusa"]
    assert len(fence_probs) == 1
    assert fence_probs[0]["gravita"] == "critico"
    assert fence_probs[0]["data"] == "2026-04-08"

    # Test the clean day — no fence problems
    _reset_config()
    r2 = igiene_diario(data_inizio="2026-04-09", data_fine="2026-04-09")
    assert r2["conteggi"]["fence_non_chiusa"] == 0


def test_giorno_lavorativo_mancante(tmp_diario):
    _reg(tmp_diario)
    # No days written at all; window: Wed 2026-04-08 .. Sun 2026-04-12
    # Working days in that range (no Italian national holiday): Wed/Thu/Fri = 3
    from mcp_cronos.config import _reset_config
    from mcp_cronos.utils.workdays import is_working_day

    _reset_config()

    # Pre-condition assertions (if any turns out to be a holiday, the test would
    # need adjusted dates; these guard against that).
    assert is_working_day(date(2026, 4, 8))  # Wednesday
    assert is_working_day(date(2026, 4, 9))  # Thursday
    assert is_working_day(date(2026, 4, 10))  # Friday
    assert not is_working_day(date(2026, 4, 11))  # Saturday
    assert not is_working_day(date(2026, 4, 12))  # Sunday

    from mcp_cronos.tools.igiene import igiene_diario

    _reset_config()
    result = igiene_diario(data_inizio="2026-04-08", data_fine="2026-04-12")
    assert result["conteggi"]["giorno_lavorativo_mancante"] == 3


def test_chiusura_mancante_solo_layout_nuovo(tmp_diario):
    _reg(tmp_diario)
    # Day without fine-giornata
    _day(
        tmp_diario,
        "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### SmarTicket - x\n\nniente.\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        fine=False,
    )
    # Day with fine-giornata
    _day(
        tmp_diario,
        "2026-04-09",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### SmarTicket - y\n\nniente.\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
        fine=True,
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.igiene import igiene_diario

    _reset_config()
    result = igiene_diario(data_inizio="2026-04-08", data_fine="2026-04-09")

    chiusura_probs = [p for p in result["problemi"] if p["tipo"] == "chiusura_mancante"]
    # Only 2026-04-08 should be flagged
    assert len(chiusura_probs) == 1
    assert chiusura_probs[0]["data"] == "2026-04-08"
    assert chiusura_probs[0]["gravita"] == "info"


def test_cap_e_conteggi_totali(tmp_diario):
    """Cap applicato a un check per-occorrenza (giorno_lavorativo_mancante)."""
    _reg(tmp_diario)
    # No diary files written; window Wed-Fri 2026-04-08..2026-04-10 (3 missing working days)
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.igiene import igiene_diario

    _reset_config()
    result = igiene_diario(data_inizio="2026-04-08", data_fine="2026-04-10", max_problemi=1)

    assert len(result["problemi"]) <= 1
    assert result["troncato"] is True
    assert result["totale_problemi"] >= 2
    assert result["conteggi"]["giorno_lavorativo_mancante"] >= 2


def test_riepilogo_umano(tmp_diario):
    _reg(tmp_diario)
    # Weekend-only window: Sat+Sun 2026-04-11..2026-04-12; no diary files
    # -> no missing working days, no diary files to scan -> 0 problems
    from mcp_cronos.config import _reset_config
    from mcp_cronos.tools.igiene import igiene_diario

    _reset_config()
    result = igiene_diario(data_inizio="2026-04-11", data_fine="2026-04-12")

    assert result["riepilogo"] == "Nessun problema rilevato nel periodo."
    assert result["totale_problemi"] == 0
