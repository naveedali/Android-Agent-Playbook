import contextlib
import io
import os
import re
import shutil
import unittest

from android_agent_playbook import cli
from tests import fixtures


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = cli.main(list(argv))
    return code, out.getvalue()


def read(root, rel):
    with open(os.path.join(root, *rel.split("/")), encoding="utf-8") as f:
        return f.read()


def snapshot(root):
    files = {}
    for dirpath, _, names in os.walk(root):
        for n in names:
            p = os.path.join(dirpath, n)
            files[os.path.relpath(p, root)] = read(root, os.path.relpath(p, root).replace(os.sep, "/"))
    return files


class InstallTest(unittest.TestCase):
    def project(self, files=fixtures.COMPOSE_HILT):
        root = fixtures.make(files)
        self.addCleanup(shutil.rmtree, root)
        return root

    def test_creates_all_files(self):
        root = self.project()
        code, out = run("install", root)
        self.assertEqual(code, 0, out)
        expected = ["AGENTS.md", "CLAUDE.md", ".cursor/rules/android-agent-playbook.mdc",
                    ".github/copilot-instructions.md"]
        for s in cli.SKILLS:
            expected += [".agents/skills/%s/SKILL.md" % s, ".claude/commands/%s.md" % s, ".cursor/commands/%s.md" % s]
        for rel in expected:
            self.assertTrue(os.path.isfile(os.path.join(root, *rel.split("/"))), rel)
        agents = read(root, "AGENTS.md")
        self.assertIn("# Agent guide: TaskFlow", agents)
        self.assertIn("`./gradlew :app:assembleDebug`", agents)
        self.assertIn("## Jetpack Compose", agents)
        self.assertIn("Hilt", agents)
        self.assertNotRegex(agents, r"\{\{[A-Z_]+\}\}")

    def test_every_preset_renders_without_placeholders(self):
        for files in (fixtures.COMPOSE_HILT, fixtures.VIEWS_COMPOSE_GROOVY, fixtures.KMP):
            info = cli.detect(self.project(files))
            for preset in cli.PRESETS:
                for t in cli.build_targets(info, preset, list(cli.AGENTS)):
                    self.assertNotRegex(t.prefix + t.body, r"\{\{[A-Z_]+\}\}", (preset, t.path))

    def test_skill_and_command_frontmatter(self):
        root = self.project()
        run("install", root)
        skill = read(root, ".agents/skills/add-screen/SKILL.md")
        self.assertTrue(skill.startswith("---\nname: add-screen\ndescription: "))
        cmd = read(root, ".claude/commands/fix-build.md")
        self.assertTrue(cmd.startswith("---\ndescription: "))
        self.assertIn("$ARGUMENTS", cmd)
        cursor_cmd = read(root, ".cursor/commands/write-tests.md")
        self.assertTrue(cursor_cmd.startswith(cli.START))  # Cursor commands take no frontmatter
        mdc = read(root, ".cursor/rules/android-agent-playbook.mdc")
        self.assertTrue(mdc.startswith("---\ndescription:"))
        self.assertIn("alwaysApply: true", mdc)

    def test_rerun_is_idempotent(self):
        root = self.project()
        run("install", root)
        before = snapshot(root)
        code, out = run("install", root)
        self.assertEqual(code, 0)
        self.assertEqual(snapshot(root), before)
        self.assertNotRegex(out, r"\b(create|update|append)\b\s")

    def test_keeps_user_text_in_shared_files(self):
        root = self.project()
        with open(os.path.join(root, "AGENTS.md"), "w") as f:
            f.write("# Team notes\n\nAlways ask Sara before touching billing.\n")
        code, out = run("install", root)
        self.assertIn("append", out)
        agents = read(root, "AGENTS.md")
        self.assertTrue(agents.startswith("# Team notes\n\nAlways ask Sara before touching billing.\n\n" + cli.START))
        # User edits outside the block survive a refresh.
        with open(os.path.join(root, "AGENTS.md"), "a") as f:
            f.write("\n## After\n\nKeep me.\n")
        run("install", root, "--preset", "views-compose")
        agents = read(root, "AGENTS.md")
        self.assertIn("Always ask Sara", agents)
        self.assertIn("Keep me.", agents)
        self.assertIn("## Views and Compose", agents)
        self.assertEqual(agents.count(cli.START), 1)

    def test_skips_owned_file_without_markers(self):
        root = self.project()
        path = os.path.join(root, ".claude", "commands")
        os.makedirs(path)
        with open(os.path.join(path, "add-screen.md"), "w") as f:
            f.write("my own command\n")
        code, out = run("install", root)
        self.assertEqual(code, 0)
        self.assertRegex(out, r"skip\s+\.claude/commands/add-screen\.md")
        self.assertEqual(read(root, ".claude/commands/add-screen.md"), "my own command\n")

    def test_unbalanced_markers_are_reported_not_touched(self):
        root = self.project()
        with open(os.path.join(root, "CLAUDE.md"), "w") as f:
            f.write("x\n" + cli.START + "\nhalf\n")
        code, out = run("install", root)
        self.assertEqual(code, 1)
        self.assertRegex(out, r"error\s+CLAUDE\.md")
        self.assertEqual(read(root, "CLAUDE.md"), "x\n" + cli.START + "\nhalf\n")

    def test_dry_run_writes_nothing(self):
        root = self.project()
        before = snapshot(root)
        code, out = run("install", root, "--dry-run", "--diff")
        self.assertEqual(code, 0)
        self.assertIn("Dry run", out)
        self.assertIn("+++ b/AGENTS.md", out)
        self.assertEqual(snapshot(root), before)

    def test_agents_filter(self):
        root = self.project()
        run("install", root, "--agents", "codex")
        self.assertTrue(os.path.isfile(os.path.join(root, "AGENTS.md")))
        self.assertTrue(os.path.isdir(os.path.join(root, ".agents", "skills")))
        for absent in ("CLAUDE.md", ".cursor", ".claude", ".github"):
            self.assertFalse(os.path.exists(os.path.join(root, absent)), absent)

    def test_refuses_non_gradle_dir(self):
        root = self.project({"README.md": "hi\n"})
        code, out = run("install", root)
        self.assertEqual(code, 2)
        self.assertIn("no settings.gradle", out)

    def test_uninstall_restores_user_files(self):
        root = self.project()
        original = snapshot(root)
        with open(os.path.join(root, "AGENTS.md"), "w") as f:
            f.write("# Team notes\n")
        run("install", root)
        code, out = run("uninstall", root)
        self.assertEqual(code, 0, out)
        after = snapshot(root)
        self.assertEqual(after.pop("AGENTS.md"), "# Team notes\n")
        self.assertEqual(after, original)
        for d in (".agents", ".claude", ".cursor", ".github"):
            self.assertFalse(os.path.exists(os.path.join(root, d)), d)


class BlockTest(unittest.TestCase):
    def test_replace_keeps_surroundings(self):
        t = cli.Target("X.md", "new", shared=True)
        text = "a\n\n" + cli.make_block("old") + "\nb\n"
        action, new = cli.apply_block(text, t)
        self.assertEqual(action, "update")
        self.assertEqual(new, "a\n\n" + cli.make_block("new") + "\nb\n")

    def test_remove_block_joins_text(self):
        text = "a\n\n" + cli.make_block("x") + "\nb\n"
        self.assertEqual(cli.remove_block(text), ("update", "a\n\nb\n"))

    def test_remove_block_with_only_frontmatter_deletes(self):
        text = "---\nname: x\n---\n" + cli.make_block("body")
        self.assertEqual(cli.remove_block(text), ("delete", None))


if __name__ == "__main__":
    unittest.main()
