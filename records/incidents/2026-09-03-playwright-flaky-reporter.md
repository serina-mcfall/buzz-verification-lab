# INC-0001 — Playwright flaky-test summarizer has never had input

**Found** 2026-09-03 · **Detected by** agent (Codex adversarial review) · **Severity** medium
**Status** OPEN · **Triggers** monitoring-failure, silent-drift

## What is wrong

`desktop/scripts/summarize-flaky-tests.mjs` reads a Playwright JSON report and writes every
`status === "flaky"` test to the GitHub Actions job summary. Its own header says why it exists:
flaky tests "pass on retry with no durable signal beyond a one-line 'N flaky'".

`desktop/playwright.config.ts` declares only two reporters:

```ts
reporter: [
  ["list"],
  ["html", { open: "never", outputFolder: "playwright-report" }],
],
```

No JSON reporter. The report the summarizer needs is never produced, so it takes its
missing-file branch and exits 0 with "Skipping". CI has been reporting success for a step that
has never once done its job.

## Why it matters more than its severity suggests

This is a **monitoring failure**, not a test failure. The mechanism intended to make flaky tests
visible has been invisible itself. Meanwhile the only real `ci.yml` failures in the last 100 runs
— four of them — were Desktop E2E flakes on documentation-only PRs (see INC-0004), exactly the
signal this summarizer exists to surface.

It also fails open in the classic shape: absent input read as nothing-to-report rather than as
"I could not check".

## Evidence

- `desktop/scripts/summarize-flaky-tests.mjs` — file dated 2026-08-07; reads `<report.json>`,
  filters `status === "flaky"`, "Skipping" branch on missing file
- `desktop/playwright.config.ts` — reporter array contains `list` and `html` only
- `.github/workflows/ci.yml` — uploads `playwright-report`, `playwright-report.json` and
  `test-results` for smoke and integration shards; the JSON artifact has no producer

## Fix

1. Add a `json` reporter to `playwright.config.ts` writing to the path CI already uploads.
2. Make the summarizer distinguish **"no flaky tests"** from **"no report found"**. Absent input
   must report that it could not check, not pass silently.
3. Confirm with a deliberately flaky spec that the summary actually renders.

Steps 1 and 3 are the fix; step 2 is the thing that stops it recurring.

## Open question — ANSWERED 2026-09-04

> How long has this been silent? The summarizer file dates from 2026-08-07, but when it was wired
> into CI is unverified. Method: `git log --follow` on both files and compare first-appearance dates.

**Since 2026-07-13.** `git log --follow` puts the summarizer's first appearance and its wiring into
`ci.yml` in the *same* commit — `a653406309`, *"ci(desktop): surface flaky E2E tests instead of
retry-masking them (#1838)"*. The 2026-08-07 file date was a later touch, not its origin.

`git log -S'"json"' -- desktop/playwright.config.ts` returns **nothing on any branch**, including
`upstream/main`. The reporter was never there. So the step has been inert from the commit that
introduced it: **53 days**, and it was never once correct.

---

## Resolution — 2026-09-04

Fixed on `fix/playwright-json-reporter`. **Not pushed, no PR, and nothing sent upstream** — Serina
ruled that explicitly.

| Commit | What |
|---|---|
| `140f7beaa` | one line: `["json", { outputFile: "playwright-report.json" }]` |
| `b0b0704a9` | `launchpad/scripts/flaky_report_wiring.py` + 14 controls + `launchpad-flaky-report-wiring.yml` |

### Step 1 — done, and proven by running it

A real `pnpm build:e2e` plus `playwright test --project=smoke tests/e2e/navigation.spec.ts` gave
**19 passed / 1 skipped** and wrote a 31,437-byte `desktop/playwright-report.json` carrying
`stats {expected: 19, unexpected: 0, flaky: 0, skipped: 1}`. Upstream's summarizer consumed it and
exited 0 silently — correct for a run with no flakes.

**A fourth reference nobody had noticed:** `desktop/.gitignore:15` has ignored
`playwright-report.json` since before this fix. Four things named the file; none produced it.

### Step 3 — done, by fixture rather than by a flaky spec

Against a synthetic report containing two flaky tests the summarizer rendered the table correctly,
walked a nested `describe`, and escaped a `|` in a title. **A deliberately flaky spec was NOT run** —
that needs a new file in `desktop/tests/e2e/`, which is upstream and out of bounds. Recorded as a
gap rather than claimed.

### Step 2 — NOT done, and it is the one that stops recurrence

The summarizer still cannot tell "clean" from "never checked":

| Input | Output | Exit |
|---|---|---|
| Real report, no flakes | *(nothing)* | `0` |
| No report at all | `Skipping flaky-test summary: ENOENT…` | `0` |

Same exit code; the only difference is a log line. The same shape appears five lines below in
`ci.yml` as `if-no-files-found: ignore`. Both remain open, and both live in upstream files.

### What guards it now

`flaky_report_wiring.py` does not grep for the reporter — a checker asserting "a json reporter
exists" would pass the moment someone re-added one writing to a path nobody reads. It compares the
**three references to each other**: what the config writes, what each `ci.yml` step passes to the
summarizer (resolved through that step's `working-directory`), and what the artifact upload
publishes. Three exit codes: `0` wired, `1` disagreement, `3` could-not-check.

Proven against the real defect, not a fixture: run against `origin/launchpad` it exits **1** and
reports *"these already expect it: desktop/playwright-report.json (invoked at
.github/workflows/ci.yml:292,566)"*. Against the fixed branch it exits **0**.

### The boundary, recorded as INC-0009

`desktop/playwright.config.ts` is an upstream file and is **not** on the AGENTS.md §3 exception
list, whose own text says it is closed. This fix crosses that line knowingly. Nothing automated
objects — `adr_boundary_check.py` governs only ADR-0005's five deployment files and contains zero
references to `desktop` or `playwright` — so the constraint is review, not CI.

The risk that matters is a silent revert by a future upstream merge. Measured: **144** upstream
commits touch `playwright.config.ts`, but only **one, in March 2026**, has ever touched the reporter
array. Low, not zero — which is what the guard is for.
