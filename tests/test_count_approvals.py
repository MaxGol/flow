"""Tests for scripts/count_approvals.py, run against synthetic transcripts."""

import os
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "count_approvals.py")
FIXTURES = os.path.join(REPO_ROOT, "tests", "fixtures")


def fixture(name):
    return os.path.join(FIXTURES, name)


def run_script(*args):
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=30,
    )


class ImplementRunTest(unittest.TestCase):
    """Default command (flow:implement) on a session with mixed activity."""

    @classmethod
    def setUpClass(cls):
        cls.result = run_script(fixture("session_mixed.jsonl"))
        cls.lines = cls.result.stdout.strip().splitlines()

    def test_lists_every_user_answered_prompt_in_run_and_its_subagents(self):
        self.assertEqual(
            self.lines,
            [
                "main | Bash | cat .flow/features/my-feature/TASKS.md | user_temporary",
                "main | Bash | cp .flow/features/my-feature/CURRENT.md archive.md | user_reject",
                "main | Edit | /repo/.flow/features/my-feature/TASKS.md | user_permanent",
                "flow:implementation-agent | Bash | python3 -m unittest discover -s tests | user_temporary",
                "flow:implementation-agent | Edit | /repo/src/rejected.py | user_reject",
                "approvals: 5",
            ],
        )

    def test_last_line_is_total_and_exit_code_is_1(self):
        self.assertEqual(self.lines[-1], "approvals: 5")
        self.assertEqual(self.result.returncode, 1)
        self.assertEqual(self.result.stderr, "")

    def test_counts_turns_after_task_notification_and_hand_back(self):
        self.assertIn(
            "main | Bash | cp .flow/features/my-feature/CURRENT.md archive.md | user_reject",
            self.lines,
        )
        self.assertIn(
            "main | Edit | /repo/.flow/features/my-feature/TASKS.md | user_permanent",
            self.lines,
        )

    def test_counts_user_reject_in_main_and_subagent(self):
        rejects = [line for line in self.lines if line.endswith("| user_reject")]
        self.assertEqual(len(rejects), 2)

    def test_excludes_ask_user_question(self):
        self.assertFalse(any("AskUserQuestion" in line for line in self.lines))

    def test_excludes_auto_approved_calls(self):
        self.assertFalse(any("SPEC.md" in line for line in self.lines))
        self.assertFalse(any("/repo/src/auto.py" in line for line in self.lines))

    def test_excludes_calls_outside_the_run(self):
        output = self.result.stdout
        self.assertNotIn("before-run", output)
        self.assertNotIn("after-run", output)
        self.assertNotIn("outside-subagent", output)
        self.assertNotIn("general-purpose", output)

    def test_excludes_other_command_runs(self):
        output = self.result.stdout
        self.assertNotIn("verify-main", output)
        self.assertNotIn("flow:verification-agent", output)


class VerifyRunTest(unittest.TestCase):
    def test_command_option_selects_verify_runs(self):
        result = run_script(fixture("session_mixed.jsonl"), "--command", "flow:verify")
        self.assertEqual(
            result.stdout.strip().splitlines(),
            [
                "main | Bash | echo verify-main | user_temporary",
                "flow:verification-agent | Bash | curl -s http://localhost:8000/health | user_temporary",
                "approvals: 2",
            ],
        )
        self.assertEqual(result.returncode, 1)


class ZeroApprovalsTest(unittest.TestCase):
    def test_zero_approvals_prints_total_and_exits_0(self):
        result = run_script(fixture("session_clean.jsonl"))
        self.assertEqual(result.stdout.strip().splitlines(), ["approvals: 0"])
        self.assertEqual(result.returncode, 0)


class ErrorTest(unittest.TestCase):
    def assert_error(self, result, fragment):
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn(fragment, result.stderr)

    def test_missing_file_exits_2(self):
        result = run_script(fixture("does_not_exist.jsonl"))
        self.assert_error(result, "not found")

    def test_unreadable_file_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "binary.jsonl")
            with open(path, "wb") as handle:
                handle.write(b"\xff\xfe\x00not utf-8\n")
            result = run_script(path)
        self.assert_error(result, "cannot read")

    def test_session_without_implement_run_exits_2(self):
        result = run_script(fixture("session_no_run.jsonl"))
        self.assert_error(result, "no /flow:implement run")

    def test_session_without_verify_run_exits_2(self):
        result = run_script(fixture("session_clean.jsonl"), "--command", "flow:verify")
        self.assert_error(result, "no /flow:verify run")


if __name__ == "__main__":
    unittest.main()
