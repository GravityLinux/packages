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
                initial = "# Preserve existing config\nCONFIG_OTHER=y\nCONFIG_DRM_NOUVEAU=m\nCONFIG_ARCH_QCOM=y\nCONFIG_USB_STORAGE=m\nCONFIG_REGMAP_SPMI=y\nCONFIG_QCOM_SCM=y\nCONFIG_SND_COMPRESS_OFFLOAD=m\n" + previous
                for variant in variants:
                    (sources / f"kernel-{variant}-fedora.config").write_text(initial)
                overlay_kernel_configs(sources)
                first = {p.name: p.read_text() for p in sources.iterdir()}
                overlay_kernel_configs(sources)
                self.assertEqual(first, {p.name: p.read_text() for p in sources.iterdir()})
                for variant in variants:
                    result = first[f"kernel-{variant}-fedora.config"]
                    if variant.startswith("aarch64-16k"):
                        self.assertIn("# CONFIG_DRM_NOUVEAU is not set\n", result)
                        self.assertNotIn("CONFIG_DRM_NOUVEAU=m\n", result)
                        self.assertIn("# CONFIG_ARCH_QCOM is not set\n", result)
                        self.assertNotRegex(result, r"(?m)^CONFIG_\w+=n$")
                        self.assertIn("CONFIG_QCOM_SCM=m\n", result)
                        self.assertNotIn("CONFIG_QCOM_SCM=y\n", result)
                        # P3S needs 47-bit VA and no AArch32 compat.
                        self.assertIn("CONFIG_ARM64_PER_PROCESS_PAGE_SIZE=y\n", result)
                        self.assertIn("# CONFIG_COMPAT is not set\n", result)
                        self.assertIn("CONFIG_SND_COMPRESS_OFFLOAD=y\n", result)
                        self.assertNotIn("CONFIG_SND_COMPRESS_OFFLOAD=m\n", result)
                    else:
                        self.assertIn("CONFIG_DRM_NOUVEAU=m\n", result)
                        self.assertIn("CONFIG_ARCH_QCOM=y\n", result)
                        self.assertIn("CONFIG_QCOM_SCM=y\n", result)
                        self.assertIn("CONFIG_SND_COMPRESS_OFFLOAD=m\n", result)
                    self.assertIn("CONFIG_USB_STORAGE=m\n", result)
                    if variant.startswith("aarch64"):
                        self.assertEqual(result.count("CONFIG_SERIAL_APPLE_DOCKCHANNEL_EARLYCON="), 1)
                        self.assertIn("CONFIG_SERIAL_APPLE_DOCKCHANNEL_EARLYCON=y\n", result)
                        self.assertNotIn("# CONFIG_SERIAL_APPLE_DOCKCHANNEL_EARLYCON is not set", result)
                        self.assertEqual("CONFIG_DRM_ASAHI=y\n" in result,
                                         variant.startswith("aarch64-16k"))
                        self.assertIn("CONFIG_ARM_APPLE_CPUIDLE=y\n", result)
                        self.assertEqual("CONFIG_SND_SOC_APPLE_T8132_SPEAKER=y\n" in result,
                                         variant.startswith("aarch64-16k"))
                        self.assertIn("CONFIG_OTHER=y\n", result)
                    else:
                        # Other architectures get only the gravity-other.config values.
                        self.assertEqual(result.replace("# CONFIG_USB_XHCI_PCI_ASMEDIA is not set\n", "")
                                         .replace("# CONFIG_BT_BRCMEXT is not set\n", "")
                                         .replace("# CONFIG_BT_HCIMT793B is not set\n", "")
                                         .replace("# CONFIG_SPI_HID_APPLE_OF is not set\n", ""), initial)
                        self.assertIn("# CONFIG_USB_XHCI_PCI_ASMEDIA is not set\n", result)


if __name__ == "__main__":
    unittest.main()
