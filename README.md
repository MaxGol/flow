# flow

A minimal agentic development pipeline for Claude Code.

`flow` breaks feature work into two phases:

1. **Plan** (`/flow:plan`) — an interactive session that turns a feature idea
   into two files: a PRD (what and why) and a PROGRESS checklist (milestones
   and tasks).
2. **Implement** (`/flow:implement`) — the orchestrator picks the next pending
   task, writes a focused context file (`MILESTONE.md`), and spawns a
   sub-agent to write the code. The sub-agent reads only that context file,
   builds the one task, and reports back. The orchestrator then marks the
   task done.

All state lives in a `.flow/` folder inside your project:

```
.flow/
  PRD.md          what & why (written by /flow:plan)
  PROGRESS.md     the task checklist with [ ] / [x] state
  MILESTONE.md    scratch context for the current task (disposable)
```

## Why it is built this way

Sub-agents start with a clean context — they do not inherit the chat. So the
orchestrator writes the task context to a file, and the sub-agent reads it.
This keeps the orchestrator's context small and stops the sub-agent from
wandering outside the current task. The PROGRESS checklist is the single
source of truth for what is left to build.

## Install

```
/plugin marketplace add <your-github-username>/flow
/plugin install flow@flow-marketplace
```

## Usage

```
/flow:plan        describe a feature, approve the breakdown
/flow:implement   build the next task
```

## Credit

The architecture — a phased plan → implement pipeline with sub-agents
coordinating through shared markdown state — is inspired by
[Belmont](https://github.com/blake-simpson/belmont). `flow` is my own
Claude-only reimplementation, written from scratch to understand the pattern
and adapt it to my workflow. It is deliberately minimal: two commands and one
agent, versus Belmont's larger multi-agent, multi-tool system.
