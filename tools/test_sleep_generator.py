#!/usr/bin/env python3
"""Run gravity-sleep-generator against fake machines (no root needed).

Usage: python3 tools/test_sleep_generator.py
"""
import os
from pathlib import Path
import subprocess
import tempfile

GENERATOR = Path(__file__).resolve().parents[1] / 'gravity-remix-scripts' / 'gravity-sleep-generator'
TARGETS = {'suspend.target', 'hibernate.target', 'hybrid-sleep.target', 'suspend-then-hibernate.target'}


def generate(compatible, s2idle_hook):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / 'root'
        out = Path(directory) / 'out'
        out.mkdir()
        if compatible is not None:
            dt = root / 'proc/device-tree'
            dt.mkdir(parents=True)
            (dt / 'compatible').write_bytes(b''.join(c.encode() + b'\0' for c in compatible))
        state = root / 'sys/devices/system/cpu/cpu0/cpuidle/state1'
        state.mkdir(parents=True)
        if s2idle_hook:
            (state / 's2idle').mkdir()
        env = dict(os.environ, GRAVITY_SLEEP_SYSROOT=str(root))
        subprocess.run(['sh', str(GENERATOR), str(out), str(out), str(out)], env=env, check=True)
        masks = {p.name for p in out.iterdir()}
        assert all(os.readlink(out / name) == '/dev/null' for name in masks)
        return masks


air = ['apple,j713', 'apple,t8132', 'apple,arm-platform']
mini = ['apple,j773g', 'apple,t8132', 'apple,arm-platform']
assert generate(air, True) == set(), 'J713 with the CPU s2idle hook may sleep'
assert generate(air, False) == TARGETS, 'J713 without the hook must not sleep'
assert generate(mini, True) == TARGETS, 'J773g must not sleep'
assert generate(['apple,j713x', 'apple,t8132'], True) == TARGETS, 'compatible must match exactly'
assert generate(None, True) == TARGETS, 'no device tree: no sleep'
print('PASS: gravity-sleep-generator allows sleep only on J713 with the CPU s2idle hook')
