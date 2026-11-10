# Speaker protection packaging

Source RPM / COPR package: `rust-speakersafetyd`.
Binary RPM, executable and service: `speakersafetyd` (provides
`gravity-speakersafetyd`).

## What ships

Fedora's f44 package of upstream speakersafetyd 2.0.1 (dist-git
`ce97ff700de0edbb672fc93c209688335bd4e065`): the crates.io source, Fedora's
crate-metadata patch and its j504 backport, plus one Gravity patch that adds the
J713 (MacBook Air 13", M4) profile `conf/apple/j713.conf` and its udev rule.
The patch is commit `27ed8ede2a25` on the `j713-speakers` branch of our
speakersafetyd checkout (based on upstream's 2.0.1 tag).

No fork is needed. The J713 uses the macaudio kernel interface (sense PCM 2,
"Speaker Volume Unlock", "Speaker Sample Rate") like the J413/J613, so stock
2.0.1 runs it with the profile alone. The earlier plan for a GravityLinux
fork came from the J773g (Mac mini) playback-energy work; the J773g's speaker
protection is in its kernel driver and does not use this daemon.

## J713 profile

Amp setup and sense slots come from the ADT. The ADT has no speaker thermal
parameters and the J713 macOS preset has not been decoded, so the profile uses
the J413/J613 values with t_limit 10 C lower (130 C) on every speaker. Replace
them with the decoded J713 preset when it is available.

## Safety

Do not enable speaker output merely because the RPM builds. Until the daemon
holds and refreshes the unlock control, macaudio limits the amp volume to its
lowest step. Validate the profile, sense scaling and failure behaviour on the
matching kernel before release. Package tests must not activate hardware or
start the daemon.
