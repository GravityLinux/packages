# SPDX-License-Identifier: GPL-2.0-only
"""Exercise package placement when production modules embed KUnit tests."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class KernelModulePackageTests(unittest.TestCase):
    def test_embedded_kunit_runtime_can_be_promoted_to_core(self):
        # The real 7.3 Hyper-V HID driver embeds tests, while separate test
        # modules and helpers should retain their preferred internal package.
        dependencies = {
            "kernel/drivers/hid/hid-hyperv.ko": [
                "kernel/drivers/hv/hv_vmbus.ko", "kernel/lib/kunit/kunit.ko"],
            "kernel/drivers/hv/hv_vmbus.ko": [],
            "kernel/lib/kunit/kunit.ko": [],
            "kernel/lib/string_kunit.ko": ["kernel/lib/kunit/kunit.ko"],
            "kernel/drivers/clk/clk_kunit_helpers.ko": ["kernel/lib/kunit/kunit.ko"],
            "kernel/drivers/clk/clk_test.ko": [
                "kernel/drivers/clk/clk_kunit_helpers.ko", "kernel/lib/kunit/kunit.ko"],
        }
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            depfile = directory / "modules.dep"
            depfile.write_text("".join(
                f"{module}: {' '.join(deps)}\n" for module, deps in dependencies.items()))
            result = subprocess.run([
                sys.executable, str(ROOT / "kernel/inputs/filtermods.py"), "sort",
                "-d", str(depfile), "-c",
                str(ROOT / "kernel/inputs/def_variants.yaml.fedora"),
                "-o", str(directory),
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            packages = {
                name: set((directory / f"{name}.list").read_text().splitlines())
                for name in ("modules-core", "modules", "modules-internal", "modules-extra")
            }
            self.assertEqual(packages["modules-core"], {
                "kernel/drivers/hid/hid-hyperv.ko", "kernel/drivers/hv/hv_vmbus.ko",
                "kernel/lib/kunit/kunit.ko",
            })
            self.assertEqual(packages["modules-internal"], {
                "kernel/lib/string_kunit.ko", "kernel/drivers/clk/clk_kunit_helpers.ko",
                "kernel/drivers/clk/clk_test.ko",
            })
            assigned = [module for modules in packages.values() for module in modules]
            self.assertCountEqual(assigned, dependencies)


if __name__ == "__main__":
    unittest.main()
