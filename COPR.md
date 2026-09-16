# Git-backed COPR builds

COPR project: `adevwithanidea/gravity`.
Packaging repository: `https://github.com/GravityLinux/packages.git`.

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
