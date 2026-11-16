# Agent guide: {{PROJECT_NAME}}

> Managed by [android-agent-playbook](https://github.com/naveedali/android-agent-playbook) v{{VERSION}} · preset: **{{PRESET}}**.
> Add your own notes outside the `android-agent-playbook` markers. Re-run `android-agent-playbook install` to refresh this block.

This is an Android codebase. Work like a senior Android engineer on this team: make the smallest change that solves the task, follow the patterns already used in the module you touch, and prove the change works with Gradle before you call it done.

## Project map

{{PROJECT_MAP}}

## Stack

{{STACK}}

## Commands

Run Gradle from the repository root. Use module-scoped tasks while you iterate, then run the full checks before you finish.

{{COMMANDS}}

{{VARIANTS_NOTE}}

If a command fails, read the first error in the output, not the last line. Fix the cause and run it again. Do not stop with a broken build, and do not add `--offline`, `-x test`, `-x lint` or similar flags just to get past a failure.

## Architecture

{{ARCHITECTURE}}

{{PRESET_SECTION}}

## Modules

- Put code in the module that owns the feature. Only move code between modules when the task asks for it.
- A feature module must not depend on another feature module. Shared code goes in a `core` or `common` module.
- Respect `internal` and existing API boundaries. Do not widen visibility just to make something compile. Ask instead.
- Register new modules in `{{SETTINGS_FILE}}` and copy the setup of an existing module of the same kind{{BUILD_LOGIC_NOTE}}.

## Dependencies and the version catalog

{{CATALOG_RULES}}

## Testing

{{TESTING}}

## Never touch

Unless the user explicitly asks, do not edit, regenerate or commit changes to:

- `build/`, `.gradle/`, `.kotlin/`, `.idea/` and other generated output (`build/generated/`, KSP or kapt sources, `R`, `BuildConfig`)
- `local.properties`, `keystore.properties`, `*.jks`, `*.keystore`, `signingConfigs` blocks, and any secrets or API keys
- `google-services.json` and `GoogleService-Info.plist`
- `gradle/wrapper/` and the Gradle, Android Gradle Plugin and Kotlin versions (no upgrades)
- Lint and detekt baselines (`lint-baseline.xml`, `detekt-baseline.xml`). Fix the issue instead of adding it to a baseline.
{{EXTRA_NEVER_TOUCH}}
Never copy secrets from these files into chat, logs, commits or code.

## Done checklist

Before you say a task is complete:

{{DONE}}

## Playbooks

Step-by-step playbooks for common Android tasks live in `.agents/skills/`. When a request matches one, read its `SKILL.md` and follow it.

{{SKILLS_INDEX}}
