"""Tests for plugins/flow/commands/plan.md (allowed tools, tool rules, SPEC commands)."""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prompt_files  # noqa: E402

COMMAND = prompt_files.command_path("plan")


def spec_template(text):
    """Return the fenced SPEC.md template (the block that starts with '# Spec:')."""
    for match in re.finditer(r"(?ms)^```[^\n]*\n(.*?)^```", text):
        if match.group(1).lstrip().startswith("# Spec:"):
            return match.group(1)
    raise AssertionError("no fenced SPEC template in plan.md")


def template_section(template, heading):
    """Return the lines under `## heading` in the template, up to the next `## `."""
    match = re.search(
        r"(?ms)^## %s[ \t]*\n(.*?)(?=^## |\Z)" % re.escape(heading), template
    )
    if match is None:
        raise AssertionError("template has no '## %s' section" % heading)
    return match.group(1)


class PlanFileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = prompt_files.read_text(COMMAND)
        cls.flat = prompt_files.flatten(cls.text)


class FrontmatterTest(PlanFileTest):
    def test_allowed_tools_is_exactly_read_and_flow_edit(self):
        meta = prompt_files.parse_frontmatter(self.text)
        self.assertEqual(meta["allowed-tools"], "Read, Edit(.flow/**)")

    def test_allowed_tools_has_no_glob_grep_or_bash(self):
        meta = prompt_files.parse_frontmatter(self.text)
        tools = [tool.strip().lower() for tool in meta["allowed-tools"].split(",")]
        for tool in tools:
            name = tool.split("(")[0]
            self.assertNotIn(name, ("glob", "grep", "bash"))

    def test_keeps_existing_frontmatter_keys(self):
        meta = prompt_files.parse_frontmatter(self.text)
        self.assertIn("description", meta)
        self.assertEqual(meta["argument-hint"], "[feature-slug]")


class SpecTemplateCommandsTest(PlanFileTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = spec_template(cls.text)
        cls.commands = template_section(cls.template, "Commands")
        cls.entries = {}
        for line in cls.commands.splitlines():
            match = re.match(r"^- (Test|Single test|Type-check|Build): (.+)$", line)
            if match:
                cls.entries[match.group(1)] = match.group(2)

    def test_template_has_commands_section_before_acceptance_criteria(self):
        commands_at = self.template.index("\n## Commands\n")
        criteria_at = self.template.index("\n## Acceptance criteria\n")
        self.assertLess(commands_at, criteria_at)

    def test_commands_section_has_the_four_entries(self):
        self.assertEqual(
            sorted(self.entries), sorted(["Test", "Single test", "Type-check", "Build"])
        )

    def test_single_test_uses_file_placeholder_or_none(self):
        single = self.entries["Single test"]
        self.assertIn("{file}", single)
        self.assertIn('"none"', single)

    def test_type_check_and_build_allow_none(self):
        self.assertIn('"none"', self.entries["Type-check"])
        self.assertIn('"none"', self.entries["Build"])

    def test_test_entry_is_required(self):
        self.assertNotIn("none", self.entries["Test"])

    def test_template_says_run_from_project_root_without_cd(self):
        flat = prompt_files.flatten(self.commands)
        self.assertIn("Run from the project root.", flat)
        self.assertIn("from the project root as written, with no `cd`", flat)
        self.assertIn("directory flag", flat)


class CommandRulesTest(PlanFileTest):
    def test_rules_require_project_root_no_cd_and_directory_flags(self):
        rules = prompt_files.flatten(prompt_files.section(self.text, "Rules"))
        self.assertIn("`## Commands`", rules)
        self.assertIn("must run from the project root with no `cd`", rules)
        self.assertIn("use the tool's own directory flag", rules)
        self.assertIn("`pnpm -C frontend test`", rules)

    def test_planner_reads_commands_from_project_config(self):
        step1 = prompt_files.flatten(
            prompt_files.section(self.text, "Step 1: Understand the feature")
        )
        self.assertIn("by reading the project's config yourself", step1)
        for label in ("**Test:**", "**Single test:**", "**Type-check:**", "**Build:**"):
            self.assertIn(label, step1)
        self.assertIn("`{file}`", step1)

    def test_breakdown_asks_user_to_confirm_commands(self):
        step2 = prompt_files.flatten(
            prompt_files.section(self.text, "Step 2: Propose the breakdown")
        )
        self.assertIn(
            "Test, Single test, Type-check and Build commands you worked out", step2
        )
        self.assertIn("ask the user to confirm or correct them", step2)


class ToolRulesTest(PlanFileTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rules = prompt_files.flatten(prompt_files.section(cls.text, "Tool rules"))

    def test_reading_only_with_read(self):
        self.assertIn("read files only with Read", self.rules)
        self.assertIn("Never use `cat`, `sed`, `head` or `tail` through Bash", self.rules)

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

    def test_bash_otherwise_only_for_simple_one_off_commands(self):
        self.assertIn("use Bash only for simple one-off commands", self.rules)
        self.assertIn(
            "one command per call, with no `cd`, `;`, `&&`, pipes or shell variables",
            self.rules,
        )


class BashMentionTest(PlanFileTest):
    def test_bash_appears_only_inside_tool_rules(self):
        self.assertIn("Bash", prompt_files.section(self.text, "Tool rules"))
        outside = prompt_files.outside_section(self.text, "Tool rules")
        frontmatter, _ = prompt_files.split_frontmatter(self.text)
        self.assertNotIn("Bash", outside)
        self.assertNotIn("Bash", frontmatter)


if __name__ == "__main__":
    unittest.main()
