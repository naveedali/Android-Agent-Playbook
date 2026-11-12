---
name: write-tests
description: Write or extend unit and UI tests for Android code (ViewModels, repositories, use cases, Room DAOs, composables) using the project's existing test stack. Use when asked to add tests, improve coverage or test a specific class.
---

# Write tests

Read the Testing section of `AGENTS.md` for the libraries this project uses. Do not add a new test framework.

## 1. Choose what to test

- Test behavior, not implementation: public functions, emitted state and observable side effects.
- For a ViewModel, cover the initial state, each user action, the success and error paths of each data call, and process-death behavior if `SavedStateHandle` is used.
- For a repository or use case, cover mapping, error handling, caching and threading assumptions.
- For a bug fix, first write a test that fails because of the bug, then make it pass.

## 2. Set up the test

- Put JVM tests in the module's `src/test`. Device or emulator tests go in `src/androidTest` only when they need a real Android runtime.
- Copy the conventions of neighboring tests: naming (`fun whenX_thenY()` or backtick names), base classes, rules and fake locations.
- Coroutines: use `runTest`. Replace `Dispatchers.Main` with the project's `MainDispatcherRule` (or equivalent), and inject a `TestDispatcher` instead of using real dispatchers.
- Flows: use Turbine if the project has it. Otherwise collect into a list inside `backgroundScope`.
- Prefer hand-written fakes (`FakeFooRepository`) over mocks for your own interfaces. Use the project's mocking library only for third-party types that are hard to fake.
- Room: test DAOs with an in-memory database. Test migrations with `MigrationTestHelper` if schemas are exported.
- Compose: test stateless `FooContent` with `createComposeRule()`. Find nodes by text, content description or test tag, and assert on what the user sees.

## 3. Keep tests honest

- One behavior per test, with a clear arrange, act and assert.
- No `Thread.sleep`, real network or real time. Use virtual time from `runTest`.
- Never weaken an assertion, add `@Ignore` or delete an existing test to make a suite pass. If an existing test looks wrong, say so.

## 4. Verify

Run the module's test task from `AGENTS.md` (for example `./gradlew :module:testDebugUnitTest`) and make sure the new tests run and pass. If you can, break the code briefly to confirm a test fails. Summarize what is now covered and what is still untested.
