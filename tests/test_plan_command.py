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


QUIET_RULE = (
    "Choose the runner's non-watch, CI-mode command with its quietest reporter "
    "that still prints failures and a summary."
)
WATCH_RULE = "Never choose a watch-mode command: it never exits."

# Known test runner names. An example command counts towards a runner when one
# of its words is in this set, so the examples can change without the test
# pinning one exact list.
KNOWN_RUNNERS = {
    "vitest", "jest", "mocha", "karma", "ng", "jasmine", "ava", "playwright",
    "cypress", "pytest", "unittest", "nose2", "tox", "go", "cargo", "rspec",
    "minitest", "phpunit", "dotnet", "mvn", "gradle", "mix", "deno", "bun",
}


def example_runners(flat_text):
    """Return the distinct runners named in the code spans of the sentence that
    starts at the first "for example" (case-insensitive) in flat_text."""
    match = re.search(r"(?i)for example:?((?:[^`.]|`[^`]*`)*)", flat_text)
    if match is None:
        return set()
    runners = set()
    for span in re.findall(r"`([^`]+)`", match.group(1)):
        for word in span.split():
            if word in KNOWN_RUNNERS:
                runners.add(word)
                break
    return runners


class QuietCommandRuleTest(PlanFileTest):
    """The quiet, non-watch command rule comes first, then runner examples."""

    def assert_rule_then_examples(self, flat):
        self.assertIn(QUIET_RULE, flat)
        self.assertIn(WATCH_RULE, flat)
        rule_at = flat.index(QUIET_RULE)
        watch_at = flat.index(WATCH_RULE, rule_at)
        self.assertLess(rule_at, watch_at)
        after = flat[watch_at + len(WATCH_RULE):]
        self.assertRegex(after, r"(?i)^\s*for example")
        runners = example_runners(after)
        self.assertGreaterEqual(
            len(runners), 3, "expected 3+ runners after 'for example', got %r" % runners
        )

    def test_rules_state_quiet_rule_then_examples(self):
        rules = prompt_files.flatten(prompt_files.section(self.text, "Rules"))
        self.assert_rule_then_examples(rules)

    def test_step1_states_quiet_rule_then_examples(self):
        step1 = prompt_files.flatten(
            prompt_files.section(self.text, "Step 1: Understand the feature")
        )
        self.assert_rule_then_examples(step1)

    def test_rules_tell_planner_to_check_config_for_flag(self):
        rules = prompt_files.flatten(prompt_files.section(self.text, "Rules"))
        self.assertIn(
            "Check the project's config or the runner's options for the right flag.",
            rules,
        )

    def test_example_runner_counting_ignores_unknown_commands(self):
        flat = "for example `npm test`, `make check` or `pytest -q`. `jest` later"
        self.assertEqual(example_runners(flat), {"pytest"})


class SpecTemplateQuietCommandsTest(PlanFileTest):
    def test_template_commands_use_quiet_vitest_examples(self):
        commands = template_section(spec_template(self.text), "Commands")
        entries = dict(
            re.match(r"^- (Test|Single test): (.+)$", line).groups()
            for line in commands.splitlines()
            if re.match(r"^- (Test|Single test): ", line)
        )
        self.assertIn("`npx vitest run --reporter=dot`", entries["Test"])
        self.assertIn("`npx vitest run --reporter=dot {file}`", entries["Single test"])


class TaskDescriptionTest(PlanFileTest):
    def test_step3_forbids_reading_whole_archive_files(self):
        step3 = prompt_files.flatten(
            prompt_files.section(self.text, "Step 3: Write the files")
        )
        self.assertIn(
            "Task descriptions must not tell the agent to read whole archive files",
            step3,
        )
        self.assertIn("Name the exact facts or paths the agent needs instead", step3)


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
