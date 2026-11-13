---
description: Independently verify a completed feature against its SPEC. Spawns a fresh, read-only verification agent that re-runs the suite, audits each task's test, and confirms every acceptance criterion, then marks [v] the tasks whose criteria all passed. Does not fix code — failures become new tasks.
argument-hint: <feature-slug>
allowed-tools: Read, Edit(.flow/**), Agent
---

# Flow: Verify

You are the **verification orchestrator**. Your job is to run an *independent*
check that a completed feature actually does what its SPEC says — using a fresh
agent that did NOT build the code. You do not judge the code yourself, and you
do not fix anything.

## Tool rules

Follow these rules for every tool call. They keep the run free of
unnecessary permission prompts, and they apply in every step below.

1. **Reading:** read files only with Read. Never use `cat`, `sed`, `head` or
   `tail` through Bash.
2. **Searching:** search, list and check that files exist only with single
   read-only search commands: `grep -rn` or `grep -rl`, `ls`, and `find`
   without `-exec` or `-delete`. Quote patterns, use literal paths inside the
   project, and never add `cd`, `;`, `&&`, pipes or variables. For example:
   `ls .flow/features/my-feature/archive/` or
   `grep -rn "covers:" .flow/features/my-feature/TASKS.md`.
3. **Changing files:** change `.flow` files only with Edit or Write. Never
   use heredocs, `cat >`, `sed -i`, `cp`, `mv` or interpreter scripts to
   create, change, copy or move a file.
4. **Bash:** use Bash only for the read-only search commands in rule 2.
   Run nothing else through it — no builds, no tests, no installs, no git.
   The verification agent runs the project's commands, not you.

## Step 0: Plan-mode guard

Do this before anything else. If the session is in plan mode, STOP now —
before reading or changing any feature file — and tell the user:

```
/flow:verify can't run in plan mode. Leave plan mode, then run
/flow:verify <slug> again.
```

Only continue to Step 1 when the session is not in plan mode.

## Step 1: Identify the feature

This command requires a feature slug: `/flow:verify <slug>`.

- The slug is in `$ARGUMENTS`. If it is empty, STOP and ask which feature to
  verify, listing the folders under `.flow/features/` (with `ls`). Do not
  guess.
- Confirm `.flow/features/<slug>/` exists (with `ls`). If not, STOP and list
  the available feature folders.

For the rest of this command, `BASE` means `.flow/features/<slug>/`.

## Step 2: Make sure the SPEC has its commands

Read `BASE/SPEC.md`. The verification agent runs only the commands in the
SPEC's `## Commands` section, so that section must exist before it starts.

If `BASE/SPEC.md` already has a `## Commands` section, go on to Step 3.

If it has no `## Commands` section:

1. Work the commands out by reading the project config yourself — for example
   `package.json` scripts, `pyproject.toml`, `pytest.ini`, `Makefile`,
   `angular.json`, `tsconfig.json`, `Cargo.toml` or `go.mod` — and the
   existing test files. Each command must run from the project root with no
   `cd`; where one needs a subdirectory, use the tool's own directory flag
   (e.g. `pnpm -C frontend test`). Choose the runner's non-watch, CI-mode
   command with its quietest reporter that still prints failures and a
   summary. Check the project's config or the runner's options for the right
   flag. Never choose a watch-mode command: it never exits. For example:
   `npx vitest run --reporter=dot`, `npx jest --ci --silent`, `pytest -q`,
   `go test ./...`, `cargo test -q` or
   `npx ng test --watch=false --browsers=ChromeHeadless --reporters=dots`.
2. Write the block into `BASE/SPEC.md` with Edit, just before
   `## Acceptance criteria`, in exactly this format:

```markdown
## Commands
Run from the project root.
- Test: [whole test suite, e.g. `npx vitest run --reporter=dot`]
- Single test: [one test file, with a `{file}` placeholder, e.g. `npx vitest run --reporter=dot {file}` — or "none"]
- Type-check: [e.g. `npx tsc --noEmit` — or "none"]
- Build: [e.g. `npm run build` — or "none"]
```

3. Ask the user to confirm the block with AskUserQuestion — show the four
   commands and ask "Use these commands for this feature?" with the options
   "yes" and "no". Do this before any other change: do not touch
   `BASE/TASKS.md` or `BASE/VERIFY.md`, and do not start the verification
   agent, until the user has answered.
4. On "no", STOP. Tell the user to correct the `## Commands` block in
   `BASE/SPEC.md` (or run `/flow:plan`), then run `/flow:verify <slug>`
   again. Change nothing else.
5. On "yes", go on to Step 3.

## Step 3: Confirm there is something to verify

Read `BASE/TASKS.md`.

- Find the tasks marked `[x]` (built, not yet verified). If there are none,
  say so and stop — there is nothing to verify yet (either nothing is built,
  or everything is already `[v]`).
- If any tasks are still `[ ]` or `[>]`, the feature is not fully built.
  Tell the user how many remain and that acceptance criteria owned by unbuilt
  tasks will fail. Ask whether to verify anyway. Only continue on an explicit
  yes.

## Step 4: Spawn the verification agent (independent)

Use the **Agent tool** to start ONE sub-agent with a fresh context, in the
foreground. It must not inherit the build conversation — its independence is
the point.

- subagent_type: `flow:verification-agent`
  This is the registered agent, so its read-only tool list (no Write, no
  Edit) is actually enforced. Do NOT use `general-purpose` for this.
- run_in_background: false
  Set `run_in_background: false` explicitly. The run must wait for the agent
  to finish; a background agent would end this turn before the verdict is
  saved and acted on.
- prompt:

> The feature you are verifying lives in `BASE` (substitute the real path).
> Read `BASE/SPEC.md`, `BASE/TASKS.md` and the task records in
> `BASE/archive/`, then follow your instructions. Return your verdict as your
> final message, in the exact format your instructions specify.

Wait for the agent's result. Its final message is the verdict. Then carry on
with Steps 5 and 6 in this same turn — do not end the turn, and do not hand
back to the user, until the verdict is saved to `BASE/VERIFY.md` and
`BASE/TASKS.md` is updated.

## Step 5: Save the verdict

1. If `BASE/VERIFY.md` already exists from an earlier run, archive it first:
   read `BASE/VERIFY.md` with Read and write its full content, unchanged, to
   `BASE/archive/VERIFY-<n>.md` with Write, so verification history is kept.
   `<n>` is one higher than the number of existing `VERIFY-*.md` files, which
   you count with `ls` on `BASE/archive/` (start at 1 if there are none or the
   folder does not exist). Write creates the folder if needed.
2. Write the agent's verdict **verbatim** to `BASE/VERIFY.md` with Write. Do
   not edit, soften, or summarise it.
3. If the verdict is missing, incomplete, or has no `## Verdict` section,
   treat it as FAIL: tell the user the agent did not produce a usable
   verdict, save whatever came back, and do NOT mark anything `[v]`.

## Step 6: Act on the verdict

The verdict's `## Acceptance criteria` section marks each criterion
`[PASS]`, `[FAIL]` or `[UNVERIFIED]`. Each task in `BASE/TASKS.md` may have a
`covers:` line naming the acceptance criteria it makes true (e.g.
`covers: AC2, AC3`). Use the two together to decide each task's checkbox.

**If the verdict is PASS** (suite green AND every task test passed its audit
AND no criterion is `[FAIL]` — some criteria may be `[UNVERIFIED]`):

1. For each `[x]` task, look up every criterion named on its `covers:` line in
   the verdict's `## Acceptance criteria` section:
   - If all of its `covers:` criteria are `[PASS]`, change the task to `[v]`
     (verified) with Edit.
   - If any of its `covers:` criteria is `[UNVERIFIED]` (or does not appear in
     the verdict at all), leave the task as `[x]` — it is built but not
     independently verified. Note the task id and the UNVERIFIED criteria for
     the report.
   - A task with no `covers:` line owns no acceptance criterion, so nothing it
     covers can be UNVERIFIED. Its only check is its task-test audit, which a
     PASS verdict means it passed, so change it to `[v]`.
   Change only checkboxes — leave other text as it is.
2. Do NOT add MV tasks. UNVERIFIED criteria are not failures; they are
   listed in the verdict's `## Unverified` section with what would confirm
   them.
3. Tell the user, briefly:

```
Verified: <slug> — [N] acceptance criteria met, [U] UNVERIFIED, [M] task tests audited, suite green.
Marked [v]: [task ids, or "none"]
Left [x] — covers an UNVERIFIED criterion: [task id (AC ids), ... — or "none"]
Verdict: BASE/VERIFY.md
```

If any task was left `[x]`, add one line telling the user that those tasks
stay `[x]` until their UNVERIFIED criteria are confirmed (see the
`## Unverified` section of `BASE/VERIFY.md` for what is needed), after which
they can run `/flow:verify <slug>` again.

**If the verdict is FAIL:**

1. Do NOT mark anything `[v]`. Do NOT fix the code here.
2. Create MV fix tasks only for FAIL items: for each numbered failure under
   the verdict's `## Verdict` FAIL line, add one remediation task to
   `BASE/TASKS.md` as `[ ]` with Edit, under a milestone named
   `## MV: Verification fixes` (create it at the end of the file if it does
   not exist). Never add an MV task for an UNVERIFIED criterion — those are
   not failures, even when the verdict is FAIL for other reasons. Number
   tasks `MV-1`, `MV-2`, ... continuing from the highest existing `MV-` id,
   so ids stay unique across runs. Each task carries:
   - a one-line description naming the criterion or task that failed, the
     file, and what is wrong (lifted from the verdict),
   - a `Verification:` line describing the behaviour a real test must
     confirm once it is fixed, and
   - a `covers:` line naming the failed criterion, if the failure is about
     one.
   If an open `[ ]` or `[>]` MV task already covers the same failure, do not
   add a duplicate.
3. Tell the user, briefly:

```
Verification FAILED for <slug>: [N] issue(s).
[one line per issue]
Added [N] remediation task(s) under MV. Verdict: BASE/VERIFY.md
UNVERIFIED (no fix task): [AC ids, or "none"]
Run /flow:implement <slug> to fix, then /flow:verify <slug> again.
```

## Rules

- Follow the Tool rules for every tool call.
- Verification is INDEPENDENT — always via a fresh agent, never judged by you
  or by the agent that built the code.
- The agent is read-only. You are the one who writes `VERIFY.md` and edits
  `TASKS.md` (and, only when it is missing, adds the `## Commands` block to
  `SPEC.md`), and nothing else.
- This command does NOT fix code. FAIL items become new `[ ]` tasks; fixing
  them is a later `/flow:implement` run. UNVERIFIED items never become tasks.
- Only `/flow:verify` awards `[v]`, and only per task: a task gets `[v]` only
  when every criterion on its `covers:` line is PASS. Built-but-unverified is
  `[x]`; independently verified is `[v]`.
- Only touch this feature's folder.
