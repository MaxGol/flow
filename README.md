# flow

A minimal agentic development pipeline for Claude Code.

`flow` breaks feature work into two phases: **plan**, then **implement**.

## The two commands

- **`/flow:plan`** — an interactive session that turns a feature idea into a
  written plan. It interviews you about scope, edge cases, and what "done"
  means, then writes the SPEC and TASKS files. No code is written in this phase.
- **`/flow:implement`** — the orchestrator. It reads the TASKS checklist, picks
  the next pending task, writes that task's context into CURRENT, and spawns a
  sub-agent to write the code. When the agent finishes, the orchestrator
  archives the task's record and ticks the checkbox.

## State files

All state lives in a `.flow/` folder inside your project:

```
.flow/
  SPEC.md                what & why — the requirements (written by /flow:plan)
  TASKS.md               the task checklist, with [ ] / [x] state
  CURRENT.md             scratch context for the active task (reset to clean between runs)
  archive/
    CURRENT-M1-1.md      a permanent record of each completed task
    CURRENT-M1-2.md
```

- **SPEC.md** — the plan: goal, users, requirements, definition of done. Written
  once during planning, then read-only. It is the stable source of intent.
- **TASKS.md** — the checklist of milestones and tasks. The single source of
  truth for what is left to build. The orchestrator ticks boxes here as tasks
  complete (`[ ]` todo, `[x]` done).
- **CURRENT.md** — disposable scratch context for the one task being built right
  now. The orchestrator writes the task into it; the sub-agent reads it and logs
  its work back. At the end of each run it is archived and reset to clean.
- **archive/** — one file per completed task, holding that task's full context
  and implementation log. This is the durable history.

## Why it is built this way

Sub-agents start with a clean context — they do not inherit the chat. So the
orchestrator writes the task context to a file (CURRENT), and the sub-agent
reads it. This keeps the orchestrator's context small and stops the sub-agent
from wandering outside the current task. The TASKS checklist is the source of
truth; CURRENT is disposable working memory; the archive is the record.

## Install

```
/plugin marketplace add MaxGol/flow
/plugin install flow@flow-marketplace
/reload-plugins
```

## Usage

```
/flow:plan        describe a feature, approve the breakdown
/flow:implement   build the next task (run once per task)
```

## Credit

The architecture — a phased plan → implement pipeline where sub-agents
coordinate through shared markdown state — is inspired by
[Belmont](https://github.com/blake-simpson/belmont). `flow` is my own
Claude-only reimplementation, written from scratch to understand the pattern
and adapt it to my workflow. It is deliberately minimal: two commands and one
agent, with per-task archiving, versus Belmont's larger multi-agent, multi-tool
system.
