# SPDX-License-Identifier: MIT
"""Tests of fetch-client against a local HTTP server (run in %check)."""
import functools
import errno
import hashlib
import http.server
import importlib.machinery
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader("fetch_client", str(Path(__file__).with_name("fetch-client")))
fetch_client = importlib.util.module_from_spec(importlib.util.spec_from_loader("fetch_client", loader))
loader.exec_module(fetch_client)


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def do_GET(self):
        site = self.server.site
        site.requests.append((self.path, self.headers.get("Range")))
        body = site.files.get(self.path)
        if body is None:
            self.send_error(404)
            return
        start = 0
        requested = self.headers.get("Range")
        if requested and site.ranges:
            start = int(requested.removeprefix("bytes=").rstrip("-"))
            if start >= len(body):
                self.send_error(416)
                return
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{len(body) - 1}/{len(body)}")
        else:
            self.send_response(200)
        self.send_header("Content-Length", str(len(body) - start))
        self.end_headers()
        end = len(body)
        if site.cut and (site.cut_path is None or self.path == site.cut_path):  # drop once
            end, site.cut = min(end, start + site.cut), 0
        try:
            self.wfile.write(body[start:end])
        except OSError:  # the client stopped reading
            self.close_connection = True
            return
        if end != len(body):
            self.close_connection = True
            self.connection.close()


class Site:
    def __init__(self):
        self.files, self.requests, self.ranges, self.cut = {}, [], True, 0
        self.cut_path = None
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.site = self
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}/repo/"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class Quiet:
    def __init__(self, cancel_at=None):
        self.texts, self.errors, self.cancel_at = [], [], cancel_at

    def update(self, text, fraction, force=False):
        self.texts.append(text)
        if self.cancel_at is not None and fraction >= self.cancel_at:
            raise fetch_client.Cancelled

    def close(self):
        pass

    def error(self, text):
        self.errors.append(text)


def package(work, marker):
    """A package like Valve's: usr/lib/steam/steam.tar.zst holding the client tree."""
    tree = work / "tree"
    (tree / "steamrtarm64").mkdir(parents=True)
    (tree / "steamrtarm64/steam").write_bytes(marker + os.urandom(1000000))
    (tree / "steamrtarm64/steam").chmod(0o755)
    outer = work / "outer/usr/lib/steam"
    outer.mkdir(parents=True)
    subprocess.run(["tar", "--zstd", "-cf", outer / "steam.tar.zst", "-C", tree, "."], check=True)
    subprocess.run(["tar", "--zstd", "-cf", work / "pkg", "-C", work / "outer", "usr"], check=True)
    return (work / "pkg").read_bytes()


def index(entries):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:xz") as archive:
        for directory, fields in entries.items():
            text = "".join(f"%{key}%\n{value}\n\n" for key, value in fields.items()).encode()
            info = tarfile.TarInfo(directory + "/desc")
            info.size = len(text)
            archive.addfile(info, io.BytesIO(text))
    return raw.getvalue()


class FetchClient(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.work = Path(self.temporary.name)
        self.site = Site()
        self.body = package(self.work, b"pinned")
        self.site.files["/repo/client-1.pkg.tar.zst"] = self.body
        self.client = {
            "what": "the Steam client", "source": "Valve", "name": "client", "url": self.site.base + "client-1.pkg.tar.zst",
            "sha256": hashlib.sha256(self.body).hexdigest(), "size": len(self.body),
            "index": "index.db", "member": "usr/lib/steam/steam.tar.zst", "unpacked": 1000,
        }
        self.downloads, self.target = self.work / "downloads", self.work / "target"
        self.target.mkdir()
        self.sleeps = []
        fetch_client.time.sleep = self.sleeps.append

    def tearDown(self):
        self.site.close()
        self.temporary.cleanup()

    def fetch(self, window=None, **options):
        fetch_client.fetch(self.client, self.downloads, self.target, window or Quiet(), **options)

    def installed(self):
        path = self.target / "steamrtarm64/steam"
        return path.read_bytes()[:6] if path.exists() and os.access(path, os.X_OK) else None

    def part(self, digest=None):
        return self.downloads / ((digest or self.client["sha256"]) + ".part")

    def test_download_verify_unpack(self):
        self.fetch()
        self.assertEqual(self.installed(), b"pinned")
        self.assertEqual(self.site.requests, [("/repo/client-1.pkg.tar.zst", None)])

    def test_interrupted_download_resumes(self):
        self.site.cut = 5000
        self.fetch()
        self.assertEqual(self.installed(), b"pinned")
        self.assertEqual(self.site.requests[1], ("/repo/client-1.pkg.tar.zst", "bytes=5000-"))

    def test_cancel_keeps_the_partial_file_and_the_next_run_continues(self):
        with self.assertRaises(fetch_client.Cancelled):
            self.fetch(Quiet(cancel_at=0.0001))
        have = self.part().stat().st_size
        self.assertTrue(0 < have < len(self.body))
        self.assertIsNone(self.installed())
        self.site.requests.clear()
        self.fetch()
        self.assertEqual(self.site.requests, [("/repo/client-1.pkg.tar.zst", f"bytes={have}-")])
        self.assertEqual(self.installed(), b"pinned")

    def test_server_without_ranges_starts_again(self):
        self.downloads.mkdir()
        self.part().write_bytes(b"x" * 100)
        self.site.ranges = False
        self.fetch()
        self.assertEqual(self.installed(), b"pinned")

    def test_checksum_mismatch_is_refused_and_deleted(self):
        self.downloads.mkdir()
        self.part().write_bytes(b"x" * 100)  # a damaged start that the rest is appended to
        with self.assertRaisesRegex(fetch_client.Stop, "checksum"):
            self.fetch()
        self.assertFalse(self.part().exists())
        self.assertIsNone(self.installed())

    def test_other_size_is_refused(self):
        self.client["size"] += 1
        with self.assertRaisesRegex(fetch_client.Stop, "expected"):
            self.fetch()
        self.assertIsNone(self.installed())

    def test_free_space(self):
        with self.assertRaisesRegex(fetch_client.Stop, "free space"):
            self.fetch(free=lambda path: self.client["size"] + 500)
        self.assertEqual(self.site.requests, [])

    def test_offline(self):
        self.site.close()
        with self.assertRaisesRegex(fetch_client.Stop, "internet connection"):
            self.fetch()
        self.assertEqual(len(self.sleeps), 3)
        self.site = Site()

    def gone(self, entries):
        del self.site.files["/repo/client-1.pkg.tar.zst"]
        if entries is not None:
            self.site.files["/repo/index.db"] = index(entries)

    def test_gone_uses_the_index_build_with_its_checksum(self):
        newer = package(self.work / "newer", b"newer!")
        self.site.files["/repo/client-2%2Bb.pkg.tar.zst"] = newer
        self.gone({"other-1": {"NAME": "other", "FILENAME": "other-1.pkg.tar.zst"},
                   "client-2+b": {"NAME": "client", "FILENAME": "client-2+b.pkg.tar.zst",
                                  "CSIZE": len(newer), "SHA256SUM": hashlib.sha256(newer).hexdigest()}})
        window = Quiet()
        self.fetch(window)
        self.assertEqual(self.installed(), b"newer!")
        self.assertTrue(any("newer than" in text for text in window.texts))

    def test_fallback_cancel_keeps_partial_for_next_launch(self):
        newer = package(self.work / "newer", b"newer!")
        digest = hashlib.sha256(newer).hexdigest()
        self.site.files["/repo/client-2.pkg.tar.zst"] = newer
        self.gone({"client-2": {"NAME": "client", "FILENAME": "client-2.pkg.tar.zst",
                                "CSIZE": len(newer), "SHA256SUM": digest}})
        with self.assertRaises(fetch_client.Cancelled):
            self.fetch(Quiet(cancel_at=0.0001))
        have = self.part(digest).stat().st_size
        self.assertTrue(0 < have < len(newer))
        self.assertIsNone(self.installed())
        self.site.requests.clear()
        self.fetch()
        self.assertEqual(self.site.requests, [("/repo/client-1.pkg.tar.zst", None),
                                             ("/repo/index.db", None),
                                             ("/repo/client-2.pkg.tar.zst", f"bytes={have}-")])
        self.assertEqual(self.installed(), b"newer!")

    def test_fallback_disconnect_resumes_with_range(self):
        newer = package(self.work / "newer", b"newer!")
        self.site.files["/repo/client-2.pkg.tar.zst"] = newer
        self.gone({"client-2": {"NAME": "client", "FILENAME": "client-2.pkg.tar.zst",
                                "CSIZE": len(newer), "SHA256SUM": hashlib.sha256(newer).hexdigest()}})
        self.site.cut, self.site.cut_path = 5000, "/repo/client-2.pkg.tar.zst"
        self.fetch()
        self.assertEqual(self.site.requests[-1], ("/repo/client-2.pkg.tar.zst", "bytes=5000-"))
        self.assertEqual(self.installed(), b"newer!")

    def test_gone_and_index_checksum_does_not_match(self):
        newer = package(self.work / "newer", b"newer!")
        self.site.files["/repo/client-2.pkg.tar.zst"] = newer
        self.gone({"client-2": {"NAME": "client", "FILENAME": "client-2.pkg.tar.zst",
                                "CSIZE": len(newer), "SHA256SUM": "0" * 64}})
        with self.assertRaisesRegex(fetch_client.Stop, "checksum"):
            self.fetch()
        self.assertIsNone(self.installed())

    def test_gone_without_a_usable_index_stops(self):
        cases = {
            "no index": None,
            "no checksum": {"client-2": {"NAME": "client", "FILENAME": "client-2.pkg.tar.zst", "CSIZE": 5}},
            "same file": {"client-1": {"NAME": "client", "FILENAME": "client-1.pkg.tar.zst", "CSIZE": 5,
                                       "SHA256SUM": "0" * 64}},
            "not listed": {"other-1": {"NAME": "other", "FILENAME": "other-1.pkg.tar.zst", "CSIZE": 5,
                                       "SHA256SUM": "0" * 64}},
            "odd name": {"client-2": {"NAME": "client", "FILENAME": "../client-2.pkg.tar.zst", "CSIZE": 5,
                                      "SHA256SUM": "0" * 64}},
        }
        self.gone(None)
        for name, entries in cases.items():
            with self.subTest(name):
                if entries is not None:
                    self.site.files["/repo/index.db"] = index(entries)
                with self.assertRaisesRegex(fetch_client.Stop, "sudo dnf upgrade"):
                    self.fetch()
                self.assertIsNone(self.installed())

    def proton(self):
        """A bundle like Proton's: one top-level directory holding the tool."""
        tool = self.work / "bundle/Proton-build/files"
        tool.mkdir(parents=True)
        (tool / "wine").write_bytes(b"proton" + os.urandom(1000000))
        (tool.parent / "proton").write_text("#!/usr/bin/python3\n")
        subprocess.run(["tar", "--zstd", "-cf", self.work / "bundle.tar.zst", "-C", self.work / "bundle",
                        "Proton-build"], check=True)
        body = (self.work / "bundle.tar.zst").read_bytes()
        self.site.files["/repo/proton-1.tar.zst"] = body
        self.client = {"what": "Proton", "source": "Gravity Linux", "url": self.site.base + "proton-1.tar.zst",
                       "sha256": hashlib.sha256(body).hexdigest(), "size": len(body), "unpacked": 1000}

    def test_proton_bundle_becomes_the_tool_directory(self):
        self.proton()
        self.site.cut = 5000
        self.fetch()
        self.assertEqual(sorted(path.name for path in self.target.iterdir()), ["files", "proton"])
        self.assertEqual((self.target / "files/wine").read_bytes()[:6], b"proton")
        self.assertEqual(self.site.requests[1], ("/repo/proton-1.tar.zst", "bytes=5000-"))

    def test_proton_checksum_mismatch_is_refused(self):
        self.proton()
        self.client["sha256"] = "0" * 64
        with self.assertRaisesRegex(fetch_client.Stop, "Proton.*checksum"):
            self.fetch()
        self.assertEqual(list(self.target.iterdir()), [])

    def test_proton_gone_has_no_other_source(self):
        self.proton()
        del self.site.files["/repo/proton-1.tar.zst"]
        with self.assertRaisesRegex(fetch_client.Stop, "Proton is not on its download server"):
            self.fetch()
        self.assertEqual(self.site.requests, [("/repo/proton-1.tar.zst", None)])

    def main(self, window):
        with patch.object(fetch_client, "CLIENT", self.client), patch.object(fetch_client, "Window", return_value=window), patch.object(fetch_client.signal, "signal"):
            return fetch_client.main(["client", str(self.downloads), str(self.target)])

    def test_directory_read_only_error_uses_error_window(self):
        window = Quiet()
        with patch.object(Path, "mkdir", side_effect=OSError(errno.EROFS, "Read-only file system", str(self.downloads))):
            self.assertEqual(self.main(window), 1)
        self.assertIn(str(self.downloads), window.errors[0])
        self.assertIn("Read-only file system", window.errors[0])
        self.assertIsNone(self.installed())

    def test_full_download_directory_reports_storage_error_without_network_retry(self):
        window = Quiet()
        original = Path.open
        def full(path, *args, **kwargs):
            if path == self.part() and args and args[0] in ("wb", "ab"):
                raise OSError(errno.ENOSPC, "No space left on device", str(path))
            return original(path, *args, **kwargs)
        with patch.object(Path, "open", full):
            self.assertEqual(self.main(window), 1)
        self.assertIn("No space left on device", window.errors[0])
        self.assertIn(str(self.part()), window.errors[0])
        self.assertEqual(self.sleeps, [])
        self.assertIsNone(self.installed())

    @unittest.skipIf(os.geteuid() == 0, "root bypasses ordinary filesystem permissions")
    def test_actual_unwritable_download_directory_uses_error_window(self):
        self.downloads.mkdir()
        self.downloads.chmod(0o500)
        window = Quiet()
        try:
            self.assertEqual(self.main(window), 1)
        finally:
            self.downloads.chmod(0o700)
        self.assertIn("Permission denied", window.errors[0])
        self.assertEqual(self.sleeps, [])
        self.assertIsNone(self.installed())

    @unittest.skipIf(os.geteuid() == 0, "root bypasses ordinary filesystem permissions")
    def test_unreadable_verified_download_uses_error_window(self):
        self.downloads.mkdir()
        self.part().write_bytes(self.body)
        self.part().chmod(0)
        window = Quiet()
        try:
            self.assertEqual(self.main(window), 1)
        finally:
            self.part().chmod(0o600)
        self.assertIn("Permission denied", window.errors[0])
        self.assertIn(str(self.part()), window.errors[0])
        self.assertIsNone(self.installed())

    def test_pinned_downloads(self):
        for item in (fetch_client.CLIENT, fetch_client.PROTON):
            self.assertTrue(item["url"].startswith("https://"))
            self.assertRegex(item["sha256"], "^[0-9a-f]{64}$")
            self.assertGreater(item["unpacked"], item["size"])
        self.assertNotIn("index", fetch_client.PROTON)


if __name__ == "__main__":
    unittest.main()
