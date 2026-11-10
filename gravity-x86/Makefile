CC ?= cc
CFLAGS ?= -O2 -g -Wall -Wextra -Werror
LDFLAGS ?=
PREFIX ?= /usr
LIBEXECDIR ?= $(PREFIX)/libexec
BINFMTDIR ?= $(PREFIX)/lib/binfmt.d
DATADIR ?= $(PREFIX)/share
UNITDIR ?= $(PREFIX)/lib/systemd/system

all: fex-4k

fex-4k: fex-4k.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ $< $(LDFLAGS)

install: all
	install -Dm755 fex-4k $(DESTDIR)$(LIBEXECDIR)/gravity-x86/fex-4k
	install -Dm644 zzz-gravity-x86-x86.conf $(DESTDIR)$(BINFMTDIR)/zzz-gravity-x86-x86.conf
	install -Dm644 zzz-gravity-x86-x86_64.conf $(DESTDIR)$(BINFMTDIR)/zzz-gravity-x86-x86_64.conf
	install -Dm644 Config.json $(DESTDIR)$(DATADIR)/fex-emu/Config.json
	install -Dm644 gravity-x86-rootfs.service $(DESTDIR)$(UNITDIR)/gravity-x86-rootfs.service
	mkdir -p $(DESTDIR)$(UNITDIR)/multi-user.target.wants
	ln -sf ../gravity-x86-rootfs.service $(DESTDIR)$(UNITDIR)/multi-user.target.wants/gravity-x86-rootfs.service

clean:
	rm -f fex-4k

.PHONY: all install clean
