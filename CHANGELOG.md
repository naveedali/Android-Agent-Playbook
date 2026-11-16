# Changelog

## Unreleased

- CI runs on `master` (and `main`), and checks that `examples/` is up to date
- Release workflow: tag `v*` publishes to PyPI with trusted publishing and creates a GitHub release
- `examples/` with generated output for each fixture project, via `scripts/generate_examples.py`

## 0.1.0 (unreleased)

- `install`, `detect` and `uninstall` commands with marker-based, re-runnable injection, `--dry-run` and `--diff`
- Stack detection from Gradle files: DSL, modules, convention plugins, Compose/Views/KMP, Hilt/Koin, Room/SQLDelight, test and lint tooling
- `AGENTS.md` template with project map, commands, architecture, module, catalog, testing, never-touch and done-checklist sections
- Presets: `compose`, `views-compose`, `kmp`
- Playbooks as Agent Skills: `add-screen`, `add-feature-module`, `migrate-to-compose`, `write-tests`, `fix-build`
- First-class Claude Code, Codex and Cursor support; Copilot pointer file
