"""The offline compiler pin must survive OSTree deployment/checkout differences."""
import hashlib
import importlib.util
import os
from pathlib import Path
import tarfile
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "gravity-flatpak-graphics/export-sdk.py"
SPEC = importlib.util.spec_from_file_location("export_sdk", MODULE)
sdk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sdk)


class SDKArchiveTests(unittest.TestCase):
    def test_same_archive_for_deployed_and_copied_sdk(self):
        lock = {"arch": "aarch64", "branch": "25.08", "refs": {
            "org.freedesktop.Sdk": "a" * 64,
            "org.freedesktop.Sdk.Extension.llvm22": "b" * 64,
        }}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hashes = []
            for variant in ("deployment", "checkout"):
                installation = root / variant
                for name, commit in lock["refs"].items():
                    parent = installation / "runtime" / name / "aarch64/25.08"
                    files = parent / commit / "files/bin"
                    files.mkdir(parents=True)
                    tool = files / "tool"
                    tool.write_bytes(b"compiler stand-in\n")
                    tool.chmod(0o555 if variant == "deployment" else 0o755)
                    os.utime(tool, (100, 100) if variant == "deployment" else (200, 200))
                    if variant == "deployment":
                        (files / "duplicate").hardlink_to(tool)
                    else:
                        (files / "duplicate").write_bytes(tool.read_bytes())
                        (files / "duplicate").chmod(0o755)
                    (files / "link").symlink_to("tool")
                    (parent / "active").symlink_to(commit)
                archive = root / (variant + ".tar.gz")
                sdk.export(installation, lock, archive)
                hashes.append(hashlib.sha256(archive.read_bytes()).hexdigest())
                with tarfile.open(archive) as stream:
                    self.assertTrue(stream.getmember("sdk/bin/link").issym())
                    self.assertTrue(stream.getmember("sdk/bin/duplicate").isreg())
                with self.assertRaises(FileExistsError):
                    sdk.export(installation, lock, archive)
                self.assertTrue(archive.exists())
            self.assertEqual(*hashes)

    def test_wrong_sdk_commit_is_rejected_before_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "runtime/org.freedesktop.Sdk/aarch64/25.08"
            (parent / "wrong/files").mkdir(parents=True)
            (parent / "active").symlink_to("wrong")
            output = root / "sdk.tar.gz"
            with self.assertRaisesRegex(ValueError, "expected"):
                sdk.export(root, {"arch": "aarch64", "branch": "25.08", "refs": {
                    "org.freedesktop.Sdk": "a" * 64,
                }}, output)
            self.assertFalse(output.exists())
