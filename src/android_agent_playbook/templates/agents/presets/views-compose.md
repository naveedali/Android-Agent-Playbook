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
