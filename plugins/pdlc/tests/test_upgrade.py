"""Tests for the pdlc upgrade script and the version nudge hook.
Run: python3 -m unittest discover plugins/pdlc/tests"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).parent.parent
REPO = PLUGIN.parent.parent
SCRIPT = PLUGIN / "skills/upgrade/scripts/upgrade.py"
VERSION_HOOK = PLUGIN / "hooks/version.py"
KNOWN_SCRIPT = REPO / "scripts/pdlc_known_files.py"
REFS = PLUGIN / "skills/init/references"
WRITING = REFS / "bin/check_writing.py"

spec = importlib.util.spec_from_file_location("upgrade", SCRIPT)
upgrade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upgrade)

hook_spec = importlib.util.spec_from_file_location("commits", PLUGIN / "hooks/commits.py")
commits = importlib.util.module_from_spec(hook_spec)
hook_spec.loader.exec_module(commits)

ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
           GIT_COMMITTER_EMAIL="t@t")

JOB_NO_INTERFACE = "# JOB-report · Report words\n\nStatus: stub\n\n## Who and why\n\nA user.\n"
JOB_WITH_INTERFACE = JOB_NO_INTERFACE + "\n## Interface\n\nNone written yet.\n"


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, env=ENV, capture_output=True, text=True,
                          check=True).stdout.strip()


def sha(text):
    return upgrade.digest(text)


class Pure(unittest.TestCase):
    def test_strip_question_removes_only_that_section(self):
        text = "# T\n\nStatus: agreed\n\n## Question\n\nWhich?\n\n- A\n\n## Rule\n\nDo it.\n\n## Why\n\nBecause.\n"
        out = upgrade.strip_question(text)
        self.assertNotIn("Which?", out)
        self.assertNotIn("## Question", out)
        self.assertIn("## Rule\n\nDo it.", out)
        self.assertIn("## Why\n\nBecause.", out)
        self.assertEqual(upgrade.strip_question("# T\n\n## Rule\n\nx\n"), "# T\n\n## Rule\n\nx\n")

    def test_normalise_ignores_noise(self):
        base = "# T\n\nStatus: agreed · Default: yes\n\n## Rule\n\nDo it.\n"
        noisy = "# T\r\n\r\nStatus: agreed · Default: yes · Ask at init: no  \r\n\r\n## Rule\r\n\r\nDo it.   \r\n\r\n\r\n"
        self.assertEqual(upgrade.normalise(base), upgrade.normalise(noisy))
        self.assertEqual(sha(base), sha(noisy))
        self.assertNotEqual(sha(base), sha(base + "More.\n"))

    def test_header_default(self):
        self.assertEqual(upgrade.header_default("# T\n\nStatus: agreed · Default: yes · Ask at init: no\n"), "yes")
        self.assertEqual(upgrade.header_default("# T\n\nStatus: agreed · Default: no\n"), "no")
        self.assertEqual(upgrade.header_default("# T\n\nStatus: stub\n"), None)

    def test_error_rows_split_and_join(self):
        text = ("# DES-errors\n\n| Code | Meaning |\n|---|---|\n| `A` | one |\n| `B` | two |\n\nAfter.\n")
        skeleton, rows = upgrade.split_error_rows(text)
        self.assertEqual(rows, ["| `A` | one |", "| `B` | two |"])
        self.assertNotIn("`A`", skeleton)
        new = "# DES-errors\n\n| Code | Meaning | Who |\n|---|---|---|\n\nAfter, new.\n"
        joined = upgrade.join_error_rows(new, rows)
        self.assertIn("| Code | Meaning | Who |\n|---|---|---|\n| `A` | one |\n| `B` | two |\n", joined)
        self.assertIn("After, new.", joined)

    def test_decide(self):
        d = upgrade.decide
        p = "ports/checks.md"
        self.assertEqual(d(p, "a\n", "a\n", None, [], False), "current")
        self.assertEqual(d(p, None, "a\n", None, [], False), "added")
        self.assertEqual(d(p, "old\n", "new\n", sha("old\n"), [], False), "refreshed")
        self.assertEqual(d(p, "old\n", "new\n", None, [sha("old\n")], False), "refreshed")
        self.assertEqual(d(p, "mine\n", "new\n", sha("old\n"), [], False), "edited")
        self.assertEqual(d(p, "mine\n", "new\n", None, [], False), "edited")
        self.assertEqual(d(p, "mine\n", "new\n", sha("old\n"), [], True), "taken")
        self.assertEqual(d(p, "old\n", None, sha("old\n"), [], False), "removed")
        self.assertEqual(d(p, "mine\n", None, sha("old\n"), [], False), "edited, no longer in pdlc")
        own = "# T\n\nStatus: agreed · Default: no\n\nmine\n"
        self.assertEqual(d("specs/design/DES-x.md", own, "# T\n\nStatus: agreed · Default: yes\n\nnew\n",
                           None, [], False), "project-owned")

    def test_format_problems(self):
        self.assertEqual(upgrade.format_problems(JOB_WITH_INTERFACE), [])
        self.assertEqual(len(upgrade.format_problems(JOB_NO_INTERFACE)), 1)

    def test_next_intent_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            inbox = Path(tmp, "pdlc/inbox")
            inbox.mkdir(parents=True)
            self.assertEqual(upgrade.next_intent_id(tmp), "IN-0001")
            (inbox / "IN-0003-x.md").write_text("x")
            (inbox / "IN-0007-y.md").write_text("x")
            self.assertEqual(upgrade.next_intent_id(tmp), "IN-0008")


class Project(unittest.TestCase):
    """A project made like init makes it, and a copy of the plugin that a test can change."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.plugin = base / "plugin"
        shutil.copytree(PLUGIN, self.plugin, ignore=shutil.ignore_patterns("__pycache__", "tests"))
        self.root = base / "project"
        self.root.mkdir()
        self.script = self.plugin / "skills/upgrade/scripts/upgrade.py"
        git(self.root, "init", "-q", "-b", "main")
        self.init_project()
        self.record = self.run_script("record")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "Set up pdlc")

    def tearDown(self):
        self.tmp.cleanup()

    def init_project(self):
        refs = self.plugin / "skills/init/references"
        pdlc = self.root / "pdlc"
        copies = {"README.md": refs / "templates/README.md", "config.md": refs / "templates/config.md"}
        for p in (refs / "templates").iterdir():
            if p.name not in ("README.md", "config.md"):
                copies["templates/" + p.name] = p
        for folder in ("ports", "adapters", "bin", "reviews"):
            for p in (refs / folder).iterdir():
                if p.is_file():
                    copies["%s/%s" % (folder, p.name)] = p
        for p in (refs / "defaults").iterdir():
            copies["specs/design/" + p.name] = p
        for rel, src in copies.items():
            target = pdlc / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            text = src.read_text()
            if rel.startswith("specs/design/"):
                text = upgrade.strip_question(text)
            target.write_text(text)
        for folder in ("inbox", "changes", "specs/jobs", "specs/capabilities"):
            (pdlc / folder).mkdir(parents=True, exist_ok=True)
            (pdlc / folder / ".gitkeep").write_text("")

    def run_script(self, *args, check=True):
        done = subprocess.run([sys.executable, str(self.script), *args, "--project", str(self.root)],
                              env=ENV, capture_output=True, text=True)
        if check and done.returncode != 0:
            self.fail("upgrade.py %s failed (%d): %s%s" % (args, done.returncode, done.stdout, done.stderr))
        return done

    def apply(self, *args):
        done = self.run_script("apply", "--json", *args)
        return json.loads(done.stdout)

    def statuses(self, data):
        return {f["path"]: f["status"] for f in data["files"]}

    def edit_plugin(self, rel, extra="\nA new line from the plugin.\n"):
        path = self.plugin / "skills/init/references" / rel
        path.write_text(path.read_text() + extra)

    def pdlc(self, rel):
        return (self.root / "pdlc" / rel).read_text()

    def subjects(self):
        return git(self.root, "log", "--format=%s").splitlines()

    def version_file(self):
        return json.loads(self.pdlc("version.json"))


class Record(Project):
    def test_record_writes_hash_of_each_managed_file(self):
        marker = self.version_file()
        self.assertEqual(marker["pdlc"], json.loads((self.plugin / ".claude-plugin/plugin.json").read_text())["version"])
        files = marker["files"]
        self.assertEqual(files["ports/checks.md"], sha(self.pdlc("ports/checks.md")))
        self.assertEqual(files["README.md"], sha(self.pdlc("README.md")))
        self.assertEqual(files["specs/design/DES-pdlc-ids.md"], sha(self.pdlc("specs/design/DES-pdlc-ids.md")))
        self.assertNotIn("config.md", files)
        self.assertNotIn("templates/config.md", files)
        self.assertNotIn("templates/README.md", files)
        self.assertTrue(all(not k.startswith("inbox") for k in files))


class Apply(Project):
    def test_pristine_files_are_refreshed(self):
        self.edit_plugin("ports/checks.md")
        self.edit_plugin("templates/job.md")
        data = self.apply()
        st = self.statuses(data)
        self.assertEqual(st["ports/checks.md"], "refreshed")
        self.assertEqual(st["templates/job.md"], "refreshed")
        self.assertNotIn("ports/inbox.md", st)  # current files are not listed
        self.assertEqual(self.pdlc("ports/checks.md"), (self.plugin / "skills/init/references/ports/checks.md").read_text())
        self.assertEqual(self.subjects()[0], "Upgrade pdlc")
        self.assertEqual(git(self.root, "status", "--porcelain"), "")

    def test_edited_file_is_kept_with_a_diff(self):
        rel = "specs/design/DES-pdlc-branches.md"
        mine = self.pdlc(rel).replace("Rule", "Rule (my team)")
        (self.root / "pdlc" / rel).write_text(mine)
        git(self.root, "commit", "-qam", "my edit")
        self.edit_plugin("defaults/DES-pdlc-branches.md")
        done = self.run_script("apply")
        self.assertEqual(self.pdlc(rel), mine)
        self.assertIn("edited", done.stdout)
        self.assertIn("```diff", done.stdout)
        self.assertIn("A new line from the plugin.", done.stdout)

    def test_default_no_is_project_owned(self):
        rel = "specs/design/DES-pdlc-ids.md"
        mine = self.pdlc(rel).replace("Default: yes", "Default: no") + "\nOur rule.\n"
        (self.root / "pdlc" / rel).write_text(mine)
        git(self.root, "commit", "-qam", "own rule")
        self.edit_plugin("defaults/DES-pdlc-ids.md")
        data = self.apply()
        self.assertEqual(self.statuses(data)[rel], "project-owned")
        self.assertEqual(self.pdlc(rel), mine)

    def test_errors_keep_project_rows(self):
        rel = "specs/design/DES-errors.md"
        text = self.pdlc(rel)
        rows = "| `NOT_FOUND` | Missing | caller | no |\n| `BUSY` | Overloaded | system | yes |\n"
        (self.root / "pdlc" / rel).write_text(text.replace("|---|---|---|---|\n", "|---|---|---|---|\n" + rows))
        git(self.root, "commit", "-qam", "rows")
        src = self.plugin / "skills/init/references/defaults/DES-errors.md"
        src.write_text(src.read_text().replace("Each error that the system can give", "Every error that the system gives"))
        data = self.apply()
        self.assertEqual(self.statuses(data)[rel], "refreshed, rows kept")
        out = self.pdlc(rel)
        self.assertIn("Every error that the system gives", out)
        self.assertIn("|---|---|---|---|\n" + rows, out)
        self.assertLess(out.index("NOT_FOUND"), out.index("BUSY"))

    def test_legacy_project_uses_known_hashes(self):
        (self.root / "pdlc/version.json").unlink()
        original = self.pdlc("ports/checks.md")
        self.edit_plugin("ports/checks.md")
        self.edit_plugin("ports/inbox.md")
        # Only ports/checks.md has a known hash. ports/inbox.md has none, so it counts as edited.
        known_path = self.plugin / "skills/upgrade/references/known.json"
        known_path.parent.mkdir(parents=True, exist_ok=True)
        known_path.write_text(json.dumps({"ports/checks.md": [sha(original)]}))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "legacy")
        data = self.apply()
        st = self.statuses(data)
        self.assertEqual(st["ports/checks.md"], "refreshed")
        self.assertEqual(st["ports/inbox.md"], "edited")
        self.assertEqual(self.version_file()["from"], "unknown")

    def test_file_removed_from_the_plugin(self):
        (self.root / "pdlc/adapters/old-one.md").write_text("old adapter\n")
        (self.root / "pdlc/adapters/old-two.md").write_text("old adapter two\n")
        marker = self.version_file()
        marker["files"]["adapters/old-one.md"] = sha("old adapter\n")
        marker["files"]["adapters/old-two.md"] = sha("something else\n")
        (self.root / "pdlc/version.json").write_text(json.dumps(marker))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "old files")
        data = self.apply()
        st = self.statuses(data)
        self.assertEqual(st["adapters/old-one.md"], "removed")
        self.assertEqual(st["adapters/old-two.md"], "edited, no longer in pdlc")
        self.assertFalse((self.root / "pdlc/adapters/old-one.md").exists())
        self.assertTrue((self.root / "pdlc/adapters/old-two.md").exists())

    def test_take_writes_the_plugin_version(self):
        rel = "ports/checks.md"
        (self.root / "pdlc" / rel).write_text("mine\n")
        git(self.root, "commit", "-qam", "mine")
        data = self.apply("--take", "pdlc/" + rel)
        self.assertEqual(self.statuses(data)[rel], "taken")
        plugin_text = (self.plugin / "skills/init/references/ports/checks.md").read_text()
        self.assertEqual(self.pdlc(rel), plugin_text)
        self.assertEqual(self.version_file()["files"][rel], sha(plugin_text))

    def test_second_apply_changes_nothing(self):
        self.edit_plugin("ports/checks.md")
        self.apply()
        count = len(self.subjects())
        marker = self.pdlc("version.json")
        done = self.run_script("apply")
        self.assertIn("pdlc is up to date", done.stdout)
        self.assertEqual(len(self.subjects()), count)
        self.assertEqual(self.pdlc("version.json"), marker)
        self.assertEqual(git(self.root, "status", "--porcelain"), "")

    def test_edited_file_keeps_its_base_hash(self):
        rel = "ports/checks.md"
        base = self.version_file()["files"][rel]
        (self.root / "pdlc" / rel).write_text("mine\n")
        git(self.root, "commit", "-qam", "mine")
        self.edit_plugin(rel)
        self.apply()
        self.assertEqual(self.version_file()["files"][rel], base)
        data = self.apply()  # still edited the next time
        self.assertEqual(self.statuses(data).get(rel), "edited")

    def test_commit_goes_to_the_unmerged_pdlc_branch(self):
        r = self.root
        (r / "pdlc/inbox/IN-0001-x.md").write_text(
            "# IN-0001 · X\n\nStatus: building · Ticket: none · Branch: pdlc/IN-0001-x · Added: 2026-10-10\n")
        change = r / "pdlc/changes/CH-0001-x/change.md"
        change.parent.mkdir(parents=True)
        change.write_text("# CH-0001 · X\n\nIntent: IN-0001 · Scope: CAP-x · Status: testing · "
                          "Ticket: none · Branch: pdlc/CH-0001-x · Base: main\n")
        git(r, "add", "-A")
        git(r, "commit", "-qm", "Plan IN-0001: x")
        git(r, "switch", "-qc", "pdlc/CH-0001-x")
        (r / "pdlc/changes/CH-0001-x/log.md").write_text("x\n")
        git(r, "add", "-A")
        git(r, "commit", "-qm", "Start CH-0001\n\nIntent: IN-0001\nChange: CH-0001")
        git(r, "switch", "-q", "main")
        self.edit_plugin("ports/checks.md")
        self.apply()
        self.assertEqual(git(r, "rev-parse", "--abbrev-ref", "HEAD"), "pdlc/CH-0001-x")
        self.assertEqual(git(r, "log", "-1", "--format=%s"), "Upgrade pdlc")
        body = git(r, "log", "-1", "--format=%b")
        self.assertIn("Intent: IN-0001", body)
        self.assertIn("Change: CH-0001", body)
        self.assertNotIn("Req:", body)
        self.assertEqual(commits.problems(str(r)), [])
        self.assertNotIn("Upgrade pdlc", git(r, "log", "main", "--format=%s"))

    def test_gitignore_line_is_added_on_main_only(self):
        data = self.apply()
        self.assertIn("pdlc/.tools/", (self.root / ".gitignore").read_text().splitlines())
        self.assertEqual(self.subjects()[0], "Upgrade pdlc")
        self.assertTrue(data["gitignore"])

    def test_open_changes_stop_the_upgrade(self):
        self.edit_plugin("ports/checks.md")
        (self.root / "stray.txt").write_text("x\n")
        done = self.run_script("apply", check=False)
        self.assertEqual(done.returncode, 3)
        self.assertIn("Commit or remove the open changes first.", done.stdout + done.stderr)
        self.assertNotEqual(self.pdlc("ports/checks.md"), (self.plugin / "skills/init/references/ports/checks.md").read_text())

    def test_not_a_pdlc_project(self):
        empty = Path(self.tmp.name) / "empty"
        empty.mkdir()
        git(empty, "init", "-q")
        done = subprocess.run([sys.executable, str(self.script), "apply", "--project", str(empty)],
                              env=ENV, capture_output=True, text=True)
        self.assertEqual(done.returncode, 4)

    def test_plan_writes_nothing(self):
        self.edit_plugin("ports/checks.md")
        done = self.run_script("plan", "--json")
        data = json.loads(done.stdout)
        self.assertEqual(self.statuses(data)["ports/checks.md"], "refreshed")
        self.assertEqual(git(self.root, "status", "--porcelain"), "")

    def test_spec_without_interface_files_one_intent(self):
        (self.root / "pdlc/specs/jobs/JOB-report.md").write_text(JOB_NO_INTERFACE)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "job")
        data = self.apply()
        self.assertEqual(len(data["spec_format"]), 1)
        intents = sorted((self.root / "pdlc/inbox").glob("IN-*-pdlc-spec-format.md"))
        self.assertEqual(len(intents), 1)
        text = intents[0].read_text()
        self.assertIn("Status: new", text)
        self.assertIn("JOB-report", text)
        self.assertIn("Awaits approval:", text)
        self.assertEqual(data["intent"], "IN-0001")
        found = subprocess.run([sys.executable, str(WRITING), str(intents[0])], capture_output=True, text=True)
        self.assertIn("No findings", found.stdout)
        self.apply()
        self.assertEqual(len(list((self.root / "pdlc/inbox").glob("IN-*-pdlc-spec-format.md"))), 1)

    def test_no_intent_flag(self):
        (self.root / "pdlc/specs/jobs/JOB-report.md").write_text(JOB_NO_INTERFACE)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "job")
        data = self.apply("--no-intent")
        self.assertEqual(len(data["spec_format"]), 1)
        self.assertEqual(list((self.root / "pdlc/inbox").glob("IN-*-pdlc-spec-format.md")), [])

    def test_config_sections_missing_are_reported_not_written(self):
        cfg = self.root / "pdlc/config.md"
        text = cfg.read_text()
        heading = re.findall(r"^## (.+)$", text, re.M)[-1]
        cfg.write_text(text.replace("## " + heading, "## Renamed section"))
        git(self.root, "commit", "-qam", "config")
        data = self.apply()
        self.assertIn(heading, data["config_missing"])
        self.assertNotIn(heading, cfg.read_text())

    def test_take_of_an_unknown_path_stops(self):
        done = self.run_script("apply", "--take", "pdlc/ports/nope.md", check=False)
        self.assertEqual(done.returncode, 2)
        self.assertIn("not a pdlc file: pdlc/ports/nope.md", done.stdout)

    def test_pdlc_branch_without_intent_file_is_not_committed(self):
        r = self.root
        git(r, "switch", "-qc", "pdlc/IN-0009-x")
        (r / "pdlc/inbox/note.md").write_text("x\n")
        git(r, "add", "-A")
        git(r, "commit", "-qm", "Start")
        git(r, "switch", "-q", "main")
        self.edit_plugin("ports/checks.md")
        done = self.run_script("apply", check=False)
        self.assertEqual(done.returncode, 6)
        self.assertNotIn("Upgraded from", done.stdout)
        self.assertIn("not committed", done.stdout)
        self.assertEqual(git(r, "log", "-1", "--format=%s"), "Start")
        self.assertNotEqual(git(r, "status", "--porcelain"), "")

    def test_same_version_refresh_is_worded(self):
        self.edit_plugin("ports/checks.md")
        done = self.run_script("apply")
        self.assertIn("Refreshed files at " + self.version_file()["pdlc"], done.stdout)
        self.assertNotIn("Upgraded from", done.stdout)

    def test_fixture_app_has_no_edited_default_spec(self):
        fixture = REPO / "bench/fixture-app"
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(fixture, tmp, dirs_exist_ok=True)
            git(tmp, "init", "-q", "-b", "main")
            git(tmp, "add", "-A")
            git(tmp, "commit", "-qm", "Set up pdlc")
            done = subprocess.run([sys.executable, str(SCRIPT), "plan", "--json", "--project", tmp],
                                  env=ENV, capture_output=True, text=True)
            data = json.loads(done.stdout)
        edited = [f["path"] for f in data["files"]
                  if f["path"].startswith("specs/design/") and f["status"].startswith("edited")]
        self.assertEqual(edited, [])


class KnownFiles(unittest.TestCase):
    def test_known_list_covers_the_current_sources(self):
        done = subprocess.run([sys.executable, str(KNOWN_SCRIPT), "--check"], cwd=REPO,
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


class VersionHook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "pdlc").mkdir()
        (self.root / "pdlc/config.md").write_text("# pdlc config\n")
        self.current = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())["version"]

    def tearDown(self):
        self.tmp.cleanup()

    def run_hook(self, prompt, cwd=None):
        payload = json.dumps({"prompt": prompt, "cwd": str(cwd or self.root)})
        return subprocess.run([sys.executable, str(VERSION_HOOK)], input=payload, capture_output=True,
                              text=True, env=dict(os.environ, CLAUDE_PLUGIN_ROOT=str(PLUGIN)))

    def test_missing_marker_gives_a_line(self):
        done = self.run_hook("/pdlc:ship add a thing")
        self.assertEqual(done.returncode, 0)
        self.assertIn("/pdlc:upgrade", done.stdout)
        self.assertIn("an older version", done.stdout)

    def test_older_marker_gives_a_line(self):
        (self.root / "pdlc/version.json").write_text(json.dumps({"pdlc": "0.1.0", "files": {}}))
        done = self.run_hook("/pdlc:intake x")
        self.assertIn("0.1.0", done.stdout)
        self.assertIn(self.current, done.stdout)

    def test_current_marker_is_silent(self):
        (self.root / "pdlc/version.json").write_text(json.dumps({"pdlc": self.current, "files": {}}))
        self.assertEqual(self.run_hook("/pdlc:intake x").stdout, "")

    def test_other_prompts_are_silent(self):
        self.assertEqual(self.run_hook("hello").stdout, "")
        self.assertEqual(self.run_hook("/pdlc:upgrade").stdout, "")
        self.assertEqual(self.run_hook("/pdlc:init defaults").stdout, "")
        with tempfile.TemporaryDirectory() as other:
            self.assertEqual(self.run_hook("/pdlc:ship x", cwd=other).stdout, "")

    def test_bad_input_never_blocks(self):
        done = subprocess.run([sys.executable, str(VERSION_HOOK)], input="not json", capture_output=True, text=True)
        self.assertEqual(done.returncode, 0)


if __name__ == "__main__":
    unittest.main()
