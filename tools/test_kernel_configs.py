"""Regression tests for the config overlays applied while preparing the SRPM."""
import tempfile
import unittest
from pathlib import Path

from package import overlay_kernel_configs


class KernelConfigTests(unittest.TestCase):
    def test_all_aarch64_variants_and_16k_driver_scope(self):
        variants = (
            "aarch64", "aarch64-debug", "aarch64-16k", "aarch64-16k-debug",
            "aarch64-rt", "aarch64-rt-debug", "aarch64-rt-64k",
            "aarch64-rt-64k-debug", "x86_64", "x86_64-debug", "riscv64",
        )
        for previous in (
            "", "CONFIG_SERIAL_APPLE_DOCKCHANNEL_EARLYCON=n\n",
            "# CONFIG_SERIAL_APPLE_DOCKCHANNEL_EARLYCON is not set\n",
        ):
            with self.subTest(previous=previous), tempfile.TemporaryDirectory() as tmp:
                sources = Path(tmp)
                initial = "# Preserve existing config\nCONFIG_OTHER=y\n" + previous
                for variant in variants:
                    (sources / f"kernel-{variant}-fedora.config").write_text(initial)
                overlay_kernel_configs(sources)
                first = {p.name: p.read_text() for p in sources.iterdir()}
                overlay_kernel_configs(sources)
                self.assertEqual(first, {p.name: p.read_text() for p in sources.iterdir()})
                for variant in variants:
                    result = first[f"kernel-{variant}-fedora.config"]
                    if variant.startswith("aarch64"):
                        self.assertEqual(result.count("CONFIG_SERIAL_APPLE_DOCKCHANNEL_EARLYCON="), 1)
                        self.assertIn("CONFIG_SERIAL_APPLE_DOCKCHANNEL_EARLYCON=y\n", result)
                        self.assertNotIn("# CONFIG_SERIAL_APPLE_DOCKCHANNEL_EARLYCON is not set", result)
                        self.assertEqual("CONFIG_DRM_ASAHI_M4=m\n" in result,
                                         variant.startswith("aarch64-16k"))
                        self.assertEqual("CONFIG_SND_SOC_APPLE_T8132_SPEAKER=y\n" in result,
                                         variant.startswith("aarch64-16k"))
                        self.assertIn("CONFIG_OTHER=y\n", result)
                    else:
                        self.assertEqual(result, initial)


if __name__ == "__main__":
    unittest.main()
