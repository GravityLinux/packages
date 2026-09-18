# Test-only successor: exercises removal of obsolete RPM-owned vendor files.
Name: gravity-remix-scripts
Version: 20260915
Release: 102.test
Summary: Test fixture for retiring the sleep policy
License: MIT
BuildArch: noarch
%description
Isolated upgrade test fixture. Never publish this RPM.
%install
install -d %{buildroot}/usr/share/gravity-policy-test
touch %{buildroot}/usr/share/gravity-policy-test/marker
%files
/usr/share/gravity-policy-test
