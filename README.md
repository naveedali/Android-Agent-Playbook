# android-agent-playbook

**Make AI coding agents work like an experienced Android engineer.**

One command drops Android-specific rules and task playbooks into your repo so Claude Code, Codex, Cursor and GitHub Copilot use the right Gradle commands, respect module boundaries and the version catalog, write previews and tests, leave generated and secret files alone, and don't stop with a broken build.

```bash
pipx install android-agent-playbook
cd your-android-project
android-agent-playbook install --dry-run   # see what it would write
android-agent-playbook install
```

> Status: v0.1.0, early. Not on PyPI yet. Until it is, install from GitHub:
> `pipx install git+https://github.com/naveedali/android-agent-playbook`

<!-- TODO: before/after demo GIF: the same "add a settings screen" prompt with and without the playbook -->

## Why

Agents on Android projects keep making the same mistakes:

- editing generated code, `build/` output, `local.properties` or signing config
- breaking the build and stopping without running Gradle
- ignoring module boundaries and `libs.versions.toml`
- mixing View and Compose patterns, skipping previews and tests

Every team ends up writing its own `AGENTS.md` from scratch. This project gives you a solid, Android-specific starting point that fills itself in from your Gradle setup.

## What it does

`install` reads your Gradle files (no Gradle run needed) and detects:

- Kotlin or Groovy DSL, the module list and each module's type, and convention plugins (`build-logic/`, `buildSrc/`)
- Compose, XML Views and View Binding, Kotlin Multiplatform, Compose Multiplatform
- Hilt or Koin, Room or SQLDelight, coroutines, Navigation, KSP and kapt
- test libraries (JUnit 4/5, MockK, Mockito, Turbine, Robolectric, Compose UI test, and more), ktlint, detekt and Spotless

Then it writes these files with your project's real commands filled in:

| File | Read by | What's in it |
| --- | --- | --- |
| `AGENTS.md` | Codex, Cursor, Copilot and most other agents | Project map, stack, build/test/lint commands, architecture, preset conventions, module rules, version catalog rules, testing, never-touch list, done checklist |
| `.agents/skills/<name>/SKILL.md` | Codex (native), and every agent through `AGENTS.md` | The five task playbooks below |
| `CLAUDE.md` | Claude Code | Imports `AGENTS.md` with `@AGENTS.md` |
| `.claude/commands/<name>.md` | Claude Code | `/add-screen` and the other commands, which run the matching playbook |
| `.cursor/rules/android-agent-playbook.mdc` | Cursor | Always-on pointer to `AGENTS.md`, plus the check commands |
| `.cursor/commands/<name>.md` | Cursor | The same five commands |
| `.github/copilot-instructions.md` | GitHub Copilot | Pointer to `AGENTS.md`, plus the key rules |

Pick agents with `--agents claude,codex,cursor,copilot` (default: all).

See [`examples/`](examples/) for the generated files on a Compose + Hilt app, a legacy Views app and a KMP project.

### Playbooks and commands

| Command | Does |
| --- | --- |
| `/add-screen` | New screen: UI state, ViewModel, stateless content composable, previews, navigation and tests, following the closest existing screen |
| `/add-feature-module` | New `:feature:x` module wired into settings, DI, navigation and the catalog, using your convention plugins |
| `/migrate-to-compose` | One XML screen to Compose with the same behavior: inventory first, ViewModel kept, interop, previews, tests |
| `/write-tests` | Unit and UI tests with your existing stack (`runTest`, fakes, Turbine, Compose test rule, in-memory Room) |
| `/fix-build` | Reproduce, find the first real error, classify it, apply a minimal fix and re-run, without skipping tests or editing generated code |

In Codex, ask for the playbook by name ("use the add-screen skill to…"). Codex also picks skills up from `.agents/skills/` on its own.

### Presets

The preset is chosen automatically. Override it with `--preset`.

| Preset | Picked when | Adds |
| --- | --- | --- |
| `compose` | Compose, no XML layouts | Compose conventions: screen/content split, state hoisting, `collectAsStateWithLifecycle`, previews, theming, performance, accessibility |
| `views-compose` | XML layouts or View Binding found | Migration rules: new UI in Compose, interop via `ComposeView`/`AndroidView`, don't rewrite XML as a side effect, one shared theme |
| `kmp` | Kotlin Multiplatform modules | `commonMain` first, expect/actual sparingly, source-set rules, multiplatform-only dependencies, `kotlin.test`, iOS verification caveats |

## Safe to re-run

Everything the tool writes sits between markers:

```markdown
<!-- android-agent-playbook:start -->
…managed content…
<!-- android-agent-playbook:end -->
```

- Re-running `install` replaces only what's between the markers. Your own text above or below is kept.
- If you already have an `AGENTS.md`, `CLAUDE.md` or `copilot-instructions.md`, the block is appended. Nothing is overwritten.
- If a file the tool would own (for example `.claude/commands/add-screen.md`) already exists without markers, it's skipped and reported.
- Unbalanced markers are reported as an error and the file is left alone.
- `--dry-run` shows the plan, and `--diff` shows the exact changes.

Put team-specific rules **outside** the block in `AGENTS.md`, and fill in the `TODO` lines (what each module owns) after the first install.

## CLI

```text
android-agent-playbook detect [PATH] [--json]
android-agent-playbook install [PATH] [--preset auto|compose|views-compose|kmp]
                                      [--agents claude,codex,cursor,copilot]
                                      [--dry-run] [--diff] [--force]
android-agent-playbook uninstall [PATH] [--dry-run] [--diff]
```

`aap` is a short alias for `android-agent-playbook`. It's zero-dependency Python 3.8+, and needs no Gradle, JDK or Android SDK.

`uninstall` removes the managed blocks and deletes files that only contained a block. Files you added text to are kept.

## Roadmap

- v0.1: rules, five playbooks, installer, three presets (this release)
- Validate on real projects, starting with an Android Compose app, then a legacy Views app and a KMP app
- Next: a Gradle output trimmer so agents see the first real error, and an Android build/emulator MCP server

## Related

[Agent Ledger](https://github.com/naveedali/Agent-Ledger) tracks what your AI agents did each day. Use this playbook to make agents work like Android engineers, and Agent Ledger to track what they did.

## Contributing

New presets and better playbooks are very welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
