---
description: Plan a feature. Interview the user, then write the SPEC and TASKS files. No code is written.
---

# Flow: Plan

You are running an **interactive planning session**. This planning work needs
your deepest reasoning — ultrathink. Carefully consider product edge cases,
what the user actually needs, and how the work breaks into tasks before
proposing any structure.

Your only goal: turn the user's idea into two files —
`.flow/SPEC.md` (what and why) and `.flow/TASKS.md` (the task checklist).

## Rules

- This is planning ONLY. Do NOT write any source code.
- Do NOT create branches or run git.
- Only write inside the `.flow/` folder.
- Ask questions until the plan is concrete. Do not guess at vague points.
- Get the user's explicit approval BEFORE writing the files.
- Testing is mandatory and built into every task, not a separate task. Each
  task that produces code MUST carry a `Verification:` line describing how to
  prove it works. Do NOT create standalone "write a test" tasks, and do NOT
  ask whether to include tests — verification is always part of every task.

## Step 1: Understand the feature

The user will describe a feature. Ask focused questions until you understand:

- What the feature does, and who it is for.
- What "done" looks like (the observable outcome).
- Any constraints (existing stack, must-not-break areas, data involved).
- The obvious edge cases.

Ask a few questions at a time, not a wall. Stop asking once the picture is
concrete enough to break into tasks.

## Step 2: Propose the breakdown

Summarise, in plain prose, the milestones you propose and the tasks inside
each. A **milestone** is a meaningful chunk that can be built and checked on
its own. A **task** is one concrete unit of work inside a milestone. Every task that
produces code carries its own `Verification:` line — a concrete, runnable check
that proves the task works. Verification is an attribute of the task, never a
separate task.

Ask the user: "Does this breakdown look right, or should I adjust it?"

Wait for approval. Adjust if needed.

## Step 3: Write the files

Once approved, create the `.flow/` folder if it does not exist, then write:

### `.flow/SPEC.md`

```markdown
# Spec: [feature name]

## Goal
[One paragraph: what this feature is and why it exists.]

## Users
[Who uses it and what they are trying to do.]

## Requirements
[Bullet list of what the feature must do.]

## Out of scope
[What this feature explicitly does NOT cover.]

## Definition of done
[The observable outcome that means this feature is complete.]
```

### `.flow/TASKS.md`

```markdown
# Tasks: [feature name]

Status legend: [ ] todo · [>] in progress · [x] done · [v] verified

## M1: [milestone name]
- [ ] M1-1: [task name] — [one line on what it involves]
  - Verification: [a concrete, runnable check that proves this task works]
- [ ] M1-2: [task name] — [one line]
  - Verification: [a concrete, runnable check that proves this task works]

## M2: [milestone name] (depends: M1)
- [ ] M2-1: [task name] — [one line]
  - Verification: [a concrete, runnable check that proves this task works]
```

## Step 4: Confirm

Tell the user, briefly:

```
Plan written:
- .flow/SPEC.md
- .flow/TASKS.md
[N] milestones, [M] tasks. Run /flow:implement to build the first task.
```
