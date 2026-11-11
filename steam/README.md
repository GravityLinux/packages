# steam

The `steam` command, desktop entry and `steam://` handler for Valve's native
ARM64 Steam client on Gravity Linux. The package contains only this launcher
(MIT). Nothing of Valve's is in the RPM or its source package: the client is
proprietary and is downloaded from Valve for each user at the first start,
followed by Proton from Gravity Linux.

## First start

`/usr/bin/steam` starts `steam-launch` as a 4K-page process (`exec-pages`;
the client needs 4K pages, which a P3S kernel gives per process). When the
user has no client yet, `steam-launch` runs `fetch-client`, which

1. checks that the data directory has room for the download and the unpacked
   client (about 3.5 GB together);
2. downloads Valve's package (about 700 MB) from the URL pinned in
   `fetch-client` to `~/.local/share/.steam-client-download`, showing a
   progress window with a Cancel button (zenity), or progress lines when
   started from a terminal without a display. A cancelled or interrupted
   download continues on the next start;
3. checks the file's size and SHA-256 against the pinned values, and deletes
   it and stops when they differ;
4. unpacks the client into a staging directory, which `steam-launch` renames
   to `~/.local/share/Steam` (or `SteamArm64` when `Steam` holds an x86
   installation), and removes the download.

If Valve has removed the pinned package (HTTP 404), `fetch-client` reads the
package index of the same directory and downloads the client build listed
there, saying so in the progress window, but only when the index gives a
SHA-256 to check it against. Otherwise it stops and asks for a system update:
the fix is a package update that pins the new build.

An existing client is never downloaded again or changed by a package update;
Steam updates itself.

## Proton

Windows games use Proton (ARM64, Gravity), a build of Valve's Proton 11.0
with a Wine fix for the Apple M4 (`PROTON-SOURCE.md`). It is not an RPM:
after the client, `steam-launch` has `fetch-client` download the archive
pinned in it (about 540 MB) from Gravity Linux's server in the same way
(progress window, resume, size and SHA-256 check; no package-index lookup)
and unpacks it to
`~/.local/share/steam-gravity/compatibilitytools.d/proton-gravity-arm64`,
adding `compatibilitytool.vdf` and `NOTICE.txt` from this package. If the
download fails or is cancelled, Steam starts without Proton and the next
start tries again. When the earlier `proton-gravity-arm64` package is
installed, its tree under `/opt/steam-gravity/compatibilitytools.d` is used
and nothing is downloaded.

To publish a new build, upload the archive and change `PROTON` in
`fetch-client` (URL, size, SHA-256).

## Updating the pinned client

Take the `deckard-steam-rel` entry of Valve's package index
(`deckard-arch-hotfixes-release-0.4.db`, a tar archive of `desc` files, in
the directory of the pinned URL): `%FILENAME%`, `%SHA256SUM%` and `%CSIZE%`
go into `CLIENT` in `fetch-client`. Test a first start before publishing.

## Compatibility tools

`steam-launch` adds the directory that holds Proton to
`STEAM_EXTRA_COMPAT_TOOLS_PATHS`. `steam-gravity-proton-default` makes
`proton-gravity-arm64` the default tool for games without another choice.
x86 Linux games run through Valve's FEX tool with the x86 Mesa of
`fex-guestos-mesa`, which this package requires.

The icon is the one of Fedora Asahi Remix's steam package (MIT,
`LICENSE.icon`).
