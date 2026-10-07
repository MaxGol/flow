---
description: Independently verify a completed feature against its SPEC. Spawns a fresh, read-only verification agent that re-runs the suite, audits each task's test, and confirms every acceptance criterion, then marks verified tasks [v]. Does not fix code — failures become new tasks.
argument-hint: <feature-slug>
---

# Flow: Verify

You are the **verification orchestrator**. Your job is to run an *independent*
check that a completed feature actually does what its SPEC says — using a fresh
agent that did NOT build the code. You do not judge the code yourself, and you
do not fix anything.

## Step 0: Identify the feature

This command requires a feature slug: `/flow:verify <slug>`.

- The slug is in `$ARGUMENTS`. If it is empty, STOP and ask which feature to
  verify, listing the folders under `.flow/features/`. Do not guess.
- Confirm `.flow/features/<slug>/` exists. If not, STOP and list the available
  feature folders.

For the rest of this command, `BASE` means `.flow/features/<slug>/`.

## Step 1: Confirm there is something to verify

Read `BASE/TASKS.md`.

- Find the tasks marked `[x]` (built, not yet verified). If there are none,
  say so and stop — there is nothing to verify yet (either nothing is built,
  or everything is already `[v]`).
- If any tasks are still `[ ]` or `[>]`, the feature is not fully built.
  Tell the user how many remain and that acceptance criteria owned by unbuilt
  tasks will fail. Ask whether to verify anyway. Only continue on an explicit
  yes.

## Step 2: Spawn the verification agent (independent)

Use the **Task tool** to spawn ONE sub-agent with a fresh context. It must not
inherit the build conversation — its independence is the point.

- subagent_type: `flow:verification-agent`
  This is the registered agent, so its read-only tool list (Read, Bash,
  Grep, Glob — no Write, no Edit) is actually enforced. Do NOT use
  `general-purpose` for this.
- prompt:

> The feature you are verifying lives in `BASE` (substitute the real path).
> Read `BASE/SPEC.md`, `BASE/TASKS.md` and the task records in
> `BASE/archive/`, then follow your instructions. Return your verdict as your
> final message, in the exact format your instructions specify.

Wait for the agent to finish. Its final message is the verdict.

## Step 3: Save the verdict

1. If `BASE/VERIFY.md` already exists from an earlier run, copy it to
   `BASE/archive/VERIFY-<n>.md` first (`<n>` = one higher than the existing
   `VERIFY-*.md` files, starting at 1), so verification history is kept.
2. Write the agent's verdict **verbatim** to `BASE/VERIFY.md`. Do not edit,
   soften, or summarise it.
3. If the verdict is missing, incomplete, or has no `## Verdict` section,
   treat it as FAIL: tell the user the agent did not produce a usable
   verdict, save whatever came back, and do NOT mark anything `[v]`.

## Step 4: Act on the verdict

**If the verdict is PASS** (suite green AND every task test passed its audit
AND every acceptance criterion confirmed):

1. In `BASE/TASKS.md`, change this feature's `[x]` tasks to `[v]` (verified).
   Change only checkboxes — leave other text as it is.
2. Tell the user, briefly:

```
Verified: <slug> — [N] acceptance criteria met, [M] task tests audited, suite green.
Verdict: BASE/VERIFY.md
```

**If the verdict is FAIL:**

1. Do NOT mark anything `[v]`. Do NOT fix the code here.
2. For each numbered failure in the verdict, add one remediation task to
   `BASE/TASKS.md` as `[ ]` under a milestone named
   `## MV: Verification fixes` (create it at the end of the file if it does
   not exist). Number tasks `MV-1`, `MV-2`, ... continuing from the highest
   existing `MV-` id, so ids stay unique across runs. Each task carries:
   - a one-line description naming the criterion or task that failed, the
     file, and what is wrong (lifted from the verdict), and
   - a `Verification:` line describing the behaviour a real test must
     confirm once it is fixed.
   If an open `[ ]` or `[>]` MV task already covers the same failure, do not
   add a duplicate.
3. Tell the user, briefly:

```
Verification FAILED for <slug>: [N] issue(s).
[one line per issue]
Added [N] remediation task(s) under MV. Verdict: BASE/VERIFY.md
Run /flow:implement <slug> to fix, then /flow:verify <slug> again.
```

## Rules

- Verification is INDEPENDENT — always via a fresh agent, never judged by you
  or by the agent that built the code.
- The agent is read-only. You are the one who writes `VERIFY.md` and edits
  `TASKS.md`, and nothing else.
- This command does NOT fix code. Failures become new `[ ]` tasks; fixing them
  is a later `/flow:implement` run.
- Only `/flow:verify` awards `[v]`. Built-but-unverified is `[x]`;
  independently verified is `[v]`.
- Only touch this feature's folder.
