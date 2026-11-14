"""Payload policy checks; runtime rendering is tested natively, not mocked here."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "graphics_assemble", Path(__file__).resolve().parents[1] / "gravity-flatpak-graphics/assemble.py"
)
graphics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graphics)


class ExtensionPayload(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name) / "work"
        self.out = Path(self.tmp.name) / "out"
        self.work.mkdir()
        for _, _, prefix, stage in graphics.SLOTS:
            base = self.work / stage / prefix.lstrip("/")
            (base / "lib").mkdir(parents=True, exist_ok=True)
            if not (base / "lib/swrast_dri.so").is_symlink():
                (base / "lib/swrast_dri.so").symlink_to("libgallium.so")
            (base / "lib/libgallium.so").write_text("test fixture, not ELF")
        (self.work / "software-driver.txt").write_text("llvmpipe\n")
        (self.work / "llvm-runtime").mkdir()
        llvm = self.work / "llvm-runtime/libLLVM.so.22.1"
        llvm.write_bytes(b'\x7fELFopaque SDK fixture; never rewritten')
        (self.work / "llvm-origin.json").write_text(json.dumps({
            "sha256_before_assembly": hashlib.sha256(llvm.read_bytes()).hexdigest()
        }))

    def assemble(self):
        graphics.assemble(self.work, self.out, "test-commit")

    def test_three_slots_share_one_llvm_inode(self):
        self.assemble()
        copies = list(self.out.rglob("libLLVM.so.22.1"))
        self.assertEqual(len(copies), 3)
        self.assertEqual(len({p.stat().st_ino for p in copies}), 1)
        self.assertTrue(all(p.stat().st_nlink == 3 for p in copies))
        original = (self.work / "llvm-runtime/libLLVM.so.22.1").read_bytes()
        self.assertTrue(all(p.read_bytes() == original for p in copies))
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o644 for p in copies))
        self.assertEqual(len(list(self.out.rglob("swrast_dri.so"))), 3)

    def test_mismatched_sdk_library_is_rejected(self):
        (self.work / "llvm-runtime/libLLVM.so.22.1").write_text("changed SDK input")
        with self.assertRaisesRegex(ValueError, "recorded origin"):
            self.assemble()

    def test_additional_llvm_library_is_rejected(self):
        (self.work / "stage/usr/lib/aarch64-linux-gnu/GL/host/lib/libLLVMTableGen.so").touch()
        with self.assertRaisesRegex(ValueError, "LLVM file payload"):
            self.assemble()

    def test_lavapipe_is_rejected(self):
        (self.work / "stage/usr/lib/aarch64-linux-gnu/GL/host/lib/libvulkan_lvp.so").touch()
        with self.assertRaisesRegex(ValueError, "Vulkan software"):
            self.assemble()

    def test_softpipe_comparison_has_no_llvm_payload(self):
        (self.work / "software-driver.txt").write_text("softpipe\n")
        self.assemble()
        self.assertFalse(list(self.out.rglob("*LLVM*")))


if __name__ == "__main__":
    unittest.main()
