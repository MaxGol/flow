"""Tests for README.md (the "Running unattended" section, SPEC commands,
UNVERIFIED and per-task [v], and the agents' tool sets)."""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prompt_files  # noqa: E402

README = os.path.join(prompt_files.REPO_ROOT, "README.md")

ENV_VARS_DOC = "https://code.claude.com/docs/en/env-vars"
SUB_AGENTS_DOC = "https://code.claude.com/docs/en/sub-agents"


def frontmatter_tools(agent_name):
    meta = prompt_files.parse_frontmatter(
        prompt_files.read_text(prompt_files.agent_path(agent_name))
    )
    return [tool.strip() for tool in meta["tools"].split(",")]


def listed_tool_set(flat_text, label):
    """Return the tools in the README's "<label> tool set (A, B — ...)" list."""
    match = re.search(re.escape(label) + r" tool set \(([^)]*?)\s+—", flat_text)
    if match is None:
        raise AssertionError("README has no %r tool set list" % label)
    return [tool.strip() for tool in match.group(1).split(",")]


class ReadmeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = prompt_files.read_text(README)
        cls.flat = prompt_files.flatten(cls.text)


class RunningUnattendedTest(ReadmeTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.section = prompt_files.section(cls.text, "Running unattended")
        cls.section_flat = prompt_files.flatten(cls.section)

    def test_heading_is_a_top_level_section(self):
        self.assertIsNotNone(re.search(r"(?m)^## Running unattended\s*$", self.text))

    def test_keeps_block_reads_outside_working_directories_on(self):
        self.assertIn("blockReadsOutsideWorkingDirectories", self.section)
        self.assertIn('"blockReadsOutsideWorkingDirectories": true', self.section)
        # It explains why untraceable Bash prompts under the setting.
        self.assertIn("can't trace", self.section_flat)
        self.assertIn("even in auto mode", self.section_flat)

    def test_sets_default_mode_auto_in_user_settings_only(self):
        self.assertIn('"defaultMode": "auto"', self.section)
        self.assertIn("~/.claude/settings.json", self.section)
        self.assertIn("no effect when set in project or local settings", self.section_flat)

    def test_turns_fork_mode_off_with_doc_links(self):
        self.assertIn('"CLAUDE_CODE_FORK_SUBAGENT": "0"', self.section)
        self.assertIn("run_in_background: false", self.section)
        self.assertIn("(%s)" % ENV_VARS_DOC, self.section_flat)
        self.assertIsNotNone(
            re.search(r"\(" + re.escape(SUB_AGENTS_DOC) + r"[#)]", self.section_flat)
        )

    def test_recommends_ask_rules_with_rm_fr_caveat(self):
        for rule in ("Bash(git push *)", "Bash(aws *)", "Bash(rm -rf *)"):
            self.assertIn('"%s"' % rule, self.section)
            self.assertIn("`%s`" % rule, self.section)
        self.assertIsNotNone(
            re.search(r"does not match variants such as `rm -fr`", self.section_flat)
        )

    def test_has_deny_rule_example_for_production_aws_profile(self):
        deny = re.search(r'"deny"\s*:\s*\[(.*?)\]', self.section, re.S)
        self.assertIsNotNone(deny, "no deny list in the settings example")
        self.assertIsNotNone(re.search(r'"Bash\(aws [^"]*--profile[ =]prod', deny.group(1)))
        self.assertIn("not a security boundary", self.section_flat)

    def test_auto_mode_drops_broad_allow_rules(self):
        self.assertIn("drops broad allow rules", self.section_flat)
        self.assertIn("Bash(python*)", self.section)
        self.assertIn("package-manager run commands", self.section_flat)

    def test_network_needs_sandbox_and_curl_rules_prompt_localhost(self):
        self.assertIn("sandbox", self.section)
        self.assertIn("Bash(curl *)", self.section)
        self.assertIn("Bash(wget *)", self.section)
        self.assertIn("localhost", self.section)

    def test_explains_how_to_run_count_approvals(self):
        self.assertIn("python3 scripts/count_approvals.py", self.section)
        self.assertIn("--command flow:verify", self.section)
        self.assertIn("~/.claude/projects/", self.section)


class ReadmeBehaviourTest(ReadmeTest):
    def test_no_longer_describes_agents_detecting_the_test_framework(self):
        self.assertNotIn("Detect the project's existing test framework", self.flat)
        self.assertNotIn("no test framework", self.flat)
        self.assertIsNone(
            re.search(r"\bdetect\w*\b[^.]{0,80}\bframework", self.flat, re.I)
        )

    def test_says_commands_come_from_the_spec(self):
        self.assertTrue(prompt_files.has_section(self.text, "Commands come from the SPEC"))
        self.assertIn("Neither agent works out how to run your tests on its own", self.flat)

    def test_missing_commands_block_is_added_by_implement_and_verify(self):
        commands = prompt_files.flatten(
            prompt_files.section(self.text, "Commands come from the SPEC")
        )
        self.assertIn(
            "If a SPEC has no `## Commands` block", commands
        )
        self.assertIn("`/flow:implement` and `/flow:verify` add it themselves", commands)
        self.assertIn("ask you to confirm", commands)

    def test_mentions_unverified_and_per_task_v(self):
        self.assertIn("UNVERIFIED", self.text)
        self.assertIn("[UNVERIFIED]", self.text)
        self.assertIn("`[v]` is awarded per task", self.flat)

    def test_blocked_reasons_match_the_agent(self):
        self.assertIn("BLOCKED (missing command)", self.flat)
        self.assertIn("BLOCKED (environment)", self.flat)


class ReadmeToolSetsTest(ReadmeTest):
    def test_no_glob_or_grep_tool_anywhere(self):
        self.assertIsNone(re.search(r"\b(Glob|Grep)\b", self.text))

    def test_implementation_agent_tool_set_matches_frontmatter(self):
        listed = listed_tool_set(self.flat, "restricted")
        self.assertEqual(listed, frontmatter_tools("implementation-agent"))
        self.assertNotIn("Glob", listed)
        self.assertNotIn("Grep", listed)

    def test_verification_agent_tool_set_matches_frontmatter(self):
        listed = listed_tool_set(self.flat, "read-only")
        self.assertEqual(listed, frontmatter_tools("verification-agent"))
        self.assertNotIn("Glob", listed)
        self.assertNotIn("Grep", listed)


if __name__ == "__main__":
    unittest.main()
