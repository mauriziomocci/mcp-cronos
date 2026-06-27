"""Tests for cronos_audit_progetti."""


def test_audit_clusters_and_drafts_registry(tmp_diario):
    month = tmp_diario / "2026" / "04"
    month.mkdir(parents=True, exist_ok=True)
    (month / "2026-04-09.md").write_text(
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### PayGW - a\n\nx\n\n---\n\n### PayGw - b\n\ny\n\n---\n\n"
        "### Prossimi passi\n\nz\n\n---\n\n## Bloccanti\n\nNessuno\n",
        encoding="utf-8",
    )
    from mcp_cronos.tools.audit_progetti import audit_progetti

    result = audit_progetti(data_inizio="2026-04-09", data_fine="2026-04-09")

    clusters = {c["chiave"]: c for c in result["cluster"]}
    assert "paygw" in clusters
    assert clusters["paygw"]["occorrenze"] == 2
    assert set(clusters["paygw"]["varianti"]) == {"PayGW", "PayGw"}
    assert "[cronos.projects." in result["bozza_toml"]
    assert "totale_nomi_grezzi" in result
