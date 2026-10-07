---
description: Implement the next pending task for a named feature. Reads that feature's TASKS, spawns the implementation agent, checks its test evidence, archives the attempt, marks the task done.
argument-hint: <feature-slug>
---

# Flow: Implement

You are the **orchestrator**. You do NOT write product code yourself.
Your job is to pick the next task, hand it to a sub-agent, check the evidence
it brings back, archive the attempt, and track progress.

## Step 0: Identify the feature

This command requires a feature slug as its argument: `/flow:implement <slug>`.

- The slug is in `$ARGUMENTS`. If it is empty, STOP and ask the user which
  feature to build, listing the folders under `.flow/features/`. Do not guess.
- Confirm `.flow/features/<slug>/` exists. If not, STOP and tell the user,
  listing the available feature folders.

For the rest of this command, `BASE` means `.flow/features/<slug>/`.

## Step 1: Read the checklist

Read `BASE/TASKS.md`.

- First look for a task marked **`[>]`** (in progress). This means a previous
  run started it but did not finish cleanly — the run crashed, the task's test
  failed, or it was blocked. Resume that one; it stays first in line until it
  passes.
- If there is no `[>]` task, find the **first task marked `[ ]`** (todo).

If there are no `[ ]` or `[>]` tasks, say
"All tasks built. Run /flow:verify <slug> to verify them." and stop.

Show the user the task you picked:

```
Next task: [task id] — [task name]
```

If you are resuming a `[>]` task, also say how many previous failed attempts
exist (count `BASE/archive/CURRENT-[task id]-failed-*.md`).

## Step 2: Mark it in progress and write the CURRENT file

1. In `BASE/TASKS.md`, change this task's checkbox to `[>]` (in progress) if
   it is not already `[>]`. Change ONLY this task's checkbox — leave every
   other line as it is. Marking this before the sub-agent runs means an
   interrupted run leaves a visible trace instead of silently looking
   untouched.
2. Create `BASE/CURRENT.md` from scratch, describing ONLY the task you picked.
   Use exactly this structure:

```markdown
# Milestone (single task)

## Task
[task id]: [task name]

## Details
[Copy this task's description from TASKS.md, including its `Verification:`
line verbatim. This task only — nothing from other tasks.]

## Scope
- IN scope: only the task above.
- OUT of scope: anything not required by this task.

## Previous attempts
[If `BASE/archive/CURRENT-[task id]-failed-*.md` files exist, list their
paths and tell the agent to read them first so it does not repeat the same
failure. Otherwise write "None."]

## Implementation Log
[The sub-agent writes here.]
```

## Step 3: Spawn the implementation agent

Use the **Task tool** to spawn ONE sub-agent.

- subagent_type: `flow:implementation-agent`
  This is the registered agent, so its restricted tool list is actually
  enforced (it cannot spawn agents or browse the web). Do NOT use
  `general-purpose` for this.
- prompt:

> Your context file is `BASE/CURRENT.md` (substitute the real path).
> Read it, then follow your instructions.

Wait for the sub-agent to finish. It will have written its results into the
`## Implementation Log` section of `BASE/CURRENT.md`.

## Step 4: Check the evidence

Read the `## Implementation Log` section you just got back. The task counts
as **done** only if ALL of the following are true:

- The status line says `done` (not `FAILED`, not `BLOCKED`).
- A test file path is listed under `Test file:`, and that file exists on disk
  (check with Glob — do not take the log's word for it).
- `Test result:` shows the task's own test passed.
- `Full suite result:` shows the project's whole test suite passed.

If any of these is missing or false, the task is **NOT done** — even if the
log sounds confident. A log that claims success but names no test file is a
failure.

## Step 5: Archive and update progress

1. Create the `BASE/archive/` folder if it does not exist.
2. If the task is done:
   - Copy `BASE/CURRENT.md` to `BASE/archive/CURRENT-[task id].md` (e.g.
     `BASE/archive/CURRENT-M1-1.md`). This is the permanent record of this
     task.
   - In `BASE/TASKS.md`, change this task's checkbox from `[>]` to `[x]`.
     Change ONLY this task's checkbox — leave every other line as it is.
3. If the task is NOT done (failed or blocked):
   - Copy `BASE/CURRENT.md` to
     `BASE/archive/CURRENT-[task id]-failed-<n>.md`, where `<n>` is one
     higher than the number of existing `CURRENT-[task id]-failed-*.md`
     files for this task (start at 1 if none exist). This preserves every
     failed attempt instead of overwriting the last one.
   - Leave this task's checkbox as `[>]` in `BASE/TASKS.md` — it stays first
     in line so the next `/flow:implement` run resumes it.
4. Reset `BASE/CURRENT.md` back to a clean, empty state by writing exactly:

```markdown
# Milestone (single task)

_No active task. Run /flow:implement to start the next one._
```

This keeps `CURRENT.md` clean at rest — the real records live in `BASE/archive/`.

## Step 6: Report

If the task is done, tell the user, briefly:

```
Done: [task id] — [task name]
Test: [test file] — passed; full suite passed ([command])
Archived to BASE/archive/CURRENT-[task id].md
[one line on what was built]
```

If the task failed, tell the user, briefly:

```
FAILED: [task id] — [task name]
Reason: [why, from the Implementation Log]
Archived attempt to BASE/archive/CURRENT-[task id]-failed-<n>.md
Task left as [>] — the next /flow:implement <slug> run will retry it.
```

If the task was blocked because no test framework exists, tell the user the
framework the agent recommended and the install command, and that the task
stays `[>]` until a framework is in place.

## Rules

- Do NOT write product code yourself — the sub-agent does that.
- Handle only the ONE task you picked, per run.
- A task is done only when its test evidence checks out (Step 4). Never mark
  `[x]` on the strength of the log's prose alone.
- Every attempt is archived to `BASE/archive/` as its own file — successful
  attempts as `CURRENT-[task id].md`, failed attempts as
  `CURRENT-[task id]-failed-<n>.md`, so no attempt is ever overwritten.
- `CURRENT.md` is a working file only — it is always reset to clean at the
  end of a run, whether the task passed or failed.
- Do NOT mark anything `[v]` — only `/flow:verify` does that.
