#!/usr/bin/env python3
"""Check SRPM config overlays against pinned Linux and Fedora's own comparator.

Usage: python3 tools/check_kernel_kconfig.py LINUX_TREE BASELINE_SRPM_SOURCES
Requires make, a host C compiler, flex and bison. Uses Fedora's dummy GCC
configuration toolchain, not a kernel compilation. Neither input is modified.
"""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from package import overlay_kernel_configs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("linux", type=Path)
    parser.add_argument("sources", type=Path)
    args = parser.parse_args()
    linux = args.linux.resolve()
    sources = args.sources.resolve()
    checker = (sources / "process_configs.sh").read_text()
    # Use the baseline's actual comparison, including its spelling-sensitive
    # handling of disabled options. Fail closed if its structure changes.
    match = re.search(r"/usr/bin/awk '(.*?)' \"\$cfg\" \"\$cfgtmp\"", checker, re.S)
    if not match:
        raise SystemExit("Cannot find Fedora config comparator")
    failures = []
    with tempfile.TemporaryDirectory(prefix="gravity-kconfig-") as tmp:
        root = Path(tmp)
        configs = root / "configs"
        configs.mkdir()
        for config in sources.glob("kernel-aarch64*-fedora.config"):
            shutil.copy2(config, configs / config.name)
        if not list(configs.glob("*16k*.config")):
            raise SystemExit("Missing baseline Apple 16K configs")
        overlay_kernel_configs(configs)
        for config in sorted(configs.glob("*.config")):
            build = root / config.stem
            build.mkdir()
            generated = build / ".config"
            shutil.copy2(config, generated)
            command = ["make", "-s", "-C", str(linux), f"O={build}",
                       "ARCH=arm64", f"CROSS_COMPILE={linux}/scripts/dummy-tools/"]
            new = subprocess.run(command + ["listnewconfig"], check=True,
                                 capture_output=True, text=True)
            if re.search(r"^CONFIG_", new.stdout, re.M) or "warning:" in new.stderr:
                failures.append(f"{config.name}: new options/warnings\n{new.stdout}{new.stderr}")
            subprocess.run(command + ["olddefconfig"], check=True, capture_output=True)
            diff = subprocess.run(["/usr/bin/awk", match[1], str(config), str(generated)],
                                  check=True, capture_output=True, text=True)
            if diff.stdout:
                failures.append(f"{config.name}:\n{diff.stdout}")
            print(f"Checked {config.name}", flush=True)
    if failures:
        raise SystemExit("\n".join(failures))
    print("PASS: no new options, config warnings or Fedora comparator mismatches")


if __name__ == "__main__":
    main()
