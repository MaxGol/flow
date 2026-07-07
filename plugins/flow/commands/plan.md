---
description: Plan a feature. Interview the user, then write the SPEC and TASKS files. No code is written.
---

# Flow: Plan

You are running an **interactive planning session**. This planning work needs
your deepest reasoning — ultrathink. Carefully consider product edge cases,
what the user actually needs, and how the work breaks into tasks before
proposing any structure.

Your only goal: turn the user's idea into a feature plan — a SPEC (what and why)
and a TASKS checklist — stored in that feature's own folder under
`.flow/features/<slug>/`. Each feature is isolated in its own folder, so planning
a new feature never disturbs an existing one.

## Rules

- This is planning ONLY. Do NOT write any source code.
- Do NOT create branches or run git.
- Only write inside `.flow/features/<slug>/` for this feature. Never touch
  another feature's folder.
- Ask questions until the plan is concrete. Do not guess at vague points.
- Get the user's explicit approval BEFORE writing the files.
- Testing is mandatory and built into every task, not a separate task. Each
  task that produces code MUST carry a `Verification:` line describing the
  behaviour a real test must confirm (in the project's own test framework).
  Do NOT create standalone "write a test" tasks, and do NOT ask whether to
  include tests — a proper test is always part of every task.

## Step 1: Understand the feature

First, check whether a spike already exists for this work. If
`.flow/features/<slug>/SPIKE.md` exists (the slug may be given, or infer it from
the feature name), READ IT. It contains prior investigation — what exists,
the options, the risks, and the decisions the user was asked to make. Use it as
your starting context and confirm with the user which decisions they have made,
rather than re-asking everything from scratch.

The user will describe a feature (and may reference the spike). Ask focused
questions until you understand:

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
produces code carries its own `Verification:` line — the behaviour that a real
test (in the project's existing test framework) must confirm. Verification is an
attribute of the task, never a separate task, and is always a proper test rather
than an ad-hoc script.

Ask the user: "Does this breakdown look right, or should I adjust it?"

Wait for approval. Adjust if needed.

## Step 3: Write the files

Once approved:

1. **Derive a slug** from the feature name: lowercase, words joined by hyphens,
   no special characters (e.g. "Temperature Converter" -> `temperature-converter`).
2. **Check for collision.** If `.flow/features/<slug>/` already exists, do NOT
   overwrite it. Tell the user it exists and ask whether to pick a different name
   or overwrite. Only proceed once resolved.
3. **Create the folder** `.flow/features/<slug>/`.
4. Write the two files inside it:

### `.flow/features/<slug>/SPEC.md`

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

### `.flow/features/<slug>/TASKS.md`

```markdown
# Tasks: [feature name]

Status legend: [ ] todo · [>] in progress · [x] done · [v] verified

## M1: [milestone name]
- [ ] M1-1: [task name] — [one line on what it involves]
  - Verification: [the behaviour a real test must confirm — e.g. "getX() returns only valid values and varies across calls"]
- [ ] M1-2: [task name] — [one line]
  - Verification: [the behaviour a real test must confirm — e.g. "getX() returns only valid values and varies across calls"]

## M2: [milestone name] (depends: M1)
- [ ] M2-1: [task name] — [one line]
  - Verification: [the behaviour a real test must confirm — e.g. "getX() returns only valid values and varies across calls"]
```

## Step 4: Confirm

Tell the user, briefly:

```
Plan written for feature "<slug>":
- .flow/features/<slug>/SPEC.md
- .flow/features/<slug>/TASKS.md
[N] milestones, [M] tasks. Run /flow:implement <slug> to build the first task.
```
