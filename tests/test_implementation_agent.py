"""Tests for plugins/flow/agents/implementation-agent.md (tool rules and SPEC commands)."""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prompt_files  # noqa: E402

AGENT = prompt_files.agent_path("implementation-agent")


def numbered_items(section_text):
    """Split a markdown section into its top-level numbered list items (flattened)."""
    items = re.split(r"(?m)^\d+\.\s+", section_text)
    return [prompt_files.flatten(item) for item in items[1:]]


def fenced_block(section_text):
    match = re.search(r"(?ms)^```[^\n]*\n(.*?)^```", section_text)
    if match is None:
        raise AssertionError("no fenced block in section")
    return match.group(1)


class AgentFileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = prompt_files.read_text(AGENT)
        cls.flat = prompt_files.flatten(cls.text)


class FrontmatterTest(AgentFileTest):
    def test_frontmatter_names_the_agent_and_keeps_its_tools(self):
        meta = prompt_files.parse_frontmatter(self.text)
        self.assertEqual(meta["name"], "implementation-agent")
        tools = [tool.strip() for tool in meta["tools"].split(",")]
        for tool in ("Read", "Write", "Edit", "Bash"):
            self.assertIn(tool, tools)

    def test_frontmatter_tools_have_no_glob_or_grep(self):
        meta = prompt_files.parse_frontmatter(self.text)
        tools = [tool.strip().lower() for tool in meta["tools"].split(",")]
        self.assertNotIn("glob", tools)
        self.assertNotIn("grep", tools)

    def test_no_instruction_to_use_glob_or_grep_tools(self):
        # The Glob and Grep tools are capitalised; the `grep -rn` command is not.
        self.assertIsNone(re.search(r"\b(Glob|Grep)\b", self.text))


class ToolRulesTest(AgentFileTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rules = prompt_files.section(cls.text, "Tool rules")
        cls.items = numbered_items(cls.rules)

    def rule_with(self, phrase):
        found = [item for item in self.items if phrase in item]
        self.assertEqual(len(found), 1, "expected one rule containing %r" % phrase)
        return found[0]

    def test_section_lists_five_rules(self):
        self.assertEqual(len(self.items), 5)

    def test_a_reading_only_with_read(self):
        rule = self.rule_with("read files only with Read")
        self.assertIn("Never use `cat`, `sed`, `head` or `tail` through Bash", rule)

    def test_a_searching_only_with_read_only_search_commands(self):
        rule = self.rule_with("Search, list and check that files exist only with")
        self.assertIn("single read-only search commands", rule)
        for command in ("`grep -rn`", "`grep -rl`", "`ls`", "`find`"):
            self.assertIn(command, rule)
        self.assertIn("`find` without `-exec` or `-delete`", rule)

    def test_a_search_commands_are_quoted_literal_and_unglued(self):
        rule = self.rule_with("Search, list and check that files exist only with")
        self.assertIn("Quote patterns", rule)
        self.assertIn("use literal paths inside the project", rule)
        self.assertIn("never add `cd`, `;`, `&&`, pipes or variables", rule)

    def test_b_file_changes_only_with_edit_or_write(self):
        rule = self.rule_with("make every file change with Edit or Write")
        for forbidden in ("heredocs", "`cat >`", "`sed -i`", "`cp`", "`mv`", "interpreter scripts"):
            self.assertIn(forbidden, rule)
        self.assertIn("Never", rule)

    def test_c_bash_only_for_spec_commands_with_file_only_substitution(self):
        rule = self.rule_with("use Bash only for the commands in the SPEC's `## Commands`")
        self.assertIn("copied exactly", rule)
        self.assertIn("Replacing `{file}`", rule)
        self.assertIn("is the only allowed edit", rule)

    def test_d_one_command_per_call_without_shell_glue(self):
        rule = self.rule_with("run exactly one command per Bash call")
        self.assertIn("Never add", rule)
        for forbidden in ("`cd`", "`;`", "`&&`", "`|`", "redirects", "shell variables"):
            self.assertIn(forbidden, rule)

    def test_e_blocked_instead_of_improvising(self):
        rule = self.rule_with("is missing from `## Commands`")
        self.assertIn("fails for an environment reason", rule)
        self.assertIn("**BLOCKED**", rule)
        self.assertIn("Do not invent, substitute or repair a command", rule)

    def test_a_partial_reads_grep_n_first_then_read_a_range(self):
        rule = self.rule_with("read files only with Read")
        self.assertIn("`grep -n`", rule)
        self.assertIn("only part of a file", rule)
        self.assertIn("`offset`", rule)
        self.assertIn("`limit`", rule)
        self.assertIn(
            "When you need only part of a file, `grep -n` first, then Read only "
            "that range with `offset` and `limit`",
            rule,
        )

    def test_a_grep_n_is_an_allowed_read_only_command(self):
        rule = self.rule_with("Search, list and check that files exist only with")
        allowed = rule.split("single read-only search commands:", 1)[1].split(".", 1)[0]
        self.assertIn("`grep -n`", allowed)

    def test_file_has_no_line_count_check(self):
        self.assertNotIn("wc -l", self.text)

    def test_c_rule_3_still_forbids_extra_flags(self):
        rule = self.rule_with("use Bash only for the commands in the SPEC's `## Commands`")
        self.assertIn("Do not add flags, arguments, prefixes or environment variables", rule)

    def test_tool_rules_come_before_the_steps(self):
        self.assertLess(self.text.index("## Tool rules"), self.text.index("## Step 1"))


OLD_DETECTION_INSTRUCTIONS = (
    re.compile(r"Detect the existing test framework", re.IGNORECASE),
    re.compile(r"^#+\s*4a\.\s*Detect\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"Inspect the project to find how it already tests code", re.IGNORECASE),
    re.compile(r"no test framework", re.IGNORECASE),
    re.compile(r"package\.json|jest\.config|vitest\.config|karma\.conf|pytest\.ini"),
)


def old_detection_instructions(text):
    """Return the old framework-detection instructions (Step 4a wording) found in text."""
    return [pattern.pattern for pattern in OLD_DETECTION_INSTRUCTIONS if pattern.search(text)]


class OldDetectionCheckTest(unittest.TestCase):
    def test_finds_the_old_step_4a_wording(self):
        old = (
            "### 4a. Detect the existing test framework (do this first)\n"
            "\n"
            "Inspect the project to find how it already tests code. Look for:\n"
            "- `package.json` `devDependencies`; `jest.config.*`; `pytest.ini`.\n"
        )
        self.assertGreaterEqual(len(old_detection_instructions(old)), 4)

    def test_ignores_unrelated_uses_of_detect(self):
        unrelated = (
            "The verification agent can detect regressions.\n"
            "Detected changes are logged. Do not try to detect the runner yourself.\n"
        )
        self.assertEqual(old_detection_instructions(unrelated), [])


class CommandsFromSpecTest(AgentFileTest):
    def test_no_instruction_to_detect_the_framework(self):
        self.assertEqual(old_detection_instructions(self.text), [])

    def test_commands_are_taken_from_the_spec(self):
        step1 = prompt_files.flatten(prompt_files.section(self.text, "Step 1: Read your context"))
        self.assertIn("Read the `## Commands` section of the SPEC file", step1)
        self.assertIn("These commands are your only source for how to run tests", step1)
        self.assertIn("Do not work out the test runner or the commands on your own", step1)
        self.assertIn("**BLOCKED (missing command)**", step1)

    def test_runs_single_test_then_test_then_type_check(self):
        run = prompt_files.section(self.text, "4b. Run the commands, in this order")
        items = numbered_items(run)
        self.assertEqual(len(items), 3)
        self.assertTrue(items[0].startswith("**Single test** first"))
        self.assertIn("replace `{file}` with the path of the test file", items[0])
        self.assertTrue(items[1].startswith("**Test:**"))
        self.assertTrue(items[2].startswith("**Type-check** (skip when it is `none`)"))

    def test_done_requires_test_suite_and_type_check(self):
        self.assertIn(
            "Only report `done` if a real test was written AND it passed AND the full "
            "suite passed AND the type-check passed (or is `none`).",
            self.flat,
        )

    def test_keeps_never_weaken_a_test_guarantee(self):
        self.assertIn("**Never make a test pass by weakening it.**", self.text)
        self.assertIn("real test in the project's own test framework", self.text)


class SingleTestFirstTest(AgentFileTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        run = prompt_files.section(cls.text, "4b. Run the commands, in this order")
        cls.step = prompt_files.flatten(run)
        cls.items = numbered_items(run)
        # The last item runs to the end of the section; keep only its own paragraph.
        cls.type_check_item = cls.items[2].split("Record each exact command", 1)[0]

    def test_three_items_in_order_single_test_test_type_check(self):
        self.assertEqual(len(self.items), 3)
        self.assertTrue(self.items[0].startswith("**Single test**"))
        self.assertTrue(self.items[1].startswith("**Test:**"))
        self.assertTrue(self.items[2].startswith("**Type-check**"))

    def test_single_test_reruns_until_it_passes(self):
        self.assertIn("fix the **code** and re-run it until it passes", self.items[0])

    def test_test_takes_single_tests_place_when_it_is_none(self):
        self.assertIn("When Single test is `none`, run Test here instead", self.items[0])
        self.assertIn("skip item 2", self.items[0])

    def test_suite_and_type_check_run_once(self):
        self.assertIn("run the whole suite once", self.items[1])
        self.assertIn("run it once", self.type_check_item)

    def test_full_suite_reruns_only_after_suite_or_type_check_failure_fix(self):
        self.assertIn(
            "Re-run the full suite only after a fix that follows a suite or type-check failure",
            self.step,
        )
        self.assertIn("the Single test before it and the Type-check after it", self.step)
        self.assertIn("Do not re-run the full suite after any other fix", self.step)

    def test_every_fix_counts_toward_the_cap(self):
        self.assertIn("Every fix counts toward the 3-attempt cap", self.step)

    def test_keeps_attempt_cap_blocked_and_done_sentences(self):
        self.assertIn("up to 3 attempts", self.step)
        self.assertIn("**BLOCKED (environment)**", self.step)
        self.assertIn(
            "If the task's test, the full suite or the type-check still fails after 3 "
            "attempts, do NOT claim success — record the failure in the log and stop.",
            self.step,
        )
        self.assertIn(
            "Only report `done` if a real test was written AND it passed AND the full "
            "suite passed AND the type-check passed (or is `none`).",
            self.step,
        )


class SpecSectionsTest(AgentFileTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        step1 = prompt_files.section(cls.text, "Step 1: Read your context")
        cls.items = numbered_items(step1)
        cls.spec_item = cls.items[3]

    def test_step_1_keeps_four_items(self):
        self.assertEqual(len(self.items), 4)

    def test_spec_beyond_commands_is_optional(self):
        self.assertIn("The rest of the SPEC beyond `## Commands` is optional", self.spec_item)
        self.assertIn("Read only the sections you need", self.spec_item)

    def test_never_reads_the_whole_spec_for_background(self):
        self.assertIn("never read the whole file for background", self.spec_item)
        self.assertNotIn("read the rest of the SPEC", self.spec_item)

    def test_always_reads_acceptance_criteria_named_on_covers_line(self):
        self.assertIn(
            "Always read the `## Acceptance criteria` entries named in your task's "
            "`covers:` line, even when you read nothing else from the SPEC",
            self.spec_item,
        )


class LogTemplateTest(AgentFileTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        step5 = prompt_files.section(cls.text, "Step 5: Write the log")
        cls.template = fenced_block(step5)
        cls.labels = [
            line.split(":", 1)[0]
            for line in cls.template.splitlines()
            if line.startswith("- ")
        ]

    def test_template_records_exact_commands_run(self):
        for label in ("- Single test command", "- Test command", "- Type-check command"):
            self.assertIn(label, self.labels)
        self.assertIn("the exact command you ran, with {file} replaced, or \"none\"", self.template)
        self.assertIn("the exact Test command you ran", self.template)
        self.assertIn("the exact Type-check command you ran, or \"none\"", self.template)

    def test_template_keeps_lines_the_orchestrator_checks(self):
        for label in ("- Test file", "- Test result", "- Full suite result"):
            self.assertIn(label, self.labels)

    def test_status_line_allows_blocked(self):
        status = self.template.splitlines()[0]
        self.assertTrue(status.startswith("### [task id]"))
        for status_word in ("done", "FAILED", "BLOCKED (missing command)", "BLOCKED (environment)"):
            self.assertIn(status_word, status)


class PromptFilesHelperTest(unittest.TestCase):
    SAMPLE = (
        "---\n"
        "description: Does a thing: with a colon\n"
        "allowed-tools: \"Read, Glob, Grep\"\n"
        "---\n"
        "\n"
        "# Title\n"
        "intro Bash\n"
        "## Tool rules\n"
        "rule text\n"
        "### Sub rule\n"
        "sub text\n"
        "```markdown\n"
        "## Not a heading\n"
        "```\n"
        "## Step 1\n"
        "step text\n"
    )

    def test_parse_frontmatter(self):
        meta = prompt_files.parse_frontmatter(self.SAMPLE)
        self.assertEqual(meta["description"], "Does a thing: with a colon")
        self.assertEqual(meta["allowed-tools"], "Read, Glob, Grep")

    def test_no_frontmatter(self):
        self.assertEqual(prompt_files.parse_frontmatter("# Title\n"), {})

    def test_section_runs_to_next_heading_of_same_level_and_skips_fences(self):
        body = prompt_files.section(self.SAMPLE, "Tool rules")
        self.assertEqual(
            body,
            "rule text\n### Sub rule\nsub text\n```markdown\n## Not a heading\n```\n",
        )

    def test_outside_section_removes_heading_and_body(self):
        outside = prompt_files.outside_section(self.SAMPLE, "Tool rules")
        self.assertIn("intro Bash", outside)
        self.assertIn("## Step 1\nstep text\n", outside)
        self.assertNotIn("rule text", outside)
        self.assertNotIn("Tool rules", outside)
        self.assertNotIn("allowed-tools", outside)

    def test_missing_section(self):
        self.assertFalse(prompt_files.has_section(self.SAMPLE, "Nope"))
        with self.assertRaises(KeyError):
            prompt_files.section(self.SAMPLE, "Nope")


if __name__ == "__main__":
    unittest.main()
