"""Tests for plugins/flow/agents/verification-agent.md (tool rules and UNVERIFIED)."""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prompt_files  # noqa: E402

AGENT = prompt_files.agent_path("verification-agent")


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
    def test_frontmatter_names_the_agent_and_keeps_read_and_bash(self):
        meta = prompt_files.parse_frontmatter(self.text)
        self.assertEqual(meta["name"], "verification-agent")
        tools = [tool.strip() for tool in meta["tools"].split(",")]
        self.assertIn("Read", tools)
        self.assertIn("Bash", tools)

    def test_frontmatter_tools_have_no_glob_or_grep(self):
        meta = prompt_files.parse_frontmatter(self.text)
        tools = [tool.strip().lower() for tool in meta["tools"].split(",")]
        self.assertNotIn("glob", tools)
        self.assertNotIn("grep", tools)

    def test_frontmatter_tools_have_no_write_or_edit(self):
        meta = prompt_files.parse_frontmatter(self.text)
        tools = [tool.strip().lower() for tool in meta["tools"].split(",")]
        self.assertNotIn("write", tools)
        self.assertNotIn("edit", tools)

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

    def test_a_reading_only_with_read(self):
        rule = self.rule_with("read files only with Read")
        self.assertIn("Never use `cat`, `sed`, `head` or `tail` through Bash", rule)

    def test_a_searching_only_with_read_only_search_commands(self):
        rule = self.rule_with("Search, list and check that files exist only with")
        self.assertIn("read-only search commands", rule)
        for command in ("`grep -rn`", "`grep -rl`", "`ls`", "`find`"):
            self.assertIn(command, rule)
        self.assertIn("`find` without `-exec` or `-delete`", rule)
        self.assertIn("Quote patterns", rule)
        self.assertIn("literal paths inside the project", rule)

    def test_b_no_file_changes_of_any_kind(self):
        rule = self.rule_with("no file changes of any kind")
        for forbidden in ("redirects", "`sed -i`", "`cp`", "`mv`"):
            self.assertIn(forbidden, rule)

    def test_c_bash_only_for_spec_commands_and_one_off_exercise_commands(self):
        rule = self.rule_with("use Bash only for the")
        self.assertIn("commands in the SPEC's `## Commands` section", rule)
        self.assertIn("simple one-off commands to exercise behaviour", rule)
        self.assertIn("one command per call", rule.lower())
        self.assertIn("no `cd`, `;` or shell variables", rule)

    def test_d_never_aws_and_never_staging_or_production(self):
        rule = self.rule_with("never run `aws`")
        self.assertIn("never run anything that reaches a staging or production system", rule)

    def test_a_partial_reads_use_grep_n_then_offset_and_limit(self):
        rule = self.rule_with("read files only with Read")
        self.assertIn("`grep -n`", rule)
        self.assertIn("only part of a file", rule)
        self.assertIn("`offset`", rule)
        self.assertIn("`limit`", rule)
        self.assertLess(rule.index("only part of a file"), rule.index("`offset`"))

    def test_a_test_file_and_files_changed_always_read_in_full(self):
        rule = self.rule_with("read files only with Read")
        self.assertIn(
            "each task's test file and every file listed under \"Files changed\" "
            "in its log are always read in full",
            rule,
        )

    def test_tool_rules_still_have_four_items(self):
        self.assertEqual(len(self.items), 4)

    def test_tool_rules_come_before_the_steps(self):
        self.assertLess(self.text.index("## Tool rules"), self.text.index("## Step 1"))


class CommandsFromSpecTest(AgentFileTest):
    def test_suite_is_run_with_the_spec_test_and_type_check_commands(self):
        step2 = prompt_files.flatten(prompt_files.section(self.text, "Step 2: Re-run the full test suite"))
        self.assertIn("Run the SPEC's **Test** command", step2)
        self.assertIn("**Type-check** command, unless it is `none`", step2)
        self.assertIn("Do not work out a test command on your own", step2)

    def test_test_and_type_check_run_once_and_suite_not_rerun_for_failures(self):
        step2 = prompt_files.flatten(prompt_files.section(self.text, "Step 2: Re-run the full test suite"))
        self.assertIn("Run Test once and Type-check once", step2)
        self.assertIn("Do not re-run the full suite to look into a failure", step2)
        self.assertIn("**Single test** command on one file", step2)


class UnverifiedTest(AgentFileTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        step5 = prompt_files.section(cls.text, "Step 5: Return the verdict")
        cls.step5_flat = prompt_files.flatten(step5)
        cls.template = fenced_block(step5)
        cls.template_headings = [
            line.strip() for line in cls.template.splitlines() if line.startswith("## ")
        ]

    def criterion_lines(self):
        section = self.template.split("## Acceptance criteria", 1)[1].split("\n## ", 1)[0]
        return [line for line in section.splitlines() if line.startswith("- ")]

    def test_template_allows_unverified_on_criterion_lines(self):
        lines = self.criterion_lines()
        self.assertTrue(lines)
        for line in lines:
            self.assertIn("UNVERIFIED", line.split("]", 1)[0])
        self.assertIn("[UNVERIFIED]", self.step5_flat)

    def test_template_has_unverified_section_with_reason_and_confirmation(self):
        self.assertIn("## Unverified", self.template_headings)
        section = self.template.split("## Unverified", 1)[1].split("\n## ", 1)[0]
        self.assertIn("why it could not be exercised", section)
        self.assertIn("what would confirm it", section)

    def test_verdict_line_stays_pass_or_fail(self):
        verdict = self.template.split("## Verdict", 1)[1]
        first = [line for line in verdict.splitlines() if line.strip()][0]
        self.assertTrue(first.startswith("PASS"))
        self.assertIn("\nFAIL\n", verdict)

    def test_states_unverified_alone_never_makes_the_verdict_fail(self):
        self.assertIn("UNVERIFIED criteria alone never make the verdict FAIL", self.step5_flat)

    def test_cannot_exercise_is_unverified_not_fail(self):
        step4 = prompt_files.flatten(
            prompt_files.section(self.text, "Step 4: Confirm each acceptance criterion independently")
        )
        self.assertIn("**UNVERIFIED** if you could not exercise it in this environment", step4)
        self.assertNotIn("is a FAIL with that reason", self.flat)


if __name__ == "__main__":
    unittest.main()
