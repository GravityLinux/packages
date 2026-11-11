"""Exercise package activation and model matching without a device or live udev."""
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'gravity-remix-scripts'


class RestartGuard(unittest.TestCase):
    def refresh(self, live=True, reload_ok=True):
        spec = (ROOT / 'gravity-remix-scripts.spec').read_text()
        start = spec.index('# Apply the restart guard')
        end = spec.index('# End of the restart guard refresh.')
        code = spec[start:end]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sock = socket.socket(socket.AF_UNIX)
            if live:
                sock.bind(str(root / 'control'))
            self.addCleanup(sock.close)
            binary = root / 'udevadm'
            binary.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$RESTART_LOG"\n' +
                              ('[ "$1" != control ] || exit 1\n' if not reload_ok else ''))
            binary.chmod(0o755)
            env = dict(os.environ, PATH=str(root) + ':' + os.environ['PATH'], RESTART_LOG=str(root / 'calls'))
            subprocess.run(['sh', '-c', code.replace('/run/udev/control', str(root / 'control'))], env=env, check=True)
            return (root / 'calls').read_text().splitlines() if (root / 'calls').exists() else []

    def test_live_upgrade_reloads_triggers_exact_device_then_settles(self):
        self.assertEqual(self.refresh(), ['control --reload-rules',
            'trigger --action=bind --subsystem-match=platform --sysname-match=macsmc-reboot',
            'settle --timeout=10'])

    def test_image_without_udev_control_socket_does_not_trigger(self):
        self.assertEqual(self.refresh(live=False), [])

    def test_reload_failure_does_not_trigger_old_rules(self):
        self.assertEqual(self.refresh(reload_ok=False), ['control --reload-rules'])

    def test_helper_unbinds_only_air_models_without_the_reset_line(self):
        source = (ROOT / 'smc-restart-quirk').read_text()
        for model, reset, expected in [('apple,j713', False, True), ('apple,j715', False, True),
                                       ('apple,j713', True, False), ('apple,j773g', False, False),
                                       ('apple,j713x', False, False), (None, False, False)]:
            with self.subTest(model=model, reset=reset), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                touch = root / 'soc' / 'mtp' / 'multi-touch'
                touch.mkdir(parents=True)
                if reset:
                    (touch / 'reset-gpios').touch()
                if model is not None:
                    (root / 'compatible').write_bytes(model.encode() + b'\0apple,t8132\0')
                driver = root / 'driver'
                driver.mkdir()
                (driver / 'macsmc-reboot').touch()
                (driver / 'unbind').touch()
                code = source.replace('dt=/proc/device-tree', 'dt=' + str(root))
                code = code.replace('/sys/bus/platform/drivers/macsmc-reboot', str(driver))
                code = code.replace('/dev/kmsg', str(root / 'kmsg'))
                subprocess.run(['sh', '-c', code], check=True, capture_output=True)
                self.assertEqual((driver / 'unbind').read_text(), 'macsmc-reboot\n' if expected else '')


if __name__ == '__main__':
    unittest.main()
