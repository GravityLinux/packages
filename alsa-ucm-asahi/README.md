# ALSA UCM for Apple silicon

Fedora's f44 `alsa-ucm-asahi` 10 (dist-git
`b11b0738875c4f2432549c7204eebc2cb7a17a4c`) plus one Gravity patch for the J713
(MacBook Air 13", M4) macaudio card: speakers on PCM 1 and a headphone-only
jack device on PCM 0 (the T8132 card has no headset capture yet). The patch is
commit `dd9e76c` on the `j713` branch of our alsa-ucm-conf-asahi checkout,
based on the v10 tag.

Patch 0002 (`0fb2830`, after a revert of the earlier by-ear commit `b65b554`) puts
the J713 headphones back on the J413/J613 DAC mapping (DAC A = ASP RX CH1). The
by-ear "crossed" result came from a kernel that still rotated the T8132 TDM
frame by one slot at stream start. Speculative until a listen test on a kernel
with the MCA alignment fix (ae1e111ceb53). Release 102 sorts above the 101
build that shipped the crossed mapping.

Patch 0003 (`4b17869`) adds the J713 internal mics on the AOP card
("MacBook Air J713 High-Power Audio Interface", 3 channels, same as the J613).
