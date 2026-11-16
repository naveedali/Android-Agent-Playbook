import shutil
import unittest

from android_agent_playbook import cli
from tests import fixtures


GROOVY_TWO_DIMENSIONS = """
android {
    flavorDimensions "api", "mode"
    productFlavors {
        demo {
            dimension "mode"
        }
        full {
            dimension "mode"
            isDefault true
        }
        minApi24 {
            dimension "api"
            minSdkVersion 24
        }
        minApi21 {
            dimension "api"
        }
    }
}
"""


class ParseFlavorsTest(unittest.TestCase):
    def test_no_flavors(self):
        self.assertEqual(cli.parse_flavors("android { }"),
                         {"dimensions": [], "flavors": [], "variant": "debug"})

    def test_kts_prefers_dev(self):
        result = cli.parse_flavors(fixtures.FLAVORED["app/build.gradle.kts"])
        self.assertEqual([f["name"] for f in result["flavors"]], ["prod", "dev"])
        self.assertEqual(result["dimensions"], ["env"])
        self.assertEqual(result["variant"], "devDebug")

    def test_groovy_two_dimensions_with_default(self):
        result = cli.parse_flavors(GROOVY_TWO_DIMENSIONS)
        self.assertEqual(result["dimensions"], ["api", "mode"])
        self.assertEqual([f["name"] for f in result["flavors"]], ["demo", "full", "minApi24", "minApi21"])
        self.assertEqual(result["variant"], "minApi24FullDebug")

    def test_is_default_kts(self):
        text = 'productFlavors { create("free") { isDefault = true }\n create("paid") { } }'
        self.assertEqual(cli.parse_flavors(text)["variant"], "freeDebug")

    def test_commented_out_flavors_ignored(self):
        text = '/* productFlavors { create("dev") { } } */\nandroid { }'
        self.assertEqual(cli.parse_flavors(text)["variant"], "debug")


class VariantCommandsTest(unittest.TestCase):
    def detect(self, files):
        root = fixtures.make(files)
        self.addCleanup(shutil.rmtree, root)
        return cli.detect(root)

    def test_flavored_app_commands(self):
        info = self.detect(fixtures.FLAVORED)
        self.assertEqual(info["variant"], "devDebug")
        cmds = cli.commands(info)
        self.assertEqual(cmds["build"], "./gradlew :app:assembleDevDebug")
        self.assertEqual(cmds["test"], "./gradlew :app:testDevDebugUnitTest testDebugUnitTest")
        self.assertEqual(cmds["lint"], "./gradlew :app:lintDevDebug")
        self.assertEqual(cmds["instrumented"], "./gradlew :app:connectedDevDebugAndroidTest")
        agents = cli.fill(cli._template("agents", "base.md"), cli.render_context(info, "compose"))
        self.assertIn("### Build variants", agents)
        self.assertIn("`:app` has product flavors `prod`, `dev` (dimension `env`). Commands use the `devDebug` variant.", agents)
        self.assertIn("--configuration devDebugRuntimeClasspath", agents)

    def test_unflavored_project_has_no_variants_section(self):
        info = self.detect(fixtures.COMPOSE_HILT)
        agents = cli.fill(cli._template("agents", "base.md"), cli.render_context(info, "compose"))
        self.assertNotIn("Build variants", agents)

    def test_flavors_in_build_logic_are_flagged(self):
        files = dict(fixtures.COMPOSE_HILT)
        files["build-logic/convention/src/main/kotlin/Flavors.kt"] = (
            'fun configureFlavors() { productFlavors { create("demo") { } } }\n')
        info = self.detect(files)
        self.assertTrue(info["flavors_in_build_logic"])
        agents = cli.fill(cli._template("agents", "base.md"), cli.render_context(info, "compose"))
        self.assertIn("Product flavors are configured in the convention plugins", agents)


class BuildFactsTest(unittest.TestCase):
    def detect(self, files):
        root = fixtures.make(files)
        self.addCleanup(shutil.rmtree, root)
        return cli.detect(root)

    def test_kts_catalog_facts(self):
        b = self.detect(fixtures.COMPOSE_HILT)["build"]
        self.assertEqual((b["min_sdk"], b["target_sdk"], b["compile_sdk"]), ("26", "36", "36"))
        self.assertEqual((b["agp"], b["kotlin"], b["jdk"], b["gradle"], b["compose_bom"]),
                         ("8.13.0", "2.2.20", "17", "9.1.0", "2026.01.00"))

    def test_groovy_facts(self):
        b = self.detect(fixtures.VIEWS_COMPOSE_GROOVY)["build"]
        self.assertEqual((b["min_sdk"], b["target_sdk"], b["compile_sdk"]), ("21", "34", "34"))
        self.assertEqual((b["agp"], b["jdk"]), ("7.4.2", "8"))
        self.assertIsNone(b["gradle"])

    def test_catalog_plugin_version_ref(self):
        catalog = '[versions]\nandroidGradle = "8.9.1"\n[plugins]\nandroid-library = { id = "com.android.library", version.ref = "androidGradle" }\n'
        versions = cli._catalog_versions(catalog)
        self.assertEqual(cli._catalog_plugin_version(catalog, versions, ("com.android.library",)), "8.9.1")

    def test_stack_lines(self):
        info = self.detect(fixtures.COMPOSE_HILT)
        stack = cli.render_context(info, "compose")["STACK"]
        self.assertIn("- Android: minSdk 26, targetSdk 36, compileSdk 36. Guard APIs above minSdk", stack)
        self.assertIn("- Toolchain: Gradle 9.1.0, AGP 8.13.0, Kotlin 2.2.20, JDK 17, Compose BOM 2026.01.00", stack)


if __name__ == "__main__":
    unittest.main()
