import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
TEMPLATE = REPOSITORY / ".github" / "pull_request_template.md"


class PullRequestTemplateRegressionGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = TEMPLATE.read_text(encoding="utf-8")

    def test_has_one_regression_ownership_section(self):
        self.assertEqual(
            1,
            self.template.count("## Regression ownership"),
        )

    def test_names_checked_manifest_and_exact_ctest(self):
        section = self.template.split("## Regression ownership", 1)[1].split(
            "\n## ", 1
        )[0]
        self.assertIn("tests/regression/ownership_manifest.json", section)
        self.assertIn("exact source-contract id", section)
        self.assertIn("exact CTest test name", section)

    def test_requires_non_unit_owner_and_trigger(self):
        section = self.template.split("## Regression ownership", 1)[1].split(
            "\n## ", 1
        )[0]
        for qualification in (
            "external integration",
            "platform-only",
            "physical",
            "pending qualification",
        ):
            self.assertIn(qualification, section)
        self.assertIn("name the owner and objective trigger", section)

    def test_checklist_requires_review_of_regression_ownership(self):
        self.assertIn(
            "- [ ] Every SDK behavior names its ownership-manifest contract, "
            "exact regression, and any external/platform/physical owner and trigger.",
            self.template,
        )


if __name__ == "__main__":
    unittest.main()
