"""Check that kernel source preparation is self-contained and preserves helpers."""
from pathlib import Path
import json
import os
import tempfile
import unittest

from package import ROOT, stage_package_sources


class KernelInputsTests(unittest.TestCase):
    def test_local_inputs_are_staged_with_overlays_and_executable_helpers(self):
        inputs = ROOT / 'kernel/inputs'
        original = (inputs / 'kernel-aarch64-16k-fedora.config').read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            sources = Path(directory)
            stage_package_sources('kernel', sources)
            for name in ('generate_all_configs.sh', 'process_configs.sh', 'merge.py', 'check-kabi'):
                self.assertEqual((sources / name).read_bytes(), (inputs / name).read_bytes())
                self.assertTrue(os.access(sources / name, os.X_OK), name)
            config = (sources / 'kernel-aarch64-16k-fedora.config').read_text()
            self.assertIn('CONFIG_DRM_ASAHI=m\n', config)
            self.assertIn('CONFIG_SND_SOC_APPLE_T8132_SPEAKER=y\n', config)
            self.assertTrue((sources / 'rebase-experimental-configs.py').is_file())
            self.assertFalse(any(p.name.startswith('linux-7.1') for p in sources.iterdir()))
            self.assertFalse((sources / 'patch-7.1-redhat.patch').exists())
        self.assertEqual((inputs / 'kernel-aarch64-16k-fedora.config').read_bytes(), original)

    def test_recipes_do_not_download_baseline_srpms(self):
        for name, recipe in json.loads((ROOT / 'sources.json').read_text()).items():
            self.assertNotIn('base_srpm', recipe, name)


if __name__ == '__main__':
    unittest.main()
