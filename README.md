# flow

A minimal agentic development pipeline for Claude Code.

`flow` breaks feature work into two phases: **plan**, then **implement**.

## The two commands

- **`/flow:plan`** — an interactive session that turns a feature idea into a
  written plan. It interviews you about scope, edge cases, and what "done"
  means, then writes the SPEC and TASKS files. No code is written in this phase.
- **`/flow:implement <feature-slug>`** — the orchestrator. It reads that
  feature's TASKS checklist, picks the next pending task, writes that task's
  context into CURRENT, and spawns a sub-agent to write the code and a real test.
  When the agent finishes, the orchestrator archives the task's record and ticks
  the checkbox.

## State files

All state lives in a `.flow/` folder inside your project. Each feature gets its
own isolated folder, so working on one feature never disturbs another:

```
.flow/
  features/
    <feature-slug>/
      SPEC.md              what & why — the requirements (written by /flow:plan)
      TASKS.md             the task checklist, with [ ] / [x] state
      CURRENT.md           scratch context for the active task (reset to clean between runs)
      archive/
        CURRENT-M1-1.md    a permanent record of each completed task
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
orchestrator writes the task context to that feature's CURRENT file, and the sub-agent
reads it. This keeps the orchestrator's context small and stops the sub-agent
from wandering outside the current task. The TASKS checklist is the source of
truth; CURRENT is disposable working memory; the archive is the record.

Every task must be backed by a real test in the project's own test framework —
the implementing agent detects the framework (pytest, Vitest, Jest, Karma, etc.),
writes a proper test, and runs it before the task can be marked done. If no test
framework exists, it stops and suggests one rather than writing a throwaway
script.

## Install

```
/plugin marketplace add MaxGol/flow
/plugin install flow@flow-marketplace
/reload-plugins
```

## Usage

```
/flow:plan               describe a feature, approve the breakdown
/flow:implement <slug>   build the next task for that feature (run once per task)
```
