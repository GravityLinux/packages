#!/usr/bin/sh

dnf -y -C --disablerepo=\* install /boot/efi/gravity/extras/*.rpm && \
  systemctl disable gravity-extras-firstboot.service
