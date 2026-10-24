"""Unit tests verifying frontend assets integrity and modular synchronization."""

from __future__ import annotations

import unittest
from pathlib import Path
from scripts.build_js import bundle

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
CSS_DIR = WEB_DIR / "css"
JS_DIR = WEB_DIR / "js"


class FrontendAssetsTestCase(unittest.TestCase):
    """Test CSS and JS modularization consistency."""

    def test_js_bundle_matches_modules(self):
        """web/app.js must stay in sync with web/js/ modular source files."""
        self.assertTrue(
            bundle(check_only=True),
            "web/app.js is out of sync with web/js/. Run 'python scripts/build_js.py' to update it.",
        )

    def test_css_aggregator_imports_all_modules(self):
        """web/style.css must import all CSS files in web/css/."""
        style_css = (WEB_DIR / "style.css").read_text(encoding="utf-8")
        for css_file in CSS_DIR.glob("*.css"):
            expected_import = f"css/{css_file.name}"
            self.assertIn(
                expected_import,
                style_css,
                f"Missing @import for {expected_import} in web/style.css",
            )

    def test_no_file_exceeds_reasonable_line_limit(self):
        """No modular source file in web/css/ or web/js/ should be a bloated god file (> 350 lines)."""
        all_modular_files = list(CSS_DIR.glob("*.css")) + list(JS_DIR.rglob("*.js"))
        for path in all_modular_files:
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            self.assertLess(
                line_count,
                350,
                f"File {path.relative_to(ROOT)} has {line_count} lines, exceeding the 350-line modular limit",
            )


if __name__ == "__main__":
    unittest.main()
