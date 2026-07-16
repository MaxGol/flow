---
description: Independently verify a completed feature against its SPEC. Spawns a fresh verification agent that re-runs the tests and confirms every acceptance criterion, then marks verified tasks [v]. Does not fix code — failures become new tasks.
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

Read `BASE/TASKS.md`. Find the tasks marked `[x]` (built, not yet verified).

- If there are no `[x]` tasks, say so and stop — there is nothing to verify yet
  (either nothing is built, or everything is already `[v]`).

## Step 2: Spawn the verification agent (independent)

Use the **Task tool** to spawn ONE sub-agent with a fresh context. It must not
inherit the build conversation — its independence is the point.

- subagent_type: `general-purpose`
- prompt:

> You are the Verification Agent.
> Your instructions are in `${CLAUDE_PLUGIN_ROOT}/agents/verification-agent.md` (read it first).
> The feature you are verifying lives in `BASE` (substitute the real path).
> Read `BASE/SPEC.md` (the acceptance criteria) and `BASE/TASKS.md`, then follow
> your instructions. Write your verdict to `BASE/VERIFY.md`.

Wait for the agent to finish. It will have written a verdict to `BASE/VERIFY.md`.

## Step 3: Read the verdict and act

Read `BASE/VERIFY.md`. It contains a PASS/FAIL result for the test run and for
each SPEC acceptance criterion.

**If everything PASSED** (tests green AND every criterion confirmed):
1. In `BASE/TASKS.md`, change this feature's `[x]` tasks to `[v]` (verified).
   Change only checkboxes — leave other text as it is.
2. Tell the user, briefly:

```
Verified: <slug> — all acceptance criteria met, tests green.
Verdict: BASE/VERIFY.md
```

**If anything FAILED:**
1. Do NOT mark anything `[v]`. Do NOT fix the code here.
2. For each failure the agent found, add a new remediation task to `BASE/TASKS.md`
   as `[ ]`, under a milestone named `## MX: Verification fixes` (create it if
   needed), each with a `Verification:` line describing how the fix will be
   confirmed.
3. Tell the user, briefly:

```
Verification FAILED for <slug>: [N] issue(s).
[one line per issue]
Added [N] remediation task(s). Verdict: BASE/VERIFY.md
Run /flow:implement <slug> to fix, then /flow:verify <slug> again.
```

## Rules

- Verification is INDEPENDENT — always via a fresh agent, never judged by you or
  by the agent that built the code.
- This command does NOT fix code. Failures become new `[ ]` tasks; fixing them is
  a later `/flow:implement` run.
- Only `/flow:verify` awards `[v]`. Built-but-unverified is `[x]`; independently
  verified is `[v]`.
- Only touch this feature's folder.
