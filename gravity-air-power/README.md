# gravity-air-power

Sleep and power defaults for the M4 MacBook Air (J713). Every unit is
conditioned on the `apple,j713` device-tree compatible, so the package can be
installed on any Gravity machine (it supplements
`gravity-platform-metapackage-core`). Units are enabled by links shipped in
`/usr/lib/systemd/system/sysinit.target.wants/` or started by udev; no preset
has to be applied, and presets cannot disable them (they report "static").
Mask a unit to turn it off.

## Suspend-to-idle (`gravity-air-s2idle-default.service`)

Gravity's vendor policy (gravity-remix-scripts `90-gravity-no-sleep.conf`)
disables sleep on every board. Early in boot, on a J713 whose kernel
implements CPU power-down for s2idle
(`/sys/devices/system/cpu/cpu0/cpuidle/state1/s2idle` exists) and offers
`s2idle` in `/sys/power/mem_sleep`, this writes three runtime overrides:

- `/run/systemd/logind.conf.d/99-gravity-air-s2idle.conf`: lid (also docked)
  and suspend key suspend.
- `/run/systemd/sleep.conf.d/99-gravity-air-s2idle.conf`: `AllowSuspend=yes`,
  s2idle only.
- `/run/systemd/system/systemd-suspend.service.d/99-gravity-air-s2idle.conf`:
  replaces the vendor `ExecCondition=/usr/bin/false` with
  `gravity-air-s2idle-default --check`, which passes only while this policy
  is in effect.

`/run` restorecon labels are applied so the confined systemd-sleep can read
them. Older kernels and other boards keep the no-sleep policy. The kernel
argument `gravity.air_s2idle=0` keeps it for one boot. The earlier lab flag
`gravity.air_s2idle=1` is no longer needed and is ignored. KDE PowerDevil
picks sleep as its lid action when logind reports that suspend is possible.

## USB4 links (`gravity-usb4-sleep-inhibit@.service`)

The Apple ACIO driver refuses system sleep while a USB4/Thunderbolt link is
up (`apple_cio_prepare()` returns -EBUSY), which is intended. Each refused
attempt still freezes and thaws userspace and makes NetworkManager drop
Wi-Fi, and PowerDevil suspends again 10 s after every "resume" while the lid
is closed, so a closed Air with a USB4 SSD retried all night.

The ACIO registers its NHI's USB4 domain only while it has a link, so
`90-gravity-usb4-sleep-inhibit.rules` starts one instance per
`thunderbolt_domain` device, bound to it (`BindsTo=`). While the s2idle
policy is active, the instance holds

    systemd-inhibit --what=sleep:handle-lid-switch --mode=block --who=USB4 --why="USB4 device connected"

- `sleep` (block): logind (systemd 259) rejects suspend requests outright,
  without a polkit prompt, so PowerDevil's lid close and idle suspend fail
  before anything is frozen. PowerDevil and Plasma list the reason.
- `handle-lid-switch`: logind itself ignores the lid while the link is up.
  It handles the lid when no desktop does (e.g. at the login screen), and
  its default `LidSwitchIgnoreInhibited=yes` would otherwise ignore the
  sleep block and keep retrying suspend.

When the domain goes away, `gravity-usb4-sleep-release` re-applies the
closed-lid action: logind re-checks a closed lid by itself once nothing
inhibits it, but PowerDevil only acts on lid changes. If the lid is still
closed, nothing else blocks sleep, and PowerDevil's lid action is sleep (and
no external monitor suppresses it), it asks PowerDevil to suspend. It
queries PowerDevil as the inhibitor's user, connected straight to that
user's session bus socket (`/run/user/UID/bus`), not with
`busctl --machine=USER@`, which starts a transient system unit and PAM login
session through systemd-run for every call. A busctl failure is logged
with busctl's error output. A stop
while the domain still exists (a restart, `systemctl stop`, a synthetic
udev event) or during shutdown does nothing. `--dry-run PATH` prints the
decision.

While the lid is closed with a USB4 device attached, the Air stays awake with
the panel off. The session is not locked by the refused suspend; Plasma's
idle lock still applies.

## cpufreq boost (`gravity-air-cpufreq-default.service`)

Before sysinit and the desktop, sets `/sys/devices/system/cpu/cpufreq/boost`
to 0 on the fanless J713. Turbo stays available through the same switch at
runtime. A missing or unwritable switch fails the unit rather than silently
keeping a different default.

## Wi-Fi lid standby (`gravity-lid-wifi.service`)

Started by udev for the Apple SMC input device with SW_LID. Sets brcmfmac
power management to PM_MAX (1) when the lid closes and PM_FAST (2) when it
opens, from cached evdev state with no polling. The NetworkManager
dispatcher script re-applies the mode after a reconnect. It never suspends.
`/etc/default/gravity-lid-wifi` can set `GRAVITY_LID_WIFI_INTERFACE`
(default `wld0`) and `GRAVITY_LID_WIFI_CLOSED_MODE` (`max` or `fast`).
Measured on the Air in the no-sleep configuration: −29.7 mW with the lid
closed. With s2idle it matters when the lid is closed and the Air stays
awake (USB4 attached, external display).

## Not included

The lab installer in `../lid-wifi-standby/` also wrote
`/etc/systemd/logind.conf.d/90-gravity-no-sleep.conf` (vendor file without
`HandleLidSwitchExternalPower=`, so logind doesn't read the AC state on
every pass while the lid is closed), the PowerDevil `POWERDEVIL_NO_DDCUTIL`
drop-in (which would apply to every board), the legacy FEX server mask and
its backup/rollback tooling. Those are lab or vendor-package changes, not
part of this package.

## Building

    make check
    rpmbuild -ba --define "_sourcedir $PWD" gravity-air-power.spec

with `gravity-air-power-20261104.tar.gz` holding this directory as
`gravity-air-power-20261104/`.
