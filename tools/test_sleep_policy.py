"""Check real RPM payload install/removal in an isolated root (run as root).

Usage: python3 tools/test_sleep_policy.py policy.rpm future-without-policy.rpm
No package scriptlets run and no host policy is changed.
Use a disposable Fedora VM with SELinux permissive for the temporary RPM DB;
restore its previous enforcement state afterward.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory(prefix='gravity-policy-test-') as directory:
    root = Path(directory)
    def rpm(*args):
        subprocess.run(['rpm', '--root', str(root), '--dbpath', '/usr/lib/sysimage/rpm', '--nodeps', '--noscripts', *args], check=True)
    db = root / 'usr/lib/sysimage/rpm'
    db.mkdir(parents=True)
    subprocess.run(['rpmdb', '--dbpath', str(db), '--initdb'], check=True)
    rpm('-i', str(Path(sys.argv[1]).resolve()))
    policy = list((root / 'usr/lib/systemd').rglob('90-gravity-no-sleep.conf'))
    assert len(policy) == 6, policy
    for path in policy:
        assert path.stat().st_mode & 0o777 == 0o644
    sleep = root / 'usr/lib/systemd/sleep.conf.d/90-gravity-no-sleep.conf'
    for key in ('AllowSuspend', 'AllowHibernation', 'AllowHybridSleep', 'AllowSuspendThenHibernate'):
        assert f'{key}=no' in sleep.read_text()
    assert not (root / 'etc').exists(), 'Package must not install /etc masks or config'
    admin = root / 'etc/systemd/sleep.conf.d/99-admin.conf'
    admin.parent.mkdir(parents=True)
    admin.write_text('[Sleep]\nAllowSuspend=no\n')
    rpm('-U', str(Path(sys.argv[2]).resolve()))
    assert all(not path.exists() for path in policy)
    assert admin.read_text() == '[Sleep]\nAllowSuspend=no\n'
    print('PASS: six policy files installed, removed on upgrade, administrator override preserved')
