# GHOST FIVE // VECTIS
# Regression coverage for cross-platform local browser launching.

from __future__ import annotations

import unittest
from unittest.mock import patch

from vectis.browser import open_local_url


class BrowserLaunchTests(unittest.TestCase):
    """Protect browser launching for desktop Python and WSL users."""

    @patch("vectis.browser.subprocess.Popen")
    @patch("vectis.browser.shutil.which", return_value="/mnt/c/Windows/System32/cmd.exe")
    @patch("vectis.browser._is_wsl", return_value=True)
    def test_wsl_uses_windows_browser_bridge(
        self,
        _wsl,
        _which,
        popen,
    ):
        self.assertTrue(open_local_url("http://127.0.0.1:8765/"))
        argv = popen.call_args.args[0]
        self.assertEqual(argv[1:4], ["/c", "start", ""])
        self.assertEqual(argv[4], "http://127.0.0.1:8765/")

    @patch("vectis.browser.webbrowser.open", return_value=True)
    @patch("vectis.browser._is_wsl", return_value=False)
    def test_standard_python_uses_webbrowser(self, _wsl, browser_open):
        self.assertTrue(open_local_url("http://127.0.0.1:8775/"))
        browser_open.assert_called_once_with("http://127.0.0.1:8775/")

    @patch("vectis.browser.webbrowser.open", side_effect=OSError("no browser"))
    @patch("vectis.browser._is_wsl", return_value=False)
    def test_browser_failure_is_nonfatal(self, _wsl, _browser_open):
        self.assertFalse(open_local_url("http://127.0.0.1:8765/"))


if __name__ == "__main__":
    unittest.main()
