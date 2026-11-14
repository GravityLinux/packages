#!/usr/bin/env python3
"""Assemble unmanaged, automatically selected Flatpak GL.host extensions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

SLOTS = (
    ("org.freedesktop.Platform.GL.host", "25.08", "/usr/lib/aarch64-linux-gnu/GL/host", "stage"),
    ("org.freedesktop.Platform.GL.host", "26.08", "/usr/lib/aarch64-linux-gnu/GL/host", "stage"),
    ("org.fedoraproject.Platform.GL.host", "f45", "/usr/lib64/GL/host", "stage-fedora"),
)


def assemble(work, destination, commit):
    software_driver = (work / "software-driver.txt").read_text().strip()
    if software_driver not in ("llvmpipe", "softpipe"):
        raise ValueError(f"Unexpected software driver: {software_driver}")
    llvm_name = "libLLVM.so.22.1"
    llvm_installed = None
    llvm_origin = None
    if software_driver == "llvmpipe":
        llvm_origin = json.loads((work / "llvm-origin.json").read_text())
        llvm_source = work / "llvm-runtime" / llvm_name
        with llvm_source.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != llvm_origin["sha256_before_assembly"]:
                raise ValueError("SDK LLVM library does not match its recorded origin")
    for extension, branch, prefix, stage in SLOTS:
        source = work / stage / prefix.lstrip("/")
        target = destination / extension / "aarch64" / branch
        shutil.copytree(source, target, symlinks=True)
        if software_driver == "llvmpipe":
            llvm_target = target / "lib" / llvm_name
            if llvm_installed is None:
                shutil.copy2(work / "llvm-runtime" / llvm_name, llvm_target)
                # A prebuilt DSO needs read permission, not executable mode.
                # This keeps find-debuginfo from rewriting the SDK binary.
                llvm_target.chmod(0o644)
            else:
                os.link(llvm_installed, llvm_target)
        for name in ("glvnd", "vulkan"):
            (target / name).symlink_to("share/" + name)
        # Development files and tools have no place in a graphics extension.
        for name in ("include", "bin", "lib/pkgconfig"):
            shutil.rmtree(target / name, ignore_errors=True)
        for path in target.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            if path.name == llvm_name:
                continue  # Redistribute the verified SDK library byte-for-byte.
            with path.open("rb") as stream:
                elf = stream.read(4) == b"\x7fELF"
            if elf:
                subprocess.run(["strip", "--strip-unneeded", path], check=True)
                # Keep dependencies findable even if an existing application's
                # ld.so.cache predates this unmanaged-extension update (#5948).
                subprocess.run(["patchelf", "--set-rpath", "$ORIGIN:$ORIGIN/..", path], check=True)
        if software_driver == "llvmpipe" and llvm_installed is None:
            llvm_installed = target / "lib" / llvm_name
        # Absolute paths also make metadata lookup independent of ld.so.cache.
        for directory, key in (("share/vulkan/icd.d", "ICD"), ("share/glvnd/egl_vendor.d", "ICD")):
            for path in (target / directory).glob("*.json"):
                data = json.loads(path.read_text())
                library = Path(data[key]["library_path"]).name
                data[key]["library_path"] = prefix + "/lib/" + library
                path.write_text(json.dumps(data, indent=2) + "\n")
        (target / "gravity-build.json").write_text(json.dumps({
            "mesa_commit": commit, "extension": extension, "branch": branch,
            "build_sdk": "25.08", "architecture": "aarch64",
            "software_gl": software_driver,
            "llvm": llvm_origin,
        }, indent=2) + "\n")
        # swrast_dri.so is the software-GL entry point, backed by llvmpipe.
        # Only the pinned SDK's single LLVM SONAME is allowed, no tools or
        # other LLVM libraries. Vulkan software rendering stays runtime-owned.
        allowed_llvm = target / "lib" / llvm_name if software_driver == "llvmpipe" else None
        forbidden = list(target.rglob("*lvp*")) + [
            path for path in target.rglob("*LLVM*") if path != allowed_llvm
        ]
        if forbidden:
            raise ValueError(f"Unexpected Vulkan software/LLVM file payload: {forbidden}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("commit")
    args = parser.parse_args()
    assemble(args.work, args.destination, args.commit)
