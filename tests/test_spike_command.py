"""Tests for plugins/flow/commands/spike.md (allowed tools and tool rules)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prompt_files  # noqa: E402

COMMAND = prompt_files.command_path("spike")


class SpikeFileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = prompt_files.read_text(COMMAND)
        cls.flat = prompt_files.flatten(cls.text)


class FrontmatterTest(SpikeFileTest):
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
        self.assertEqual(meta["argument-hint"], "<feature-slug>")


class ToolRulesTest(SpikeFileTest):
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


class BashMentionTest(SpikeFileTest):
    def test_bash_appears_only_inside_tool_rules(self):
        self.assertIn("Bash", prompt_files.section(self.text, "Tool rules"))
        outside = prompt_files.outside_section(self.text, "Tool rules")
        frontmatter, _ = prompt_files.split_frontmatter(self.text)
        self.assertNotIn("Bash", outside)
        self.assertNotIn("Bash", frontmatter)


class WebSearchKeptTest(SpikeFileTest):
    def test_still_allows_web_search(self):
        self.assertIn("You may web-search for external facts", self.flat)


if __name__ == "__main__":
    unittest.main()
