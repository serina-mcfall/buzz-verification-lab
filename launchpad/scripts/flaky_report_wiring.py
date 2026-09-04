#!/usr/bin/env python3
"""Check that the Playwright flaky-report wiring still agrees with itself.

WHY THIS EXISTS — INC-0001, and it is not the obvious reason.

Three places referred to `desktop/playwright-report.json` and none produced it:
`ci.yml` invoked the summarizer with that filename, the same workflow uploaded
that path as an artifact, and `desktop/.gitignore` already ignored it. Every
individual reference was correct. The SET of them did not agree, because
`playwright.config.ts` declared only the `list` and `html` reporters.

So the summarizer took its missing-file branch and exited 0 on every run from
2026-07-13 until the reporter was added. CI reported success for a step that had
never once done its job — while the only real ci.yml failures in the preceding
100 runs were Desktop E2E flakes, exactly the signal it existed to surface.

WHAT THIS CHECKS, AND WHY IT IS NOT "IS THE REPORTER THERE".

A checker that grepped for `"json"` would pass the moment someone re-added a
reporter writing to the wrong path, which is the same bug with a new spelling.
This compares the three references TO EACH OTHER:

    playwright.config.ts   ["json", { outputFile: X }]      -> desktop/X
    ci.yml                 summarize-flaky-tests.mjs ARG    -> <workdir>/ARG
    ci.yml                 upload-artifact path: P          -> P

and requires all of them to name the same repo-relative file. Adding a reporter
that writes somewhere nobody reads fails here, as it should.

EXIT CODES — three, never two.

    0  checked, and the references agree
    1  checked, and they disagree
    3  COULD NOT CHECK — a file is missing, or nothing consumes the report

The third exists because this checker guards against exactly one mistake:
absent input read as nothing-to-report. Repeating that mistake here would be a
poor joke. A missing config is not a passing check.

Usage:  python3 flaky_report_wiring.py [repo-root]
"""

import re
import sys
from pathlib import Path

OK, MISMATCH, CANNOT_CHECK = 0, 1, 3

CONFIG_REL = "desktop/playwright.config.ts"
CI_REL = ".github/workflows/ci.yml"
SUMMARIZER_REL = "desktop/scripts/summarize-flaky-tests.mjs"

# The reporter entry, anchored on "json" so the html entry beside it cannot
# match. DOTALL and non-greedy because the entry may be wrapped across lines by
# a formatter; `[^\]]` would break on a nested bracket, and `.*?` up to the
# first closing brace is enough for an options object with no nesting.
JSON_REPORTER = re.compile(
    r"""\[\s*["']json["']\s*,\s*\{(.*?)\}""", re.DOTALL
)
OUTPUT_FILE = re.compile(r"""outputFile\s*:\s*["']([^"']+)["']""")

SUMMARIZER_CALL = re.compile(r"""summarize-flaky-tests\.mjs\s+(\S+)""")
WORKING_DIR = re.compile(r"""^\s*working-directory:\s*(\S+)""")


def _find_invocations(ci_text):
    """Every summarizer call in ci.yml, with the working-directory it runs in.

    Line-based rather than a YAML parse, deliberately: PyYAML is not guaranteed
    on the runner, and a hard dependency would turn a missing package into a
    silently skipped check — which is the failure mode this file exists to stop.

    `working-directory` is a sibling key of `run` within the same step, so it is
    searched forward a few lines only. Searching the whole document would let one
    step's directory answer for another's.
    """
    lines = ci_text.splitlines()
    found = []
    for i, line in enumerate(lines):
        m = SUMMARIZER_CALL.search(line)
        if not m:
            continue
        arg = m.group(1).strip("\"'")
        workdir = "."
        for ahead in lines[i + 1 : i + 5]:
            wm = WORKING_DIR.match(ahead)
            if wm:
                workdir = wm.group(1).strip("\"'")
                break
        found.append((arg, workdir, i + 1))
    return found


def _normalise(workdir, arg):
    """Repo-relative path for a report named relative to a working directory."""
    if workdir in (".", ""):
        return arg.lstrip("./")
    return f"{workdir.rstrip('/')}/{arg.lstrip('./')}"


def check(repo_root):
    root = Path(repo_root)
    problems = []

    config_path = root / CONFIG_REL
    ci_path = root / CI_REL
    summarizer_path = root / SUMMARIZER_REL

    # Fail closed on absence, and say which piece is absent. A partial checkout,
    # a moved file or a deleted consumer must not read as a passing wiring.
    for label, p in (
        ("the Playwright config", config_path),
        ("the CI workflow", ci_path),
        ("the summarizer", summarizer_path),
    ):
        if not p.is_file():
            problems.append(
                f"could not check: {label} is missing at {p.relative_to(root)}"
            )
    if problems:
        return CANNOT_CHECK, problems

    ci_text = ci_path.read_text()
    invocations = _find_invocations(ci_text)
    if not invocations:
        # Nothing consumes the report, so there is no wiring to verify. That may
        # be a deliberate removal, but this checker cannot tell that from a
        # rename, and guessing "fine" is the fail-open it exists to prevent.
        return CANNOT_CHECK, [
            f"could not check: no summarize-flaky-tests.mjs invocation in {CI_REL} — "
            "if the step was removed deliberately, retire this checker with it"
        ]

    config_text = config_path.read_text()
    reporter = JSON_REPORTER.search(config_text)
    output_match = OUTPUT_FILE.search(reporter.group(1)) if reporter else None

    if not output_match:
        expected = sorted({_normalise(w, a) for a, w, _ in invocations})
        problems.append(
            f"{CONFIG_REL} declares no json reporter with an outputFile, so the "
            f"report is never produced."
        )
        problems.append(
            "  but these already expect it: "
            + ", ".join(expected)
            + f"  (invoked at {CI_REL}:"
            + ",".join(str(ln) for _, _, ln in invocations)
            + ")"
        )
        problems.append(
            '  fix: add [\"json\", { outputFile: \"'
            + Path(expected[0]).name
            + '\" }] to the reporter array'
        )
        return MISMATCH, problems

    produced = _normalise("desktop", output_match.group(1))

    # Every invocation, not just the first. ci.yml calls the summarizer once per
    # E2E job, and a checker that stopped at the first match would miss a second
    # one that had drifted.
    for arg, workdir, line_no in invocations:
        consumed = _normalise(workdir, arg)
        if consumed != produced:
            problems.append(
                f"{CI_REL}:{line_no} reads {consumed} but {CONFIG_REL} writes {produced}"
            )

    # The artifact upload is how a human retrieves the report after a red run. A
    # produced-and-consumed report that is never uploaded is still a gap.
    if produced not in ci_text:
        problems.append(
            f"{CONFIG_REL} writes {produced} but {CI_REL} does not upload that path"
        )

    if problems:
        return MISMATCH, problems
    return OK, [f"wired: {produced} is produced, consumed by {len(invocations)} step(s), and uploaded"]


def main(argv):
    root = argv[1] if len(argv) > 1 else "."
    code, messages = check(root)
    for m in messages:
        print(m)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
