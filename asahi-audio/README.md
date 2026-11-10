# Apple silicon DSP profiles

Fedora's f44 `asahi-audio` 4.1 (dist-git `19a447864c512320a55d82cb519c5bacbf2a49c1`) plus one Gravity patch:
the J713 (MacBook Air 13", M4) speakers use the J413 graph, as upstream already
does for the J613 (same chassis and speaker layout). The patch is commit
`6de3ccc25f37` on the `j713` branch of our asahi-audio checkout, based on the v4.1 tag.

Without a J713 entry, asahi-audio's volume lock pins the raw J713 speaker
route at 100% and leaves no DSP sink with its own volume.

The J413 tuning on J713 hardware needs a listening check.

Patch 0002 (`e9e1499`) gives the J713 internal mics (AOP card AppleJ713HPAI)
the J413 Triforce mic graph, like the J613. Raw capture verified on hardware
2026-11-08 (three channels live); the graph's output level still needs a check.
