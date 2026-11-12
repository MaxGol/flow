#!/usr/bin/env python3
"""Count the permission prompts the user answered during flow command runs.

Usage:
    python3 scripts/count_approvals.py <session.jsonl> [--command flow:implement]

A run starts at a user-typed message (``origin.kind == "human"``) that invokes
the command (``<command-name>/flow:implement</command-name>``) and lasts until
the user's next typed message. Turns triggered by agent completion
(``task-notification``) or hand-back (``peer``) messages stay inside the run.

Counted: tool calls made inside a run, in the main session or in a sub-agent
started by an Agent call inside the run, whose ``permissionDecision.source``
starts with ``user`` (rejections included). AskUserQuestion is never counted.

Output: one line per counted prompt, then ``approvals: N`` as the last line.
Exit code: 0 when N is 0, 1 when N is above 0, 2 on error (missing or
unreadable transcript, or no run of the requested command).
"""

import argparse
import glob
import json
import os
import sys

AGENT_TOOLS = ("Agent", "Task")
EXCLUDED_TOOLS = ("AskUserQuestion",)
SHORT_INPUT_LIMIT = 100


class TranscriptError(Exception):
    pass


def load_jsonl(path):
    """Return the parsed JSON objects in ``path``, skipping malformed lines."""
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise TranscriptError(f"cannot read transcript {path}: {exc}") from exc
    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def content_items(entry):
    message = entry.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if isinstance(content, list):
        return [item for item in content if isinstance(item, dict)]
    return []


def message_text(entry):
    message = entry.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    parts = []
    for item in content_items(entry):
        if item.get("type") == "text" and isinstance(item.get("text"), str):
            parts.append(item["text"])
    return "\n".join(parts)


def origin_kind(entry):
    origin = entry.get("origin")
    if isinstance(origin, dict):
        return origin.get("kind")
    return None


def short_input(tool_input):
    if isinstance(tool_input, dict):
        for key in ("command", "file_path", "path", "pattern", "url"):
            value = tool_input.get(key)
            if isinstance(value, str) and value:
                text = value
                break
        else:
            text = json.dumps(tool_input, sort_keys=True)
    else:
        text = json.dumps(tool_input)
    text = " ".join(text.split())
    if len(text) > SHORT_INPUT_LIMIT:
        text = text[: SHORT_INPUT_LIMIT - 3] + "..."
    return text


def tool_uses(entry):
    for item in content_items(entry):
        if item.get("type") == "tool_use" and isinstance(item.get("id"), str):
            yield item


def tool_results(entry):
    for item in content_items(entry):
        if item.get("type") == "tool_result" and isinstance(item.get("tool_use_id"), str):
            yield item


def decision_source(entry, result_item):
    decision = result_item.get("permissionDecision")
    if not isinstance(decision, dict):
        decision = entry.get("permissionDecision")
    if not isinstance(decision, dict):
        return None
    source = decision.get("source")
    return source if isinstance(source, str) else None


def user_answered(entries, agent_name, in_scope):
    """Return (prompt lines, Agent tool_use ids) for tool calls ``in_scope``.

    ``in_scope`` is either True (every call counts, used for sub-agents) or a
    set of tool_use ids made inside a run (used for the main session).
    """
    calls = {}
    for entry in entries:
        if entry.get("type") != "assistant":
            continue
        for use in tool_uses(entry):
            if in_scope is True or use["id"] in in_scope:
                calls[use["id"]] = use
    lines = []
    for entry in entries:
        if entry.get("type") != "user":
            continue
        for result in tool_results(entry):
            use = calls.get(result["tool_use_id"])
            if use is None or use.get("name") in EXCLUDED_TOOLS:
                continue
            source = decision_source(entry, result)
            if source is None or not source.startswith("user"):
                continue
            lines.append(
                f"{agent_name} | {use.get('name')} | {short_input(use.get('input'))} | {source}"
            )
    agent_ids = [cid for cid, use in calls.items() if use.get("name") in AGENT_TOOLS]
    return lines, agent_ids


def run_tool_ids(entries, command):
    """Return (number of runs, ids of tool_use calls made inside a run)."""
    marker = f"<command-name>/{command}</command-name>"
    in_run = False
    runs = 0
    ids = set()
    for entry in entries:
        kind = entry.get("type")
        if kind == "user" and origin_kind(entry) == "human":
            in_run = marker in message_text(entry)
            if in_run:
                runs += 1
        elif kind == "assistant" and in_run:
            for use in tool_uses(entry):
                ids.add(use["id"])
    return runs, ids


def load_subagents(session_path):
    """Return a list of (toolUseId, agentType, path) for the session's sub-agents."""
    base = session_path[:-len(".jsonl")] if session_path.endswith(".jsonl") else session_path
    found = []
    for path in sorted(glob.glob(os.path.join(base, "subagents", "agent-*.jsonl"))):
        meta_path = path[:-len(".jsonl")] + ".meta.json"
        try:
            with open(meta_path, encoding="utf-8") as handle:
                meta = json.load(handle)
        except (OSError, ValueError):
            continue
        if not isinstance(meta, dict) or not isinstance(meta.get("toolUseId"), str):
            continue
        agent_type = meta.get("agentType") or os.path.basename(path)[: -len(".jsonl")]
        found.append((meta["toolUseId"], str(agent_type), path))
    return found


def count(session_path, command):
    if not os.path.isfile(session_path):
        raise TranscriptError(f"transcript not found: {session_path}")
    entries = load_jsonl(session_path)
    runs, ids = run_tool_ids(entries, command)
    if runs == 0:
        raise TranscriptError(f"no /{command} run found in {session_path}")

    lines, pending = user_answered(entries, "main", ids)
    subagents = load_subagents(session_path)
    seen = set()
    while pending:
        tool_use_id = pending.pop(0)
        if tool_use_id in seen:
            continue
        seen.add(tool_use_id)
        for agent_tool_use_id, agent_type, path in subagents:
            if agent_tool_use_id != tool_use_id:
                continue
            try:
                agent_entries = load_jsonl(path)
            except TranscriptError as exc:
                print(f"warning: {exc}", file=sys.stderr)
                continue
            agent_lines, nested = user_answered(agent_entries, agent_type, True)
            lines.extend(agent_lines)
            pending.extend(nested)
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Count user-answered permission prompts during flow command runs."
    )
    parser.add_argument("transcript", help="path to the Claude Code session .jsonl")
    parser.add_argument(
        "--command",
        default="flow:implement",
        help="flow command whose runs are measured (default: flow:implement)",
    )
    args = parser.parse_args(argv)
    command = args.command.lstrip("/")
    try:
        lines = count(args.transcript, command)
    except TranscriptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    print(f"approvals: {len(lines)}")
    return 0 if not lines else 1


if __name__ == "__main__":
    sys.exit(main())
