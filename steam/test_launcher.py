# SPDX-License-Identifier: MIT
"""Launcher process/lock checks in a throwaway HOME; no real Steam or account."""
import os
from pathlib import Path
import subprocess
import time
import tempfile
import unittest


class Launcher(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.work = Path(self.temporary.name)
        self.home = self.work / 'home'
        self.data = self.home / '.local/share'
        self.root = self.data / 'Steam'
        self.libexec = self.work / 'libexec'
        self.bindir = self.work / 'bin'
        for p in [self.home / '.steam', self.data, self.libexec, self.bindir]:
            p.mkdir(parents=True, exist_ok=True)
        self.env = dict(os.environ, HOME=str(self.home), XDG_DATA_HOME=str(self.data),
                        PATH=str(self.bindir) + ':' + os.environ['PATH'], DISPLAY=':fixture', WAYLAND_DISPLAY='',
                        TEST_WORK=str(self.work))
        self.command(self.bindir / 'id', '#!/bin/sh\necho 1000\n')
        self.command(self.bindir / 'getconf', '#!/bin/sh\necho 4096\n')
        self.command(self.bindir / 'pgrep', '#!/bin/sh\nexit 1\n')
        self.command(self.bindir / 'zenity', '#!/bin/sh\nprintf "%s\\n" "$@" >> "$TEST_WORK/dialogs"\n')
        self.command(self.libexec / 'fetch-client', '#!/bin/sh\necho unexpected-download >> "$TEST_WORK/fetched"\nexit 1\n')
        text = Path(__file__).with_name('steam-launch').read_text()
        text = text.replace('/usr/libexec/steam-gravity', str(self.libexec))
        text = text.replace('/usr/share/steam-gravity', str(self.work / 'share'))
        text = text.replace('/opt/steam-gravity', str(self.work / 'legacy'))
        self.launcher = self.work / 'steam-launch'
        self.command(self.launcher, text)

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def command(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        path.chmod(0o755)

    def launch(self):
        return subprocess.run(['bash', str(self.launcher)], env=self.env, capture_output=True, text=True, timeout=10)

    def assert_error(self, result, text):
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(text, result.stderr)
        self.assertIn('--error', (self.work / 'dialogs').read_text())
        self.assertFalse((self.work / 'fetched').exists())

    def test_lock_open_failure_preserves_active_staging(self):
        (self.home / '.steam/.bootstrap.lock').mkdir()
        stage = self.data / '.steam-bootstrap-keep'
        stage.mkdir()
        (stage / 'active').write_text('untouched')
        self.assert_error(self.launch(), 'Cannot open the Steam setup lock')
        self.assertEqual((stage / 'active').read_text(), 'untouched')

    def test_proton_lock_acquisition_failure_preserves_staging(self):
        self.command(self.root / 'steamrtarm64/steam', '#!/bin/sh\nexit 0\n')
        stage = self.data / 'steam-gravity/compatibilitytools.d/.proton-keep'
        stage.mkdir(parents=True)
        (stage / 'active').write_text('untouched')
        self.command(self.bindir / 'flock', '#!/bin/sh\nexit 42\n')
        self.assert_error(self.launch(), 'Cannot acquire the Steam setup lock')
        self.assertEqual((stage / 'active').read_text(), 'untouched')

    def test_unwritable_directory_reports_error_before_setup(self):
        # ENOTDIR is deterministic even if an RPM builder runs %check as root.
        self.env['XDG_DATA_HOME'] = str(self.work / 'not-a-directory')
        (self.work / 'not-a-directory').write_text('occupied')
        self.assert_error(self.launch(), 'Cannot create the Steam directories')

    def test_two_starts_seed_once_through_delayed_client_handoff(self):
        self.command(self.bindir / 'pgrep', """#!/usr/bin/python3
import os, pathlib, sys
p = pathlib.Path(os.environ['TEST_WORK']) / 'running'
try:
    os.kill(int(p.read_text()), 0)
except (OSError, ValueError):
    sys.exit(1)
""")
        self.command(self.libexec / 'seed-compat', """#!/usr/bin/python3
import os, pathlib, sys, time
w = pathlib.Path(os.environ['TEST_WORK'])
with (w / 'seed-count').open('a') as f: f.write('seed\n')
p = pathlib.Path(sys.argv[1]); old = p.read_text()
(w / 'seed-reading').touch()
time.sleep(0.3)
p.write_text(old + 'seeded\n')
""")
        self.command(self.root / 'steamrtarm64/steam', """#!/usr/bin/python3
import os, pathlib, time
w = pathlib.Path(os.environ['TEST_WORK'])
# Stay alive but invisible to the launcher's process check during startup.
time.sleep(0.3)
try:
    os.kill(int((w / 'running').read_text()), 0)
except (OSError, ValueError):
    (w / 'running').write_text(str(os.getpid()))
    p = pathlib.Path(os.environ['XDG_DATA_HOME']) / 'Steam/config/config.vdf'
    p.write_text(p.read_text() + 'newer-client-setting\n')
    time.sleep(1)
with (w / 'launch-count').open('a') as f: f.write('start\n')
""")
        config = self.root / 'config/config.vdf'
        config.parent.mkdir(parents=True)
        config.write_text('original\n')
        tools = self.data / 'steam-gravity/compatibilitytools.d/proton-gravity-arm64'
        tools.mkdir(parents=True)
        (tools / 'compatibilitytool.vdf').touch()
        first = subprocess.Popen(['bash', str(self.launcher)], env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        second = None
        try:
            deadline = time.monotonic() + 5
            while not (self.work / 'seed-reading').exists():
                self.assertIsNone(first.poll())
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.01)
            second = subprocess.Popen(['bash', str(self.launcher)], env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for process in [first, second]:
                _, err = process.communicate(timeout=8)
                self.assertEqual(process.returncode, 0, err)
            self.assertEqual((self.work / 'seed-count').read_text(), 'seed\n')
            self.assertEqual((self.work / 'launch-count').read_text(), 'start\nstart\n')
            self.assertEqual(config.read_text(), 'original\nseeded\nnewer-client-setting\n')
        finally:
            for process in [first, second]:
                if process is not None and process.poll() is None:
                    process.kill()
                    process.communicate()


if __name__ == '__main__':
    unittest.main()
