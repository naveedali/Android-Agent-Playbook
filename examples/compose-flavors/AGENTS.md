<!-- android-agent-playbook:start -->
# Agent guide: Shopper

> Managed by [android-agent-playbook](https://github.com/naveedali/android-agent-playbook) v0.1.0 · preset: **compose**.
> Add your own notes outside the `android-agent-playbook` markers. Re-run `android-agent-playbook install` to refresh this block.

This is an Android codebase. Work like a senior Android engineer on this team: make the smallest change that solves the task, follow the patterns already used in the module you touch, and prove the change works with Gradle before you call it done.

## Project map

- `:app` (`app/`): Android app
- `:core:network` (`core/network/`): Android library

TODO: add one line per module describing what it owns, so agents put code in the right place.

## Stack

- UI: Jetpack Compose
- DI: constructor injection, no DI framework detected
- Android: minSdk 24, compileSdk 35. Guard APIs above minSdk with `Build.VERSION.SDK_INT` checks
- Build: Gradle Kotlin DSL
- Tests: JUnit 4

## Commands

Run Gradle from the repository root. Use module-scoped tasks while you iterate, then run the full checks before you finish.

| Purpose | Command |
| --- | --- |
| Build (debug) | `./gradlew :app:assembleDevDebug` |
| Unit tests | `./gradlew :app:testDevDebugUnitTest testDebugUnitTest` |
| One module's tests | `./gradlew :core:network:testDebugUnitTest` |
| Lint | `./gradlew :app:lintDevDebug` |
| Instrumented tests (needs a device; only when asked) | `./gradlew :app:connectedDevDebugAndroidTest` |
| Dependencies of a module | `./gradlew :app:dependencies --configuration devDebugRuntimeClasspath` |

### Build variants

- `:app` has product flavors `prod`, `dev` (dimension `env`). Commands use the `devDebug` variant. Build other flavors or release variants only when asked.

If a command fails, read the first error in the output, not the last line. Fix the cause and run it again. Do not stop with a broken build, and do not add `--offline`, `-x test`, `-x lint` or similar flags just to get past a failure.

## Architecture

- Layers: UI → ViewModel (state holder) → use cases (optional) → repositories → data sources. Dependencies point inward, and UI never talks to data sources directly.
- Unidirectional data flow: a ViewModel exposes one immutable `StateFlow<UiState>` and receives user actions as function calls or events. Match the style (MVVM or MVI) already used in the module you touch, and do not introduce a new one.
- ViewModels never hold `Context`, Views, composables or Activity references.
- Use constructor injection and follow the existing wiring. Do not add a DI framework unless asked.
- Errors: map exceptions to domain results at the repository boundary, and show errors through `UiState`. Do not swallow exceptions or catch `CancellationException`.

## Jetpack Compose

All UI is written in Compose. Do not add XML layouts, Fragments or View-based widgets.

- **Screen and content split.** Write a `FooRoute`/`FooScreen` that gets the ViewModel and collects its state, plus a stateless `FooContent(state, onEvent, modifier)` that only renders. Previews and UI tests target the stateless one.
- **State hoisting.** Composables receive state and callbacks as parameters. Keep state as low as possible, but hoist it to the lowest common owner when siblings share it. Do not pass a ViewModel into child composables.
- **Collecting state.** Use `collectAsStateWithLifecycle()` for flows. Do not use `collectAsState()` in Android UI code.
- **Modifiers.** Every public composable that emits UI takes `modifier: Modifier = Modifier` as its first optional parameter and applies it to the root element only.
- **Previews.** Every new or changed screen and reusable component gets at least one `@Preview` with representative data, plus light and dark variants for screens. Previews call the stateless composable with fake state and never touch a ViewModel, network or database.
- **Theming.** Use `MaterialTheme.colorScheme`, `MaterialTheme.typography` and the project's theme or design-system tokens. Do not hardcode colors, text sizes or fonts. Put user-visible strings in `strings.xml` and read them with `stringResource`.
- **Performance.** Give `LazyColumn`/`LazyRow` items stable `key`s. Use `remember` and `derivedStateOf` for derived values. Make state classes immutable (`val`, immutable collections) so recomposition can skip.
- **Side effects.** Use `LaunchedEffect`, `DisposableEffect` and `rememberCoroutineScope` correctly. Never start coroutines or do I/O directly in a composable body.
- **Navigation.** Follow the navigation setup already in the project. Register new destinations where existing ones are registered, and pass IDs, not whole objects.
- **Accessibility.** Give icons and images a `contentDescription` (or `null` if decorative), keep touch targets at least 48dp, and avoid conveying meaning by color alone.

## Modules

- Put code in the module that owns the feature. Only move code between modules when the task asks for it.
- A feature module must not depend on another feature module. Shared code goes in a `core` or `common` module.
- Respect `internal` and existing API boundaries. Do not widen visibility just to make something compile. Ask instead.
- Register new modules in `settings.gradle.kts` and copy the setup of an existing module of the same kind.

## Dependencies and the version catalog

- This project does not use a version catalog. Declare dependencies the way existing build files do, and do not introduce a catalog unless asked.
- Before adding a library, check whether an existing dependency or the platform already covers the need. List every new dependency in your summary.
- Do not upgrade existing versions unless the task asks for it.

## Testing

- Every new ViewModel, use case and repository function gets unit tests in the module's `src/test` (or `commonTest` for shared KMP code). Every bug fix gets a regression test.
- Use `runTest` from coroutines-test and replace `Dispatchers.Main` with a test dispatcher rule.
- Prefer hand-written fakes over mocks.
- Compose UI tests target the stateless content composable with `createComposeRule()`.
- Never delete, `@Ignore` or weaken a failing test to get a green build. Fix the code, or explain why the test is wrong.

## Never touch

Unless the user explicitly asks, do not edit, regenerate or commit changes to:

- `build/`, `.gradle/`, `.kotlin/`, `.idea/` and other generated output (`build/generated/`, KSP or kapt sources, `R`, `BuildConfig`)
- `local.properties`, `keystore.properties`, `*.jks`, `*.keystore`, `signingConfigs` blocks, and any secrets or API keys
- `google-services.json` and `GoogleService-Info.plist`
- `gradle/wrapper/` and the Gradle, Android Gradle Plugin and Kotlin versions (no upgrades)
- Lint and detekt baselines (`lint-baseline.xml`, `detekt-baseline.xml`). Fix the issue instead of adding it to a baseline.

Never copy secrets from these files into chat, logs, commits or code.

## Done checklist

Before you say a task is complete:

- [ ] `./gradlew :app:assembleDevDebug` succeeds
- [ ] Unit tests pass for every module you touched (`./gradlew :app:testDevDebugUnitTest testDebugUnitTest`, or the module-scoped task)
- [ ] `./gradlew :app:lintDevDebug` reports no new issues
- [ ] Every new or changed composable screen and component has a `@Preview`
- [ ] New logic has tests, and no existing test was deleted, ignored or weakened
- [ ] Dependencies go through the existing build files, and nothing in the Never touch list changed
- [ ] Your summary lists the commands you ran with their results, and anything you could not verify (for example instrumented tests that need a device)

## Playbooks

Step-by-step playbooks for common Android tasks live in `.agents/skills/`. When a request matches one, read its `SKILL.md` and follow it.

- `add-screen` (`.agents/skills/add-screen/SKILL.md`): Add a new screen to this Android app (UI, ViewModel, state, navigation, preview and tests). Use when asked to create or add a screen, page or destination. Not for changing an existing screen.
- `add-feature-module` (`.agents/skills/add-feature-module/SKILL.md`): Create a new Gradle feature module (e.g. :feature:settings) wired into settings, DI, navigation and the version catalog. Use when asked to add a new module or split a feature into its own module.
- `migrate-to-compose` (`.agents/skills/migrate-to-compose/SKILL.md`): Migrate one XML/View screen or component to Jetpack Compose without changing behavior. Use when asked to convert, migrate or rewrite a layout, Fragment or custom View in Compose.
- `write-tests` (`.agents/skills/write-tests/SKILL.md`): Write or extend unit and UI tests for Android code (ViewModels, repositories, use cases, Room DAOs, composables) using the project's existing test stack. Use when asked to add tests, improve coverage or test a specific class.
- `fix-build` (`.agents/skills/fix-build/SKILL.md`): Diagnose and fix a failing Gradle build, compile error, test failure or lint error in this Android project. Use when the build is red, Gradle sync fails, or a task like assembleDebug, test or lint fails.
<!-- android-agent-playbook:end -->
