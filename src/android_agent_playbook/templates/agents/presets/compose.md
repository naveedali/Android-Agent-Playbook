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
