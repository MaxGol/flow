---
description: Investigate a vague or unfamiliar problem before planning it. Produces a findings document (SPIKE.md) with options, risks, and the decisions you must make. Writes no code and no plan.
argument-hint: <feature-slug>
---

# Flow: Spike

You are running an **investigation**, not a build and not a plan. This planning
work needs your deepest reasoning — ultrathink. The goal is to turn a vague or
unfamiliar problem into a clear map: what already exists, what the options are,
what the risks are, and — most importantly — the decisions the developer must
make before the work can be planned.

You produce ONE output: a `SPIKE.md` findings document. You do NOT write code,
tests, a SPEC, or a task list. You do NOT pick an approach.

## Step 0: Identify the feature

This command requires a feature slug: `/flow:spike <slug>`.

- The slug is in `$ARGUMENTS`. If it is empty, STOP and ask the user what to
  investigate and what slug to use. Do not guess.
- Create `.flow/features/<slug>/` if it does not exist.

For the rest of this command, `BASE` means `.flow/features/<slug>/`.

## Step 1: Understand the question

The user will describe a problem — often vaguely (e.g. "integrate Stripe",
"improve our caching"). Ask a few clarifying questions to pin down the *scope of
the investigation* — not the solution. For example: which part of the system is
in play, what outcome they care about, any hard constraints.

Keep this short. You are scoping what to look into, not designing anything yet.

## Step 2: Investigate

Gather the facts needed to lay out the decision space. Draw on:

- **The codebase.** Read the relevant existing code, config, and docs. Find what
  already exists that touches this problem — current patterns, related modules,
  half-built work, conventions you would need to respect.
- **The web, when useful.** You may web-search for external facts: library or
  API options, documented approaches, version/compatibility details, known
  pitfalls. Prefer official docs and primary sources. Cite what you rely on.

Investigate broadly enough to describe the real options and the real risks. Do
not go so deep that you start implementing — the moment you are writing solution
code, you have gone too far.

## Step 3: Write SPIKE.md

Write `BASE/SPIKE.md` with exactly these sections:

```markdown
# Spike: [feature name]

## Question
[The problem being investigated, stated clearly — sharpened from the user's
original vague ask.]

## What already exists
[What the codebase already has that is relevant: files, patterns, related or
half-built work, conventions to respect. Be concrete — name files and modules.]

## Options
[The viable approaches, each with its trade-offs. Present them fairly. Do NOT
recommend one — lay them out so the developer can choose.]

## Risks & unknowns
[What could go wrong, what is still unclear, what would need to be validated.
Include anything that makes this harder than it first appears.]

## Decisions you must make
[An explicit, numbered list of questions that ONLY the developer can answer.
This is the handoff to /flow:plan. Each decision should be concrete enough that
answering it moves the problem from vague toward well-defined.]

## Sources
[Any web sources you relied on, or "codebase only".]
```

## Step 4: Hand off

Tell the user, briefly:

```
Spike written for feature "[slug]":
- BASE/SPIKE.md

[N] decisions surfaced. Answer the "Decisions you must make" section, then run
/flow:plan to turn them into a concrete plan.
```

## Rules

- Investigation only. Do NOT write code, tests, a SPEC, or a task list.
- Do NOT decide the approach or recommend one. Your job is to lay out the
  options and surface the decisions — the developer chooses.
- Only write `BASE/SPIKE.md`. Do not touch any other feature's folder.
- If the problem turns out to be small and already well-defined, say so plainly
  and suggest going straight to /flow:plan rather than padding a spike.
