"""Tests for plugins/flow/commands/implement.md (allowed tools, tool rules,
plan-mode guard, missing-Commands flow, archiving and agent spawning)."""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prompt_files  # noqa: E402
from test_plan_command import QUIET_RULE, WATCH_RULE, example_runners  # noqa: E402

COMMAND = prompt_files.command_path("implement")


def step_headings(text):
    """Return the `## Step ...` heading titles in order, outside code fences."""
    _, body = prompt_files.split_frontmatter(text)
    titles = []
    in_fence = False
    for line in body.splitlines():
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"^## (Step .*?)\s*$", line)
        if match:
            titles.append(match.group(1))
    return titles


def step_section(text, prefix):
    """Return the body of the single `## Step` section whose title starts with prefix."""
    matches = [title for title in step_headings(text) if title.startswith(prefix)]
    if len(matches) != 1:
        raise AssertionError("expected one step starting %r, got %r" % (prefix, matches))
    return prompt_files.section(text, matches[0])


class ImplementFileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = prompt_files.read_text(COMMAND)
        cls.flat = prompt_files.flatten(cls.text)


class FrontmatterTest(ImplementFileTest):
    def test_allowed_tools_is_exactly_read_flow_edit_and_agent(self):
        meta = prompt_files.parse_frontmatter(self.text)
        self.assertEqual(meta["allowed-tools"], "Read, Edit(.flow/**), Agent")

    def test_allowed_tools_has_no_glob_grep_or_bash(self):
        meta = prompt_files.parse_frontmatter(self.text)
        tools = [tool.strip().lower() for tool in meta["allowed-tools"].split(",")]
        for tool in tools:
            self.assertNotIn(tool.split("(")[0], ("glob", "grep", "bash"))

    def test_keeps_existing_frontmatter_keys(self):
        meta = prompt_files.parse_frontmatter(self.text)
        self.assertIn("description", meta)
        self.assertEqual(meta["argument-hint"], "<feature-slug>")

    def test_no_instruction_to_use_glob_or_grep_tools(self):
        self.assertIsNone(re.search(r"\b(Glob|Grep)\b", self.text))


class PlanModeGuardTest(ImplementFileTest):
    def test_first_step_is_the_plan_mode_guard(self):
        steps = step_headings(self.text)
        self.assertTrue(steps, "implement.md has no steps")
        self.assertIn("plan-mode guard", steps[0].lower())

    def test_guard_stops_before_reading_feature_files_and_says_to_leave_plan_mode(self):
        guard = prompt_files.flatten(step_section(self.text, "Step 0"))
        self.assertIn("If the session is in plan mode, STOP", guard)
        self.assertIn("before reading or changing any feature file", guard)
        self.assertIn("Leave plan mode", guard)
        self.assertIn("again", guard)

    def test_guard_comes_before_the_instruction_that_sets_in_progress(self):
        guard_at = self.flat.index("## Step 0: Plan-mode guard")
        mark_at = self.flat.index("change this task's checkbox to `[>]`")
        self.assertLess(guard_at, mark_at)


class MissingCommandsTest(ImplementFileTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.step = prompt_files.flatten(step_section(cls.text, "Step 2"))

    def test_step_handles_spec_without_commands_section(self):
        self.assertIn("If it has no `## Commands` section", self.step)

    def test_commands_worked_out_from_project_config(self):
        self.assertIn("Work the commands out by reading the project config", self.step)

    def test_block_written_into_spec_in_the_commands_format(self):
        self.assertIn("Write the block into `BASE/SPEC.md`", self.step)
        for entry in ("Run from the project root.", "- Test:", "- Single test:",
                      "- Type-check:", "- Build:", "{file}"):
            self.assertIn(entry, self.step)

    def test_user_confirms_with_ask_user_question_before_other_changes(self):
        self.assertIn("confirm the block with AskUserQuestion", self.step)
        self.assertIn("Do this before any other change", self.step)

    def test_stops_on_no(self):
        self.assertIn('On "no", STOP.', self.step)

    def test_missing_commands_step_is_after_guard_and_before_marking(self):
        guard_at = self.flat.index("## Step 0: Plan-mode guard")
        commands_at = self.flat.index("confirm the block with AskUserQuestion")
        mark_at = self.flat.index("change this task's checkbox to `[>]`")
        self.assertLess(guard_at, commands_at)
        self.assertLess(commands_at, mark_at)


class QuietCommandRuleTest(ImplementFileTest):
    """Step 2 states the quiet, non-watch command rule, then runner examples."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.raw_step = step_section(cls.text, "Step 2")
        cls.step = prompt_files.flatten(cls.raw_step)

    def test_rule_and_watch_sentence_then_examples_from_three_runners(self):
        self.assertIn(QUIET_RULE, self.step)
        self.assertIn(WATCH_RULE, self.step)
        rule_at = self.step.index(QUIET_RULE)
        watch_at = self.step.index(WATCH_RULE, rule_at)
        after = self.step[watch_at + len(WATCH_RULE):]
        self.assertRegex(after, r"(?i)^\s*for example")
        runners = example_runners(after)
        self.assertGreaterEqual(
            len(runners), 3, "expected 3+ runners after 'for example', got %r" % runners
        )

    def test_tells_orchestrator_to_check_config_for_flag(self):
        self.assertIn(
            "Check the project's config or the runner's options for the right flag.",
            self.step,
        )

    def test_block_template_uses_quiet_vitest_examples(self):
        entries = dict(
            re.match(r"^- (Test|Single test): (.+)$", line).groups()
            for line in self.raw_step.splitlines()
            if re.match(r"^- (Test|Single test): ", line)
        )
        self.assertIn("`npx vitest run --reporter=dot`", entries["Test"])
        self.assertIn("`npx vitest run --reporter=dot {file}`", entries["Single test"])


class CurrentDetailsTest(ImplementFileTest):
    """Step 4 copies only this task's lines and summarises pointers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.step = prompt_files.flatten(step_section(cls.text, "Step 4"))
        details = re.search(
            r"## Details(.*?)## Scope", step_section(cls.text, "Step 4"), re.S
        )
        cls.details = prompt_files.flatten(details.group(1))

    def test_details_copy_verification_and_covers_verbatim(self):
        self.assertIn(
            "Copy only this task's description from TASKS.md, with its "
            "`Verification:` and `covers:` lines verbatim",
            self.details,
        )

    def test_pointer_replaced_by_summary_of_at_most_five_lines(self):
        self.assertIn(
            "points at earlier tasks' archives or at the SPEC, do not pass that "
            "pointer on",
            self.details,
        )
        self.assertIn("in at most 5 lines", self.details)
        self.assertIn(
            "Full notes: <path>. Read only if the summary isn't enough.", self.details
        )

    def test_forbids_reading_whole_archive_or_whole_spec(self):
        self.assertIn(
            "CURRENT.md never tells the agent to read a whole archive file or the "
            "whole SPEC",
            self.step,
        )

    def test_previous_attempts_still_read_first(self):
        attempts = re.search(
            r"## Previous attempts(.*?)## Implementation Log",
            step_section(self.text, "Step 4"),
            re.S,
        )
        self.assertIn(
            "list their paths and tell the agent to read them first so it does not "
            "repeat the same failure",
            prompt_files.flatten(attempts.group(1)),
        )


class ArchiveAndEvidenceTest(ImplementFileTest):
    def test_archiving_reads_current_with_read_and_writes_archive_with_write(self):
        archive = prompt_files.flatten(step_section(self.text, "Step 7"))
        self.assertIn(
            "Archive by reading `BASE/CURRENT.md` with Read and writing its full "
            "content, unchanged, to the archive file with Write",
            archive,
        )

    def test_current_reset_with_write(self):
        archive = prompt_files.flatten(step_section(self.text, "Step 7"))
        self.assertIn("Reset `BASE/CURRENT.md` back to a clean, empty state with Write", archive)

    def test_no_copy_wording_left_for_archiving(self):
        self.assertNotIn("Copy `BASE/CURRENT.md`", self.flat)

    def test_failed_attempts_counted_with_ls_on_archive(self):
        checklist = prompt_files.flatten(step_section(self.text, "Step 3"))
        self.assertIn(
            "Count the previous failed attempts for this task with `ls` on `BASE/archive/`",
            checklist,
        )

    def test_test_file_existence_checked_with_read_or_ls(self):
        evidence = prompt_files.flatten(step_section(self.text, "Step 6"))
        self.assertIn("check it yourself with Read or `ls`", evidence)

    def test_evidence_includes_type_check_result(self):
        evidence = prompt_files.flatten(step_section(self.text, "Step 6"))
        self.assertIn("`Type-check result:` shows PASS, or \"none\"", evidence)


class BlockedReportTest(ImplementFileTest):
    def test_blocked_report_uses_agent_reasons(self):
        report = prompt_files.flatten(step_section(self.text, "Step 8"))
        self.assertIn("missing command", report)
        self.assertIn("environment", report)
        self.assertIn("BLOCKED reason", report)

    def test_no_mention_of_missing_test_framework(self):
        self.assertNotIn("no test framework", self.flat.lower())
        self.assertNotIn("framework the agent recommended", self.flat)


class AgentSpawnTest(ImplementFileTest):
    def test_spawns_with_agent_tool_in_the_foreground(self):
        spawn = prompt_files.flatten(step_section(self.text, "Step 5"))
        self.assertIn("**Agent tool**", spawn)
        self.assertIn("`run_in_background: false`", spawn)
        self.assertIn("flow:implementation-agent", spawn)

    def test_waits_and_archives_in_the_same_turn(self):
        spawn = prompt_files.flatten(step_section(self.text, "Step 5"))
        self.assertIn("Wait for the agent's result", spawn)
        self.assertIn("in this same turn", spawn)
        self.assertIn("until the attempt is archived", spawn)

    def test_no_task_tool_wording(self):
        self.assertNotIn("Task tool", self.flat)


class ToolRulesTest(ImplementFileTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rules = prompt_files.flatten(prompt_files.section(cls.text, "Tool rules"))

    def test_reading_only_with_read(self):
        self.assertIn("read files only with Read", self.rules)

    def test_searching_only_with_read_only_search_commands(self):
        self.assertIn(
            "search, list and check that files exist only with single read-only "
            "search commands",
            self.rules,
        )
        for command in ("`grep -rn`", "`grep -rl`", "`ls`"):
            self.assertIn(command, self.rules)
        self.assertIn("`find` without `-exec` or `-delete`", self.rules)
        self.assertIn(
            "Quote patterns, use literal paths inside the project, and never add "
            "`cd`, `;`, `&&`, pipes or variables",
            self.rules,
        )

    def test_flow_files_changed_with_edit_or_write(self):
        self.assertIn("change `.flow` files only with Edit or Write", self.rules)

    def test_bash_limited_to_read_only_search_commands(self):
        self.assertIn("use Bash only for the read-only search commands in rule 2", self.rules)
        self.assertNotIn("one-off", self.rules)


class BashMentionTest(ImplementFileTest):
    def test_bash_appears_only_inside_tool_rules(self):
        self.assertIn("Bash", prompt_files.section(self.text, "Tool rules"))
        outside = prompt_files.outside_section(self.text, "Tool rules")
        frontmatter, _ = prompt_files.split_frontmatter(self.text)
        self.assertNotIn("Bash", outside)
        self.assertNotIn("Bash", frontmatter)


if __name__ == "__main__":
    unittest.main()
