# SPDX-License-Identifier: MIT
"""Launcher process/lock checks in a throwaway HOME; no real Steam or account."""
import os
from pathlib import Path
import subprocess
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


if __name__ == '__main__':
    unittest.main()
