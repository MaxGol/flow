"""Shared helpers for tests that check the plugin's markdown prompt files.

Prompt files (agents and commands under plugins/flow/) start with a YAML-like
frontmatter block between `---` lines, followed by a markdown body. These
helpers parse that frontmatter and pull sections out of the body by heading,
so tests can assert on what a specific section says.
"""

import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_DIR = os.path.join(REPO_ROOT, "plugins", "flow")
AGENTS_DIR = os.path.join(PLUGIN_DIR, "agents")
COMMANDS_DIR = os.path.join(PLUGIN_DIR, "commands")

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")


def agent_path(name):
    return os.path.join(AGENTS_DIR, name + ".md")


def command_path(name):
    return os.path.join(COMMANDS_DIR, name + ".md")


def read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def flatten(text):
    """Collapse all runs of whitespace to single spaces, so phrases that wrap
    across lines in the markdown can be matched with a plain substring test."""
    return " ".join(text.split())


def split_frontmatter(text):
    """Return (frontmatter_text, body). frontmatter_text is "" when absent."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return "", text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "".join(lines[1:index]), "".join(lines[index + 1:])
    raise ValueError("frontmatter opened with --- but never closed")


def parse_frontmatter(text):
    """Parse simple `key: value` frontmatter into a dict of stripped strings.

    Surrounding quotes are removed from values. Indented continuation lines
    are appended to the previous key's value, joined by a space.
    """
    frontmatter, _ = split_frontmatter(text)
    result = {}
    last_key = None
    for line in frontmatter.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace() and last_key is not None:
            result[last_key] = (result[last_key] + " " + line.strip()).strip()
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError("frontmatter line without a colon: %r" % line)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        last_key = key.strip()
        result[last_key] = value
    return result


def _headings(lines):
    """Yield (line_index, level, title) for headings outside code fences."""
    in_fence = False
    for index, line in enumerate(lines):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _HEADING.match(line.rstrip("\n"))
        if match:
            yield index, len(match.group(1)), match.group(2)


def _section_bounds(text, heading):
    """Return (lines, start, end) for the section titled `heading`.

    `heading` is the title without the leading #'s, e.g. "Tool rules".
    The section runs from the heading line to the next heading of the same
    or a higher level (fewer #'s). `end` is exclusive. Raises KeyError when
    the heading is absent and ValueError when it appears more than once.
    """
    _, body = split_frontmatter(text)
    lines = body.splitlines(keepends=True)
    headings = list(_headings(lines))
    matches = [h for h in headings if h[2] == heading]
    if not matches:
        raise KeyError("no section titled %r" % heading)
    if len(matches) > 1:
        raise ValueError("section %r appears %d times" % (heading, len(matches)))
    start, level, _ = matches[0]
    end = len(lines)
    for index, other_level, _ in headings:
        if index > start and other_level <= level:
            end = index
            break
    return lines, start, end


def has_section(text, heading):
    try:
        _section_bounds(text, heading)
    except KeyError:
        return False
    return True


def section(text, heading):
    """Return the body of the section titled `heading`, without its heading line."""
    lines, start, end = _section_bounds(text, heading)
    return "".join(lines[start + 1:end])


def outside_section(text, heading):
    """Return the body with the section titled `heading` (and its heading) removed."""
    lines, start, end = _section_bounds(text, heading)
    return "".join(lines[:start] + lines[end:])
