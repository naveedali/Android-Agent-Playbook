---
name: add-feature-module
description: Create a new Gradle feature module (e.g. :feature:settings) wired into settings, DI, navigation and the version catalog. Use when asked to add a new module or split a feature into its own module.
---

# Add a feature module

Read `AGENTS.md` first for the module list, build setup and commands.

## 1. Decide the shape

- Confirm the name and location from the existing layout (for example `:feature:<name>` in `feature/<name>/`). Follow the naming used by existing modules exactly.
- Decide which modules the new one depends on, normally only `core`/`common` modules. A feature module must never depend on another feature module. If the task seems to need that, stop and propose moving the shared code into a core module.

## 2. Create the module

- Copy the build file of the most similar existing feature module, then strip it down to what the new module needs.
- If the project has convention plugins (`build-logic/` or `buildSrc/`), apply them instead of configuring Android, Kotlin, Compose or Hilt by hand.
- Set a `namespace` that follows the existing pattern.
- Add only the dependencies the module uses, through the version catalog. Do not add libraries that are not already in the catalog without saying so.
- Create the source folders that existing modules have (`src/main/kotlin` or `src/main/java`, `src/test`, and so on). Add a minimal `AndroidManifest.xml` only if other library modules have one.

## 3. Register and wire

- Add `include(":feature:<name>")` to the settings file, next to its siblings.
- Add the dependency from the app module (or the navigation host module) the same way other features are added.
- Expose the feature's navigation entry point (route plus graph builder, or a Fragment destination) the way other features do. Keep implementation details `internal`.
- Add a DI module if the feature provides bindings, following the existing pattern.

## 4. Seed it

- Add the first screen with the `add-screen` playbook if the task includes one. Otherwise add a placeholder screen only if asked.
- Add at least one unit test so the module's test task actually runs something.

## 5. Verify

- Run a Gradle sync-equivalent build: `./gradlew :feature:<name>:assembleDebug` (or `:build` for non-Android modules).
- Run the app build, the new module's tests and lint from `AGENTS.md`.
- If the project has a dependency-graph or module check task, run it too.

Summarize the module path, its dependencies, how it is registered and the commands you ran.
