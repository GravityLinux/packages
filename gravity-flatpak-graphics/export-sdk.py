#!/usr/bin/env python3
"""Export pinned installed SDKs as an offline compiler input (not a Mesa payload)."""
import argparse
import gzip
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile


class Archive(tarfile.TarFile):
    def gettarinfo(self, *args, **kwargs):
        # OSTree checkout/deployment hardlinks are an implementation detail.
        # Keep symbolic links, but serialize every regular file independently.
        self.inodes.clear()
        return super().gettarinfo(*args, **kwargs)


def download(installation, lock):
    """Source-preparation only: download aarch64 tools without executing them."""
    env = {**os.environ, "FLATPAK_USER_DIR": str(installation)}
    subprocess.run(["flatpak", "remote-add", "--user", "flathub", "https://dl.flathub.org/repo/flathub.flatpakrepo"], env=env, check=True, timeout=120)
    for name, commit in lock["refs"].items():
        ref = f"{name}/{lock['arch']}/{lock['branch']}"
        subprocess.run(["flatpak", "install", "--user", "--assumeyes", "--noninteractive", "--no-related", "--no-deps", "flathub", ref], env=env, check=True, timeout=5400)
        active = installation / "runtime" / ref / "active"
        if active.resolve(strict=True).name != commit:
            # Never build against a moved branch accidentally. Ask Flatpak for
            # the locked revision, and export() checks the result again.
            subprocess.run(["flatpak", "update", "--user", "--assumeyes", "--noninteractive", "--no-related", "--commit=" + commit, ref], env=env, check=True, timeout=5400)


def export(installation, lock, output):
    trees = {}
    for name, commit in lock["refs"].items():
        active = installation / "runtime" / name / lock["arch"] / lock["branch"] / "active"
        deployment = active.resolve(strict=True)
        if deployment.name != commit:
            raise ValueError(f"{name}: expected {commit}, found {deployment.name}")
        trees[name] = deployment / "files"
    # Never overwrite a reviewed archive. Stable ownership/times, gzip header
    # and traversal order make its hash independent of the exporting account.
    def normalize(info):
        info.uid = info.gid = info.mtime = 0
        info.uname = info.gname = ""
        info.pax_headers = {}
        if not info.issym():
            info.mode &= ~0o222
        return info

    try:
        with output.open("xb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0, compresslevel=1) as zipped:
            with Archive.open(fileobj=zipped, mode="w|") as archive:
                archive.add(trees["org.freedesktop.Sdk"], arcname="sdk", filter=normalize)
                archive.add(trees["org.freedesktop.Sdk.Extension.llvm22"], arcname="sdk/lib/sdk/llvm22", filter=normalize)
                data = (json.dumps(lock, sort_keys=True) + "\n").encode()
                info = normalize(tarfile.TarInfo("sdk/gravity-sdk.json"))
                info.size = len(data)
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(data))
    except BaseException:
        # An existing output was not ours to remove.
        if 'raw' in locals():
            output.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installation", type=Path, help="Export an existing installation instead of downloading the pinned commits")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads(Path(__file__).with_name("sdk.lock.json").read_text())
    if args.installation:
        export(args.installation, lock, args.output)
    else:
        with tempfile.TemporaryDirectory(prefix="gravity-flatpak-sdk-", dir=args.output.parent) as temporary:
            installation = Path(temporary)
            download(installation, lock)
            export(installation, lock, args.output)
