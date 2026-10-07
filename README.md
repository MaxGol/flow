# flow

A minimal agentic development pipeline for Claude Code.

`flow` breaks feature work into phases — **spike** (optional), **plan**,
**implement**, **verify** — and makes two promises about quality:

1. Every task is backed by a real test in your project's own test framework,
   written and run by the agent that built it.
2. Every finished feature is checked again by a separate, read-only agent that
   did not build it, against the acceptance criteria in the SPEC.

## The commands

| Command | What it does | Writes |
|---|---|---|
| `/flow:spike <slug>` | Investigates a vague problem: what exists, options, risks, decisions you must make. Optional. | `SPIKE.md` |
| `/flow:plan <slug>` | Interviews you, then writes the requirements, numbered acceptance criteria, and the task checklist. | `SPEC.md`, `TASKS.md` |
| `/flow:implement <slug>` | Builds the next task via a sub-agent, which must also write and pass a real test. Run once per task. | code, a test, `archive/` |
| `/flow:verify <slug>` | Spawns a fresh read-only agent to re-run the suite, audit each task's test, and confirm every acceptance criterion. | `VERIFY.md` |

## How it works, end to end

```
/flow:spike payments        ->  SPIKE.md: options + "Decisions you must make"
/flow:plan payments         ->  SPEC.md (AC1..ACn) + TASKS.md (M1-1, M1-2, ...)
/flow:implement payments    ->  M1-1 built + tested      [ ] -> [>] -> [x]
/flow:implement payments    ->  M1-2 built + tested      [ ] -> [>] -> [x]
...
/flow:verify payments       ->  PASS: all tasks [x] -> [v]
                                FAIL: new MV-n fix tasks added, loop back to implement
```

Each `/flow:implement` run handles exactly one task, so you can review the
diff between runs. The orchestrator never writes product code itself; it
prepares context, spawns a sub-agent, checks the evidence that comes back, and
updates the checklist.

### Task lifecycle

| State | Meaning | Who sets it |
|---|---|---|
| `[ ]` | todo | `/flow:plan`, or `/flow:verify` when it adds fix tasks |
| `[>]` | in progress — a run started it and has not finished cleanly | `/flow:implement`, before the sub-agent is spawned |
| `[x]` | built — code written, its own test and the full suite pass | `/flow:implement`, after checking the evidence |
| `[v]` | verified — an independent agent confirmed the SPEC's acceptance criteria | `/flow:verify` only |

`[>]` is set *before* the sub-agent runs. If the run crashes, the test fails, or
the task is blocked, it stays `[>]` and the next `/flow:implement` resumes it
first, with its previous failed attempts linked in the context so the agent
does not repeat the same mistake.

## Verification and testing

Quality is enforced in two layers. Each layer catches what the other cannot.

### Layer 1: every task ships with a real test

**At planning time.** Every task in `TASKS.md` that produces code carries a
`Verification:` line — the behaviour a test must confirm, e.g. *"a non-numeric
input returns 400 with a JSON error body"*. Tests are an attribute of each
task, never a separate "write tests" task, and the planner does not ask
whether you want them.

**At build time.** The implementation agent (`agents/implementation-agent.md`)
is spawned as the registered `flow:implementation-agent` type with a restricted
tool set (Read, Write, Edit, Bash, Grep, Glob — no spawning agents, no web).
After writing the code it must:

1. **Detect the project's existing test framework** — `package.json` scripts
   and config files for JS/TS (Jest, Vitest, Karma + Jasmine for Angular),
   `pyproject.toml` / `pytest.ini` / `tests/` for Python, or the conventional
   runner for any other stack. It matches the runner, folder, naming and style
   of the tests already in the repo.
2. **Write a proper test** for the `Verification:` line, in that framework, in
   the conventional location. The test must assert the described behaviour.
   "Does not throw" and tautologies do not count. Throwaway "run it and print
   PASS" scripts are never acceptable.
3. **Run the task's test**, fixing the *code* and re-running on failure, up to
   three attempts.
4. **Run the full suite**, so a regression elsewhere is caught before the task
   is marked built. If an existing test breaks, the agent fixes its own change,
   not the existing test.
5. **Never weaken a test to get green** — no deleting or loosening assertions,
   no skipping, no special-casing product code to satisfy the test. The only
   legitimate edit to a test is that it did not match the `Verification:`
   line, and the agent has to say so in its log.

If **no test framework exists**, the agent stops with
`BLOCKED (no test framework)` and recommends the standard one for the stack
with the install command. It never installs anything silently and never falls
back to a script. You decide, then re-run.

**What the orchestrator checks.** `/flow:implement` does not take the agent's
word for it. A task is marked `[x]` only if the Implementation Log shows:

- status `done`,
- a `Test file:` path, and that file actually exists on disk,
- the task's test passed, and
- the full suite passed.

Anything else is a failed attempt: it is archived as
`archive/CURRENT-<task>-failed-<n>.md`, the task stays `[>]`, and the next
run retries it with the failed log in context.

### Layer 2: independent verification of the whole feature

Passing per-task tests proves each piece works as its builder understood it.
It does not prove the feature does what you asked for, and it does not catch
gaps between tasks. That is what `/flow:verify` is for.

**Separation of roles.** The builder never grades its own work. `/flow:verify`
spawns the registered `flow:verification-agent`, which has a fresh context and
a read-only tool set (Read, Bash, Grep, Glob — no Write, no Edit). It cannot
fix code, cannot touch tests, and does not even write its own verdict file; it
returns the verdict as its final message and the orchestrator saves it
verbatim. It is instructed to fail anything it cannot confirm — "could not
exercise this here" is a FAIL with a reason, not a pass.

**What the verifier does.**

1. **Reads the contract**: the numbered `## Acceptance criteria` in `SPEC.md`,
   the `Verification:` line on each built task, and each task's archived
   Implementation Log (which test file it wrote, which commands it ran).
2. **Re-runs the full suite** itself and records the exact command and counts.
   Green is necessary, not sufficient — it continues regardless.
3. **Audits each task's test**: the file exists, it calls the real code, and
   it asserts the behaviour the `Verification:` line promised. A missing,
   skipped, or hollow test fails the audit even if the product code looks
   right.
4. **Confirms each acceptance criterion independently**: finds the code,
   reads it, and where possible exercises it end to end (runs the flow, calls
   the function or endpoint, checks the observable result). It pays special
   attention to behaviour that no single task owned — the end-to-end paths
   where "every task passed" can still hide a gap.
5. **Returns a structured verdict**, saved as `VERIFY.md`:

```markdown
# Verification: Temperature converter

## Test run
- Command: npx vitest run
- Result: PASS — 14 passed, 0 failed

## Task tests
- [PASS] M1-1 — src/convert.test.ts — asserts c→f for 0, 100, -40 and NaN handling
- [FAIL] M1-2 — src/api.test.ts — only asserts status 200; never checks the body

## Acceptance criteria
- [PASS] AC1: GET /convert?c=100 returns {"f":212} — curl against dev server, body matched
- [FAIL] AC2: non-numeric input returns 400 with JSON error — returns 500 with HTML stack trace

## End-to-end checks
- Started server, hit /convert with valid, missing and non-numeric params; see above.

## Verdict
FAIL
1. AC2 — src/api.ts — no input validation before parseFloat; non-numeric falls through to 500
2. M1-2 — src/api.test.ts — test does not assert the response body or the error case
```

**What happens next.**

- **PASS**: every `[x]` task becomes `[v]`. That is the only way a task
  reaches `[v]`.
- **FAIL**: nothing is fixed automatically. Each numbered failure becomes a
  new `[ ]` task under `## MV: Verification fixes` in `TASKS.md`, with its own
  `Verification:` line, so the fix goes through the same build-and-test path
  as any other task. Run `/flow:implement` to fix, then `/flow:verify` again.
  Earlier verdicts are kept as `archive/VERIFY-<n>.md`.

If some tasks are still `[ ]` or `[>]`, `/flow:verify` warns that the feature
is incomplete and asks before proceeding, since criteria owned by unbuilt
tasks will fail.

### What each layer catches

| Failure | Caught by |
|---|---|
| Code does not do what the task said | Layer 1 — the task's own test |
| Change breaks something elsewhere | Layer 1 — full-suite run before `[x]` |
| Agent claims a test it never wrote | Layer 1 — orchestrator checks the file exists; Layer 2 — test audit |
| Test is hollow (tautology, "does not throw", skipped) | Layer 2 — test audit |
| Each task passes but the feature as a whole does not meet the SPEC | Layer 2 — acceptance criteria, end-to-end checks |
| Builder misunderstood the requirement and tested its misunderstanding | Layer 2 — fresh agent reads the SPEC, not the builder's log |

### What flow does not do

- It does not commit, branch, or push. Review the diff between runs and commit
  when you are happy.
- It does not replace CI. Verification runs locally, in the agent's sandbox,
  with whatever services are reachable there.
- It does not guarantee the acceptance criteria are the *right* criteria. That
  is what the planning interview is for — write criteria as external,
  observable checks, and the verifier will hold the code to them.

## State files

All state lives in a `.flow/` folder inside your project. Each feature gets its
own isolated folder, so working on one feature never disturbs another:

```
.flow/
  features/
    <feature-slug>/
      SPIKE.md                   investigation findings & decisions (/flow:spike, optional)
      SPEC.md                    goal, requirements, numbered acceptance criteria (/flow:plan)
      TASKS.md                   the checklist, with [ ] / [>] / [x] / [v] state
      CURRENT.md                 scratch context for the active task (clean between runs)
      VERIFY.md                  latest verification verdict (/flow:verify)
      archive/
        CURRENT-M1-1.md          permanent record of a completed task
        CURRENT-M1-2-failed-1.md a failed attempt, kept so retries can learn from it
        CURRENT-M1-2.md          the attempt that finally passed
        VERIFY-1.md              an earlier verdict, kept when a new one is written
```

- **SPEC.md** — the plan: goal, users, requirements, out of scope, acceptance
  criteria, definition of done. Written once during planning, then read-only.
  It is the stable source of intent and the contract the verifier checks.
- **TASKS.md** — the checklist of milestones and tasks, each with its
  `Verification:` line and the acceptance criteria it covers. The single
  source of truth for what is left to build.
- **CURRENT.md** — disposable scratch context for the one task being built
  right now. The orchestrator writes the task into it (plus links to any
  previous failed attempts); the sub-agent reads it and logs its work back.
  Archived and reset at the end of every run, pass or fail.
- **VERIFY.md** — the verification agent's verdict. Overwritten by each
  `/flow:verify` run; the previous one moves to `archive/`.
- **archive/** — one file per attempt. This is the durable history, and it is
  what the verifier reads to check what each task claimed.

## Why it is built this way

Sub-agents start with a clean context — they do not inherit the chat. So the
orchestrator writes the task context to that feature's CURRENT file, and the
sub-agent reads it. This keeps the orchestrator's context small and stops the
sub-agent from wandering outside the current task. The TASKS checklist is the
source of truth; CURRENT is disposable working memory; the archive is the
record.

Agents are spawned by their registered plugin type (`flow:implementation-agent`,
`flow:verification-agent`) rather than as `general-purpose`, so the tool
restrictions in their definitions are enforced by Claude Code, not merely
requested in a prompt. The verifier's read-only tool set is what makes "does
not fix code" a guarantee instead of an instruction.

Tests are required in the project's own framework because a test that lives
in the repo keeps protecting the behaviour after the agent is gone; a
throwaway script proves nothing once it is deleted. And the builder never
grades its own work because an agent that wrote the code tends to test the
code it wrote, not the behaviour you asked for.

## Install

```
/plugin marketplace add MaxGol/flow
/plugin install flow@flow-marketplace
/reload-plugins
```

## Usage

```
/flow:spike <slug>       investigate a vague problem, surface the decisions (optional)
/flow:plan <slug>        describe a feature (or answer the spike), approve the breakdown
/flow:implement <slug>   build the next task for that feature (run once per task)
/flow:verify <slug>      independently confirm the built feature meets the SPEC
```

## Credit

The architecture — a phased plan → implement pipeline where sub-agents
coordinate through shared markdown state — is inspired by
[Belmont](https://github.com/blake-simpson/belmont). `flow` is my own
Claude-only reimplementation, written from scratch to understand the pattern
and adapt it to my workflow. It is deliberately minimal: four commands and two
agents, with per-task archiving and an independent verification pass, versus
Belmont's larger multi-agent, multi-tool system.
