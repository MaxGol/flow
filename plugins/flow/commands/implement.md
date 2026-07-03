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
Find the **first task marked `[ ]`** (todo).

If there are no `[ ]` tasks, say "All tasks done." and stop.

Show the user the task you picked:

```
Next task: [task id] — [task name]
```

## Step 2: Write the CURRENT file

Create `BASE/CURRENT.md` from scratch, describing ONLY the task you picked.
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

- subagent_type: `general-purpose`
- prompt:

> You are the Implementation Agent.
> Your instructions are in `${CLAUDE_PLUGIN_ROOT}/agents/implementation-agent.md` (read it first).
> The context file is `BASE/CURRENT.md` — read it, then follow your instructions.

Wait for the sub-agent to finish. It will have written its results into the
`## Implementation Log` section of `BASE/CURRENT.md`.

## Step 4: Archive the completed task

Now that the task is done and its log is written:

1. Create the `BASE/archive/` folder if it does not exist.
2. Copy the completed `BASE/CURRENT.md` to `BASE/archive/CURRENT-[task id].md`
   (e.g. `BASE/archive/CURRENT-M1-1.md`). This is the permanent record of
   this task.
3. Reset `BASE/CURRENT.md` back to a clean, empty state by writing exactly:

```markdown
# Milestone (single task)

_No active task. Run /flow:implement to start the next one._
```

This keeps `CURRENT.md` clean at rest — the real records live in `BASE/archive/`.

## Step 5: Update progress and report

1. Check the `## Implementation Log` you just read. If the agent reported the
   verification as FAILED (or did not pass it), do NOT mark the task done —
   tell the user it failed, show the reason, and stop so they can decide.
2. If verification passed, in `BASE/TASKS.md` change this task's `[ ]` to
   `[x]`. Change ONLY this task's checkbox — leave every other line as it is.
3. Tell the user, briefly:

```
Done: [task id] — [task name] (verification passed)
Archived to BASE/archive/CURRENT-[task id].md
[one line on what was built]
```

## Rules

- Do NOT write product code yourself — the sub-agent does that.
- Handle only the ONE task you picked, per run.
- Every task is archived to `BASE/archive/` as its own file. `CURRENT.md` is
  a working file only — it is always reset to clean at the end of a run.
- Do NOT mark anything `[v]` — that is the verify step's job (added later).
