#!/usr/bin/env python3
"""Tests for the scripted rubric item (the `check` field). Run: python3 test_suite_check.py"""

import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHEMA = os.path.join(ROOT, "vet", "references", "suite.schema.json")
WORKFLOW = os.path.join(ROOT, "vet", "references", "vet.workflow.js")
PLACEHOLDERS = {"{run}", "{bench}"}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class SchemaTest(unittest.TestCase):
    def test_item_has_optional_string_check(self):
        item = load(SCHEMA)["$defs"]["item"]
        self.assertEqual(item["properties"]["check"]["type"], "string")
        self.assertNotIn("check", item["required"])


class SuiteTest(unittest.TestCase):
    def suites(self):
        return glob.glob(os.path.join(ROOT, "evals", "*", "suite.json"))

    def test_every_check_is_a_command_with_known_placeholders(self):
        for path in self.suites():
            for item in load(path)["rubric"]:
                if "check" not in item:
                    continue
                check = item["check"]
                self.assertIn("{run}", check, f"{path} {item['id']}")
                for name in re.findall(r"\{[a-z]+\}", check):
                    self.assertIn(name, PLACEHOLDERS, f"{path} {item['id']}")

    def test_ship_r5_and_r7_have_a_check(self):
        rubric = load(os.path.join(ROOT, "evals", "pdlc-ship", "suite.json"))["rubric"]
        by_id = {i["id"]: i for i in rubric}
        for rid in ("R5", "R7"):
            self.assertIn("check", by_id[rid], rid)
            self.assertIn("check_trailers.py", by_id[rid]["check"], rid)
        self.assertNotEqual(by_id["R5"]["check"], by_id["R7"]["check"])


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.js = read(WORKFLOW)

    def test_item_text_shows_the_check(self):
        self.assertIn("i.check", self.js)

    def test_grade_rules_tell_the_grader_to_copy_the_verdict(self):
        self.assertIn("scripted check", self.js)
        self.assertIn("{run}", self.js)
        self.assertIn("{bench}", self.js)

    def test_grade_rules_copy_the_verdict_of_a_check_including_n_a(self):
        self.assertIn('Copy that verdict exactly, including "n/a"', self.js)
        self.assertIn('"met" | "partial" | "missed" | "n/a"', self.js)
        self.assertNotIn("give n/a and do not run the command", self.js)

    def test_runner_plugin_calls_vetrun_with_the_plugin_and_replies(self):
        for text in ("args.runner", "args.pluginDir", "run_bench.py vetrun", "--reply", "--plugin", "--capture",
                     "RUNNER === 'plugin' ? pluginRunPrompt"):
            self.assertIn(text, self.js)

    def test_runner_is_documented_in_the_skill(self):
        skill = read(os.path.join(ROOT, "vet", "SKILL.md"))
        self.assertIn('"runner"', skill)
        self.assertIn('"pluginDir"', skill)

    def test_bench_directory_comes_from_args_or_vet_scripts(self):
        self.assertIn("args.benchDir", self.js)


HARNESS = """
const fs = require('fs')
const src = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const args = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'))
const prompts = []
const agent = async (text, opts) => {
  prompts.push(text)
  if (process.argv[4] === 'grade' && text.startsWith('You are running')) return { status: 'ok', capture: '/w/.vet-capture/P01-r01.md' }
  throw new Error('stop')
}
const f = new AsyncFunction('args', 'agent', 'log', 'phase', 'parallel', 'pool', src)
f(args, agent, () => {}, () => {}, async (xs) => Promise.all(xs.map((x) => x())), null).then(() => console.log(JSON.stringify(prompts)), () => console.log(JSON.stringify(prompts)))
"""

SETUP = ("Setup, before you start: run `python3 /b/run_bench.py prepare --dest proj --plugin PLUGIN`. "
         "PLUGIN is the folder two levels above the skill file. Then treat `proj` as the project root. "
         "This session cannot start agents. Where the skill starts a pdlc agent, do that agent's work yourself. "
         "Follow its file, and keep to its limits: a reviewer reads only its packet. "
         "In the capture, list each new commit with `git -C proj log --all --not start`.")


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class RunnerPromptTest(unittest.TestCase):
    """The text that the run agent gets, for each runner. The script runs under node with a stub agent."""

    def run_grade_prompt(self, prompt):
        return self.run_prompts("agent", prompt, mode="grade", grade=True)

    def run_prompts(self, runner, prompt, mode="run", grade=False):
        prompt = {"id": "P01", "axis": "a", "exercises": "e", "replies": ["ok"], **prompt}
        args = {"skill": {"name": "pdlc:ship", "dir": "/s", "file": "/s/SKILL.md"}, "vetScripts": "/v/vet/scripts",
                "runs": 2, "wave": 2, "runner": runner, "pluginDir": "/plug",
                "suite": {"rubric": [{"id": "R1", "kind": "outcome", "criterion": "c", "pass": "p", "partial": "q",
                                      "weight": 1, "source": "s"}],
                          "structure": {"summary": "s", "elements": []}, "prompts": [prompt]}}
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        harness, argfile = os.path.join(folder, "h.js"), os.path.join(folder, "args.json")
        with open(harness, "w") as f:
            f.write(HARNESS)
        with open(argfile, "w") as f:
            json.dump(args, f)
        out = subprocess.run(["node", harness, WORKFLOW, argfile, mode], capture_output=True, text=True, check=True).stdout
        prompts = json.loads(out)
        if grade:
            return next(t for t in prompts if t.startswith("You are grading"))
        return prompts[0]

    def test_agent_runner_shows_prompt_then_setup_as_one_text(self):
        joined = self.run_prompts("agent", {"prompt": "defaults Add x.\n\n" + SETUP})
        split = self.run_prompts("agent", {"prompt": "defaults Add x.", "setup": SETUP, "project": "proj"})
        self.assertEqual(split, joined)
        self.assertIn("/pdlc:ship defaults Add x.\n\n" + SETUP, split)

    def test_grade_prompt_names_the_project_folder_and_the_run_rule(self):
        text = self.run_grade_prompt({"prompt": "defaults Add x.", "setup": SETUP, "project": "proj"})
        self.assertIn("Project folder: proj", text)
        self.assertIn("replace {run} with the absolute path of the run's project", text)
        self.assertIn('joined with the "Project folder" above when one is given', text)

    def test_grade_prompt_without_a_project_has_no_project_line(self):
        text = self.run_grade_prompt({"prompt": "defaults Add x."})
        self.assertNotIn("Project folder", text.split("An item with")[0])
        self.assertIn("replace {run} with the absolute path of the run's project", text)

    def test_agent_runner_without_setup_is_unchanged(self):
        text = self.run_prompts("agent", {"prompt": "defaults Add x."})
        self.assertIn("The user's message is:\n/pdlc:ship defaults Add x.\n\nThe user is not live.", text)

    def test_plugin_runner_follows_the_setup_with_the_plugin_dir(self):
        text = self.run_prompts("plugin", {"prompt": "defaults Add x.", "setup": SETUP, "project": "proj"})
        self.assertIn("run_bench.py prepare --dest proj --plugin PLUGIN", text)
        self.assertIn("PLUGIN is /plug", text)

    def test_plugin_runner_drops_the_agent_only_sentences(self):
        text = self.run_prompts("plugin", {"prompt": "defaults Add x.", "setup": SETUP, "project": "proj"})
        for gone in ("cannot start agents", "reads only its packet", "do that agent's work yourself",
                     "In the capture, list each new commit"):
            self.assertNotIn(gone, text)

    def test_plugin_runner_gives_vetrun_the_project_and_only_the_users_words(self):
        text = self.run_prompts("plugin", {"prompt": "defaults Add x.", "setup": SETUP, "project": "proj"})
        command = [l for l in text.splitlines() if "run_bench.py vetrun" in l][0]
        self.assertIn("--project <the absolute path of your working directory>/proj ", command)
        self.assertIn("--prompt '/pdlc:ship defaults Add x.'", command)
        self.assertIn("--root <the absolute path of your working directory> ", command)
        self.assertNotIn("Setup", command)
        self.assertIn("The user's message is:\n/pdlc:ship defaults Add x.\n\nThe user is not live.", text)

    def test_plugin_runner_without_project_runs_in_the_worktree(self):
        text = self.run_prompts("plugin", {"prompt": "defaults Add x."})
        command = [l for l in text.splitlines() if "run_bench.py vetrun" in l][0]
        self.assertIn("--project <the absolute path of your working directory> --root", command)


class SetupFieldTest(unittest.TestCase):
    def test_schema_has_optional_string_setup_and_project(self):
        prompt = load(SCHEMA)["$defs"]["prompt"]
        for name in ("setup", "project"):
            self.assertEqual(prompt["properties"][name]["type"], "string")
            self.assertNotIn(name, prompt["required"])

    def test_every_project_is_a_relative_folder_inside_the_worktree(self):
        for path in glob.glob(os.path.join(ROOT, "evals", "*", "suite.json")):
            for p in load(path)["prompts"]:
                for name in ("setup", "project"):
                    self.assertIsInstance(p.get(name, ""), str, f"{path} {p['id']}")
                project = p.get("project")
                if project is not None:
                    self.assertTrue(project and not project.startswith("/") and ".." not in project.split("/"),
                                    f"{path} {p['id']}")
                    self.assertIn("setup", p, f"{path} {p['id']}: project needs a setup")

    def test_pdlc_prompts_keep_the_setup_out_of_the_user_words(self):
        for path in glob.glob(os.path.join(ROOT, "evals", "pdlc-*", "suite.json")):
            for p in load(path)["prompts"]:
                self.assertNotIn("Setup, before you start", p["prompt"], f"{path} {p['id']}")
                self.assertTrue(p["setup"].startswith("Setup, before you start: run `python3 "), f"{path} {p['id']}")
                self.assertEqual(p["project"], "proj", f"{path} {p['id']}")
                self.assertIn("--dest proj", p["setup"], f"{path} {p['id']}")

    def test_workflow_reads_both_fields(self):
        js = read(WORKFLOW)
        self.assertIn("p.setup", js)
        self.assertIn("p.project", js)



if __name__ == "__main__":
    unittest.main()
