"""Controls for flaky_report_wiring.py.

Written before the checker existed and run against nothing, so the first run
failed on the import. That is deliberate: a control suite that has never been
red has not been shown to be capable of failing.

The bug these controls exist to prevent is INC-0001, and it is worth stating
precisely because a weaker guard would miss it. THREE places referred to
desktop/playwright-report.json and NONE produced it:

  - .github/workflows/ci.yml invoked the summarizer with that filename
  - the same workflow uploaded that path as an artifact
  - desktop/.gitignore already ignored it

The file was simply never written, because playwright.config.ts declared only
the `list` and `html` reporters. Every individual reference was correct; the set
of them did not agree. So this checker compares the references to each other,
rather than asserting that any one of them looks right.
"""

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import flaky_report_wiring as w  # noqa: E402

OK, MISMATCH, CANNOT_CHECK = 0, 1, 3

CONFIG_WITH_JSON = """
export default defineConfig({
  reporter: [
    ["list"],
    ["json", { outputFile: "playwright-report.json" }],
    ["html", { open: "never", outputFolder: "playwright-report" }],
  ],
});
"""

# The pre-INC-0001 config, reproduced exactly. This is the input the checker
# must reject; if it ever passes, the checker is worthless.
CONFIG_WITHOUT_JSON = """
export default defineConfig({
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "playwright-report" }],
  ],
});
"""

CI_YML = """
jobs:
  smoke:
    steps:
      - name: Summarize flaky tests
        run: node scripts/summarize-flaky-tests.mjs playwright-report.json "Desktop Smoke E2E"
        working-directory: desktop
      - name: Upload
        uses: actions/upload-artifact@v7
        with:
          path: |
            desktop/playwright-report
            desktop/playwright-report.json
            desktop/test-results
"""


def build(tmp, config=CONFIG_WITH_JSON, ci=CI_YML, summarizer=True):
    """Write a minimal tree. Each piece is omittable so absence can be tested."""
    root = Path(tmp)
    if config is not None:
        (root / "desktop").mkdir(parents=True, exist_ok=True)
        (root / "desktop" / "playwright.config.ts").write_text(textwrap.dedent(config))
    if ci is not None:
        (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
        (root / ".github" / "workflows" / "ci.yml").write_text(textwrap.dedent(ci))
    if summarizer:
        (root / "desktop" / "scripts").mkdir(parents=True, exist_ok=True)
        (root / "desktop" / "scripts" / "summarize-flaky-tests.mjs").write_text("//\n")
    return root


class TestNotVacuous(unittest.TestCase):
    """A checker that says OK to everything would pass every other control here."""

    def test_a_correctly_wired_tree_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, msgs = w.check(build(tmp))
            self.assertEqual(code, OK, msgs)

    def test_the_checker_can_say_something_other_than_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = w.check(build(tmp, config=CONFIG_WITHOUT_JSON))
            self.assertNotEqual(code, OK)


class TestTheOriginalBug(unittest.TestCase):
    def test_no_json_reporter_is_a_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, msgs = w.check(build(tmp, config=CONFIG_WITHOUT_JSON))
            self.assertEqual(code, MISMATCH, msgs)

    def test_and_it_names_the_config_rather_than_failing_vaguely(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, msgs = w.check(build(tmp, config=CONFIG_WITHOUT_JSON))
            joined = "\n".join(msgs)
            self.assertIn("playwright.config.ts", joined)
            self.assertIn("json", joined)

    def test_it_says_who_expected_the_file(self):
        """The message must name the consumers, or a reader cannot tell whether
        to add the reporter or delete the expectation."""
        with tempfile.TemporaryDirectory() as tmp:
            _, msgs = w.check(build(tmp, config=CONFIG_WITHOUT_JSON))
            joined = "\n".join(msgs)
            self.assertIn("playwright-report.json", joined)


class TestDisagreement(unittest.TestCase):
    def test_config_path_disagreeing_with_the_summarizer_argument_fails(self):
        cfg = CONFIG_WITH_JSON.replace(
            "playwright-report.json", "some-other-name.json"
        )
        with tempfile.TemporaryDirectory() as tmp:
            code, msgs = w.check(build(tmp, config=cfg))
            self.assertEqual(code, MISMATCH, msgs)
            self.assertIn("some-other-name.json", "\n".join(msgs))

    def test_config_path_disagreeing_with_the_uploaded_artifact_fails(self):
        ci = CI_YML.replace("desktop/playwright-report.json\n", "desktop/nope.json\n")
        with tempfile.TemporaryDirectory() as tmp:
            code, msgs = w.check(build(tmp, ci=ci))
            self.assertEqual(code, MISMATCH, msgs)

    def test_a_second_shard_with_a_different_path_is_caught(self):
        """ci.yml invokes the summarizer twice, for smoke and integration. A
        checker that stops at the first match would miss a drifted second one."""
        ci = CI_YML + textwrap.dedent(
            """
      - name: Summarize flaky tests
        run: node scripts/summarize-flaky-tests.mjs drifted-report.json "Integration"
        working-directory: desktop
"""
        )
        with tempfile.TemporaryDirectory() as tmp:
            code, msgs = w.check(build(tmp, ci=ci))
            self.assertEqual(code, MISMATCH, msgs)
            self.assertIn("drifted-report.json", "\n".join(msgs))


class TestCannotCheck(unittest.TestCase):
    """Absent input must never read as a passing check.

    This is the shape of INC-0001 itself: the summarizer treated a missing
    report as nothing-to-report and exited 0. A checker that repeated that
    mistake would be an especially poor joke.
    """

    def test_missing_config_cannot_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, msgs = w.check(build(tmp, config=None))
            self.assertEqual(code, CANNOT_CHECK, msgs)

    def test_missing_ci_workflow_cannot_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, msgs = w.check(build(tmp, ci=None))
            self.assertEqual(code, CANNOT_CHECK, msgs)

    def test_missing_summarizer_cannot_check(self):
        """If the consumer is gone the wiring question is moot, and answering
        'fine' would be wrong in the other direction."""
        with tempfile.TemporaryDirectory() as tmp:
            code, msgs = w.check(build(tmp, summarizer=False))
            self.assertEqual(code, CANNOT_CHECK, msgs)

    def test_cannot_check_is_distinguishable_from_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            clean, _ = w.check(build(tmp))
            with tempfile.TemporaryDirectory() as tmp2:
                absent, msgs = w.check(build(tmp2, config=None))
            self.assertNotEqual(clean, absent)
            self.assertIn("could not check", "\n".join(msgs).lower())


class TestAgainstTheRealRepository(unittest.TestCase):
    """Fixtures test the cases I thought of. This tests the tree we ship."""

    def test_this_repository_is_correctly_wired(self):
        root = Path(__file__).resolve().parents[2]
        code, msgs = w.check(root)
        self.assertEqual(code, OK, "\n".join(msgs))


class TestCommandLine(unittest.TestCase):
    def test_exit_code_reaches_the_shell(self):
        """The workflow reads the exit code, so a checker that reports failures
        on stdout and exits 0 would be green in CI while naming its own faults."""
        with tempfile.TemporaryDirectory() as tmp:
            root = build(tmp, config=CONFIG_WITHOUT_JSON)
            proc = subprocess.run(
                [sys.executable, str(Path(w.__file__)), str(root)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, MISMATCH, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
