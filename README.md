# flow

A minimal agentic development pipeline for Claude Code.

`flow` breaks feature work into phases: **plan**, **implement**, then **verify**.

## The commands

- **`/flow:spike <feature-slug>`** — investigate a vague or unfamiliar problem
  *before* planning it. It reads the codebase (and may search the web), then
  writes a findings document (SPIKE.md): what already exists, the options, the
  risks, and the decisions you must make. It writes no code and no plan — it
  turns "vague" into "well-defined enough to plan". Optional; skip it when the
  problem is already clear.
- **`/flow:plan <feature-slug>`** — an interactive session that turns a feature
  idea (or the answers to a spike) into a written plan. It interviews you about scope, edge cases, and what "done"
  means, then writes the SPEC and TASKS files. No code is written in this phase.
- **`/flow:implement <feature-slug>`** — the orchestrator. It reads that
  feature's TASKS checklist, picks the next pending task, writes that task's
  context into CURRENT, and spawns a sub-agent to write the code and a real test.
  When the agent finishes, the orchestrator archives the task's record and ticks
  the checkbox.
- **`/flow:verify <feature-slug>`** — independently checks that completed
  (`[x]`) tasks actually satisfy the SPEC. It spawns a fresh agent that did
  *not* build the code, which re-runs the tests and confirms every acceptance
  criterion, writing its verdict to VERIFY.md. On a pass, tasks move from
  `[x]` to `[v]` (verified). On a failure, nothing is fixed automatically —
  the orchestrator adds new `[ ]` remediation tasks for `/flow:implement` to
  pick up.

## State files

All state lives in a `.flow/` folder inside your project. Each feature gets its
own isolated folder, so working on one feature never disturbs another:

```
.flow/
  features/
    <feature-slug>/
      SPIKE.md             investigation findings & decisions (written by /flow:spike, optional)
      SPEC.md              what & why — the requirements (written by /flow:plan)
      TASKS.md             the task checklist, with [ ] / [x] / [v] state
      CURRENT.md           scratch context for the active task (reset to clean between runs)
      VERIFY.md            latest verification verdict (written by /flow:verify)
      archive/
        CURRENT-M1-1.md    a permanent record of each completed task
        CURRENT-M1-2.md
```

- **SPEC.md** — the plan: goal, users, requirements, definition of done. Written
  once during planning, then read-only. It is the stable source of intent.
- **TASKS.md** — the checklist of milestones and tasks. The single source of
  truth for what is left to build. The orchestrator ticks boxes here as tasks
  complete (`[ ]` todo, `[x]` built, `[v]` independently verified).
- **CURRENT.md** — disposable scratch context for the one task being built right
  now. The orchestrator writes the task into it; the sub-agent reads it and logs
  its work back. At the end of each run it is archived and reset to clean.
- **VERIFY.md** — the verification agent's verdict: PASS/FAIL for the test run
  and for each SPEC acceptance criterion. Overwritten by each `/flow:verify` run.
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

Verification follows the same principle: the agent that builds a task should
not be the one that grades it. `/flow:verify` always spawns a fresh agent with
no memory of the build conversation, so its check of the SPEC's acceptance
criteria is genuinely independent rather than the builder re-checking its own
work.

## Install

```
/plugin marketplace add MaxGol/flow
/plugin install flow@flow-marketplace
/reload-plugins
```

## Usage

```
/flow:spike <slug>       investigate a vague problem, surface the decisions (optional)
/flow:plan <slug>        describe a feature (or answer the spike), approve the breakdown
/flow:implement <slug>   build the next task for that feature (run once per task)
/flow:verify <slug>      independently confirm completed tasks meet the SPEC
```

## Credit

The architecture — a phased plan → implement pipeline where sub-agents
coordinate through shared markdown state — is inspired by
[Belmont](https://github.com/blake-simpson/belmont). `flow` is my own
Claude-only reimplementation, written from scratch to understand the pattern
and adapt it to my workflow. It is deliberately minimal: a few commands and one
agent, with per-task archiving, versus Belmont's larger multi-agent, multi-tool
system.
