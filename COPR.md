# Git-backed COPR builds

COPR project: `adevwithanidea/gravity`.
Packaging repository: `https://github.com/GravityLinux/packages.git`.

## Experimental channel

`adevwithanidea/gravity-experimental` builds from the `experimental` packaging
branch. Keep the same SCM settings below, with committish `experimental`, and
add stable `copr://adevwithanidea/gravity` as an external build repository.
Both installed Gravity repositories use priority 10: newer RPM versions win.

Current experimental build entries:

| Package | Spec File |
| --- | --- |
| kernel | `kernel/kernel.spec` |
| mesa | `mesa/mesa.spec` |
| gravity-repos-experimental | `gravity-repos-experimental/gravity-repos-experimental.spec` |

The last package is the separate opt-in repository configuration required by
KIWI's `Workstation-Sway-Experimental` profile. Its key URL uses COPR's HTTPS
endpoint. The project signing key must be available before building the image.
The kernel builds the complete 7.3 integration source and rebases the baseline
Fedora config seeds against it; it does not apply the previous 7.1 source delta.

No new U-Boot NVMe implementation is needed for the pinned J700/T8140 tree:
its NVMe node includes `apple,t8132-nvme-ans2`, which already selects the newer
queue-registration implementation in our U-Boot. The mailbox falls back to
`apple,asc-mailbox-v4` and SART to `apple,t6000-sart`, both supported. This assumes
the same compatible strings are present in the DT handed to U-Boot; hardware
boot remains to be tested. Keep bootloader and U-Boot pins unchanged for now.

COPR clones the packaging repository and runs `.copr/Makefile` to prepare
the SRPM on its own worker, then builds and signs the binary RPMs. There is
no local SRPM upload in this workflow. `sources.json` pins separate source
repositories; `downloads.lock.json` pins downloaded inputs.

## First Git-backed build

Publish the packaging commits and make the repository publicly readable over
HTTPS. An unauthenticated `git ls-remote` must work. For packages with Git source
recipes, also publish the pinned source commit at the URL in `sources.json`.
Local source checkouts are not available on COPR workers.

In the project's new-build form, choose the SCM/Git source type:

| Field | Value for gravity-repos |
| --- | --- |
| Clone URL | `https://github.com/GravityLinux/packages.git` |
| SCM type | `git` |
| Committish | Full published packaging commit SHA |
| Subdirectory | Leave empty |
| Spec File | `gravity-repos/gravity-repos.spec` |
| SRPM build method | `make_srpm` (shown as "make srpm" in some interfaces) |
| Chroot | `fedora-44-aarch64` |

For another package, change Spec File to `PACKAGE/PACKAGE.spec`. Do not use
a raw spec URL: the shared builder needs the rest of this repository, including
source pins, patches, configuration and the signing key.

For the bootloader, use `gravity-bootloader/gravity-bootloader.spec`. Its source repository is
`https://github.com/GravityLinux/bootloader.git`. RPMs are named `gravity-bootloader`,
`gravity-bootloader-stage1` and `gravity-bootloader-tools`; upstream binary names, Python module
names and installed `/usr/lib64/m1n1` paths remain compatible with the boot chain.

Use `gravity-repos` for the first SCM smoke test: all its source inputs are
contained in this repository. Submit dependencies in the order documented in
README.md. New builds must use a new RPM Release when package contents change.

The SRPM preparation worker can fetch sources and install preparation tools;
binary-build network access can remain disabled.

## Repeat builds and automation

Save each package's SCM configuration in COPR so subsequent builds can be
triggered without entering the source details again. For release builds, update
the committish to the reviewed packaging SHA; moving `main` does not update a
configuration pinned to an older SHA.

For push-triggered development builds, configure a branch such as `main`, enable
the package's automatic rebuild setting, and obtain the GitHub webhook from
COPR Settings / Integrations. Add it to the packaging repository's GitHub
webhook settings. Keep the integration URL private. Only enable the intended
events; don't route untrusted pull-request builds into the release repository.

All packages share one repository, so push-triggered builds can rebuild more
than the changed package and do not provide dependency ordering. Start with
explicit Git-backed submissions; add selective triggers and dependency-aware
orchestration as a separate step. Changes to a driver repository alone do not
change the release: update its pin in `sources.json` first.

Manual repository publication remains enabled on this project: a successful
build is not automatically a published update for users. Publish metadata only
after the intended batch is validated. Build workers can still consume newly
built project dependencies.

References: [SCM builds](https://docs.copr.fedorainfracloud.org/user_documentation.html#scm),
[saved packages](https://docs.copr.fedorainfracloud.org/user_documentation.html#working-with-packages),
[webhooks](https://docs.copr.fedorainfracloud.org/user_documentation.html#webhooks).
