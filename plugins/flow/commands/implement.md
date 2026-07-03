---
description: Implement the next pending task for a named feature. Reads that feature's TASKS, spawns the implementation agent, archives the result, marks the task done.
argument-hint: <feature-slug>
---

# Flow: Implement

You are the **orchestrator**. You do NOT write product code yourself.
Your job is to pick the next task, hand it to a sub-agent, archive the result,
and track progress.

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
  run started it but it did not finish cleanly — either the run crashed, or
  verification failed and it was left here for retry. Resume that one.
- If there is no `[>]` task, find the **first task marked `[ ]`** (todo).

If there are no `[ ]` or `[>]` tasks, say "All tasks done." and stop.

Show the user the task you picked:

```
Next task: [task id] — [task name]
```

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
[Copy this task's description from TASKS.md. If it has acceptance
criteria, copy them too. This task only — nothing from other tasks.]

## Scope
- IN scope: only the task above.
- OUT of scope: anything not required by this task.

## Implementation Log
[The sub-agent writes here.]
```

## Step 3: Spawn the implementation agent

Use the **Task tool** to spawn ONE sub-agent.

- subagent_type: `flow:implementation-agent`
- prompt:

> Read `BASE/CURRENT.md`, then follow your instructions.

Wait for the sub-agent to finish. It will have written its results into the
`## Implementation Log` section of `BASE/CURRENT.md`.

## Step 4: Check the result

Read the `## Implementation Log` section you just got back.

- If it reports verification **passed**: this task is done.
- If it reports verification **FAILED** or **BLOCKED (no test framework)**:
  this task is NOT done.

## Step 5: Archive and update progress

1. Create the `BASE/archive/` folder if it does not exist.
2. If verification passed:
   - Copy `BASE/CURRENT.md` to `BASE/archive/CURRENT-[task id].md` (e.g.
     `BASE/archive/CURRENT-M1-1.md`). This is the permanent record of this
     task.
   - In `BASE/TASKS.md`, change this task's checkbox from `[>]` to `[x]`.
     Change ONLY this task's checkbox — leave every other line as it is.
3. If verification failed:
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

If verification passed, tell the user, briefly:

```
Done: [task id] — [task name] (verification passed)
Archived to BASE/archive/CURRENT-[task id].md
[one line on what was built]
```

If verification failed, tell the user, briefly:

```
FAILED: [task id] — [task name]
Reason: [why, from the Implementation Log]
Archived attempt to BASE/archive/CURRENT-[task id]-failed-<n>.md
Task left as [>] in TASKS.md — it will be retried on the next /flow:implement run.
```

## Rules

- Do NOT write product code yourself — the sub-agent does that.
- Handle only the ONE task you picked, per run.
- Every attempt is archived to `BASE/archive/` as its own file — successful
  attempts as `CURRENT-[task id].md`, failed attempts as
  `CURRENT-[task id]-failed-<n>.md`, so no attempt is ever overwritten.
- `CURRENT.md` is a working file only — it is always reset to clean at the
  end of a run, whether the task passed or failed.
- Do NOT mark anything `[v]` — that is the verify step's job (added later).
