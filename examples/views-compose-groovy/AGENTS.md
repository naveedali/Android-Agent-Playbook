<!-- android-agent-playbook:start -->
# Agent guide: LegacyShop

> Managed by [android-agent-playbook](https://github.com/naveedali/Android-Agent-Playbook) v0.2.0 · preset: **views-compose**.
> Add your own notes outside the `android-agent-playbook` markers. Re-run `android-agent-playbook install` to refresh this block.

This is an Android codebase. Work like a senior Android engineer on this team: make the smallest change that solves the task, follow the patterns already used in the module you touch, and prove the change works with Gradle before you call it done.

## Project map

- `:app` (`app/`): Android app
- `:feature:cart` (`feature/cart/`): Android library

TODO: add one line per module describing what it owns, so agents put code in the right place.

## Stack

- UI: Jetpack Compose + XML Views with View Binding
- DI: Koin
- Android: minSdk 21, targetSdk 34, compileSdk 34. Guard APIs above minSdk with `Build.VERSION.SDK_INT` checks
- Toolchain: AGP 7.4.2, JDK 8
- Build: Gradle Groovy DSL
- Code generation: kapt
- Tests: JUnit 4, Mockito

## Commands

Run Gradle from the repository root. Use module-scoped tasks while you iterate, then run the full checks before you finish.

| Purpose | Command |
| --- | --- |
| Build (debug) | `./gradlew :app:assembleDebug` |
| Unit tests | `./gradlew testDebugUnitTest` |
| One module's tests | `./gradlew :feature:cart:testDebugUnitTest` |
| Lint | `./gradlew :app:lintDebug` |
| Instrumented tests (needs a device; only when asked) | `./gradlew :app:connectedDebugAndroidTest` |
| Dependencies of a module | `./gradlew :app:dependencies --configuration debugRuntimeClasspath` |

If a command fails, read the first error in the output, not the last line. Fix the cause and run it again. Do not stop with a broken build, and do not add `--offline`, `-x test`, `-x lint` or similar flags just to get past a failure.

## Architecture

- Layers: UI → ViewModel (state holder) → use cases (optional) → repositories → data sources. Dependencies point inward, and UI never talks to data sources directly.
- Unidirectional data flow: a ViewModel exposes one immutable `StateFlow<UiState>` and receives user actions as function calls or events. Match the style (MVVM or MVI) already used in the module you touch, and do not introduce a new one.
- ViewModels never hold `Context`, Views, composables or Activity references.
- DI with Koin: declare new types in the existing Koin modules and use `koinViewModel()`/`viewModelOf`. No manual singletons.
- Errors: map exceptions to domain results at the repository boundary, and show errors through `UiState`. Do not swallow exceptions or catch `CancellationException`.

## Views and Compose (migration in progress)

This project has both XML/View screens and Jetpack Compose. Compose is the target. Migrate gradually and never as a side effect of an unrelated task.

- **New UI is Compose.** Build new screens and components in Compose, hosted in the existing navigation (a Fragment with `ComposeView`, or a Compose destination if the graph already uses them).
- **Do not rewrite existing XML screens** unless the task is a migration (see the `migrate-to-compose` playbook). Small fixes to an XML screen stay in XML.
- **Interop.** Use `ComposeView` with `setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed)` inside Fragments, and `AndroidView` for View widgets that have no Compose equivalent yet.
- **View code.** Use View Binding, not `findViewById` or Kotlin synthetics. Collect flows with `repeatOnLifecycle(Lifecycle.State.STARTED)` in `viewLifecycleOwner.lifecycleScope`.
- **One theme.** Compose screens use the Compose `MaterialTheme` mapped to the same colors and typography as the XML theme. Do not create a second, divergent palette.
- **Shared ViewModels.** A screen keeps its ViewModel and `UiState` when it moves from Views to Compose. The migration changes only the UI layer.

### Compose conventions

- Split screens into a ViewModel-aware `FooScreen` and a stateless `FooContent(state, onEvent, modifier)`. Previews and UI tests target the stateless one.
- Hoist state. Composables take state and callbacks as parameters, and ViewModels are never passed into child composables.
- Use `collectAsStateWithLifecycle()` for flows.
- Every public composable that emits UI takes `modifier: Modifier = Modifier` as its first optional parameter.
- Every new or changed composable screen and component gets an `@Preview` with representative data.
- Use theme tokens and `stringResource`. Do not hardcode colors, sizes or strings.
- Give lazy list items stable `key`s, and use `remember`/`derivedStateOf` for derived values.

## Modules

- Put code in the module that owns the feature. Only move code between modules when the task asks for it.
- A feature module must not depend on another feature module. Shared code goes in a `core` or `common` module.
- Respect `internal` and existing API boundaries. Do not widen visibility just to make something compile. Ask instead.
- Register new modules in `settings.gradle` and copy the setup of an existing module of the same kind.

## Dependencies and the version catalog

- This project does not use a version catalog. Declare dependencies the way existing build files do, and do not introduce a catalog unless asked.
- Before adding a library, check whether an existing dependency or the platform already covers the need. List every new dependency in your summary.
- Do not upgrade existing versions unless the task asks for it.

## Testing

- Every new ViewModel, use case and repository function gets unit tests in the module's `src/test` (or `commonTest` for shared KMP code). Every bug fix gets a regression test.
- Use `runTest` from coroutines-test and replace `Dispatchers.Main` with a test dispatcher rule.
- Prefer hand-written fakes for the project's own interfaces. Use Mockito only for third-party types.
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

- [ ] `./gradlew :app:assembleDebug` succeeds
- [ ] Unit tests pass for every module you touched (`./gradlew testDebugUnitTest`, or the module-scoped task)
- [ ] `./gradlew :app:lintDebug` reports no new issues
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
