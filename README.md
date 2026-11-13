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
| `/flow:plan <slug>` | Interviews you, then writes the requirements, numbered acceptance criteria, the exact test commands, and the task checklist. | `SPEC.md`, `TASKS.md` |
| `/flow:implement <slug>` | Builds the next task via a sub-agent, which must also write and pass a real test. Run once per task. | code, a test, `archive/` |
| `/flow:verify <slug>` | Spawns a fresh read-only agent to re-run the suite, audit each task's test, and confirm every acceptance criterion. | `VERIFY.md` |

`/flow:implement` and `/flow:verify` refuse to run in plan mode: they stop
before touching any feature file and ask you to leave plan mode first.

## How it works, end to end

```
/flow:spike payments        ->  SPIKE.md: options + "Decisions you must make"
/flow:plan payments         ->  SPEC.md (AC1..ACn) + TASKS.md (M1-1, M1-2, ...)
/flow:implement payments    ->  M1-1 built + tested      [ ] -> [>] -> [x]
/flow:implement payments    ->  M1-2 built + tested      [ ] -> [>] -> [x]
...
/flow:verify payments       ->  PASS: [x] -> [v] for each task whose criteria all passed
                                      (a task covering an UNVERIFIED criterion stays [x])
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
| `[v]` | verified — an independent agent confirmed every acceptance criterion on this task's `covers:` line | `/flow:verify` only, per task |

`[>]` is set *before* the sub-agent runs. If the run crashes, the test fails, or
the task is blocked, it stays `[>]` and the next `/flow:implement` resumes it
first, with its previous failed attempts linked in the context so the agent
does not repeat the same mistake.

## Verification and testing

Quality is enforced in two layers. Each layer catches what the other cannot.

### Commands come from the SPEC

Neither agent works out how to run your tests on its own. Every SPEC carries a
`## Commands` section with the exact commands for the feature, each run from
the project root with no `cd`. For a project that uses vitest, for example:

```markdown
## Commands
Run from the project root.
- Test: `npx vitest run --reporter=dot`
- Single test: `npx vitest run --reporter=dot {file}`
- Type-check: `npx tsc --noEmit`
- Build: `npm run build`
```

`/flow:plan` works these out from your project config and shows them to you
with the task breakdown. Whatever your runner, it picks the runner's
non-watch, CI-mode command with its quietest reporter that still prints
failures and a summary, so a test run costs few tokens and a failure is still
readable. A watch-mode command is never chosen: it never exits. The implementation and verification agents run them
exactly as written — replacing `{file}` with a test file path is the only
edit allowed — one command per Bash call, with no `cd`, `;`, `&&`, pipes,
redirects or shell variables added. That keeps every Bash call a single,
traceable command (see [Running unattended](#running-unattended)).

If a SPEC has no `## Commands` block (for example one written before this
section existed), `/flow:implement` and `/flow:verify` add it themselves: they
read the project config, write the block into `SPEC.md` just before
`## Acceptance criteria`, and ask you to confirm the commands before changing
anything else. Answer "no" and the run stops so you can correct the block or
re-run `/flow:plan`.

### Layer 1: every task ships with a real test

**At planning time.** Every task in `TASKS.md` that produces code carries a
`Verification:` line — the behaviour a test must confirm, e.g. *"a non-numeric
input returns 400 with a JSON error body"*. Tests are an attribute of each
task, never a separate "write tests" task, and the planner does not ask
whether you want them. The SPEC also records the `## Commands` the agents will
use to run those tests.

**At build time.** The implementation agent (`agents/implementation-agent.md`)
is spawned as the registered `flow:implementation-agent` type with a restricted
tool set (Read, Write, Edit, Bash — no spawning agents, no web). It reads files
with Read, changes them only with Edit or Write, and uses Bash only for
single read-only searches (`grep -rn`, `ls`, `find`) and the SPEC's
`## Commands`. After writing the code it must:

1. **Use the SPEC's commands** — the `Test:` line names the project's runner.
   It finds the existing tests and matches their runner, folder, naming and
   style.
2. **Write a proper test** for the `Verification:` line, in that framework, in
   the conventional location. The test must assert the described behaviour.
   "Does not throw" and tautologies do not count. Throwaway "run it and print
   PASS" scripts are never acceptable.
3. **Run the task's test** with the SPEC's `Single test:` command, fixing the
   *code* and re-running the Single test until it passes. Every fix counts
   toward a cap of three attempts.
4. **Then run the full suite once** with the SPEC's `Test:` command, and
   `Type-check:` once (unless it is `none`), so a regression elsewhere is
   caught before the task is marked built. The suite is re-run only after a
   fix that follows a suite or type-check failure. If an existing test breaks,
   the agent fixes its own change, not the existing test. When `Single test:`
   is `none`, the `Test:` command takes its place in step 3 and no separate
   suite run follows.
5. **Never weaken a test to get green** — no deleting or loosening assertions,
   no skipping, no special-casing product code to satisfy the test. The only
   legitimate edit to a test is that it did not match the `Verification:`
   line, and the agent has to say so in its log.

The agent never improvises a command. If one it needs is missing from
`## Commands` — or the SPEC has no `## Commands` section or no `Test:` line —
it stops with `BLOCKED (missing command)`. If a command fails for an
environment reason (command not found, missing dependency, no network, wrong
runtime version), it stops with `BLOCKED (environment)`. It never installs
anything silently and never falls back to a script. `/flow:implement` reports
the missing command or the environment error; you fix it, then re-run.

**What the orchestrator checks.** `/flow:implement` does not take the agent's
word for it. A task is marked `[x]` only if the Implementation Log shows:

- status `done`,
- a `Test file:` path, and that file actually exists on disk,
- the task's test passed,
- the full suite passed, and
- the type-check passed (or the SPEC's `Type-check:` is `none`).

Anything else is a failed attempt: it is archived as
`archive/CURRENT-<task>-failed-<n>.md`, the task stays `[>]`, and the next
run retries it with the failed log in context.

### Layer 2: independent verification of the whole feature

Passing per-task tests proves each piece works as its builder understood it.
It does not prove the feature does what you asked for, and it does not catch
gaps between tasks. That is what `/flow:verify` is for.

**Separation of roles.** The builder never grades its own work. `/flow:verify`
spawns the registered `flow:verification-agent`, which has a fresh context and
a read-only tool set (Read, Bash — no Write, no Edit). Its tool rules also
forbid changing files through Bash, and limit Bash to read-only searches, the
SPEC's `## Commands`, and simple local checks such as `curl` against
localhost; it never runs `aws` or reaches a staging or production system. It
cannot fix code, cannot touch tests, and does not even write its own verdict
file; it returns the verdict as its final message and the orchestrator saves
it verbatim. A criterion is PASS only when the verifier confirmed it itself.
If the code contradicts it, it is FAIL. If it could not be exercised in this
environment (it needs `aws`, credentials, a staging system, or a service that
is not running), it is **UNVERIFIED** — never a pass — with the reason and
what would confirm it.

**What the verifier does.**

1. **Reads the contract**: the numbered `## Acceptance criteria` in `SPEC.md`,
   the `Verification:` line on each built task, and each task's archived
   Implementation Log (which test file it wrote, which commands it ran).
2. **Re-runs the full suite once** itself with the SPEC's `Test:` command (and
   `Type-check:` once, unless it is `none`) and records the exact commands and
   counts. It does not re-run the suite to look into a failure; it works from
   the output it has, or runs `Single test:` on one file. Green is necessary,
   not sufficient — it continues regardless.
3. **Audits each task's test**: the file exists, it calls the real code, and
   it asserts the behaviour the `Verification:` line promised. A missing,
   skipped, or hollow test fails the audit even if the product code looks
   right.
4. **Confirms each acceptance criterion independently**: finds the code,
   reads it, and where possible exercises it end to end (runs the flow, calls
   the function or endpoint, checks the observable result). It pays special
   attention to behaviour that no single task owned — the end-to-end paths
   where "every task passed" can still hide a gap. Each criterion is marked
   `[PASS]`, `[FAIL]` or `[UNVERIFIED]`.
5. **Returns a structured verdict**, saved as `VERIFY.md`:

```markdown
# Verification: Temperature converter

## Test run
- Command: npm test
- Type-check: npx tsc --noEmit
- Result: PASS — 14 passed, 0 failed

## Task tests
- [PASS] M1-1 — src/convert.test.ts — asserts c→f for 0, 100, -40 and NaN handling
- [FAIL] M1-2 — src/api.test.ts — only asserts status 200; never checks the body

## Acceptance criteria
- [PASS] AC1: GET /convert?c=100 returns {"f":212} — curl against dev server, body matched
- [FAIL] AC2: non-numeric input returns 400 with JSON error — returns 500 with HTML stack trace
- [UNVERIFIED] AC3: rates are cached in the shared Redis — no Redis reachable locally

## Unverified
- AC3: rates are cached in the shared Redis — why it could not be exercised: no Redis running locally — what would confirm it: run the flow against a local Redis and check the key is written

## End-to-end checks
- Started server, hit /convert with valid, missing and non-numeric params; see above.

## Verdict
FAIL
1. AC2 — src/api.ts — no input validation before parseFloat; non-numeric falls through to 500
2. M1-2 — src/api.test.ts — test does not assert the response body or the error case
```

**What happens next.**

- **PASS** (suite green, every task test passed its audit, and no criterion
  is `[FAIL]`): `[v]` is awarded per task. An `[x]` task becomes `[v]` only
  when every criterion on its `covers:` line is `[PASS]`. A task that covers
  an `[UNVERIFIED]` criterion stays `[x]` — built, but not independently
  verified — until a later `/flow:verify` run can confirm it. UNVERIFIED
  criteria never fail the verdict on their own and never become fix tasks.
  That is the only way a task reaches `[v]`.
- **FAIL**: nothing is fixed automatically. Each numbered failure becomes a
  new `[ ]` task under `## MV: Verification fixes` in `TASKS.md`, with its own
  `Verification:` line, so the fix goes through the same build-and-test path
  as any other task. UNVERIFIED criteria get no fix task, even when the
  verdict is FAIL for other reasons. Run `/flow:implement` to fix, then `/flow:verify` again.
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
      SPEC.md                    goal, requirements, commands, numbered acceptance criteria (/flow:plan)
      TASKS.md                   the checklist, with [ ] / [>] / [x] / [v] state
      CURRENT.md                 scratch context for the active task (clean between runs)
      VERIFY.md                  latest verification verdict (/flow:verify)
      archive/
        CURRENT-M1-1.md          permanent record of a completed task
        CURRENT-M1-2-failed-1.md a failed attempt, kept so retries can learn from it
        CURRENT-M1-2.md          the attempt that finally passed
        VERIFY-1.md              an earlier verdict, kept when a new one is written
```

- **SPEC.md** — the plan: goal, users, requirements, out of scope, the
  `## Commands` the agents run, acceptance criteria, definition of done.
  Written once during planning, then read-only — the one exception is that
  `/flow:implement` or `/flow:verify` adds a missing `## Commands` block, after
  you confirm it. It is the stable source of intent and the contract the
  verifier checks.
- **TASKS.md** — the checklist of milestones and tasks, each with its
  `Verification:` line and the acceptance criteria it covers. The single
  source of truth for what is left to build.
- **CURRENT.md** — disposable scratch context for the one task being built
  right now. The orchestrator copies only this task's description into it,
  with its `Verification:` and `covers:` lines verbatim, plus links to any
  previous failed attempts. Where the task depends on earlier tasks or the
  SPEC, it adds a short summary of the facts the agent needs (at most 5
  lines) and an optional "Full notes: <path>" line, instead of telling the
  agent to read whole archive files or the whole SPEC. The sub-agent reads it
  and logs its work back.
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

## Running unattended

flow's prompt files keep every tool call to something Claude Code can approve
without asking: reads with Read, edits with Edit or Write, and Bash only for
single read-only searches and the SPEC's `## Commands`, one command per call.
Some settings that decide whether a run is interrupted by prompts can only be
set by you, not by a plugin. Put them in your user settings,
`~/.claude/settings.json`:

```json
{
  "permissions": {
    "defaultMode": "auto",
    "blockReadsOutsideWorkingDirectories": true,
    "ask": [
      "Bash(git push *)",
      "Bash(aws *)",
      "Bash(rm -rf *)"
    ],
    "deny": [
      "Bash(aws * --profile prod*)",
      "Bash(aws * --profile=prod*)"
    ]
  },
  "env": {
    "CLAUDE_CODE_FORK_SUBAGENT": "0"
  }
}
```

Replace `prod*` with the names of your production AWS profiles.

**Keep `permissions.blockReadsOutsideWorkingDirectories` on.** It stops
commands reading files outside your working directories. Under it, a Bash
command the shell parser can't trace — such as one that changes directory more
than once or runs a subshell — prompts you even in auto mode and
`bypassPermissions` mode, even when it names no path outside the working
directories (the prompt does not apply when the command runs in a sandbox that
enforces the block). A `true` in any settings file applies, and a repository
can't lift it. That is why flow's agents never chain commands: an
investigation of earlier runs counted 425 manual approvals across four
sessions, almost all Bash — `cat`/`sed`/`grep` chains, interpreter heredoc
edits, and `cd`-prefixed compound commands. Even
`cd <project-root> && <test command> 2>&1 | tail -5` prompted, while the same
command without the `cd` did not. Leave the setting on and let the agents
follow their tool rules, rather than turning it off to silence the prompts.

**Set `"permissions": {"defaultMode": "auto"}` in `~/.claude/settings.json`.**
Auto mode approves routine actions without asking. `auto` (like
`bypassPermissions`) has no effect when set in project or local settings
(`.claude/settings.json`, `.claude/settings.local.json`), so it has to go in
your user settings. On entering auto mode, Claude Code drops broad allow
rules that grant arbitrary code execution: blanket `Bash(*)`, wildcarded
interpreters such as `Bash(python*)`, package-manager run commands, and
`Agent` allow rules. Don't rely on rules like those; explicit ask and deny
rules still apply.

**Set `"env": {"CLAUDE_CODE_FORK_SUBAGENT": "0"}`, then restart Claude Code.**
`/flow:implement` and `/flow:verify` spawn their agent with
`run_in_background: false`, so the run waits for the agent and checks its
evidence in the same turn. Fork mode is on by default, and while it is on,
Claude can't wait for a sub-agent in interactive terminal, VS Code or desktop
sessions, so the agent runs in the background instead. Setting
`CLAUDE_CODE_FORK_SUBAGENT` to `0` turns fork mode off, so
`run_in_background: false` is honoured. See the
[environment variables reference](https://code.claude.com/docs/en/env-vars)
and [Let Claude wait for a subagent](https://code.claude.com/docs/en/sub-agents#let-claude-wait-for-a-subagent)
in the sub-agents docs.

**Add ask rules for commands you always want to see.** Explicit ask rules
still force a prompt in auto mode. The recommended set is `Bash(git push *)`,
`Bash(aws *)` and `Bash(rm -rf *)`. Bash rules match the command text, so they
are easy to slip past: `Bash(rm -rf *)` does not match variants such as
`rm -fr`, `rm -r -f` or `rm --recursive --force`. A rule does match past a
leading environment-variable assignment, so `AWS_PROFILE=prod aws s3 ls`
still hits `Bash(aws *)`.

**Add deny rules for production AWS profiles**, as in the example above. Deny
beats ask, which beats allow, so a denied command is refused even though
`Bash(aws *)` asks. Pattern rules are not a security boundary: rules that try
to constrain arguments are fragile, and `AWS_PROFILE=prod aws ...` or a
profile name you didn't list slips past the deny rules (the `Bash(aws *)` ask
rule still catches it). Keep production credentials out of reach of the
machine where you run agents if you need a real guarantee.

**Network access needs the sandbox.** Permission rules can't restrict which
hosts a shell command reaches; per-host network prompting needs Claude Code's
[sandbox](https://code.claude.com/docs/en/sandboxing), which flow does not
set up. You can add `Bash(curl *)` and `Bash(wget *)` ask rules, but they also
prompt for the verification agent's `curl` checks against localhost.

**Count the prompts you still get.** `scripts/count_approvals.py` (in a clone
of this repository) reads a session transcript and counts the permission
prompts you answered during `/flow:implement` runs — the main session plus the
sub-agents those runs started, not counting AskUserQuestion. Session
transcripts live under `~/.claude/projects/<project folder>/`:

```
python3 scripts/count_approvals.py ~/.claude/projects/<project folder>/<session id>.jsonl
python3 scripts/count_approvals.py <session.jsonl> --command flow:verify
```

It prints one line per approval and `approvals: N` last. The exit code is 0
when there were none, 1 when there were some, and 2 for a missing or
unreadable transcript or no run of the requested command.

## Credit

The architecture — a phased plan → implement pipeline where sub-agents
coordinate through shared markdown state — is inspired by
[Belmont](https://github.com/blake-simpson/belmont). `flow` is my own
Claude-only reimplementation, written from scratch to understand the pattern
and adapt it to my workflow. It is deliberately minimal: four commands and two
agents, with per-task archiving and an independent verification pass, versus
Belmont's larger multi-agent, multi-tool system.
