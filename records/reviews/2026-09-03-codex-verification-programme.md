# REV-0001 — Codex adversarial review of the verification programme

**Date** 2026-09-03 · **Reviewer** Codex CLI 0.147.0 · **Subject** the verification programme and
hardening plan · **Verdict** rethink, not patch

Fourth review pass. The first two were `review-plan` (Claude), the third external feedback relayed
via Ben. This one was given the seven closed findings up front and told not to repeat them, so
everything below is new ground.

## Blockers

1. **The phase graph cannot execute.** `STEP 7 [needs 6]`, but step 6 sits in Phase 4
   (charter-blocked) while step 7 sits in Phase 2 (advertised as unblocked). Phase 2 therefore
   cannot complete before Phase 4. **Verified.** A second forward dependency: step 7 requires the
   step-8 guard "once it exists", but step 8 follows step 7.

2. **The individual enforcement layer was overclaimed.** The programme said Claude hooks are
   bypassable by "nothing the agent controls" and fully cover three of four threats. They do not
   govern Codex, other harnesses, IDEs, browser edits, the ACP harness, or humans; a Bash-pattern
   matcher can be walked around (this repo's own `verify-gate.sh` records a `git -C` bypass); a Stop
   hook does not retract files already written. Sharpest point: `launchpad-pr-check.yml` states
   plainly that PR-owned checking code is not a security boundary — the programme applied the
   opposite reasoning to local hooks. **Accepted with qualification:** the layer is real accident
   prevention within one harness, but it is ergonomics, not an integrity control, and must be
   described that way.

3. **The programme aims at the wrong surface.** Mutation on `crates/**`, nextest and Playwright
   config are upstream *product* code the fork explicitly does not develop. Cohort-owned work —
   Python checkers, shell, workflows, docs under `launchpad/` — receives no verification signal.
   The expensive parts buy the least. **Accepted.**

## High findings worth carrying forward

- **Test-modification guard covers a fraction of the suites.** Counted: ~610 Desktop `.test.mjs`,
  156 Flutter `_test.dart`, 100 Tauri Rust, 12 Python test files under `launchpad/scripts/` —
  including `test_pr_body_check.py`, the tests for the very checker the plan modifies. None matched
  the guard's stated patterns. **Verified.**
- **Playwright flaky machinery already exists and is fail-open.** Recorded separately as INC-0001.
- **"Fail closed" is contradicted by checks the plan would make required.** `pr_body_check.py`
  deliberately degrades to text search when the GitHub API is unavailable, so a required gate could
  pass while saying it did not verify.
- **nextest JUnit path collides.** One configured path, but `ci.yml` invokes `cargo nextest run`
  many times; later runs overwrite earlier reports. The artifact would show a fraction of the run
  as though it were the whole run.
- **The advertised inner loop uses tools this repo lacks.** `--lf` is last-failed, not
  affected-tests; Desktop uses Node's built-in runner, so `--findRelatedTests` does not exist;
  Flutter has no affected-test mechanism at all.
- **`core.hooksPath` would disable the repo hook layer.** Git honours one hooks directory; setting
  it globally redirects away from `.git/hooks` where lefthook installs, removing DCO, formatting and
  pre-push checks. No chaining was specified.
- **`retries = 2` with exclusions is default-on retries, not scoped retries.** New stateful or
  timing-sensitive tests would silently inherit retries. Default should be 0 with opt-in.
- **The human-approval check has no event lifecycle.** The PR workflow runs on `pull_request`, not
  `pull_request_review`, so an approval would not re-trigger it.

## Medium

- **The planning artifacts violate the fork's process contract.** `launchpad/AGENTS.md`: *"No
  `PLANNED.md`, no roadmap files. Those are issues."* Both documents are exactly that.
  **Verified.**
- Phase 0 says "three decisions" and lists four.
- The evidence validator would reject legitimate commands (`flutter analyze`, `dart test`, shell
  contract scripts) while accepting a fabricated pass count. It is a formatting validator.

## Assessment

Accepted. The research foundation and the portable skill suite survive; the Buzz application needs
re-aiming at cohort surfaces and re-expressing as issues rather than roadmap files.

Three of four review passes have now caught planning that prescribed already-existing
infrastructure — recorded as a recurring pattern in the `serina-skills` record, INC-0005.
