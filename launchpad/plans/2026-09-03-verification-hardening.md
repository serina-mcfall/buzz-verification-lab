# Verification hardening — legible gates, flake defence aimed where flakes live, reward-hacking guardrails, trivia auto-fixed

Stated size: Deep Plan  →  cap: 15 steps

Grounding: `~/research/test-automation-for-agentic-coding.md` (2026-09-03, claims
verified against primaries). Revision 3 — incorporates both review-plan passes
of 2026-09-03 (10 findings pass 1; 2 blockers + 3 findings pass 2) plus external
feedback relayed 2026-09-03, which closed the two tool-verification unknowns in
steps 3, 6 and 10. Full review log — including what each review changed and the
still-open items — lives in the companion programme document's "Review record".

STATUS: SUPERSEDED 2026-09-03 by the reworked phases in the companion programme
document. DO NOT BUILD FROM THIS PLAN. It is kept as history — the record of what
was proposed before the Codex review, and of what that review changed.

Why it was superseded, in one line each:
  - Circular ordering: step 7 [needs 6], but 6 sat in a charter-blocked phase
    while 7 sat in an unblocked one, so the phase plan could not execute.
  - Wrong surface: mutation and flake defence aimed at upstream Rust and
    Desktop code the cohort does not author, while cohort-owned Python, shell
    and workflows got no verification at all.
  - Three steps prescribed mechanisms that already existed (see INC-0005).
  - Several mechanisms could not work as specified: the fixed nextest JUnit
    path collides across many invocations; the human-approval check runs on the
    wrong event; core.hooksPath would disable this repo's lefthook.

See the programme document's "What happened to the old 13-step plan" for where
each step went. Design goals, in the requester's words: test
automation, CI and verification working seamlessly and efficiently; breaks stop;
gates surface real bugs, not trivia — trivia gets fixed on the spot by the agent
that finds it. "Foolproof" is explicitly NOT claimed: every layer here can miss;
the design is layers with uncorrelated blind spots plus legible failures.

ALREADY TRUE  (verified against git, gh API and gh run list, 2026-09-03; corrected
              after review findings)
  Meta-checks are the dominant failure source: "launchpad — PR body check" failed
    9/25 recent runs, "launchpad — issue body check" 5/7 (26/28 on the launchpad
    branch). PR #126 (fix/pr-body-check-code-spans) merged 2026-08-12; no open PR
    or live worktree currently touches pr_body_check.py, launchpad-pr-check.yml,
    or launchpad/review-agent/** (all 50 open PRs' changed files checked).
  Code CI (`ci.yml`) failed 4/100 recent runs — all four were docs(corpus) PRs
    failing "Desktop Smoke E2E" / "Desktop" jobs. Docs-only changes failing
    browser tests is a flake signature: the live flake problem is in the Desktop
    Playwright E2E suite (162 .spec.ts files under desktop/tests), not Rust.
  cargo-nextest 0.9.136 pinned in ci.yml; NO .config/nextest.toml, no --retries
    anywhere. Several ci.yml nextest lanes run serialized (--test-threads=1)
    against one shared live Postgres, with comments stating tests mutate global
    roster state — blanket retries there could mask real concurrency bugs.
  No mutation testing exists.
  .github/CODEOWNERS EXISTS (`* @block/buzz-oss-team`) but its ONLY owner is
    invalid on this fork: `gh api repos/launchpad-26/buzz/codeowners/errors`
    reports "Unknown owner" (no teams have access to the fork — collaborators
    are individual users). There is NO branch protection, NO ruleset, and NO
    required_status_checks on the fork's `launchpad` branch (rulesets → [],
    protection → 404) — today, NOTHING can block a merge, so every gate this
    plan builds is advisory until step 7 lands. (Org-level rulesets could not
    be checked — needs admin:org scope; verify during step 7.)
  ACCESS BLOCKER, verified 2026-09-03: `launchpad-26/buzz` is an ORG-owned fork
    of block/buzz. Serina has `maintain: true, admin: false` and org role
    `member`. GitHub's role table gives "Manage branch protection rules and
    repository rulesets" to Admin ONLY — Maintain is explicitly ✗. So step 7(a)
    CANNOT be done by her; it needs whoever holds admin. Jeff (`tucktuck101`)
    is the named person to establish whether the cohort has admin at all.
    If the answer is no, see the programme doc's "Contingency — if (h) is
    no admin": enforcement moves to lefthook pre-push plus legibility, and
    "red must block" becomes "red must be impossible to miss".
  launchpad/AGENT_PR_TEMPLATE.md already has a "### Verification" section
    (Command run + Raw output fences); pr_body_check.py already requires a fenced
    block — but any fence anywhere satisfies it, including an empty one. The
    template forbids adding headings not already in it.
  launchpad-review-agent-controls.yml has no reusable "control flag" mechanism
    (REVIEW_AGENT_ALLOW_MUTATION is an unrelated CLI env var) — path-flagging
    must be built, not reused.
  crates/ test styles: #[test] (241 files), #[tokio::test] (124), mod tests
    blocks (250), proptest! (1 file). desktop/tests: Playwright test() specs.
  Trivia auto-fix ALREADY EXISTS and works: lefthook.yml pre-commit lanes run
    `just fmt` (cargo fmt), desktop/web `biome check --write`, mobile dart
    format — every lane with `stage_fixed: true`. Formatting cannot reject a
    commit today. What does NOT exist is the severity-floor policy (trivia
    fixed inline by agents, never reported as findings).
  desktop/playwright.config.ts already sets `retries: process.env.CI ? 2 : 0`
    and `trace: "on-first-retry"`; reporters are `list` + `html` only — no
    JUnit, no CI-visible flaky-status surfacing, no quarantine wiring.
  Default branch `launchpad`. This plan file is untracked; commit it on its own
    branch off `launchpad`, not on fix/1996.

STEP 1  Triage the failing gates, both kinds.  [independent]
        (a) Meta-checks: fetch logs for the last ~25 failing PR/issue body check
        runs; classify checker-bug / agent non-conformance / template gap /
        nagging-by-design; save failing bodies as a replay corpus under
        launchpad/scripts/testdata/. (b) Desktop E2E: pull the four failing
        docs(corpus) CI runs' Playwright output; identify which specs failed and
        whether the failures correlate with the diff (they should not, for docs
        PRs) — that spec list seeds the flake corpus for step 5. Check open PRs
        for overlap before starting (verified none as of 2026-09-03).
        Write both tables to launchpad/docs/verification-failure-triage-2026-09.md.
        done when: every fetched failing run appears in a table with a class and
        a one-line cause; meta-check corpus replays against the current checker
        reproducing each failure; the flaky Desktop spec names are listed.

STEP 2  Fix the dominant meta-check failure class from step 1.  [needs 1]
        Checker-bug → patch pr_body_check.py (or issue checker) with a unit test
        per corpus case; template gap → amend AGENT_PR_TEMPLATE.md and the agent
        guidance feeding it. Every failure message must name the violated rule
        and show a conforming example — agents iterating blind against vague
        failures is where retry-spam starts. If step 1 classifies the issue body
        check as nagging-by-design, convert it to a non-required check or
        comment bot (a gate that is usually red trains everyone to ignore red).
        done when: the checker run locally against the step-1 corpus passes every
        body that should pass and fails only true non-conformances, each failure
        naming its rule.

STEP 3  Add .config/nextest.toml with SCOPED retry profiles.  [independent]  ← RUNS HERE
        VERIFIED 2026-09-03 against nexte.st docs + GitHub releases: pinned
        0.9.136 (released 2026-05-17) supports everything this step needs —
        `[profile.ci] retries = 2 / fail-fast = false`; per-test overrides
        `[[profile.ci.overrides]] filter = '...' retries = 0`; JUnit via
        `[profile.ci.junit] path = "junit.xml"` written to
        target/nextest/ci/junit.xml; flaky runs emit `<flakyFailure>` elements
        (distinct from failures) and `flaky-fail-status` exists since 0.9.131.
        No pin bump needed. (`report-skipped` needs 0.9.143 — see step 6.)
        Override retries = 0 for EVERY lane that touches the shared live
        Postgres — enumerate from ci.yml by DB/compose usage, NOT by
        --test-threads=1 alone: the serialized roster lane, "Replaceable
        persistence PostgreSQL tests" (concurrent_parameterized_*), "Invite
        security tests", "NIP-MP coordinate deletion guard", and any other lane
        whose job starts docker compose. Retrying stateful lanes can hide real
        state-pollution bugs. Add a deliberately
        flaky fixture test (gated out of normal runs) to prove reporting.
        done when: `cargo nextest run --profile ci` locally reports the fixture
        as FLAKY (not silently green), the JUnit file carries retry metadata,
        and a test in a serialized lane shows retries = 0 under the same profile.

STEP 4  Wire ci.yml to the scoped profiles; publish machine-readable results.  [needs 3]
        `--profile ci` on parallel lanes, the zero-retry override covering the
        serialized lanes; upload JUnit XML artifacts; print a flaky-test summary
        to GITHUB_STEP_SUMMARY (empty list is valid output, absence of the
        section is a job failure — no fail-open).
        done when: a CI run on a test PR shows the artifact and summary section;
        a forced-flaky test appears as flaky, not passed; deleting the summary
        step makes the job fail, not silently pass.

STEP 5  Desktop E2E flake defence — where the real flakes are.  [independent]
        Retries (CI ? 2 : 0) and trace-on-first-retry ALREADY EXIST in
        desktop/playwright.config.ts — do not rebuild them. The missing delta:
        add a JUnit reporter, surface Playwright's native "flaky" status in the
        CI job summary (never folded into "passed"), upload trace artifacts on
        retry. Quarantine via a human-owned annotations list
        (step 6's file) mapped to `grep-invert` or per-spec `test.fixme` with a
        required issue link. Use step 1(b)'s spec list as the first entries if
        the flakes reproduce.
        done when: a forced-flaky spec reports status "flaky" with a trace
        artifact attached in CI, and a quarantined spec is excluded from the
        gating job while still running in a non-required job.

STEP 6  One human-owned quarantine list feeding both runners.  [needs 4, 5]
        launchpad/quarantine.toml: entries carry test id, runner (nextest |
        playwright), issue number, date. A small script (with its own unit
        tests) generates the nextest filterset override and the Playwright
        exclusion from it — first verifying from the docs of the pinned nextest
        version HOW an external exclusion is expressed. VERIFIED 2026-09-03:
        nextest has NO native external-file exclusion — use a generated
        filterset (`default-filter` exists since 0.9.84, or an overrides
        `filter`), so the generator script is required, not optional. NOTE:
        `report-skipped` (making quarantined tests visible in the JUnit report)
        needs 0.9.143+; the pin is 0.9.136, so either bump the pin or accept
        that quarantined tests are invisible in JUnit — decide in this step. A lint step fails any entry without an issue number.
        Quarantined tests run in a separate non-required job so they keep
        producing signal without blocking merges.
        done when: adding an entry removes the test from the gating job and runs
        it in the non-gating job for its runner; an entry without an issue
        number fails the lint; removing the entry restores gating.

STEP 7  Make ANY gate able to block a merge — nothing can today.  [needs 6]
        (a) Enable a ruleset on `launchpad` with required PRs, required status
        checks (name them explicitly: the CI test jobs, PR body check, the
        step-8 test-mod guard once it exists), and require_code_owner_review.
        First check org-level rulesets with adequate scope (unverifiable at
        plan time). (b) FIX .github/CODEOWNERS before extending it: the sole
        owner `@block/buzz-oss-team` is "Unknown owner" on this fork (verified
        via the codeowners/errors API), so every entry is inert — replace with
        valid fork owners (individual users with write access; WHO is an OPEN
        decision for the cohort), then append specific patterns after the `*`
        line for: launchpad/quarantine.toml, .config/nextest.toml, lefthook.yml,
        .github/workflows/**, the desktop Playwright config. (c) Build (from
        scratch — no precedent exists) a small required check that comments and
        fails when a by:agent PR touches those paths without a human approval
        present. Scope (c) to fail-closed: missing path data = failure, not pass.
        done when: `gh api repos/launchpad-26/buzz/codeowners/errors` returns
        zero errors; on a test PR from an agent touching quarantine.toml, merge
        is blocked pending code-owner review and the required checks; a PR not
        touching governed paths is unaffected.

STEP 8  Test-modification guard, wide enough to matter.  [needs 2]
        New job in the PR-check workflow, diff-based and deterministic (no LLM):
        fail when the diff (a) deletes a Rust test fn — detect #[test],
        #[tokio::test], #[rstest], proptest! blocks — (b) deletes any test file
        (crates/**/tests/**, *_test.rs, desktop/tests/**/*.spec.ts), or
        (c) reduces assertion count in a modified test — unless the PR body
        carries `test-change: <reason>`. Known limit, stated in the check's own
        output: assertion WEAKENING with unchanged count is not statically
        detectable — that is what the mutation layer (step 10) exists to catch.
        done when: fixture diffs — Rust test deletion, proptest! deletion, and
        .spec.ts deletion — each fail without the declaration and pass with it;
        a diff only adding tests passes with no declaration.

STEP 9  Tighten the EXISTING evidence check — do not add a parallel one.  [needs 8]
        AGENT_PR_TEMPLATE.md already requires Command run + Raw output; the
        current pr_body_check.py accepts any fenced block anywhere, including an
        empty one. Tighten it: the fences must sit under "### Verification", the
        command fence must name a real just/cargo/pnpm target (validate against
        Justfile/package.json/workspace members), the output fence must be
        non-empty and contain a recognizable summary line (nextest/playwright/
        pytest-style pass counts). No new template headings (template forbids
        them).
        done when: corpus tests show an empty-fence body failing, a body with a
        fake command name failing, and a genuine command+summary body passing.

STEP 10 Diff-scoped mutation job, advisory first.  [independent]
        VERIFIED 2026-09-03 (mutants.rs/in-diff.html): `--in-diff DIFF_FILE`
        takes a FILE PATH; the diff needs a `b/` new-filename prefix (what
        `git diff` produces) or none; non-Rust files are ignored; it composes
        on top of --package/--regex filters. CRITICAL CAVEAT: "The diff is only
        matched against the code under test, not the test code" — so a PR that
        only adds or changes tests produces NO mutants, and this job can never
        be the sole test-quality signal for test-only PRs. Docs also warn edits
        in one region can leave code elsewhere untested, which --in-diff misses.
        Then: non-required workflow on PRs touching crates/**,
        `cargo mutants --in-diff` against the merge-base diff, survivors posted
        to GITHUB_STEP_SUMMARY, time-boxed (--timeout + timeout-minutes 20),
        skipped when no Rust source changed.
        done when: a sample PR shows a surviving/killed summary inside the
        time-box on a typical one-crate diff.

STEP 11 Mutation baseline and promotion ADR.  [needs 10]
        Run the step-10 job against ~10 recently merged PRs; record survivors,
        noise and wall-clock into an ADR draft in launchpad/decisions/
        recommending gate / advisory / label-triggered, with thresholds.
        done when: the ADR draft contains the per-PR table and a recommendation.

STEP 12 Trivia is fixed, not reported — severity-floor policy ONLY.  [independent]
        Formatting auto-fix already fully exists (lefthook stage_fixed lanes —
        see ALREADY TRUE; do NOT rebuild it, the pass-2 review caught revision 2
        planning exactly that). What is missing is the POLICY: add a severity
        floor to launchpad/AGENTS.md and the review-agent guidance — findings an
        implementing agent can fix in-place without changing behaviour or scope
        (typos, dead imports, obvious lint, doc slips) are fixed in the same PR
        under a "fixed en route" note, never raised as gate failures or review
        findings. Gates fail only for behavioural, security, or verification-
        integrity defects. Reference the existing lefthook lanes by name as the
        mechanical layer of this policy.
        done when: the policy section exists naming at least three fix-inline
        classes and at least three must-report classes with one example each,
        the review-agent guidance references it, and it names the existing
        lefthook auto-fix lanes rather than proposing new ones.

STEP 13 Write the ladder where agents read it.  [needs 6, 8, 9, 12]
        TESTING.md + launchpad/AGENTS.md gain a verification-ladder section
        mapping every check to its loop (inner loop: fmt/lint/affected tests;
        merge gate: full nextest + Desktop E2E + body checks + test-mod guard;
        advisory: mutation; post-merge: canaries) with each mechanism's file
        path, plus the flake policy: agents never add retries/sleeps/timeout
        bumps to make a failing test pass — flakes go to the human-owned
        quarantine with an issue. State plainly that no single layer is
        foolproof and which layer covers which blind spot.
        done when: the sections exist, name each mechanism's path, and
        pr_body_check.py's failure messages link to them.

PARALLEL  Steps 1, 3, 5, 10 and 12 are mutually independent (different files:
          triage docs vs nextest.toml vs Playwright config vs mutants workflow
          vs lefthook.yml) and can run as parallel subagents. Steps 2→8→9 are
          strictly sequential — all edit pr_body_check.py and/or the PR-check
          workflow. 4 follows 3 (ci.yml); 6 follows 4 and 5 (consumes both
          runners' wiring); 7 follows 6 (protects the files 6 creates); 11
          follows 10; 13 documents what 6/8/9/12 built. Before dispatching,
          re-check open PRs for new overlap — the 2026-09-03 check found none,
          but two other sessions were active in this repo that day.

GATES     review-plan re-review on this revision before building (revision 2
          responds to the first review's findings — confirm they are closed).
          review-code after steps 2, 8, 9 (checker logic), 4-7 (CI/workflow
          changes) and 12 (hook changes). review-tests after 2, 3, 8, 9 — the
          corpus replay tests are load-bearing. review-final on the branch
          before merge. qa explore mode APPLIES: checkers and the nextest
          profile run locally — exercise with hostile inputs (malformed bodies,
          empty fences, unicode, huge diffs, fake command names).

BUDGET    Step 10 (cargo-mutants time-box tuning on a big workspace; fallback:
          label-triggered advisory, decided in step 11's ADR). Second risk:
          step 7(a) — enabling a ruleset on a busy fork branch mid-fleet can
          block in-flight agent PRs; schedule it, announce it, and have the
          rollback (disable ruleset) ready.

OPEN      (a) Which meta-check failure class dominates — step 1 decides step 2's
          shape; if issue body check is nagging-by-design it stops being a
          required check. (b) Mutation promotion threshold — step 11's ADR.
          (c) Harness-level read-only-tests enforcement (Claude Code hooks in
          buzz-infrastructure) as a second layer under step 8 — CI-level chosen
          first because it catches every agent regardless of harness. (d) web/
          still has no unit test runner; its verification rests on typecheck +
          E2E only — separate change. (e) Whether Desktop E2E belongs in the
          merge gate at all for docs-only diffs (path-filtering it out would
          have prevented all four observed breaks) — cheap, worth deciding
          during step 5. (f) FORK CHARTER, decide before building steps 3-5:
          this fork's own guide says "We operate Buzz; we do not develop it" —
          cohort work lives under launchpad/ and .github/workflows/launchpad-*.
          Steps 3, 4 and 5 modify UPSTREAM files (ci.yml, .config/nextest.toml,
          desktop/playwright.config.ts), which diverges the fork from
          block/buzz and will conflict on upstream syncs. Options: contribute
          the changes upstream, carry them as conscious documented fork
          divergence, or restrict this plan to launchpad-* surfaces and accept
          weaker flake defence. Cohort decision — not the builder's.
          (g) WHO the valid CODEOWNERS owners are on the fork (individual
          users; the existing team owner is invalid) — cohort decision.

LEFT OUT  review-agent adjudication internals — no live overlap found, but the
          review-agent stream owns that surface; this plan only adds the path
          guard (step 7c). JS unit-test framework adoption for web/ (OPEN d).
          Any change to `just test` local flow beyond the nextest profile.
          "Foolproof" as a goal — explicitly replaced by layered defence with
          stated blind spots (step 8 names what it cannot catch; step 10 covers
          it; step 13 writes the map). Plan lives in launchpad/plans/ (repo
          convention) rather than docs/plans/ (skill default) — deliberate.
