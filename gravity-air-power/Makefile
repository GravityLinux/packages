PREFIX ?= /usr
LIBEXECDIR ?= $(PREFIX)/libexec
UNITDIR ?= $(PREFIX)/lib/systemd/system
UDEVRULESDIR ?= $(PREFIX)/lib/udev/rules.d
NMDISPATCHERDIR ?= $(PREFIX)/lib/NetworkManager/dispatcher.d

BIN = gravity-air-s2idle-default gravity-air-cpufreq-default gravity-lid-wifi gravity-usb4-sleep-release
UNITS = gravity-air-s2idle-default.service gravity-air-cpufreq-default.service gravity-lid-wifi.service \
	gravity-usb4-sleep-inhibit@.service
RULES = 90-gravity-lid-wifi.rules 90-gravity-usb4-sleep-inhibit.rules
# Enabled by these vendor links (no [Install]: presets and "systemctl disable"
# leave them alone; mask a unit or boot with gravity.air_s2idle=0 instead).
SYSINIT_WANTS = gravity-air-s2idle-default.service gravity-air-cpufreq-default.service

all:

check:
	python3 -I tests/test_policy.py

install:
	for f in $(BIN); do install -Dm755 $$f $(DESTDIR)$(LIBEXECDIR)/$$f; done
	for f in $(UNITS); do install -Dm644 $$f $(DESTDIR)$(UNITDIR)/$$f; done
	for f in $(RULES); do install -Dm644 $$f $(DESTDIR)$(UDEVRULESDIR)/$$f; done
	install -Dm755 90-gravity-lid-wifi-dispatcher $(DESTDIR)$(NMDISPATCHERDIR)/90-gravity-lid-wifi
	mkdir -p $(DESTDIR)$(UNITDIR)/sysinit.target.wants
	for f in $(SYSINIT_WANTS); do ln -sf ../$$f $(DESTDIR)$(UNITDIR)/sysinit.target.wants/$$f; done

.PHONY: all check install
