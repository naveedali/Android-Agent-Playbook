# Contributing

Thanks for helping make AI agents better Android engineers.

## Setup

No dependencies are needed beyond Python 3.8+.

```bash
git clone https://github.com/naveedali/android-agent-playbook
cd android-agent-playbook
PYTHONPATH=src python -m unittest discover -s tests -t .
PYTHONPATH=src python -m android_agent_playbook install --dry-run --diff /path/to/an/android/project
```

## Layout

```text
src/android_agent_playbook/
  cli.py                      detection, rendering, marker-block install/uninstall
  templates/agents/base.md    AGENTS.md skeleton with {{PLACEHOLDERS}}
  templates/agents/presets/   one file per preset, inserted as {{PRESET_SECTION}}
  templates/skills/           one SKILL.md per playbook (frontmatter + body)
tests/
  fixtures.py                 tiny fake Android projects
```

## Adding a preset

1. Add `templates/agents/presets/<name>.md`. Start it with a `## Heading` and keep it to rules an agent can act on. Every bullet should change behavior.
2. Add `<name>` to `PRESETS` in `cli.py`. If it should be picked automatically, extend `suggest_preset()` and, if needed, `FEATURE_PATTERNS`.
3. Add a fixture in `tests/fixtures.py` and a detection test in `tests/test_detect.py`. `test_every_preset_renders_without_placeholders` covers rendering automatically.
4. Update the presets table in `README.md`.

## Adding or changing a playbook

- Playbooks live in `templates/skills/<name>.md` as [Agent Skills](https://agentskills.io) (`name` + `description` frontmatter). The description decides when agents pick the skill, so say when to use it and when not to.
- Write numbered phases with concrete actions, and always end with a **Verify** step that runs commands from `AGENTS.md`.
- Refer to `AGENTS.md` for project-specific commands rather than hardcoding Gradle tasks.
- Add the name to `SKILLS` and `ARG_HINTS` in `cli.py`. The Claude Code and Cursor command wrappers are generated from it.

## Rules for the installer

- Standard library only, and Python 3.8 compatible (no `X | Y` types, no `str.removeprefix`).
- Never write outside the marker block in a file that already exists.
- Every behavior change needs a test.

## Pull requests

Use one branch per change, with a short description of what changed and how you tested it. If you can, include the before/after of a real agent run.
