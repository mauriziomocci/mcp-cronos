"""Tests for the shared diary scanner."""

from datetime import date


def _day(diario, ymd, body):
    y, m, _ = ymd.split("-")
    p = diario / y / m / ymd
    p.mkdir(parents=True, exist_ok=True)
    (p / "raw.md").write_text(body, encoding="utf-8")


def test_iter_diary_days_yields_entries_and_skips_missing(tmp_diario):
    _day(
        tmp_diario,
        "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### SmarTicket - a\n\nbody A\n\n---\n\n"
        "### Infomobile - b\n\nbody B\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
    )
    from mcp_cronos.utils.scan import iter_diary_days

    days = list(iter_diary_days(date(2026, 4, 8), date(2026, 4, 9)))
    assert len(days) == 1
    d, content, entries = days[0]
    assert str(d) == "2026-04-08"
    assert "## Bloccanti" in content
    headings = [h for h, _ in entries]
    assert headings == ["SmarTicket - a", "Infomobile - b"]
    bodies = [b for _, b in entries]
    assert "body A" in bodies[0]
    assert "body B" in bodies[1]


def test_iter_diary_days_fence_aware(tmp_diario):
    _day(
        tmp_diario,
        "2026-04-08",
        "# T\n\n## Cosa ho fatto ieri\n\n"
        "### Real - x\n\n```\n### not a heading\n```\n\n---\n\n"
        "## Bloccanti\n\nNessuno\n",
    )
    from mcp_cronos.utils.scan import iter_diary_days

    _d, _c, entries = next(iter(iter_diary_days(date(2026, 4, 8), date(2026, 4, 8))))
    assert [h for h, _ in entries] == ["Real - x"]
