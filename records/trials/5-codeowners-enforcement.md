# Trial — code-owner review as a merge gate

**Phase** 5 · **Started** 2026-09-03 · **Closed** 2026-09-03
**Where** `serina-mcfall/buzz-verification-lab`, PR #1 · **Verdict** `fix`

---

## What this mechanism is meant to catch

A merge into a protected branch that no code owner has approved.

## What was set up

Fork of `launchpad-26/buzz` where Serina holds `admin` — the permission `launchpad-26/buzz` does not
grant her, and therefore the only place this is testable at all.

```bash
gh repo fork launchpad-26/buzz --clone=false --fork-name buzz-verification-lab
# Settings → Actions → allow all            (verified: enabled=true, allowed_actions=all)
# Settings → Rulesets → launchpad-verification-trial
```

Ruleset `launchpad-verification-trial` (id 22167683), read back from the API rather than the form:

| Setting | Value |
|---|---|
| enforcement | `active` |
| **bypass actors** | **0 — admin included** |
| target | `~DEFAULT_BRANCH` (`launchpad`) |
| rules | `deletion`, `non_fast_forward`, `pull_request` |
| `require_code_owner_review` | `true` |
| `required_approving_review_count` | 1 |
| `require_extra_approval_for_unattributed_changes` | `true` (GitHub default, not chosen) |

Test subject: PR #1, a one-line CODEOWNERS fix replacing the invalid `@block/buzz-oss-team` with
`@serina-mcfall`. Deliberately self-referential — a PR fixing CODEOWNERS, gated by a rule requiring
CODEOWNERS review.

## What was thrown at it

| # | Input | Expected | Actual | ✅/❌ |
|---|---|---|---|---|
| 1 | PR into protected `launchpad` with no approval | blocked | `mergeStateStatus: BLOCKED`, `reviewDecision: REVIEW_REQUIRED` | ✅ |
| 2 | Content that merges cleanly | not blocked *for conflicts* | `mergeable: MERGEABLE` — blocked by rule, not by conflict | ✅ |
| 3 | CODEOWNERS invalid on the **base** branch | ? | **review requested from nobody**: `reviewRequests: []` | ⚠️ see below |
| 4 | Bypass attempt — admin with empty bypass list | cannot merge | API reports `BLOCKED` | ✅ (button not eyeballed) |

Row 4 note: the API's verdict was taken as the answer. Nobody clicked the merge button to see whether
GitHub offers an admin override in the UI. **Not fully tested.**

---

## What happened

### ✅ What was great

- **The gate holds.** `BLOCKED` with an empty bypass list, on an admin's own PR. The distinction
  between `mergeable: MERGEABLE` and `mergeStateStatus: BLOCKED` is exactly right — content is fine,
  the rule stops it.
- **`gh pr view --json mergeStateStatus,reviewDecision` is a clean machine-readable probe.** No
  scraping, no guessing. Good candidate for an automated check later.
- **The PR body checker fired correctly** (see below) — a true positive, not noise.

### ⚠️ What needs work

**The CODEOWNERS catch-22.** GitHub evaluates CODEOWNERS from the **base** branch. With
`require_code_owner_review: true` and an invalid owner on base, the PR requires code-owner approval
and requests it from **nobody** — `reviewRequests: []`.

Consequence, stated plainly: **a repository with an invalid CODEOWNERS and code-owner review required
has no path to merge the fix for its own CODEOWNERS.** The fix must land *before* the rule is
enabled, or the rule must be temporarily lifted.

This applies directly to `launchpad-26/buzz`, which has the invalid `@block/buzz-oss-team` owner
today and whose required-checks configuration cannot be read at `maintain` permission. **If anyone
enables code-owner review there before fixing CODEOWNERS, the repo locks itself.** That is the
single most actionable finding of this trial.

### ❌ What broke

Nothing broke. The one failure — `launchpad — PR body check` — was **correct**:

```
- No issue reference GitHub recognises. Use 'Closes #<n>' ... or 'Refs #<n>'
- Missing '### Feature' section. ADR-0052 makes a Feature the PR unit.
- Missing '### Issue type' section.
```

All three were true of the body. No incident recorded: a check doing its job is not an incident.

Worth noting for Phase 1: this **weakens the hypothesis that the 43/100 body-check failure rate is a
checker bug.** The failure messages name the violated rule, cite the ADR, and point at both
templates. The rate is more likely non-conformance than malfunction — but this PR is a lab
experiment in a fork with no issues, so it is *unrepresentative* and cannot settle the question.
Phase 1 still needs the real 43.

### 🗑️ What should go

Nothing yet. `require_extra_approval_for_unattributed_changes` is on by GitHub's default and was
never exercised — no verdict, and it should not be assumed benign.

---

## The numbers

| Field | Value | Notes |
|---|---|---|
| `ci_seconds` | ~20 | PR body check 10s, ADR boundary 11s, publish 20s |
| `true_positives` | 2 | merge correctly blocked; body check correctly failed |
| `false_positives` | 0 | nothing fired wrongly |
| runs observed | 1 | **one PR. A verdict from one run is a guess** |

---

## What this trial could NOT determine

- **Whether approval unblocks the merge.** GitHub does not permit approving your own PR, so a
  one-person fork cannot exercise the approve → merge path at all. Needs a second account or a
  collaborator.
- **Whether the UI offers an admin override** despite the API reporting `BLOCKED`. The button was
  never clicked.
- **Whether `require_extra_approval_for_unattributed_changes` fires on agent commits.** Not
  triggered here; unknown behaviour.
- **Anything about fleet scale, contention, or CI queueing.** The lab has one PR and no colleagues.
- **Whether the failure messages read clearly to someone who did not write them.** Author-tested only.

---

## Verdict

**`fix`** — the mechanism works, the *rollout order* is wrong.

Blocking behaviour is confirmed and clean, with zero false positives. But enabling code-owner review
against an invalid CODEOWNERS produces an unmergeable repository, and that is precisely the state
`launchpad-26/buzz` is in. The mechanism does not ship as "turn on code-owner review". It ships as an
ordered pair:

1. Fix CODEOWNERS to a resolving owner. Verify with
   `gh api repos/<owner>/<repo>/codeowners/errors` returning zero errors.
2. **Only then** enable `require_code_owner_review`.

Re-trial needed for the approval path, which is `blocked` here and must not be recorded as working.

## Meta-findings from running the trial itself

Two constraints on the testing approach, both discovered by hitting them:

1. **Agents cannot open PRs in the lab fork.** `pr-gate.sh` refuses `gh pr create --repo <name>`
   because it cannot verify a repository it is not standing in. Every trial PR needs a human, or the
   hook needs a lab-fork exception.
2. **Fork PRs default to targeting upstream, silently.** The first attempt opened against
   `launchpad-26/buzz` as PR #2066 and had to be closed. Given this trial plan involves deliberately
   broken PRs — deleted tests, empty evidence blocks — this is a real hazard. Mandatory check after
   opening any trial PR:

   ```bash
   gh pr list --repo serina-mcfall/buzz-verification-lab
   ```

   If the PR just opened is not in that output, it went upstream.

Prose warnings did not prevent #2: it was written into the testing approach twice and happened
anyway. A one-line check is worth more than a paragraph of caution.

## Record it

```bash
<skill>/record.sh --kind review \
  --summary "code-owner review gate: fix — works, but must be enabled AFTER CODEOWNERS is valid" \
  --tags ci/codeowners,ci/required-checks \
  --field verdict=fix --field mechanism=code-owner-review-gate \
  --field ci_seconds=20 --field false_positives=0 --field true_positives=2 \
  --doc trials/5-codeowners-enforcement.md
```
