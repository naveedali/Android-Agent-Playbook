<!-- android-agent-playbook:start -->
This is an Android project. The full rules for AI assistants are in [`AGENTS.md`](../AGENTS.md) at the repository root. Read and follow it.

Key points:

- Build: `./gradlew :app:assembleDebug`. Unit tests: `./gradlew testDebugUnitTest`. Lint: `./gradlew :app:lintDebug`.
- Follow the existing architecture and module boundaries. Feature modules never depend on each other.
- Declare dependencies the way existing build files do.
- Never edit `build/`, generated code, `local.properties`, signing config, keystores or `google-services.json`.
- New logic needs unit tests, and new composables need a `@Preview`.
- Playbooks for common tasks (adding a screen or module, migrating to Compose, writing tests, fixing the build) are in `.agents/skills/`.
<!-- android-agent-playbook:end -->
