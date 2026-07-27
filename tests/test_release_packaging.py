from __future__ import annotations

import unittest
from pathlib import Path


class ReleasePackagingTests(unittest.TestCase):
    def test_self_contained_runtime_is_enabled_for_distribution_builds(self) -> None:
        project_file = Path(__file__).resolve().parents[1] / "src" / "Similaris.WinUI" / "Similaris.WinUI.csproj"
        contents = project_file.read_text(encoding="utf-8")

        self.assertIn("<SelfContained>true</SelfContained>", contents)
        self.assertIn("<WindowsAppSDKSelfContained>true</WindowsAppSDKSelfContained>", contents)


if __name__ == "__main__":
    unittest.main()
