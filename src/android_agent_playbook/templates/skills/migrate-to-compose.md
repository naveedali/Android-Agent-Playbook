---
name: migrate-to-compose
description: Migrate one XML/View screen or component to Jetpack Compose without changing behavior. Use when asked to convert, migrate or rewrite a layout, Fragment or custom View in Compose.
---

# Migrate a screen to Compose

The goal is the same behavior with a different UI toolkit. Change the UI layer only, and change one screen per task.

## 1. Inventory the existing screen

- Read the layout XML, the Fragment or Activity, any adapters or custom Views, and the ViewModel.
- List everything the screen does: states shown, user actions, navigation, dialogs, snackbars, menus, `onSaveInstanceState`, accessibility labels, analytics events, and visibility rules.
- Note any existing UI or screenshot tests. They define behavior you must keep.

## 2. Keep the ViewModel

- Reuse the existing ViewModel and `UiState`. If state is spread across LiveData fields or imperative View updates, consolidate it into one immutable `UiState` exposed as `StateFlow`. Keep it behavior-preserving and make it a separate, reviewable step.
- Convert one-off View commands (toasts, navigation) into events the way the project already does.

## 3. Build the Compose UI

- Write `FooScreen` (collects state with `collectAsStateWithLifecycle()`) and a stateless `FooContent(state, onEvent, modifier)`.
- Map each XML element to Compose deliberately: `RecyclerView` to `LazyColumn` with stable keys, `ConstraintLayout` to `Column`/`Row`/`Box` where possible, `include` layouts to small composables.
- Keep the existing look: use the Compose theme mapped from the XML theme, the same strings, dimensions and content descriptions.
- Wrap custom Views that have no Compose equivalent yet with `AndroidView` instead of rewriting them.
- Add `@Preview`s for every state you listed in step 1.

## 4. Swap the host

- Keep the Fragment and navigation destination. Replace its `onCreateView` with a `ComposeView` using `ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed`, unless the navigation graph is already Compose-based.
- Delete the old layout XML, adapters and binding code only after nothing references them. Search for usages before deleting.

## 5. Tests and verification

- Port or replace the existing UI tests with Compose tests on `FooContent`. Keep the ViewModel tests passing unchanged.
- Run the build, unit tests and lint from `AGENTS.md`.
- In your summary, compare behavior before and after against the inventory from step 1, and flag anything you could not verify without a device.
