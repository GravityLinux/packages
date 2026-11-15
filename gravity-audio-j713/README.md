# J713 audio add-on

This package layers J713 UCM, WirePlumber rules, DSP and speaker protection
configuration on unmodified Fedora alsa-ucm-asahi, asahi-audio and
speakersafetyd. It owns /usr/share/asahi-audio/j713/graph.json; its trigger
only regenerates the J413 microphone alias. A Fedora audio update must never
replace this speaker graph with a J413 alias.

The speaker graph retains the J413 FIR data, Bankstown and crossover. Its
woofer and tweeter compressors precede installed LSP true-peak limiters and
final PipeWire clamps. At amplifier gain 15 (18.5 dBV), the graph's sample
ceilings correspond to 9 V peak on each woofer and 6 V on each tweeter. There is
no short-term RMS guard. Matching output ceilings does not calibrate the
speakers' thermal or excursion limits.

The protection profile uses 130 C woofer / 120 C tweeter limits and 50 C assumed
ambient. Thermal resistance/time constants:

- Woofer: coil 32.1 C/W, 4.7 s; magnet 20 C/W, 66.5 s. These values occur in M4 LSM18
  and also match the existing M2 profile.
- Tweeter: coil 140 C/W, 1.47 s; magnet 200 C/W, 52 s, from the M4 LSM19 data reading.

The limits are release policy, not measured macOS temperature thresholds.
The nominal steady model budgets are 1.536 W per woofer and 0.206 W per tweeter.
Measured paired V/I feeds the daemon; it has no excursion or resistance-based
absolute temperature observer. The daemon retains Fedora's 4096-frame (85.33 ms at 48 kHz) read cadence.
Synthetic ceiling-level onsets can overshoot the thermal limit before the
next control update; this is a known, accepted property of the chosen cadence.
No compensating graph stage, guard, window or hysteresis change is included.
Physical control latency and feedback integrity still require validation.

## Coordination and validation

Keep the emergency kernel caps until the profile, feedback integrity, latency
and listening checks have been validated. The next kernel must include the
amplifier reset-cache/SDOUT feedback fix. Only then consider the separately
prepared cap-removal commit. Without a live daemon owning and refreshing the
controls, the kernel locks the amps to their lowest volume step.

The add-on intentionally leaves Fedora files untouched. The UCM includes
laptops/HiFi.conf and aop_audio/3chan/HiFi.conf; FIR paths continue to use
asahi-audio's j413 directory. If Fedora introduces its own J713 files/rules,
review ownership and avoid duplicate filter chains. Tests and package builds
must not activate hardware or start playback.
