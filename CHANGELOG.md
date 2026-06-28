# Changelog

All notable changes to mcp-cronos are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `cronos_riferimento`: project-aware cross-reference search — the timeline of
  every diary entry mentioning a given ticket/MR/repo, with the projects and
  systems it spans.

## [1.4.0] - 2026-06-27

### Added
- `cronos_statistiche`: work-distribution statistics over a period — entries and
  distinct days per project, per-system roll-up with a share percentage
  (including work tagged with the system's own name), and a per-month activity
  trend. Read-only, capped, proxy effort (no manual time tracking).

## [1.3.0] - 2026-06-27

### Added
- `cronos_progetto`: a read-only per-project or per-system dossier — chronological
  timeline, aggregated references, per-component breakdown on system roll-up, and
  the day-level blockers seen on days the project was worked. Capped output.

### Changed
- Dossier references are grouped into structured buckets
  (`repository`/`branch`/`jira`/`gitlab_mr`) plus an `altri` bucket for free-form
  labels, instead of a flat noisy list.

## [1.2.0] - 2026-06-27

### Added
- Optional two-level project registry `[cronos.projects]` (system -> component)
  in `cronos.toml`: read-time canonical project identity over the markdown diary,
  with automatic normalization (case/spacing/punctuation) and aliases. Empty by
  default — the tool works out of the box, the registry is an opt-in refinement.
- `cronos_audit_progetti`: clusters raw project names over a period and emits a
  ready-to-edit `[cronos.projects]` draft, so building the registry is simple.
- `cronos_lista_progetti` now aggregates by canonical project, groups by system,
  and caps its output.

### Changed
- Example project names in the shipped package (tool descriptions, docstrings,
  default templates, README) are now neutral placeholders — no
  customer/domain-specific identifiers ship in the public package.

### Fixed
- End of day now commits and pushes the whole diary (`git add -A`) after
  preparing the next day, instead of staging only the end-of-day file — the
  day's raw entries, todos and blockers are no longer left uncommitted.

## [1.1.0] - 2026-06-15

### Added
- Holiday-aware working-day calculation: the next/previous working day (used by
  `cronos_prepara_domani` and the standup) skips national holidays for the
  configured country plus user `extra_holidays`, in addition to weekends.
  Configurable via `[cronos.calendar]`.
- Git auto-detection of `repository` and `branch` from the working directory when
  not provided explicitly (optional `working_dir` parameter).
- `cronos_scrivi_fine_giornata` accepts an optional `contenuto_todo` to prepare
  the next working day in the same call.
- Internationalised `references` and `requested_by` diary labels.

### Changed
- Markdown entry parsing is fence-aware: `### ` or `---` lines inside fenced code
  blocks are no longer mistaken for entry boundaries (including nested fences).
- `cronos_cerca` accepts `max_risultati` (default 50) and reports truncation
  (`troncato`, `totale_risultati`).
- `cronos_leggi_diario` range output is compact: missing days are summarised in
  `riepilogo.date_mancanti` instead of a stub per day.
- `paragrafo_intro` is now optional when adding an entry.

### Fixed
- Diary labels (`references`, `requested_by`) honour the configured language while
  still parsing diaries written with the Italian defaults (no data migration).
- README and CLAUDE.md aligned with the actual registered tools and the per-day
  folder layout.

## [1.0.0] - 2026-04-09

### Added
- Initial public release: structured daily work-diary MCP server — add entries,
  read by date/range, standup summary, blockers, end-of-day workflow,
  consolidation, list projects, full-text search, weekly report, append to an
  existing project entry, write the end-of-day file, todo and month views.
- Per-day folder layout (`raw.md`, `fine-giornata.md`, `todo.md`) with legacy
  single-file support; Italian/English i18n; automatic git commit/push at end of
  day.

[Unreleased]: https://github.com/mauriziomocci/mcp-cronos/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/mauriziomocci/mcp-cronos/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/mauriziomocci/mcp-cronos/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/mauriziomocci/mcp-cronos/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/mauriziomocci/mcp-cronos/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/mauriziomocci/mcp-cronos/releases/tag/v1.0.0
