# SPDX-License-Identifier: GPL-2.0-only
"""Check that the expanded RPM build preserves the advertised kernel minor."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("rpmspec"), "Fedora RPM tooling required")
class KernelVersionTests(unittest.TestCase):
    def test_makefile_minor_tracks_advertised_version(self):
        source = (ROOT / "kernel/kernel.spec").read_text()
        advertised = re.search(r"^%define specversion (\S+)$", source, re.M).group(1)
        for version in (advertised, "7.4.0", "7.10.2"):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as temporary:
                spec = Path(temporary) / "kernel.spec"
                spec.write_text(re.sub(r"^%define specversion \S+$",
                                       f"%define specversion {version}", source, flags=re.M))
                result = subprocess.run([
                    "rpmspec", "--target", "aarch64", "--define", "fedora 44",
                    "--define", "fc44 1", "--define", "dist .fc44", "-P", str(spec),
                ], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                minor = version.split(".")[1]
                self.assertIn(f"s/^PATCHLEVEL.*/PATCHLEVEL = {minor}/", result.stdout)
                self.assertIn(f"KernelVer={version}-", result.stdout)


if __name__ == "__main__":
    unittest.main()
