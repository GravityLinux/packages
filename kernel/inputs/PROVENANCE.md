# Kernel RPM packaging inputs

These are checked-in packaging files maintained by Gravity Linux. SRPM
preparation copies them locally, applies Gravity config overlays, and creates
the kernel source archive from the explicit Git pin in sources.json.
No upstream SRPM, COPR output or packaging branch is downloaded for these files.

The initial import contains 99 files extracted from the previously cached
kernel-7.1.13-403.asahi.fc44.src.rpm. Its SHA-256 was verified before extraction:

`b21403621e44d6390c089126afb2c8ee41a9926b4bd7a840b544b39ffd15be9a`

The original source location, retained only as historical provenance, was:
https://download.copr.fedorainfracloud.org/results/@asahi/kernel/srpm-builds/10979408/kernel-7.1.13-403.asahi.fc44.src.rpm

Original file contents, copyright notices and license headers are preserved.
This import does not relicense Fedora/Red Hat/Asahi contributions. Public
verification certificates and key-generation templates are packaging inputs;
there are no private signing keys here.

Excluded from the import: the old Linux source archive, the old Red Hat source
patch and the old kernel.spec. The current kernel.spec, Gravity patches and
config fragments live one directory above. The full Linux tree supplies its own
COPYING file. Older ABI-list archives are retained for the inherited spec's
source declarations, not as a compatibility guarantee for experimental 7.3.

Future changes to config seeds and helpers should be reviewed and committed
directly here. Update the source pin separately when rebasing Linux.
