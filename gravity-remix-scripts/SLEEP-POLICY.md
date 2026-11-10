# Sleep policy

Gravity machines use systemd's and the desktop's default sleep policy where
suspend-to-idle (s2idle) works, and cannot sleep anywhere else. Real
macOS-style deep sleep is not attempted; the kernel offers s2idle only.

## Where it is decided

`/usr/lib/systemd/system-generators/gravity-sleep-generator` runs at boot and
on every `systemctl daemon-reload`. Suspend-to-idle is supported when both
hold:

- the board's drivers keep storage, USB and Bluetooth working across s2idle:
  the device tree is `apple,j713` (MacBook Air M4);
- the running kernel's CPU idle driver powers CPUs down in s2idle: a
  `/sys/devices/system/cpu/cpu0/cpuidle/state*/s2idle` directory exists.
  Without it s2idle would idle the CPUs in a state that loses their
  registers. Kernels without the driver, or booted with
  `cpuidle_apple_m4.enable=0`, are unsupported.

On a supported machine the generator does nothing. Nothing else in Gravity
changes the sleep configuration: lid close, the suspend key and idle sleep
follow systemd-logind and KDE PowerDevil defaults.

Everywhere else it masks `suspend.target`, `hibernate.target`,
`hybrid-sleep.target` and `suspend-then-hibernate.target` in
`/run/systemd/generator`, which is what the `systemd.mask=` kernel argument
does. logind then answers `CanSuspend` with `no`, desktops do not offer
sleep, and requests (`systemctl suspend`, the suspend key) are refused with
"Unit suspend.target is masked" before anything is frozen. Hibernation is
also unavailable because the kernel reports it disabled.

The Mac mini M4 (J773g) is unsupported for now. The kernel keeps its USB
controllers, NVMe and Bluetooth on the cold-restart resume paths (the
retention used on J713 is board-gated), and after a full device and
platform suspend cycle the internal USB hub's xHCI controller stops
responding, so USB hot-plug hangs and every later suspend fails to freeze
tasks. A connected USB4 device also makes the kernel refuse to suspend.

## USB4 links (temporary)

The kernel's Apple USB4 driver refuses system sleep while a USB4 or
Thunderbolt link is up. Each refused attempt still freezes and thaws
userspace and drops Wi-Fi, and the desktop retries while the lid stays
closed. Until the driver suspends with a link up,
`90-gravity-usb4-sleep-inhibit.rules` starts
`gravity-usb4-sleep-inhibit@.service` for each USB4 domain, which holds a
logind `sleep:handle-lid-switch` block while the link exists. With a USB4
device attached and the lid closed, the Air stays awake with the panel off;
after unplugging, close the lid again to sleep.

## Overrides

- Allow sleep on every machine: `ln -s /dev/null
  /etc/systemd/system-generators/gravity-sleep-generator`, then reboot.
- Block sleep on a supported machine: `systemctl mask suspend.target`.

Both are ordinary administrator configuration in /etc; the package never
writes to /etc or /run itself.

## History

Releases 101 to 105 blocked sleep on every machine with vendor files under
/usr/lib (`90-gravity-no-sleep.conf` in sleep.conf.d and logind.conf.d and
`ExecCondition=/usr/bin/false` drop-ins on the four sleep services). RPM
removes them on upgrade. The unreleased gravity-air-power package, which
re-enabled sleep on the Air with runtime overrides, is obsoleted.
logind reads its configuration at start, so the lid and key defaults apply
after the next reboot.
