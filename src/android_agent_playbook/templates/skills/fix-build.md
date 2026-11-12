---
name: fix-build
description: Diagnose and fix a failing Gradle build, compile error, test failure or lint error in this Android project. Use when the build is red, Gradle sync fails, or a task like assembleDebug, test or lint fails.
---

# Fix the build

Fix the cause, not the symptom. A green build reached by skipping work is not fixed.

## 1. Reproduce

- Run the failing command from `AGENTS.md`. If the user did not name one, run the debug build first and then the unit tests.
- Scope it to the failing module once you know it (`./gradlew :module:compileDebugKotlin`, `:module:testDebugUnitTest`).
- Add `--stacktrace` only when the error message alone is not enough.

## 2. Read the right error

- Find the first `e:` (Kotlin compiler), `error:` (Java/kapt/KSP), `FAILURE: Build failed`, `What went wrong:` or failing test name. Later errors are often caused by the first one.
- Classify it before you change anything:
  - **Compile error** in your own code: fix the code.
  - **Unresolved reference to generated code** (`Hilt_`, `_Impl`, `BuildConfig`, `R`, `Binding`): the generator failed earlier. Find the KSP/kapt/annotation error above it.
  - **Dependency resolution or version conflict**: inspect with `./gradlew :module:dependencies --configuration debugRuntimeClasspath`. Fix it in the version catalog and do not add `force` or excludes without explaining why.
  - **Test failure**: read the assertion, then decide whether the code or the test is wrong. Never delete or `@Ignore` a test to make the build green.
  - **Lint error**: fix the issue. Do not add it to a baseline or suppress it without a clear reason in a comment.
  - **Environment** (JDK version, SDK missing, `local.properties`, out of memory, no network): do not edit secrets or local config. Report what is missing and how to fix it.

## 3. Fix minimally

- Change as little as possible, in the module that owns the problem.
- Do not upgrade Gradle, AGP, Kotlin or libraries to fix an error unless that is clearly the cause. If it is, propose the upgrade and say why.
- Do not edit generated sources or anything under `build/`.
- `./gradlew clean` or deleting caches is a last resort. Say when you used it.

## 4. Verify

- Re-run the exact failing command, then the full build, test and lint commands from `AGENTS.md`.
- Summarize the root cause in one or two sentences, the change you made, and the commands that now pass.
