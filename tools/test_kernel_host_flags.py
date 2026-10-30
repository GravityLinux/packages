# SPDX-License-Identifier: GPL-2.0-only
"""Check the host policy survives recursive make calls that clear CFLAGS."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "kernel/host-tool-flags.sh"


class KernelHostFlagTests(unittest.TestCase):
    def test_recursive_make_inherits_hardening(self):
        flags = ("-O2 -specs=/usr/lib/rpm/redhat/redhat-hardened-cc1 "
                 "-specs=/usr/lib/rpm/redhat/redhat-annobin-cc1 -fstack-protector-strong")
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "parent.mk").write_text(
                "all:\n\t@CFLAGS= $(MAKE) --no-print-directory -f child.mk\n")
            (directory / "child.mk").write_text(
                "all:\n\t@printf '%s\\n' \"$$HOST_EXTRACFLAGS\"\n")
            result = subprocess.run([
                "bash", "-c", '. "$1" "$2"; exec make --no-print-directory -f parent.mk',
                "host-policy-test", str(POLICY), flags,
            ], cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("-specs=/usr/lib/rpm/redhat/redhat-hardened-cc1", result.stdout)
            self.assertIn("-fstack-protector-strong", result.stdout)
            self.assertNotIn("annobin", result.stdout)

    def test_cross_build_can_supply_its_own_host_flags(self):
        environment = dict(os.environ, HOST_EXTRACFLAGS="-O1 -fPIE")
        result = subprocess.run([
            "bash", "-c", '. "$1" ""; printf "%s" "$HOST_EXTRACFLAGS"',
            "host-policy-test", str(POLICY),
        ], env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "-O1 -fPIE")


if __name__ == "__main__":
    unittest.main()
