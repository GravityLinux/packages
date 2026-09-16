# Downstream speaker protection packaging

Source RPM / COPR package: `rust-speakersafetyd`.
Binary RPM, executable and service: `speakersafetyd`.
COPR spec path: `rust-speakersafetyd/rust-speakersafetyd.spec` in GravityLinux/packages.

This is a preparation scaffold, not a validated M4 build. `sources.json` has no
source pin, so the shared builder intentionally refuses to build it. The URL
`https://github.com/GravityLinux/speakersafetyd.git` is the proposed publication
location and needs confirmation; the fork was not publicly accessible when this
recipe was prepared. Version 2.0.1 is inherited from Fedora, not an assertion
about the downstream fork's version.

## Before enabling builds

1. Confirm the actual fork URL and select a full Git commit hash. A tag is not
   required. Align spec Version and the archive/root names with Cargo.toml.
2. Review the fork's license and Cargo dependency changes. Regenerate the binary
   License expression from its actual dependency set if necessary.
3. Reconcile the Fedora 44 patches. Its crate-metadata patch relaxes alsa to
   >=0.10,<0.12 and signal-hook to >=0.4.3,<0.5. That patch targets normalized
   crates.io Cargo.toml, so it cannot simply be applied to a Git snapshot.
   Verify supported APIs before relaxing requirements. Its other patch fixes
   j504 speaker names; retain that fix if the fork does not already include it.
4. Confirm the fork still supplies the binary, service, udev rules and
   conf/apple directory used by this spec; adapt file lists for any new layout.
5. Build in fedora-44-aarch64 and run the Rust tests. Check the generated
   LICENSE.dependencies and installed model profiles.

## Release safety and related packages

This recipe provides `gravity-speakersafetyd`. The audio metapackage requires
that capability as well as speakersafetyd, preventing stock Fedora's daemon
from silently satisfying Gravity's downstream requirement.

Do not enable speaker output merely because the RPM builds. Have the audio
developer validate the M4 model profile, amplifier controls, sensing/scaling,
thermal limits and protection/failure behavior against the matching kernel.
Never bypass safety controls to make a packaging smoke test pass. Package tests
must not activate hardware or start the daemon.

Audit the matching ALSA UCM definitions and PipeWire/WirePlumber configuration.
Our image currently takes alsa-ucm-asahi and asahi-audio from Fedora. If the new
audio stack needs downstream changes there, those require additional source
pins and package recipes too; this scaffold does not claim they are sufficient.

## Provenance

Adapted from Fedora's rust-speakersafetyd f44 spec at commit
`ce97ff700de0edbb672fc93c209688335bd4e065`:
https://src.fedoraproject.org/rpms/rust-speakersafetyd/tree/ce97ff700de0edbb672fc93c209688335bd4e065

The service scriptlets, runtime directories, configuration installation and
Cargo build/test macros follow that packaging. Fedora's two source patches
are deliberately not applied blindly to an unavailable downstream Git tree.
