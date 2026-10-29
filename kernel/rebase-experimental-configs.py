#!/usr/bin/env python3
"""Rebase experimental Fedora config seeds, preserving strict validation afterward."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def rebase(linux, version):
    linux = Path(linux).resolve()
    configs = sorted((linux / 'configs').glob(f'kernel-{version}-*.config'))
    if not configs:
        raise ValueError('No generated Fedora configs to rebase')
    for config in configs:
        header = config.read_text().splitlines()[0]
        arch = header.removeprefix('# ').strip()
        if arch not in {'arm64', 'x86_64', 's390', 'powerpc', 'riscv'}:
            raise ValueError(f'Unknown architecture in {config}: {header}')
        with tempfile.TemporaryDirectory(prefix='gravity-kconfig-') as temporary:
            build = Path(temporary)
            shutil.copy2(config, build / '.config')
            subprocess.run(['make', '-s', '-C', str(linux), f'O={build}',
                            f'ARCH={arch}', f'CROSS_COMPILE={linux}/scripts/dummy-tools/',
                            'olddefconfig'], check=True)
            contents = (build / '.config').read_text()
            if arch == 'arm64' and '-16k' in config.name:
                for required in ('CONFIG_RUST=y', 'CONFIG_DRM_ASAHI=m', 'CONFIG_NVME_APPLE=m'):
                    if required not in contents.splitlines():
                        raise ValueError(f'{config.name}: required option lost during rebase: {required}')
            config.write_text(header + '\n' + contents)
        print(f'Rebased experimental config: {config.name}', flush=True)


if __name__ == '__main__':
    rebase(sys.argv[1], sys.argv[2])
