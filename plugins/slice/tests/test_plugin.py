"""Tests for the plugin layout: manifest, marketplace entry, hooks, agents, skills, templates."""
import json
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
REPO = PLUGIN.parent.parent


def front_matter(path):
    text = path.read_text()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, path
    return dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M))


class Layout(unittest.TestCase):
    def test_manifest(self):
        data = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())
        self.assertEqual(data["name"], "slice")
        self.assertEqual(data["version"], "0.1.0")

    def test_marketplace_lists_the_plugin(self):
        data = json.loads((REPO / ".claude-plugin/marketplace.json").read_text())
        entry = [p for p in data["plugins"] if p["name"] == "slice"]
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry[0]["source"], "./plugins/slice")
        self.assertTrue((REPO / entry[0]["source"] / ".claude-plugin/plugin.json").is_file())
        self.assertTrue(any(p["name"] == "pdlc" for p in data["plugins"]))

    def test_hooks_run_the_guard_on_files_and_bash(self):
        data = json.loads((PLUGIN / "hooks/hooks.json").read_text())
        entries = data["hooks"]["PreToolUse"]
        matchers = "|".join(e["matcher"] for e in entries).split("|")
        for tool in ("Read", "Glob", "Grep", "Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"):
            self.assertIn(tool, matchers)
        for e in entries:
            for h in e["hooks"]:
                self.assertIn("hooks/guard.py", h["command"])

    def test_agents(self):
        for name in ("test-writer", "implementer", "reviewer"):
            fm = front_matter(PLUGIN / "agents" / (name + ".md"))
            self.assertEqual(fm["name"], name)

    def test_the_implementer_has_no_tests_in_its_text(self):
        text = (PLUGIN / "agents/implementer.md").read_text()
        self.assertIn("slice.py test", text)

    def test_skills(self):
        for name in ("spec", "plan", "interface", "build", "run"):
            fm = front_matter(PLUGIN / "skills" / name / "SKILL.md")
            self.assertEqual(fm["name"], name)

    def test_spec_skill_contract(self):
        text = (PLUGIN / "skills/spec/SKILL.md").read_text()
        for word in ("AskUserQuestion", "(Recommended)", "one question at a time", "up to 4", "ratified",
                     "confirms the summary"):
            self.assertIn(word, text)

    def test_templates_match_what_the_script_reads(self):
        t = PLUGIN / "templates"
        self.assertIn("- tests folder:", (t / "config.md").read_text())
        self.assertIn("- test command:", (t / "config.md").read_text())
        self.assertIn("Status: draft", (t / "spec.md").read_text())
        self.assertRegex((t / "slices.md").read_text(), r"(?m)^## S1: ")
        self.assertIn("- Status: planned", (t / "slices.md").read_text())
        self.assertIn("- Test rounds: 0", (t / "slices.md").read_text())
        self.assertTrue((t / "interface.md").is_file())

    def test_readme_exists_and_is_short(self):
        self.assertLess(len((PLUGIN / "README.md").read_text().split()), 400)


if __name__ == "__main__":
    unittest.main()
