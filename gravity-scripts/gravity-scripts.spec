Name:           gravity-scripts
Vendor:         Gravity Linux
Version:        20260915
Release:        101.gravity%{?dist}
Summary:        Miscellaneous admin scripts for Gravity Linux

License:        MIT
URL:            https://github.com/GravityLinux/scripts
Source0:        %{name}-%{version}.tar.gz
Source:         update-m1n1.sysconfig
Source2:        15-update-m1n1.install

Patch02:        0002-fedora-update-m1n1-handle-dangling-boot-dtb-symlinks.patch

BuildArch:      noarch
Conflicts:      asahi-scripts

BuildRequires:  make
BuildRequires:  sed
BuildRequires:  systemd-rpm-macros

Requires:       bash
Requires:       coreutils
Requires:       grep
Requires:       sed
Requires:       systemd-udev
Requires:       util-linux-core

%description
This package contains miscellaneous admin scripts for Gravity Linux.

%package -n     gravity-fwupdate
Summary:        Gravity Linux firmware extractor

Requires:       %{name} = %{version}-%{release}
# Not using python3dist(gravity-firmware) because its version is fixed
Requires:       python3-gravity_firmware >= 0.9.1

%description -n gravity-fwupdate
Gravity Linux firmware updater.

%package -n     dracut-gravity
Summary:        Dracut config for Apple Silicon Macs

Requires:       dracut
Requires:       linux-firmware-vendor = %{version}-%{release}

%description -n dracut-gravity
Dracut config for Apple Silicon Macs.

%package -n     linux-firmware-vendor
Summary:        Ensure /lib/firmware/vendor exists for firmware handoff
Requires:       linux-firmware

%description -n linux-firmware-vendor
This package ensures /lib/firmware/vendor exists so that firmware can be handed
over properly from the initramfs.

%package -n     update-m1n1
Summary:        Keep m1n1 up to date

Requires:       %{name} = %{version}-%{release}
Requires:       bash
Requires:       gzip
Requires:       bootloader
Requires:       uboot-images-armv8
# grubby's /usr/lib/kernel/install.d/10-devicetree.install creates the
# /boot/dtb symlink update-m1n1 uses to construct the 2nd stage m1n1 image
Requires:       grubby

%description -n update-m1n1
Keep m1n1 up to date on Apple Silicon systems.

%package -n     gravity-battery
Summary:        Gravity Linux battery charge control scripts

Requires:       %{name} = %{version}-%{release}
Requires:       systemd
Requires:       systemd-udev

%description -n gravity-battery
Gravity Linux battery charge control scripts restore charge_control_end_threshold
on system start.

%prep
%autosetup -p1

%build
# nothing to do here

%install
%make_install install-fedora \
  PREFIX="%{_prefix}" \
  BIN_DIR="%{_sbindir}" \
  CONFIG_DIR="%{_sysconfdir}/sysconfig"

install -Ddpm0755 %{buildroot}%{_prefix}/lib/firmware/vendor
install -Dpm0644 %SOURCE1 %{buildroot}%{_sysconfdir}/sysconfig/update-m1n1
# Install kernel-install script
install -Dpm0755 -t %{buildroot}%{_kernel_install_dir} %{SOURCE2}

%transfiletriggerin -n gravity-fwupdate -- %{_sbindir}/gravity-fwupdate %{_bindir}/gravity-fwextract
%{_sbindir}/gravity-fwupdate || :

# This needs to be a separate trigger because we can't use python3_sitearch here
%transfiletriggerin -n gravity-fwupdate -- /usr/lib/python
grep -q 'gravity_firmware' && %{_sbindir}/gravity-fwupdate || :

# We can't use _libdir here because it gets incorrectly expanded to /usr/lib
%transfiletriggerin -n update-m1n1 -- /usr/lib/m1n1 /usr/lib64/m1n1 /usr/share/uboot/apple_m1 /etc/m1n1.conf
%{_sbindir}/update-m1n1 || :

%files
%license LICENSE
%{_datadir}/%{name}/
%{_sbindir}/gravity-diagnose
%{_udevhwdbdir}/65-autosuspend-override-gravity-sdhci.hwdb

%files -n gravity-fwupdate
%license LICENSE
%{_sbindir}/gravity-fwupdate

%files -n dracut-gravity
%license LICENSE
%{_prefix}/lib/dracut/dracut.conf.d/10-gravity.conf
%{_prefix}/lib/dracut/modules.d/91kernel-modules-gravity/
%{_prefix}/lib/dracut/modules.d/99gravity-firmware/

%files -n linux-firmware-vendor
%license LICENSE
%dir %{_prefix}/lib/firmware/vendor

%files -n update-m1n1
%license LICENSE
%config(noreplace) %{_sysconfdir}/sysconfig/update-m1n1
%{_kernel_install_dir}/15-update-m1n1.install
%{_sbindir}/update-m1n1

%files -n gravity-battery
%{_unitdir}/macsmc-battery-charge-control-end-threshold.path
%{_unitdir}/macsmc-battery-charge-control-end-threshold.service
%{_udevrulesdir}/93-macsmc-battery-charge-control.rules
%ghost %config(noreplace) %{_sysconfdir}/udev/macsmc-battery.conf

%changelog
* Tue Sep 15 2026 Gravity Linux maintainers - 20260915-101.gravity
- Depend on the renamed bootloader package and update diagnostics

* Tue Sep 15 2026 Gravity Linux maintainers - 20260915-100.gravity
- Package Gravity firmware consumers and retain Fedora integration
