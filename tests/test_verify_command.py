"""Tests for plugins/flow/commands/verify.md (allowed tools, tool rules,
plan-mode guard, missing-Commands flow, agent spawning, VERIFY.md archiving
and how the verdict is applied per task)."""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prompt_files  # noqa: E402

COMMAND = prompt_files.command_path("verify")


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


def verdict_branch(step_text, start_marker, end_marker=None):
    """Return the flattened slice of a step between two bold branch markers."""
    flat = prompt_files.flatten(step_text)
    start = flat.index(start_marker)
    end = flat.index(end_marker, start) if end_marker else len(flat)
    return flat[start:end]


class VerifyFileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = prompt_files.read_text(COMMAND)
        cls.flat = prompt_files.flatten(cls.text)


class FrontmatterTest(VerifyFileTest):
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


class ToolRulesTest(VerifyFileTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rules = prompt_files.flatten(prompt_files.section(cls.text, "Tool rules"))

    def test_tool_rules_section_comes_before_the_steps(self):
        rules_at = self.flat.index("## Tool rules")
        first_step_at = self.flat.index("## Step 0")
        self.assertLess(rules_at, first_step_at)

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
        self.assertIn("Run nothing else through it", self.rules)
        self.assertNotIn("one-off", self.rules)


class BashMentionTest(VerifyFileTest):
    def test_bash_appears_only_inside_tool_rules(self):
        self.assertIn("Bash", prompt_files.section(self.text, "Tool rules"))
        outside = prompt_files.outside_section(self.text, "Tool rules")
        frontmatter, _ = prompt_files.split_frontmatter(self.text)
        self.assertNotIn("Bash", outside)
        self.assertNotIn("Bash", frontmatter)


class PlanModeGuardTest(VerifyFileTest):
    def test_first_step_is_the_plan_mode_guard(self):
        steps = step_headings(self.text)
        self.assertTrue(steps, "verify.md has no steps")
        self.assertTrue(steps[0].startswith("Step 0"))
        self.assertIn("plan-mode guard", steps[0].lower())

    def test_guard_stops_before_reading_feature_files_and_says_to_leave_plan_mode(self):
        guard = prompt_files.flatten(step_section(self.text, "Step 0"))
        self.assertIn("Do this before anything else", guard)
        self.assertIn("If the session is in plan mode, STOP", guard)
        self.assertIn("before reading or changing any feature file", guard)
        self.assertIn("Leave plan mode", guard)
        self.assertIn("/flow:verify <slug> again", guard)

    def test_guard_comes_before_any_feature_file_is_read(self):
        guard_at = self.flat.index("## Step 0: Plan-mode guard")
        first_read_at = self.flat.index("Read `BASE/")
        self.assertLess(guard_at, first_read_at)


class MissingCommandsTest(VerifyFileTest):
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
        for entry in ("## Commands", "Run from the project root.", "- Test:",
                      "- Single test:", "- Type-check:", "- Build:", "{file}"):
            self.assertIn(entry, self.step)

    def test_user_confirms_with_ask_user_question_before_other_changes(self):
        self.assertIn("confirm the block with AskUserQuestion", self.step)
        self.assertIn("Do this before any other change", self.step)
        self.assertIn("do not start the verification agent", self.step)

    def test_stops_on_no(self):
        self.assertIn('On "no", STOP.', self.step)

    def test_missing_commands_step_is_after_guard_and_before_spawning(self):
        guard_at = self.flat.index("## Step 0: Plan-mode guard")
        commands_at = self.flat.index("confirm the block with AskUserQuestion")
        spawn_at = self.flat.index("run_in_background: false")
        self.assertLess(guard_at, commands_at)
        self.assertLess(commands_at, spawn_at)


class AgentSpawnTest(VerifyFileTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spawn = prompt_files.flatten(step_section(cls.text, "Step 4"))

    def test_spawns_verification_agent_with_agent_tool_in_the_foreground(self):
        self.assertIn("**Agent tool**", self.spawn)
        self.assertIn("`run_in_background: false`", self.spawn)
        self.assertIn("flow:verification-agent", self.spawn)
        self.assertIn("fresh context", self.spawn)

    def test_waits_and_saves_verdict_in_the_same_turn(self):
        self.assertIn("Wait for the agent's result", self.spawn)
        self.assertIn("in this same turn", self.spawn)
        self.assertIn("until the verdict is saved", self.spawn)

    def test_no_task_tool_wording(self):
        self.assertNotIn("Task tool", self.flat)


class SaveVerdictTest(VerifyFileTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.save = prompt_files.flatten(step_section(cls.text, "Step 5"))

    def test_previous_verify_archived_with_read_and_write(self):
        self.assertIn(
            "read `BASE/VERIFY.md` with Read and write its full content, unchanged, "
            "to `BASE/archive/VERIFY-<n>.md` with Write",
            self.save,
        )

    def test_archive_number_counted_with_ls(self):
        self.assertIn("count with `ls` on `BASE/archive/`", self.save)

    def test_no_copy_wording_for_archiving(self):
        self.assertNotIn("copy it to", self.flat)

    def test_verdict_saved_verbatim(self):
        self.assertIn("Write the agent's verdict **verbatim** to `BASE/VERIFY.md`", self.save)

    def test_unusable_verdict_treated_as_fail(self):
        self.assertIn("no `## Verdict` section", self.save)
        self.assertIn("do NOT mark anything `[v]`", self.save)


class ApplyVerdictTest(VerifyFileTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        step = step_section(cls.text, "Step 6")
        cls.passed = verdict_branch(step, "**If the verdict is PASS**",
                                    "**If the verdict is FAIL:**")
        cls.failed = verdict_branch(step, "**If the verdict is FAIL:**")

    def test_v_awarded_only_when_all_covers_criteria_pass(self):
        self.assertIn("If all of its `covers:` criteria are `[PASS]`, change the task to `[v]`",
                      self.passed)

    def test_task_covering_unverified_criterion_stays_x(self):
        self.assertIn("If any of its `covers:` criteria is `[UNVERIFIED]`", self.passed)
        self.assertIn("leave the task as `[x]`", self.passed)

    def test_tasks_left_x_are_listed_in_the_report(self):
        self.assertIn("Left [x] — covers an UNVERIFIED criterion:", self.passed)

    def test_task_without_covers_line_is_handled_explicitly(self):
        self.assertIn("A task with no `covers:` line", self.passed)

    def test_pass_branch_adds_no_mv_tasks(self):
        self.assertIn("Do NOT add MV tasks", self.passed)

    def test_no_blanket_promotion_of_all_x_tasks(self):
        self.assertNotIn("change this feature's `[x]` tasks to `[v]`", self.flat)

    def test_fail_branch_marks_nothing_verified(self):
        self.assertIn("Do NOT mark anything `[v]`", self.failed)

    def test_mv_tasks_created_only_for_fail_items(self):
        self.assertIn("Create MV fix tasks only for FAIL items", self.failed)
        self.assertIn("Never add an MV task for an UNVERIFIED criterion", self.failed)

    def test_mv_numbering_and_deduplication_kept(self):
        self.assertIn("continuing from the highest existing `MV-` id", self.failed)
        self.assertIn("do not add a duplicate", self.failed)
        self.assertIn("`## MV: Verification fixes`", self.failed)

    def test_rules_restate_per_task_v(self):
        rules = prompt_files.flatten(prompt_files.section(self.text, "Rules"))
        self.assertIn("a task gets `[v]` only when every criterion on its `covers:` line is PASS",
                      rules)
        self.assertIn("UNVERIFIED items never become tasks", rules)


class IncompleteFeatureTest(VerifyFileTest):
    def test_incomplete_feature_warning_kept(self):
        step = prompt_files.flatten(step_section(self.text, "Step 3"))
        self.assertIn("If any tasks are still `[ ]` or `[>]`, the feature is not fully built", step)
        self.assertIn("Only continue on an explicit yes", step)


if __name__ == "__main__":
    unittest.main()
