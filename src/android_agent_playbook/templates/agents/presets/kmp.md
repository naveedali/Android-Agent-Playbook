## Kotlin Multiplatform

Shared logic lives in `commonMain`. Platform code is the exception, not the default.

- **commonMain first.** Put models, repositories, use cases and ViewModels/state holders in `commonMain` when they have no platform dependency. Never import `android.*`, `java.*` or `platform.*` in `commonMain`.
- **expect/actual sparingly.** Prefer an interface in `commonMain` with platform implementations injected via DI. Use `expect`/`actual` only for small platform primitives, and keep each `actual` thin.
- **Source sets.** Android-only code goes in `androidMain` and iOS-only code in `iosMain`. Respect the source-set hierarchy already in the build files, and do not add new targets unless asked.
- **Dependencies.** Shared code may only use multiplatform libraries (for example kotlinx.coroutines, kotlinx.serialization, Ktor, SQLDelight or Room KMP, Koin). Check that a library supports every configured target before adding it to `commonMain`.
- **Tests.** Write shared tests with `kotlin.test` in `commonTest`. Run `allTests` (or the module's `jvmTest`/`testDebugUnitTest` while iterating). Platform-specific behavior gets tests in the matching platform test source set.
- **iOS.** You may not be able to build iOS targets in this environment. If you change `iosMain` or shared APIs used by Swift, say what you could not verify.
{{KMP_UI_NOTE}}
