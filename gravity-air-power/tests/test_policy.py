#!/usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Niklas Sheth
"""Host checks: board/kernel gates, the cmdline opt-out and unit wiring."""
import configparser, importlib.machinery, importlib.util, tempfile
from pathlib import Path

src = Path(__file__).resolve().parent.parent


def load(name):
    loader = importlib.machinery.SourceFileLoader(name.replace('-', '_'), str(src / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


def unit(name):
    c = configparser.ConfigParser(strict=False, interpolation=None)
    c.optionxform = str
    c.read_string((src / name).read_text())
    return c


m = load('gravity-air-s2idle-default')
assert all(p.startswith('/run/') for p in m.FILES)
assert m.SERVICE.count('ExecCondition=') == 2 and '--check' in m.SERVICE
with tempfile.TemporaryDirectory() as d:
    r = Path(d)

    def write(p, v):
        q = r / p.lstrip('/')
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_bytes(v if isinstance(v, bytes) else v.encode())

    assert not m.eligible(r)
    write('/proc/device-tree/compatible', b'apple,j713\0apple,t8132\0apple,arm-platform\0')
    write('/proc/cmdline', 'root=UUID=x rw tick_broadcast_hrtimer.cpu=1')
    write('/sys/devices/system/cpu/cpu0/cpuidle/state1/s2idle/usage', '0')
    write('/sys/power/mem_sleep', '[s2idle]')
    assert m.eligible(r), 'J713 + kernel s2idle needs no cmdline flag'
    assert not m.active(r), 'not active before the overrides are written'
    write(m.SLEEP_FILE, m.SLEEP)
    assert m.active(r)
    write(m.SLEEP_FILE, '[Sleep]\nAllowSuspend=no\n')
    assert not m.active(r), 'a foreign sleep file is not ours'
    write(m.SLEEP_FILE, m.SLEEP)
    write('/proc/cmdline', 'root=UUID=x rw gravity.air_s2idle=0')
    assert not m.eligible(r) and not m.active(r), 'gravity.air_s2idle=0 opts out'
    write('/proc/cmdline', 'root=UUID=x rw gravity.air_s2idle=1')
    assert m.eligible(r)
    write('/proc/device-tree/compatible', b'apple,j773g\0apple,t8132\0apple,arm-platform\0')
    assert not m.eligible(r), 'the mini keeps the no-sleep policy'
    write('/proc/device-tree/compatible', b'apple,j713x\0apple,t8132\0')
    assert not m.eligible(r), 'whole compatible strings only'
    write('/proc/device-tree/compatible', b'apple,j713\0apple,t8132\0')
    write('/sys/power/mem_sleep', 'deep')
    assert not m.eligible(r)
    write('/sys/power/mem_sleep', '[s2idle]')
    (r / 'sys/devices/system/cpu/cpu0/cpuidle/state1/s2idle/usage').unlink()
    assert not m.eligible(r), 'kernels without CPU s2idle support keep no-sleep'

s = unit('gravity-air-s2idle-default.service')
assert s['Unit']['ConditionFirmware'] == 'device-tree-compatible(apple,j713)'
assert s['Unit']['ConditionKernelCommandLine'] == '!gravity.air_s2idle=0'
assert s['Service']['ExecCondition'].endswith('--eligible')
for name in ['gravity-air-s2idle-default.service', 'gravity-air-cpufreq-default.service']:
    assert not unit(name).has_section('Install'), name + ': enabled by the shipped wants link only'
for name in ['gravity-air-cpufreq-default.service', 'gravity-lid-wifi.service']:
    assert unit(name)['Unit']['ConditionFirmware'] == 'device-tree-compatible(apple,j713)', name

i = unit('gravity-usb4-sleep-inhibit@.service')
assert i['Unit']['BindsTo'] == '%i.device'
assert i['Service']['ExecCondition'].endswith('--check'), 'only while the s2idle policy is active'
start = i['Service']['ExecStart']
assert '--what=sleep:handle-lid-switch' in start and '--mode=block' in start
assert i['Service']['ExecStopPost'].endswith(' %f')
rule = (src / '90-gravity-usb4-sleep-inhibit.rules').read_text()
assert 'ENV{DEVTYPE}=="thunderbolt_domain"' in rule
assert 'ENV{SYSTEMD_WANTS}+="gravity-usb4-sleep-inhibit@.service"' in rule

mk = (src / 'Makefile').read_text()
spec = (src / 'gravity-air-power.spec').read_text()
for f in ['gravity-air-s2idle-default', 'gravity-air-cpufreq-default', 'gravity-lid-wifi',
          'gravity-usb4-sleep-release', 'gravity-usb4-sleep-inhibit@.service',
          '90-gravity-usb4-sleep-inhibit.rules', '90-gravity-lid-wifi.rules']:
    assert f in mk and f in spec, f

rel = load('gravity-usb4-sleep-release')
assert rel.main(['--dry-run', str(src)]) == 0, 'an existing domain path is a no-op'
assert rel.main([]) == 2
# PowerDevil is queried as its user on the session bus socket, not through
# systemd-run (busctl --machine), and a busctl failure reports its stderr.
seen = {}


def fake_run(cmd, **kw):
    seen.update(kw, cmd=cmd)
    return rel.subprocess.CompletedProcess(cmd, 1, '', 'Call failed: boom\n')


real_run, rel.subprocess.run = rel.subprocess.run, fake_run
pw = rel.pwd.struct_passwd(('u', 'x', 1234, 1234, '', '/', '/bin/sh'))
rel.os.getgrouplist = lambda name, gid: [gid]
try:
    rel.busctl('call', 'a', '/b', 'c', 'd', user=pw)
    raise AssertionError('busctl failure not raised')
except rel.subprocess.CalledProcessError as e:
    assert 'Call failed: boom' in rel.describe(e) and 'status 1' in rel.describe(e)
rel.subprocess.run = real_run
assert not any(a.startswith('--machine') for a in seen['cmd']) and '--user' in seen['cmd']
assert seen['user'] == 1234 and seen['group'] == 1234 and seen['extra_groups'] == [1234]
assert seen['env']['DBUS_SESSION_BUS_ADDRESS'] == 'unix:path=/run/user/1234/bus'
print('PASS: J713+s2idle only, no cmdline flag needed, =0 opts out, units board-keyed, USB4 block wired')
