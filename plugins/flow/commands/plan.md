---
description: Plan a feature. Interview the user, then write the SPEC (with acceptance criteria) and TASKS files. No code is written.
argument-hint: [feature-slug]
allowed-tools: Read, Edit(.flow/**)
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
- The SPEC MUST carry a numbered `## Acceptance criteria` list. These are
  what `/flow:verify` checks one by one, so each must be observable and
  testable from outside ("POST /x with a bad token returns 401"), not a
  restatement of a requirement ("auth works").
- The SPEC MUST carry a `## Commands` section with the exact Test, Single
  test, Type-check and Build commands. The implementation and verification
  agents run these commands exactly as written and nothing else, so each one
  must run from the project root with no `cd`. Where a command needs a
  subdirectory, use the tool's own directory flag instead (e.g.
  `pnpm -C frontend test`, `npm --prefix frontend test`,
  `pytest backend/tests`). Write "none" for Single test, Type-check or Build
  when the project has no such command. Choose the runner's non-watch,
  CI-mode command with its quietest reporter that still prints failures and
  a summary. Check the project's config or the runner's options for the
  right flag. Never choose a watch-mode command: it never exits. For
  example: `npx vitest run --reporter=dot`, `npx jest --ci --silent`,
  `pytest -q`, `go test ./...`, `cargo test -q` or
  `npx ng test --watch=false --browsers=ChromeHeadless --reporters=dots`.

## Tool rules

Follow these rules for every tool call. They keep the session free of
unnecessary permission prompts, and they apply in every step below.

1. **Reading:** read files only with Read. Never use `cat`, `sed`, `head` or
   `tail` through Bash.
2. **Searching:** search, list and check that files exist only with single
   read-only search commands: `grep -rn` or `grep -rl`, `ls`, and `find`
   without `-exec` or `-delete`. Quote patterns, use literal paths inside the
   project, and never add `cd`, `;`, `&&`, pipes or variables. For example:
   `grep -rn "vitest" package.json` or `find . -name "pyproject.toml"`.
3. **Changing files:** change `.flow` files only with Edit or Write. Never
   use heredocs, `cat >`, `sed -i`, `cp`, `mv` or interpreter scripts to
   create, change, copy or move a file.
4. **Bash:** apart from the search commands in rule 2, use Bash only for
   simple one-off commands (for example `node --version`). Run one command
   per call, with no `cd`, `;`, `&&`, pipes or shell variables. These
   one-off commands go through the normal permission flow.

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

Then work out the project's commands for the SPEC's `## Commands` section by
reading the project's config yourself — for example `package.json` scripts,
`pyproject.toml`, `pytest.ini`, `Makefile`, `angular.json`, `tsconfig.json`,
`Cargo.toml` or `go.mod` — and the existing test files. You need:

- **Test:** the command that runs the whole test suite.
- **Single test:** the command that runs one test file, with a `{file}`
  placeholder where the file path goes — or "none".
- **Type-check:** the type-check command — or "none".
- **Build:** the build command — or "none".

Each must run from the project root with no `cd` (see Rules).

Choose the runner's non-watch, CI-mode command with its quietest reporter
that still prints failures and a summary. Check the project's config or the
runner's options for the right flag. Never choose a watch-mode command: it
never exits. For example: `npx vitest run --reporter=dot`,
`npx jest --ci --silent`, `pytest -q`, `go test ./...`, `cargo test -q` or
`npx ng test --watch=false --browsers=ChromeHeadless --reporters=dots`.

## Step 2: Propose the breakdown

Summarise, in plain prose, the acceptance criteria you propose for the SPEC,
then the milestones and the tasks inside each. A **milestone** is a meaningful chunk that can be built and checked on
its own. A **task** is one concrete unit of work inside a milestone. Every task that
produces code carries its own `Verification:` line — the behaviour that a real
test (in the project's existing test framework) must confirm. Verification is an
attribute of the task, never a separate task, and is always a proper test rather
than an ad-hoc script. Where a task is what makes an acceptance criterion true,
say so (`covers: AC2`) so the verify step can trace criteria back to tasks.
Every acceptance criterion should be covered by at least one task.

Also show the Test, Single test, Type-check and Build commands you worked out
from the project config, and ask the user to confirm or correct them as part
of the breakdown. If the project has no test runner, say so here and agree
with the user on which one to use before writing the files.

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

## Commands
[The exact commands the implementation and verification agents run, as
confirmed by the user. Each runs from the project root as written, with no
`cd`; use the tool's own directory flag where needed (e.g.
`pnpm -C frontend test`). Write "none" when the project has no such command.]
Run from the project root.
- Test: [whole test suite, e.g. `npx vitest run --reporter=dot`]
- Single test: [one test file, with a `{file}` placeholder, e.g. `npx vitest run --reporter=dot {file}` — or "none"]
- Type-check: [e.g. `npx tsc --noEmit` — or "none"]
- Build: [e.g. `npm run build` — or "none"]

## Acceptance criteria
[Numbered, observable, testable statements. /flow:verify confirms each one
independently, so write them as checks, not goals.]
1. AC1: [e.g. "GET /api/convert?c=100 returns {"f": 212} with status 200"]
2. AC2: [e.g. "a non-numeric value returns 400 and a JSON error body"]
3. AC3: [...]

## Definition of done
[The observable outcome that means this feature is complete — usually "all
acceptance criteria pass and the existing test suite stays green".]
```

### `.flow/features/<slug>/TASKS.md`

```markdown
# Tasks: [feature name]

Status legend: [ ] todo · [>] in progress · [x] done · [v] verified

## M1: [milestone name]
- [ ] M1-1: [task name] — [one line on what it involves]
  - Verification: [the behaviour a real test must confirm — e.g. "getX() returns only valid values and varies across calls"]
  - covers: [AC ids this task makes true, e.g. AC1 — or omit if none]
- [ ] M1-2: [task name] — [one line]
  - Verification: [the behaviour a real test must confirm]
  - covers: [AC2]

## M2: [milestone name] (depends: M1)
- [ ] M2-1: [task name] — [one line]
  - Verification: [the behaviour a real test must confirm]
  - covers: [AC3]
```

Task descriptions must not tell the agent to read whole archive files (such
as "read the M1 archive first"). Name the exact facts or paths the agent
needs instead — for example "`parseDate` in `src/date.ts` returns `null` on
bad input".

## Step 4: Confirm

Tell the user, briefly:

```
Plan written for feature "<slug>":
- .flow/features/<slug>/SPEC.md
- .flow/features/<slug>/TASKS.md
[N] milestones, [M] tasks, [K] acceptance criteria. Run /flow:implement <slug> to build the first task.
```
