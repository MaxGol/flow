---
description: Implement the next pending task for a named feature. Reads that feature's TASKS, spawns the implementation agent, checks its test evidence, archives the attempt, marks the task done.
argument-hint: <feature-slug>
allowed-tools: Read, Edit(.flow/**), Agent
---

# Flow: Implement

You are the **orchestrator**. You do NOT write product code yourself.
Your job is to pick the next task, hand it to a sub-agent, check the evidence
it brings back, archive the attempt, and track progress.

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
   `grep -rn "vitest" package.json`.
3. **Changing files:** change `.flow` files only with Edit or Write. Never
   use heredocs, `cat >`, `sed -i`, `cp`, `mv` or interpreter scripts to
   create, change, copy or move a file.
4. **Bash:** use Bash only for the read-only search commands in rule 2.
   Run nothing else through it — no builds, no tests, no installs, no git.
   The sub-agent runs the project's commands, not you.

## Step 0: Plan-mode guard

Do this before anything else. If the session is in plan mode, STOP now —
before reading or changing any feature file — and tell the user:

```
/flow:implement can't run in plan mode. Leave plan mode, then run
/flow:implement <slug> again.
```

Only continue to Step 1 when the session is not in plan mode.

## Step 1: Identify the feature

This command requires a feature slug as its argument: `/flow:implement <slug>`.

- The slug is in `$ARGUMENTS`. If it is empty, STOP and ask the user which
  feature to build, listing the folders under `.flow/features/` (with `ls`).
  Do not guess.
- Confirm `.flow/features/<slug>/` exists (with `ls`). If not, STOP and tell
  the user, listing the available feature folders.

For the rest of this command, `BASE` means `.flow/features/<slug>/`.

## Step 2: Make sure the SPEC has its commands

Read `BASE/SPEC.md`. The implementation agent runs only the commands in the
SPEC's `## Commands` section, so that section must exist before any task
starts.

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
   `BASE/TASKS.md` or `BASE/CURRENT.md` until the user has answered.
4. On "no", STOP. Tell the user to correct the `## Commands` block in
   `BASE/SPEC.md` (or run `/flow:plan`), then run `/flow:implement <slug>`
   again. Change nothing else.
5. On "yes", go on to Step 3.

## Step 3: Read the checklist

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

Count the previous failed attempts for this task with `ls` on
`BASE/archive/` (for example `ls .flow/features/<slug>/archive/`), counting
the files named `CURRENT-[task id]-failed-<n>.md`. If the folder does not
exist, the count is 0. If you are resuming a `[>]` task, tell the user how
many previous failed attempts exist.

## Step 4: Mark it in progress and write the CURRENT file

1. In `BASE/TASKS.md`, change this task's checkbox to `[>]` (in progress)
   with Edit, if it is not already `[>]`. Change ONLY this task's checkbox —
   leave every other line as it is. Marking this before the sub-agent runs
   means an interrupted run leaves a visible trace instead of silently
   looking untouched.
2. Create `BASE/CURRENT.md` from scratch with Write, describing ONLY the task
   you picked. Use exactly this structure:

```markdown
# Milestone (single task)

## Task
[task id]: [task name]

## Details
[Copy only this task's description from TASKS.md, with its `Verification:`
and `covers:` lines verbatim. This task only — nothing from other tasks.
If the description points at earlier tasks' archives or at the SPEC, do not
pass that pointer on. Instead, under the task details, summarise the facts
the agent needs in at most 5 lines, then add:
"Full notes: <path>. Read only if the summary isn't enough."]

## Scope
- IN scope: only the task above.
- OUT of scope: anything not required by this task.

## Previous attempts
[If the `ls` in Step 3 found `BASE/archive/CURRENT-[task id]-failed-*.md`
files, list their paths and tell the agent to read them first so it does not
repeat the same failure. Otherwise write "None."]

## Implementation Log
[The sub-agent writes here.]
```

Apart from the failed attempts listed under `## Previous attempts`,
CURRENT.md never tells the agent to read a whole archive file or the whole
SPEC.

## Step 5: Spawn the implementation agent

Use the **Agent tool** to start ONE sub-agent, in the foreground:

- subagent_type: `flow:implementation-agent`
  This is the registered agent, so its restricted tool list is actually
  enforced (it cannot spawn agents or browse the web). Do NOT use
  `general-purpose` for this.
- run_in_background: false
  Set `run_in_background: false` explicitly. The run must wait for the agent
  to finish; a background agent would end this turn before the evidence is
  checked and the attempt archived.
- prompt:

> Your context file is `BASE/CURRENT.md` (substitute the real path).
> Read it, then follow your instructions.

Wait for the agent's result. It will have written its results into the
`## Implementation Log` section of `BASE/CURRENT.md`. Then carry on with
Steps 6, 7 and 8 in this same turn — do not end the turn, and do not hand
back to the user, until the attempt is archived and `BASE/CURRENT.md` is
reset.

## Step 6: Check the evidence

Read `BASE/CURRENT.md` and look at the `## Implementation Log` section. The
task counts as **done** only if ALL of the following are true:

- The status line says `done` (not `FAILED`, not `BLOCKED (missing command)`,
  not `BLOCKED (environment)`).
- A test file path is listed under `Test file:`, and that file exists on disk
  — check it yourself with Read or `ls`; do not take the log's word for it.
- `Test result:` shows the task's own test passed.
- `Full suite result:` shows the project's whole test suite passed.
- `Type-check result:` shows PASS, or "none" when the SPEC's Type-check
  command is "none".

If any of these is missing or false, the task is **NOT done** — even if the
log sounds confident. A log that claims success but names no test file is a
failure.

## Step 7: Archive and update progress

Archive by reading `BASE/CURRENT.md` with Read and writing its full content,
unchanged, to the archive file with Write. Write creates the `BASE/archive/`
folder if it does not exist yet.

1. If the task is done:
   - Write the content of `BASE/CURRENT.md` to
     `BASE/archive/CURRENT-[task id].md` (e.g.
     `BASE/archive/CURRENT-M1-1.md`). This is the permanent record of this
     task.
   - In `BASE/TASKS.md`, change this task's checkbox from `[>]` to `[x]`
     with Edit. Change ONLY this task's checkbox — leave every other line as
     it is.
2. If the task is NOT done (failed or blocked):
   - Write the content of `BASE/CURRENT.md` to
     `BASE/archive/CURRENT-[task id]-failed-<n>.md`, where `<n>` is one
     higher than the failed-attempt count from the `ls` on `BASE/archive/`
     in Step 3 (start at 1 if none exist). This preserves every failed
     attempt instead of overwriting the last one.
   - Leave this task's checkbox as `[>]` in `BASE/TASKS.md` — it stays first
     in line so the next `/flow:implement` run resumes it.
3. Reset `BASE/CURRENT.md` back to a clean, empty state with Write, writing
   exactly:

```markdown
# Milestone (single task)

_No active task. Run /flow:implement to start the next one._
```

This keeps `CURRENT.md` clean at rest — the real records live in `BASE/archive/`.

## Step 8: Report

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

If the task was blocked, report the agent's BLOCKED reason from the
Implementation Log, briefly:

```
BLOCKED: [task id] — [task name]
Reason: [missing command | environment] — [the missing command or the
environment error, from the log's Notes]
Archived attempt to BASE/archive/CURRENT-[task id]-failed-<n>.md
Task left as [>] — fix the cause, then run /flow:implement <slug> again.
```

- For "missing command", tell the user which command the SPEC's
  `## Commands` section lacks, and that they should add it to `BASE/SPEC.md`.
- For "environment", tell the user the environment error the agent hit (for
  example a missing dependency or a service that is not running), so they
  can fix it.

## Rules

- Follow the Tool rules for every tool call.
- Do NOT write product code yourself — the sub-agent does that.
- Handle only the ONE task you picked, per run.
- A task is done only when its test evidence checks out (Step 6). Never mark
  `[x]` on the strength of the log's prose alone.
- Every attempt is archived to `BASE/archive/` as its own file — successful
  attempts as `CURRENT-[task id].md`, failed attempts as
  `CURRENT-[task id]-failed-<n>.md`, so no attempt is ever overwritten.
- `CURRENT.md` is a working file only — it is always reset to clean at the
  end of a run, whether the task passed or failed.
- Do NOT mark anything `[v]` — only `/flow:verify` does that.
