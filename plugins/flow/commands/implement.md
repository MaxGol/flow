---
description: Implement the next pending task. Reads PROGRESS, spawns the implementation agent, archives the result, marks the task done.
---

# Flow: Implement

You are the **orchestrator**. You do NOT write product code yourself.
Your job is to pick the next task, hand it to a sub-agent, archive the result,
and track progress.

## Step 1: Read the checklist

Read `.flow/PROGRESS.md`.
Find the **first task marked `[ ]`** (todo).

If there are no `[ ]` tasks, say "All tasks done." and stop.

Show the user the task you picked:

```
Next task: [task id] — [task name]
```

## Step 2: Write the MILESTONE file

Create `.flow/MILESTONE.md` from scratch, describing ONLY the task you picked.
Use exactly this structure:

```markdown
# Milestone (single task)

## Task
[task id]: [task name]

## Details
[Copy this task's description from PROGRESS.md. If it has acceptance
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
> The context file is `.flow/MILESTONE.md` — read it, then follow your instructions.

Wait for the sub-agent to finish. It will have written its results into the
`## Implementation Log` section of `.flow/MILESTONE.md`.

## Step 4: Archive the completed task

Now that the task is done and its log is written:

1. Create the `.flow/archive/` folder if it does not exist.
2. Copy the completed `.flow/MILESTONE.md` to `.flow/archive/MILESTONE-[task id].md`
   (e.g. `.flow/archive/MILESTONE-M1-1.md`). This is the permanent record of
   this task.
3. Reset `.flow/MILESTONE.md` back to a clean, empty state by writing exactly:

```markdown
# Milestone (single task)

_No active task. Run /flow:implement to start the next one._
```

This keeps `MILESTONE.md` clean at rest — the real records live in `.flow/archive/`.

## Step 5: Update progress and report

1. In `.flow/PROGRESS.md`, change this task's `[ ]` to `[x]`. Change ONLY this
   task's checkbox — leave every other line exactly as it is.
2. Tell the user, briefly:

```
Done: [task id] — [task name]
Archived to .flow/archive/MILESTONE-[task id].md
[one line on what was built]
```

## Rules

- Do NOT write product code yourself — the sub-agent does that.
- Handle only the ONE task you picked, per run.
- Every task is archived to `.flow/archive/` as its own file. `MILESTONE.md` is
  a working file only — it is always reset to clean at the end of a run.
- Do NOT mark anything `[v]` — that is the verify step's job (added later).