# Temporary M4 sleep policy

Release 101.gravity disables suspend, hibernation, hybrid sleep and
suspend-then-hibernate using RPM-owned vendor configuration under /usr/lib.
Logind ignores automatic idle sleep, sleep keys and lid events. Four service
drop-ins use ExecCondition=/usr/bin/false to block direct service activation.
Screen locking and display blanking are not system suspend and are unchanged.

No /etc files or masks are created by the package. Normal RPM upgrades remove
obsolete vendor files, preserving administrator configuration in /etc.

When sleep is supported, bump Release and remove the six installed policy files
and their spec install/file entries. The systemd scriptlet reloads unit state;
reboot after upgrading to refresh logind policy as well. Check for administrator
overrides if sleep remains disabled. Do not automatically remove user masks.

This is a userspace safety policy, not a security boundary against root writing
directly to kernel power-management interfaces. It applies to every machine
with this Gravity package installed until the policy is revised.

Validation: build the real spec and tools/sleep-policy-future.spec, then run
tools/test_sleep_policy.py against the resulting RPMs in a disposable Fedora
VM. The successor is only a test fixture and must never be published.
