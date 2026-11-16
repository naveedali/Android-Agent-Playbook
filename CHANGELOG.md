# Changelog

## 0.2.0 (2026-11-16)

- CI runs on `master` (and `main`), and checks that `examples/` is up to date
- Release workflow: tag `v*` publishes to PyPI with trusted publishing and creates a GitHub release
- `examples/` with generated output for each fixture project, via `scripts/generate_examples.py`
- Product flavor detection (Kotlin and Groovy DSL, multiple dimensions, `isDefault`). Commands now use a real variant such as `assembleDevDebug`, `:app:testDevDebugUnitTest` and `lintDevDebug`, and `AGENTS.md` gets a Build variants section. Flavors configured only in convention plugins are flagged with a TODO
- Stack section now lists minSdk, targetSdk and compileSdk (with a reminder to guard newer APIs), plus Gradle, AGP, Kotlin, JDK and Compose BOM versions read from the catalog, build files and Gradle wrapper
- KMP and JVM modules use `allTests` and `test` in the per-module test command

## 0.1.0 (2026-11-11)

- `install`, `detect` and `uninstall` commands with marker-based, re-runnable injection, `--dry-run` and `--diff`
- Stack detection from Gradle files: DSL, modules, convention plugins, Compose/Views/KMP, Hilt/Koin, Room/SQLDelight, test and lint tooling
- `AGENTS.md` template with project map, commands, architecture, module, catalog, testing, never-touch and done-checklist sections
- Presets: `compose`, `views-compose`, `kmp`
- Playbooks as Agent Skills: `add-screen`, `add-feature-module`, `migrate-to-compose`, `write-tests`, `fix-build`
- First-class Claude Code, Codex and Cursor support; Copilot pointer file
