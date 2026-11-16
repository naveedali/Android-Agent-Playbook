<!-- android-agent-playbook:start -->
# Agent guide: NotesKmp

> Managed by [android-agent-playbook](https://github.com/naveedali/android-agent-playbook) v0.1.0 · preset: **kmp**.
> Add your own notes outside the `android-agent-playbook` markers. Re-run `android-agent-playbook install` to refresh this block.

This is an Android codebase. Work like a senior Android engineer on this team: make the smallest change that solves the task, follow the patterns already used in the module you touch, and prove the change works with Gradle before you call it done.

## Project map

- `:shared` (`shared/`): Kotlin Multiplatform
- `:androidApp` (`androidApp/`): Android app

TODO: add one line per module describing what it owns, so agents put code in the right place.

## Stack

- UI: Compose Multiplatform
- Kotlin Multiplatform (shared code in `commonMain`)
- DI: Koin
- Async: Kotlin coroutines and Flow
- Data: SQLDelight
- Build: Gradle Kotlin DSL, version catalog
- Tests: kotlin.test

## Commands

Run Gradle from the repository root. Use module-scoped tasks while you iterate, then run the full checks before you finish.

| Purpose | Command |
| --- | --- |
| Build (debug) | `./gradlew :androidApp:assembleDebug` |
| Unit tests | `./gradlew allTests` |
| One module's tests | `./gradlew :shared:testDebugUnitTest` |
| Lint | `./gradlew :androidApp:lintDebug` |
| Instrumented tests (needs a device; only when asked) | `./gradlew :androidApp:connectedDebugAndroidTest` |
| Dependencies of a module | `./gradlew :androidApp:dependencies --configuration debugRuntimeClasspath` |

If a command fails, read the first error in the output, not the last line. Fix the cause and run it again. Do not stop with a broken build, and do not add `--offline`, `-x test`, `-x lint` or similar flags just to get past a failure.

## Architecture

- Layers: UI → ViewModel (state holder) → use cases (optional) → repositories → data sources. Dependencies point inward, and UI never talks to data sources directly.
- Unidirectional data flow: a ViewModel exposes one immutable `StateFlow<UiState>` and receives user actions as function calls or events. Match the style (MVVM or MVI) already used in the module you touch, and do not introduce a new one.
- ViewModels never hold `Context`, Views, composables or Activity references.
- DI with Koin: declare new types in the existing Koin modules and use `koinViewModel()`/`viewModelOf`. No manual singletons.
- Coroutines: launch in `viewModelScope` (or the owning scope), inject dispatchers instead of hardcoding `Dispatchers.IO`, expose `Flow` for streams and `suspend` for one-shot calls. Never use `GlobalScope`, and never use `runBlocking` in production code.
- SQLDelight: change schema through `.sq`/`.sqm` files with a migration. Never hand-edit generated code.
- Errors: map exceptions to domain results at the repository boundary, and show errors through `UiState`. Do not swallow exceptions or catch `CancellationException`.

## Kotlin Multiplatform

Shared logic lives in `commonMain`. Platform code is the exception, not the default.

- **commonMain first.** Put models, repositories, use cases and ViewModels/state holders in `commonMain` when they have no platform dependency. Never import `android.*`, `java.*` or `platform.*` in `commonMain`.
- **expect/actual sparingly.** Prefer an interface in `commonMain` with platform implementations injected via DI. Use `expect`/`actual` only for small platform primitives, and keep each `actual` thin.
- **Source sets.** Android-only code goes in `androidMain` and iOS-only code in `iosMain`. Respect the source-set hierarchy already in the build files, and do not add new targets unless asked.
- **Dependencies.** Shared code may only use multiplatform libraries (for example kotlinx.coroutines, kotlinx.serialization, Ktor, SQLDelight or Room KMP, Koin). Check that a library supports every configured target before adding it to `commonMain`.
- **Tests.** Write shared tests with `kotlin.test` in `commonTest`. Run `allTests` (or the module's `jvmTest`/`testDebugUnitTest` while iterating). Platform-specific behavior gets tests in the matching platform test source set.
- **iOS.** You may not be able to build iOS targets in this environment. If you change `iosMain` or shared APIs used by Swift, say what you could not verify.
- **Compose Multiplatform.** Shared UI goes in `commonMain` using `org.jetbrains.compose` APIs and `Res` resources. Android-only UI APIs stay in `androidMain`. Hoist state and add previews as for Jetpack Compose.

## Modules

- Put code in the module that owns the feature. Only move code between modules when the task asks for it.
- A feature module must not depend on another feature module. Shared code goes in a `core` or `common` module.
- Respect `internal` and existing API boundaries. Do not widen visibility just to make something compile. Ask instead.
- Register new modules in `settings.gradle.kts` and copy the setup of an existing module of the same kind.

## Dependencies and the version catalog

- Declare every dependency and plugin in `gradle/libs.versions.toml` (`[versions]`, `[libraries]`, `[plugins]`) and reference it as `libs.…` / `alias(libs.plugins.…)`. Never hardcode coordinates or versions in a build file.
- Before adding a library, check whether the catalog or the platform already covers the need. List every new dependency in your summary with the reason.
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
- Xcode project settings and `iosApp/` signing configuration

Never copy secrets from these files into chat, logs, commits or code.

## Done checklist

Before you say a task is complete:

- [ ] `./gradlew :androidApp:assembleDebug` succeeds
- [ ] Unit tests pass for every module you touched (`./gradlew allTests`, or the module-scoped task)
- [ ] `./gradlew :androidApp:lintDebug` reports no new issues
- [ ] Every new or changed composable screen and component has a `@Preview`
- [ ] New logic has tests, and no existing test was deleted, ignored or weakened
- [ ] Dependencies go through the version catalog, and nothing in the Never touch list changed
- [ ] Your summary lists the commands you ran with their results, and anything you could not verify (for example instrumented tests that need a device)

## Playbooks

Step-by-step playbooks for common Android tasks live in `.agents/skills/`. When a request matches one, read its `SKILL.md` and follow it.

- `add-screen` (`.agents/skills/add-screen/SKILL.md`): Add a new screen to this Android app (UI, ViewModel, state, navigation, preview and tests). Use when asked to create or add a screen, page or destination. Not for changing an existing screen.
- `add-feature-module` (`.agents/skills/add-feature-module/SKILL.md`): Create a new Gradle feature module (e.g. :feature:settings) wired into settings, DI, navigation and the version catalog. Use when asked to add a new module or split a feature into its own module.
- `migrate-to-compose` (`.agents/skills/migrate-to-compose/SKILL.md`): Migrate one XML/View screen or component to Jetpack Compose without changing behavior. Use when asked to convert, migrate or rewrite a layout, Fragment or custom View in Compose.
- `write-tests` (`.agents/skills/write-tests/SKILL.md`): Write or extend unit and UI tests for Android code (ViewModels, repositories, use cases, Room DAOs, composables) using the project's existing test stack. Use when asked to add tests, improve coverage or test a specific class.
- `fix-build` (`.agents/skills/fix-build/SKILL.md`): Diagnose and fix a failing Gradle build, compile error, test failure or lint error in this Android project. Use when the build is red, Gradle sync fails, or a task like assembleDebug, test or lint fails.
<!-- android-agent-playbook:end -->
