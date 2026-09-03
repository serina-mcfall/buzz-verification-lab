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

## Open question

How long has this been silent? The summarizer file dates from 2026-08-07, but when it was wired
into CI is unverified. Method: `git log --follow` on both files and compare first-appearance dates.
