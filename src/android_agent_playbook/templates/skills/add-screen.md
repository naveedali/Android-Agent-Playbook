---
name: add-screen
description: Add a new screen to this Android app (UI, ViewModel, state, navigation, preview and tests). Use when asked to create or add a screen, page or destination. Not for changing an existing screen.
---

# Add a screen

Read `AGENTS.md` first for this project's modules, commands and conventions.

## 1. Find the pattern

- Choose the module that owns the feature. If none fits and the screen is a new feature area, stop and suggest the `add-feature-module` playbook.
- Open the closest existing screen in that module and copy its structure: file layout, naming, ViewModel style (MVVM or MVI), DI and navigation registration. Consistency beats your personal preference.

## 2. State and ViewModel

- Define an immutable `FooUiState` (data class or sealed interface covering loading, content, empty and error as needed).
- Define user actions as functions or a sealed `FooEvent`, matching the existing style.
- Create `FooViewModel` that exposes `StateFlow<FooUiState>`, gets its dependencies through constructor injection, and launches work in `viewModelScope`. It must not reference `Context`, Views or composables.
- Reuse existing repositories and use cases. Add a new repository method only when nothing existing fits.

## 3. UI

- Compose: write a `FooScreen` that collects state with `collectAsStateWithLifecycle()`, and a stateless `FooContent(state, onEvent, modifier)`.
- Use theme tokens, `stringResource` and existing design-system components. Add new strings to `strings.xml`.
- Add `@Preview`s for the main states (content, loading, empty and error where they apply), plus a dark variant.

## 4. Wire it up

- Register the destination and route where the other destinations are registered. Pass IDs as navigation arguments, not objects.
- Add the entry point the task asks for (a button, menu item or deep link). Do not invent extra entry points.

## 5. Tests

- ViewModel unit test: initial state, a successful load and an error path, using fakes and `runTest`. Use Turbine if the project does.
- If the project has Compose UI tests, add one that renders `FooContent` with fake state and checks the key element and one interaction.

## 6. Verify

Run the module build, the module's unit tests and lint from `AGENTS.md`. Fix every failure, then go through the done checklist. In your summary, list the files you added, the commands you ran and anything you could not verify.
