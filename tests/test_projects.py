"""Tests for mcp_cronos.utils.projects."""


def test_project_tokens_plain(tmp_diario):
    from mcp_cronos.utils.projects import project_tokens

    assert project_tokens("SmarTicket - Fix login") == ["SmarTicket"]


def test_project_tokens_emdash(tmp_diario):
    from mcp_cronos.utils.projects import project_tokens

    assert project_tokens("SmarTicket — Campo is_bookable (DVT-439)") == ["SmarTicket"]


def test_project_tokens_composite(tmp_diario):
    from mcp_cronos.utils.projects import project_tokens

    assert project_tokens("RapsodiaTrace / IoPollicino") == ["RapsodiaTrace", "IoPollicino"]


def test_project_tokens_keeps_internal_hyphen(tmp_diario):
    from mcp_cronos.utils.projects import project_tokens

    assert project_tokens("django-db-maintenance - release") == ["django-db-maintenance"]


def test_canonical_passthrough_when_no_registry(tmp_diario):
    from mcp_cronos.utils.projects import canonical_projects

    assert canonical_projects("SmarTicket — desc") == ["SmarTicket"]
    assert canonical_projects("A / B") == ["A", "B"]


def test_canonical_resolves_and_filters_with_registry(tmp_diario):
    (tmp_diario / "cronos.toml").write_text(
        '[cronos]\ngit = false\n\n'
        '[cronos.projects.SmarTicket]\nsistema = "Teseo"\nalias = ["BDI"]\n',
        encoding="utf-8",
    )
    from mcp_cronos.config import _reset_config
    from mcp_cronos.utils.projects import canonical_projects, system_of

    _reset_config()
    assert canonical_projects("smarticket - x") == ["SmarTicket"]
    assert canonical_projects("BDI - y") == ["SmarTicket"]
    assert canonical_projects("Totally Unknown Thing") == []
    assert system_of("SmarTicket") == "Teseo"
    assert system_of("SomethingElse") is None
