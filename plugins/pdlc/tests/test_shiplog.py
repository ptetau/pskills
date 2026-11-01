"""Tests for pdlc's ship log hook. Run: python3 -m unittest discover plugins/pdlc/tests"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).parent.parent
HOOK = PLUGIN / "hooks/shiplog.py"
HOOKS_JSON = PLUGIN / "hooks/hooks.json"

INTENT = "# IN-0001 · Password reset\n\nStatus: %s · Ticket: none · " \
         "Branch: pdlc/IN-0001-reset · Added: 2026-10-10\n"
SESSION = "sess-1"


def git(root, *args):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=root,
                          capture_output=True, text=True, check=True).stdout.strip()


class ShipLog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = self.root = Path(self.tmp.name)
        (r / "pdlc/inbox").mkdir(parents=True)
        (r / "pdlc/config.md").write_text("# pdlc config\n")
        (r / "pdlc/inbox/IN-0001-reset.md").write_text(INTENT % "specifying")
        git(r, "init", "-q", "-b", "main")
        git(r, "add", "-A")
        git(r, "commit", "-qm", "Set up pdlc")
        git(r, "switch", "-qc", "pdlc/IN-0001-reset")

    def tearDown(self):
        self.tmp.cleanup()

    # helpers
    def hook(self, event, session=SESSION, cwd=None, **fields):
        data = {"hook_event_name": event, "session_id": session, "cwd": str(cwd or self.root)}
        data.update(fields)
        run = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(data),
                             capture_output=True, text=True, timeout=30)
        return run

    def start(self, prompt="/pdlc:ship defaults add password reset"):
        return self.hook("UserPromptSubmit", prompt=prompt)

    def log(self):
        files = sorted((self.root / "pdlc/.logs").glob("ship-*.jsonl"))
        self.assertEqual(len(files), 1)
        return [json.loads(line) for line in files[0].read_text().splitlines()]

    def events(self, name):
        return [e for e in self.log() if e["event"] == name]

    def commit(self, subject, status=None):
        (self.root / "pdlc/inbox/note.md").write_text(subject + "\n" + str(len(subject)))
        if status:
            (self.root / "pdlc/inbox/IN-0001-reset.md").write_text(INTENT % status)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "%s\n\nIntent: IN-0001" % subject)

    def after_bash(self):
        return self.hook("PostToolUse", tool_name="Bash",
                         tool_input={"command": "git commit -m x"}, tool_response={})

    def stop(self, **fields):
        return self.hook("Stop", stop_hook_active=False, **fields)

    def blocked(self, run):
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(run.stdout.strip(), "expected a block")
        out = json.loads(run.stdout)
        self.assertEqual(out["decision"], "block")
        return out["reason"]

    def last_turn_end(self):
        return [e for e in self.log() if e["event"] == "turn_end"][-1]

    # 1
    def test_run_start_and_current(self):
        self.assertEqual(self.start().returncode, 0)
        entry = self.events("run_start")[0]
        self.assertIn("/pdlc:ship defaults", entry["prompt"])
        self.assertEqual(entry["branch"], "pdlc/IN-0001-reset")
        self.assertTrue(entry["head"])
        self.assertEqual(entry["session"], SESSION)
        self.assertIn(entry["run"], (self.root / "pdlc/.logs/current").read_text())

    def test_other_prompt_makes_no_log(self):
        run = self.start("/pdlc:intake add a thing")
        self.assertEqual((run.returncode, run.stdout), (0, ""))
        self.assertFalse((self.root / "pdlc/.logs").exists())
        self.start("please ship it later")
        self.assertFalse((self.root / "pdlc/.logs").exists())

    def test_ship_skill_call_starts_a_run(self):
        self.hook("PostToolUse", tool_name="Skill", tool_input={"skill": "pdlc:ship"})
        self.assertEqual(len(self.events("run_start")), 1)

    def test_logs_folder_ignores_itself(self):
        self.start()
        self.assertEqual((self.root / "pdlc/.logs/.gitignore").read_text().strip(), "*")
        self.assertEqual(git(self.root, "status", "--porcelain"), "")

    def test_stage_start(self):
        self.start()
        self.hook("PostToolUse", tool_name="Skill", tool_input={"skill": "pdlc:intake"})
        self.hook("PostToolUse", tool_name="Skill", tool_input={"skill": "other:thing"})
        stages = self.events("stage_start")
        self.assertEqual([s["stage"] for s in stages], ["pdlc:intake"])
        self.assertEqual(stages[0]["branch"], "pdlc/IN-0001-reset")

    # 2
    def test_commit_entry(self):
        self.start()
        self.commit("Specify IN-0001: reset")
        self.after_bash()
        self.after_bash()  # the same commit makes one entry
        (entry,) = self.events("commit")
        self.assertEqual(entry["subject"], "Specify IN-0001: reset")
        self.assertTrue(entry["stage_end"])
        self.assertEqual(entry["branch"], "pdlc/IN-0001-reset")
        self.assertEqual(entry["trailers"], {"Intent": "IN-0001"})
        self.assertEqual(entry["files"], 1)
        self.assertEqual(len(entry["hash"]), 40)

    def test_commit_that_ends_no_stage(self):
        self.start()
        self.commit("Update IN-0001: notes")
        self.after_bash()
        self.assertFalse(self.events("commit")[0]["stage_end"])

    def test_old_commit_is_not_logged(self):
        self.start()
        self.after_bash()
        self.assertEqual(self.events("commit"), [])

    # 3
    def test_agent_attempts_and_duration(self):
        self.start()
        self.hook("PostToolUse", tool_name="Skill", tool_input={"skill": "pdlc:verify"})
        for n in (1, 2):
            tool = {"subagent_type": "pdlc:reviewer", "description": "review %d" % n}
            self.hook("PreToolUse", tool_name="Agent", tool_input=tool, tool_use_id="tu%d" % n)
            self.hook("PostToolUse", tool_name="Agent", tool_input=tool, tool_use_id="tu%d" % n)
        starts = self.events("agent_start")
        self.assertEqual([s["attempt"] for s in starts], [1, 2])
        self.assertEqual(starts[0]["agent"], "pdlc:reviewer")
        ends = self.events("agent_end")
        self.assertEqual(len(ends), 2)
        self.assertIsInstance(ends[0]["seconds"], (int, float))
        self.assertEqual(ends[1]["description"], "review 2")

    def test_attempt_resets_in_a_new_stage(self):
        self.start()
        tool = {"subagent_type": "pdlc:reviewer", "description": "d"}
        self.hook("PreToolUse", tool_name="Agent", tool_input=tool, tool_use_id="a")
        self.hook("PostToolUse", tool_name="Skill", tool_input={"skill": "pdlc:show"})
        self.hook("PreToolUse", tool_name="Agent", tool_input=tool, tool_use_id="b")
        self.assertEqual([s["attempt"] for s in self.events("agent_start")], [1, 1])

    def test_subagent_stop(self):
        self.start()
        self.hook("SubagentStop", agent_type="pdlc:builder")
        self.assertEqual(self.events("agent_stop")[0]["agent"], "pdlc:builder")

    # 4
    def test_tool_error_and_rate_limit(self):
        self.start()
        self.hook("PostToolUseFailure", tool_name="Bash", error="boom " * 200)
        self.hook("PostToolUseFailure", tool_name="Agent", error="API Error: 429 rate limit hit")
        plain, limited = self.events("tool_error")
        self.assertFalse(plain["rate_limit"])
        self.assertEqual(len(plain["error"]), 500)
        self.assertTrue(limited["rate_limit"])
        self.assertEqual(limited["tool"], "Agent")

    # 5
    def test_stop_after_specify_only_blocks(self):
        self.start()
        self.commit("Specify IN-0001: x")
        self.after_bash()
        reason = self.blocked(self.stop())
        self.assertIn("not at an end state", reason)
        self.assertIn("Stop <id>: <why>", reason)
        entry = self.events("stop_blocked")[0]
        self.assertEqual(entry["last_subject"], "Specify IN-0001: x")
        self.assertEqual(entry["block"], 1)
        self.assertIn("reason", entry)

    # 6
    def test_stop_after_recorded_stop(self):
        self.start()
        self.commit("Specify IN-0001: x")
        self.after_bash()
        self.commit("Stop IN-0001: two requirements contradict")
        self.after_bash()
        run = self.stop()
        self.assertEqual((run.returncode, run.stdout), (0, ""))
        self.assertEqual(self.last_turn_end()["end_state"], "stopped")

    def test_stop_found_by_git_alone(self):
        # no PostToolUse entry was logged: the rule still reads git
        self.start()
        self.commit("Stop IN-0001: why")
        self.assertEqual(self.stop().stdout, "")
        self.assertEqual(self.last_turn_end()["end_state"], "stopped")

    # 7
    def test_stop_after_propose(self):
        self.start()
        self.commit("Propose CH-0001: x", status="in review")
        self.after_bash()
        self.assertEqual(self.stop().stdout, "")
        self.assertEqual(self.last_turn_end()["end_state"], "proposed")

    def test_propose_needs_intent_in_review(self):
        self.start()
        self.commit("Propose CH-0001: x", status="building")
        self.blocked(self.stop())

    # 8
    def test_stop_with_no_commit(self):
        self.start()
        self.assertEqual(self.stop().stdout, "")
        self.assertEqual(self.last_turn_end()["end_state"], "no work")

    # 9
    def test_third_stop_lets_the_turn_end(self):
        self.start()
        self.commit("Specify IN-0001: x")
        self.blocked(self.stop())
        self.blocked(self.hook("Stop", stop_hook_active=True))
        run = self.hook("Stop", stop_hook_active=True)
        self.assertEqual((run.returncode, run.stdout), (0, ""))
        self.assertEqual(self.last_turn_end()["end_state"], "unrecorded")
        self.assertEqual(len(self.events("stop_blocked")), 2)

    def test_turn_end_ends_the_run(self):
        self.start()
        self.stop()
        self.assertFalse((self.root / "pdlc/.logs/current").exists())
        self.assertEqual(self.stop().stdout, "")  # a later turn is not a ship run
        self.assertEqual(len(self.events("turn_end")), 1)

    # 10 and the rule that a normal session is never blocked
    def test_stop_with_no_run(self):
        run = self.stop()
        self.assertEqual((run.returncode, run.stdout), (0, ""))
        self.assertFalse((self.root / "pdlc/.logs").exists())

    def test_normal_session_never_blocked_or_logged(self):
        self.commit("Specify IN-0001: x")  # work that looks like ship, but no ship run
        calls = [
            ("UserPromptSubmit", dict(prompt="fix the bug")),
            ("PostToolUse", dict(tool_name="Bash", tool_input={"command": "git commit"})),
            ("PostToolUse", dict(tool_name="Skill", tool_input={"skill": "pdlc:intake"})),
            ("PreToolUse", dict(tool_name="Agent", tool_input={"subagent_type": "x"})),
            ("PostToolUseFailure", dict(tool_name="Bash", error="rate limit")),
            ("SubagentStop", dict(agent_type="x")),
            ("Stop", dict(stop_hook_active=False)),
        ]
        for event, fields in calls:
            run = self.hook(event, **fields)
            self.assertEqual((run.returncode, run.stdout, run.stderr), (0, "", ""), event)
        self.assertFalse((self.root / "pdlc/.logs").exists())

    def test_other_session_is_not_blocked(self):
        self.start()
        self.commit("Specify IN-0001: x")
        run = self.hook("Stop", session="another", stop_hook_active=False)
        self.assertEqual((run.returncode, run.stdout), (0, ""))
        self.assertEqual(self.events("turn_end"), [])

    def test_stale_current_file_is_not_blocking(self):
        (self.root / "pdlc/.logs").mkdir()
        (self.root / "pdlc/.logs/current").write_text("ship-gone.jsonl\n")
        run = self.stop()
        self.assertEqual((run.returncode, run.stdout), (0, ""))

    def test_outside_a_pdlc_project(self):
        with tempfile.TemporaryDirectory() as other:
            for event, fields in [("UserPromptSubmit", dict(prompt="/pdlc:ship")), ("Stop", {})]:
                run = self.hook(event, cwd=other, **fields)
                self.assertEqual((run.returncode, run.stdout, run.stderr), (0, "", ""))
            self.assertFalse((Path(other) / "pdlc").exists())

    # 11
    def test_summary(self):
        self.start()
        self.hook("PostToolUse", tool_name="Skill", tool_input={"skill": "pdlc:intake"})
        self.commit("Specify IN-0001: x")
        self.after_bash()
        self.hook("PostToolUse", tool_name="Skill", tool_input={"skill": "pdlc:ready"})
        for n in (1, 2):
            tool = {"subagent_type": "pdlc:reviewer", "description": "d"}
            self.hook("PreToolUse", tool_name="Agent", tool_input=tool, tool_use_id=str(n))
        self.hook("PostToolUseFailure", tool_name="Agent", error="429 overloaded")
        log = next((self.root / "pdlc/.logs").glob("ship-*.jsonl"))
        out = subprocess.run([sys.executable, str(HOOK), "summary", str(log)],
                             capture_output=True, text=True).stdout
        self.assertIn("pdlc:intake", out)
        self.assertIn("pdlc:ready", out)
        intake = next(l for l in out.splitlines() if "pdlc:intake" in l)
        self.assertIn("Specify IN-0001: x", intake)
        ready = next(l for l in out.splitlines() if "pdlc:ready" in l)
        self.assertRegex(ready, r"\|\s*1\s*\|\s*1\s*\|\s*1\s*$")  # retries, errors, rate limits
        self.assertIn("the log ends with no turn_end", out)

    def test_summary_end_line(self):
        self.start()
        self.commit("Stop IN-0001: why")
        self.stop()
        log = next((self.root / "pdlc/.logs").glob("ship-*.jsonl"))
        out = subprocess.run([sys.executable, str(HOOK), "summary", str(log)],
                             capture_output=True, text=True).stdout
        self.assertIn("end state: stopped", out)
        self.assertNotIn("no turn_end", out)

    # 12
    def test_broken_stdin(self):
        for text in ("", "not json", "[1]", '{"hook_event_name": 5}'):
            run = subprocess.run([sys.executable, str(HOOK)], input=text,
                                 capture_output=True, text=True, timeout=30)
            self.assertEqual((run.returncode, run.stdout, run.stderr), (0, "", ""), text)

    def test_hook_error_is_logged_and_never_fatal(self):
        self.start()
        # a corrupt log line must not stop the Stop rule from answering
        log = next((self.root / "pdlc/.logs").glob("ship-*.jsonl"))
        with open(log, "a") as handle:
            handle.write("{broken\n")
        run = self.stop()
        self.assertEqual(run.returncode, 0)

    # hooks.json
    def test_hooks_json_wires_the_events(self):
        hooks = json.loads(HOOKS_JSON.read_text())["hooks"]
        for event in ("UserPromptSubmit", "PreToolUse", "PostToolUse", "PostToolUseFailure",
                      "Stop", "SubagentStop"):
            commands = [h["command"] for entry in hooks[event] for h in entry["hooks"]]
            self.assertTrue(any("shiplog.py" in c for c in commands), event)
        prompt = [h["command"] for e in hooks["UserPromptSubmit"] for h in e["hooks"]]
        self.assertTrue(any("version.py" in c for c in prompt))
        matchers = {e.get("matcher") for e in hooks["PostToolUse"]}
        self.assertTrue(any("Skill" in (m or "") and "Agent" in (m or "") for m in matchers))


if __name__ == "__main__":
    unittest.main()
