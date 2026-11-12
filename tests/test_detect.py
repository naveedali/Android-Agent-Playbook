import shutil
import unittest

from android_agent_playbook import cli
from tests import fixtures


class ParseModulesTest(unittest.TestCase):
    def test_kts_multiline_and_comments(self):
        text = fixtures.COMPOSE_HILT["settings.gradle.kts"]
        self.assertEqual(cli.parse_modules(text), [":app", ":core:data", ":core:ui", ":feature:home"])

    def test_groovy_comma_list(self):
        self.assertEqual(cli.parse_modules("include ':app', ':lib'\ninclude 'other'"), [":app", ":lib", ":other"])

    def test_include_build_is_not_a_module(self):
        self.assertEqual(cli.parse_modules('includeBuild("build-logic")\ninclude(":app")'), [":app"])


class DetectTest(unittest.TestCase):
    def detect(self, files):
        root = fixtures.make(files)
        self.addCleanup(shutil.rmtree, root)
        return cli.detect(root)

    def test_compose_hilt_project(self):
        info = self.detect(fixtures.COMPOSE_HILT)
        self.assertEqual(info["project_name"], "TaskFlow")
        self.assertEqual(info["dsl"], "kts")
        self.assertTrue(info["version_catalog"])
        self.assertEqual(info["build_logic"], "build-logic")
        self.assertEqual(info["app_module"], ":app")
        types = {m["path"]: m["type"] for m in info["modules"]}
        self.assertEqual(types, {":app": "application", ":core:data": "library",
                                 ":core:ui": "library", ":feature:home": "library"})
        f = info["features"]
        for key in ("compose", "hilt", "room", "ksp", "navigation_compose"):
            self.assertTrue(f[key], key)
        for key in ("views", "kmp", "koin"):
            self.assertFalse(f[key], key)
        for lib in ("JUnit 4", "MockK", "Turbine", "Compose UI test", "coroutines-test"):
            self.assertIn(lib, info["tests"])
        self.assertEqual(info["lint_tools"], ["ktlint"])
        self.assertEqual(info["preset"], "compose")

    def test_views_compose_groovy_project(self):
        info = self.detect(fixtures.VIEWS_COMPOSE_GROOVY)
        self.assertEqual(info["dsl"], "groovy")
        self.assertEqual(info["settings_file"], "settings.gradle")
        self.assertFalse(info["version_catalog"])
        self.assertTrue(info["features"]["views"])
        self.assertTrue(info["features"]["compose"])
        self.assertTrue(info["features"]["koin"])
        self.assertTrue(info["features"]["kapt"])
        self.assertIn("Mockito", info["tests"])
        self.assertEqual(info["preset"], "views-compose")

    def test_kmp_project(self):
        info = self.detect(fixtures.KMP)
        types = {m["path"]: m["type"] for m in info["modules"]}
        self.assertEqual(types, {":shared": "kmp", ":androidApp": "application"})
        self.assertEqual(info["app_module"], ":androidApp")
        self.assertTrue(info["features"]["kmp"])
        self.assertTrue(info["features"]["compose_multiplatform"])
        self.assertTrue(info["features"]["sqldelight"])
        self.assertIn("kotlin.test", info["tests"])
        self.assertEqual(info["preset"], "kmp")

    def test_commands(self):
        info = self.detect(fixtures.COMPOSE_HILT)
        cmds = cli.commands(info)
        self.assertEqual(cmds["build"], "./gradlew :app:assembleDebug")
        self.assertEqual(cmds["test"], "./gradlew testDebugUnitTest")
        self.assertEqual(cmds["lint"], "./gradlew :app:lintDebug && ./gradlew ktlintCheck")
        self.assertEqual(cli.commands(self.detect(fixtures.KMP))["test"], "./gradlew allTests")


if __name__ == "__main__":
    unittest.main()
