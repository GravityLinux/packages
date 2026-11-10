#!/usr/bin/python3 -I
# SPDX-License-Identifier: MIT
"""Assemble the x86 Mesa trees that FEX uses on ARM64 Gravity systems.

Runs in the x86_64 build root of mesa-fex-guest, after the x86_64 and i686
Mesa builds are installed into their stage directories (Fedora layout: x86_64
in usr/lib64, i686 in usr/lib). It writes, below OUT:

  gravity-x86/   The Mesa runtime files in Fedora's layout. gravity-x86 mounts
                 them over Fedora's x86 FEX root filesystem.
  guestos/       The tree that Valve's FEX tool for ARM64 Steam expects at
                 /usr/share/guestos/fex-mesa: the Mesa files, the Fedora x86
                 libraries they need (installed in this build root from
                 Fedora's repositories) and a shell, in an Arch-style layout
                 (x86_64 in usr/lib, i686 in usr/lib32), with ld.so.cache and
                 graphics_provider.json.
  MANIFEST-gravity-x86.json, MANIFEST-guestos.json
                 The source of every file: mesa:<revision>:<arch>,
                 fedora:<NEVRA> or generated.

Usage: assemble.py STAGE_X86_64 STAGE_I686 REVISION PACKAGES OUT
"""
import functools
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ARCHES = ('x86_64', 'i686')
FEDORA_LIBDIR = {'x86_64': 'usr/lib64', 'i686': 'usr/lib'}
GUESTOS_LIBDIR = {'x86_64': 'usr/lib', 'i686': 'usr/lib32'}
ELFCLASS = {'x86_64': 2, 'i686': 1}
# Mesa: runtime files only (no headers, pkg-config files or development links).
MESA_SKIP = ('usr/include/', '/pkgconfig/')
MESA_DEV_LINKS = ('libGLX_mesa.so', 'libEGL_mesa.so', 'libgbm.so')
# Always in the guestos tree: all of glibc, and the C/C++ runtime and libglvnd
# libraries that games link against. Other Fedora libraries only when
# something in the tree needs them.
ROOT_PACKAGES = ('glibc',)
ROOT_LIBS = ('libgcc_s.so.1', 'libstdc++.so.6', 'libGL.so.1', 'libGLX.so.0', 'libEGL.so.1',
             'libOpenGL.so.0', 'libGLESv2.so.2', 'libGLESv1_CM.so.1', 'libGLdispatch.so.0')
# x86_64 programs: the /bin/sh FEX runs the Steam Linux Runtime entry point
# with, the few utilities that script calls before it re-executes natively,
# and ldconfig (steam-runtime-graphics-provider.json(5) requires one).
TOOLS = {'bash': ['usr/bin/bash'], 'busybox': ['usr/bin/busybox'], 'glibc': ['usr/bin/ldconfig']}
TOOL_LINKS = {'usr/bin/sh': 'bash', 'usr/bin/readlink': 'busybox', 'usr/bin/date': 'busybox',
              'usr/bin/getopt': 'busybox', 'usr/bin/env': 'busybox'}
DIR_LINKS = {'lib': 'usr/lib', 'lib64': 'usr/lib', 'usr/lib64': 'lib', 'lib32': 'usr/lib32',
             'bin': 'usr/bin', 'sbin': 'usr/bin', 'usr/sbin': 'bin'}
PROVIDER = {
    'graphics_provider_v0': {
        'root': './',
        'locales': False,
        'va_api': False,
        'vdpau': False,
        'architectures': {
            'x86_64-linux-gnu': {
                'dri': '/usr/lib/dri',
                'gbm': '/usr/lib/gbm',
                'gconv': '/usr/lib/gconv',
                'fallback_library_paths': ['/lib64', '/usr/lib64'],
            },
            'i386-linux-gnu': {
                'dri': '/usr/lib32/dri',
                'gbm': '/usr/lib32/gbm',
                'gconv': '/usr/lib32/gconv',
                'fallback_library_paths': ['/lib', '/usr/lib'],
            },
        },
    },
}


def fail(message):
    sys.exit(f'assemble.py: {message}')


def sha256(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_packages(path):
    out = []
    for line in Path(path).read_text().splitlines():
        words = line.split('#', 1)[0].split()
        if words:
            out.append((words[0], words[1:]))
    return out


def put(root, manifest, rel, src, source):
    dst = root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(dst):
        fail(f'{rel}: provided twice ({manifest[rel]["source"]} and {source})')
    if src.is_symlink():
        os.symlink(os.readlink(src), dst)
        manifest[rel] = {'source': source, 'link': os.readlink(src)}
    else:
        shutil.copy2(src, dst)
        manifest[rel] = {'source': source, 'sha256': sha256(dst)}


def link(root, manifest, rel, target):
    dst = root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(target, dst)
    manifest[rel] = {'source': 'generated', 'link': target}


def readelf(path):
    """(ELF class, SONAME or None, [NEEDED]) or None if not an ELF file."""
    with open(path, 'rb') as f:
        head = f.read(5)
    if head[:4] != b'\x7fELF':
        return None
    out = subprocess.run(['readelf', '-dW', str(path)], capture_output=True, text=True,
                         check=True).stdout
    tag = lambda kind: [l.split('[', 1)[1].rstrip(']') for l in out.splitlines() if f'({kind})' in l]
    soname = tag('SONAME')
    return head[4], soname[0] if soname else None, tag('NEEDED')


def mesa_files(stage):
    """(relative path, path) of the runtime files in a Mesa stage directory."""
    for p in sorted(stage.rglob('*')):
        rel = p.relative_to(stage).as_posix()
        if p.is_dir() and not p.is_symlink():
            continue
        if any(s in '/' + rel for s in MESA_SKIP) or p.name in MESA_DEV_LINKS:
            continue
        yield rel, p


def take_mesa(root, manifest, stages, rev, libdirs):
    """Copy both Mesa builds, moving Fedora's library directories to libdirs.
    Architecture-independent files must be the same in both builds."""
    for arch in ARCHES:
        source = f'mesa:{rev}:{arch}'
        fedora = FEDORA_LIBDIR[arch] + '/'
        for rel, p in mesa_files(stages[arch]):
            if rel.startswith(fedora):
                rel = libdirs[arch] + '/' + rel[len(fedora):]
            elif not rel.startswith('usr/share/'):
                fail(f'{arch} Mesa installs {rel}, outside {fedora} and usr/share')
            if arch == 'i686' and rel.startswith('usr/share/') and os.path.lexists(root / rel):
                if (root / rel).read_bytes() != p.read_bytes():
                    fail(f'{rel}: x86_64 and i686 Mesa differ')
                continue
            put(root, manifest, rel, p, source)


def fix_icds(root, manifest, libdirs):
    for arch in ARCHES:
        rel = f'usr/share/vulkan/icd.d/asahi_icd.{arch}.json'
        icd = json.loads((root / rel).read_text())
        path = f'/{libdirs[arch]}/libvulkan_asahi.so'
        if icd['ICD']['library_path'] != path:
            icd['ICD']['library_path'] = path
            (root / rel).write_text(json.dumps(icd, indent=4) + '\n')
            manifest[rel]['sha256'] = sha256(root / rel)
            manifest[rel]['edited'] = 'library_path for this layout'


def rpm_query(name, arch, fmt):
    return subprocess.run(['rpm', '-q', '--qf', fmt, f'{name}.{arch}'], capture_output=True,
                          text=True, check=True).stdout


def take_fedora(root, manifest, sysroot, package_list):
    """Put the listed Fedora packages' programs, gconv modules and license texts
    in the tree, and return their shared libraries as candidates:
    {arch: {name: (path, source)}}."""
    libs = {arch: {} for arch in ARCHES}
    for name, arches in package_list:
        for arch in arches:
            nevra = rpm_query(name, arch, '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}')
            source = f'fedora:{nevra}'
            files = [f.lstrip('/') for f in rpm_query(name, arch, '[%{FILENAMES}\n]').splitlines()]
            libdir = FEDORA_LIBDIR[arch] + '/'
            for rel in files:
                p = sysroot / rel
                # A few packages (libgcc) still name /lib64 and /lib, which
                # are links to usr/lib64 and usr/lib.
                if rel.startswith(('lib/', 'lib64/')):
                    rel = 'usr/' + rel
                if not os.path.lexists(p) or (p.is_dir() and not p.is_symlink()):
                    continue
                if rel.startswith(libdir + 'gconv/'):
                    put(root, manifest, GUESTOS_LIBDIR[arch] + '/' + rel[len(libdir):], p, source)
                elif rel.startswith(libdir) and '/' not in rel[len(libdir):]:
                    base = rel[len(libdir):]
                    if base.startswith(('lib', 'ld-linux')) and '.so' in base:
                        if base in libs[arch]:
                            fail(f'{arch} {base}: in {libs[arch][base][1]} and {source}')
                        libs[arch][base] = (p, source)
                elif arch == 'x86_64' and rel in TOOLS.get(name, []):
                    put(root, manifest, rel, p, source)
                elif arch == 'x86_64' and rel.startswith('usr/share/licenses/'):
                    put(root, manifest, rel, p, source)
            if arch == 'x86_64':
                for rel in TOOLS.get(name, []):
                    if rel not in manifest:
                        fail(f'{nevra} has no {rel}')
    return libs


def gconv_caches(root, manifest):
    """glibc ships gconv-modules.cache empty and fills it with iconvconfig
    when it is installed, so the build root's copy describes its own modules.
    Write the tree's for exactly the modules it holds."""
    for libdir in GUESTOS_LIBDIR.values():
        rel = f'{libdir}/gconv/gconv-modules.cache'
        if rel not in manifest:
            continue
        (root / rel).unlink()
        subprocess.run(['iconvconfig', '--nostdlib', f'--prefix={root}', '-o', str(root / rel),
                        f'/{libdir}/gconv'], check=True)
        manifest[rel] = {'source': 'generated by iconvconfig', 'sha256': sha256(root / rel)}


def take_libraries(root, manifest, libs):
    """Add the candidates reachable through NEEDED from what the tree already
    holds (Mesa, gconv, programs) and from ROOT_LIBS."""
    for arch, libdir in GUESTOS_LIBDIR.items():
        want = [n for n, (_, src) in libs[arch].items()
                if src.startswith(tuple(f'fedora:{p}-' for p in ROOT_PACKAGES))]
        want += [n for n in ROOT_LIBS if n in libs[arch]]
        elves = list((root / libdir).rglob('*'))
        if arch == 'x86_64':
            elves += list((root / 'usr/bin').iterdir())
        for p in elves:
            info = None if p.is_symlink() or not p.is_file() else readelf(p)
            if info:
                want += info[2]
        while want:
            name = want.pop()
            rel = f'{libdir}/{name}'
            if name not in libs[arch] or os.path.lexists(root / rel):
                continue
            src, source = libs[arch][name]
            put(root, manifest, rel, src, source)
            if src.is_symlink():
                want.append(os.path.basename(os.readlink(src)))
            else:
                info = readelf(src)
                want += info[2] if info else []


def check_closure(root, libdirs, programs=True):
    """Every ELF file must have its architecture's class, and every NEEDED
    library must be in that architecture's directory."""
    missing = []
    for arch, libdir in libdirs.items():
        have = {p.name for p in (root / libdir).iterdir()}
        for p in sorted((root / libdir).rglob('*')):
            info = None if p.is_symlink() or not p.is_file() else readelf(p)
            if not info:
                continue
            if info[0] != ELFCLASS[arch]:
                missing.append(f'{p.relative_to(root)}: wrong ELF class')
            missing += [f'{p.relative_to(root)}: {n}' for n in info[2] if n not in have]
    if programs:
        have = {q.name for q in (root / libdirs['x86_64']).iterdir()}
        for p in (root / 'usr/bin').iterdir():
            info = None if p.is_symlink() else readelf(p)
            if info:
                missing += [f'{p.relative_to(root)}: {n}' for n in info[2] if n not in have]
    if missing:
        fail('unresolved:\n  ' + '\n  '.join(missing))


# ld.so.cache in glibc's current format ("glibc-ld.so.cache1.1", the only one
# ldconfig writes since glibc 2.32). ldconfig -r would need chroot privileges.
FLAG_ELF_LIBC6 = 0x0003
FLAG_X8664_LIB64 = 0x0300
CACHE_FLAGS = {2: FLAG_ELF_LIBC6 | FLAG_X8664_LIB64, 1: FLAG_ELF_LIBC6}


def dl_cache_libcmp(a, b):
    """glibc's _dl_cache_libcmp: digit runs compare as numbers."""
    i = j = 0
    while i < len(a):
        if a[i].isdigit():
            if j < len(b) and b[j].isdigit():
                m = i
                while m < len(a) and a[m].isdigit():
                    m += 1
                n = j
                while n < len(b) and b[n].isdigit():
                    n += 1
                if int(a[i:m]) != int(b[j:n]):
                    return int(a[i:m]) - int(b[j:n])
                i, j = m, n
            else:
                return 1
        elif j < len(b) and b[j].isdigit():
            return -1
        elif j >= len(b) or a[i] != b[j]:
            return ord(a[i]) - (ord(b[j]) if j < len(b) else 0)
        else:
            i += 1
            j += 1
    return 0 - (ord(b[j]) if j < len(b) else 0)


def cache_entries(root, dirs):
    """(soname, flags, path) for the libraries ldconfig would list in dirs."""
    entries = []
    for d in dirs:
        seen = set()
        for p in sorted((root / d.lstrip('/')).iterdir()):
            name = p.name
            if not name.startswith(('lib', 'ld-')) or '.so' not in name:
                continue
            real = p.resolve()
            if not real.is_file() or not str(real).startswith(str(root.resolve()) + '/'):
                continue
            info = readelf(real)
            if not info or info[0] not in CACHE_FLAGS:
                continue
            soname = info[1] or real.name
            if p.is_symlink() and real.name == soname:
                soname = name
            if soname in seen or not os.path.lexists(root / d.lstrip('/') / soname):
                continue
            seen.add(soname)
            entries.append((soname, CACHE_FLAGS[info[0]], f'{d}/{soname}'))
    return entries


def write_ld_so_cache(path, entries):
    def order(x, y):
        res = dl_cache_libcmp(y[0], x[0])
        if res == 0:
            res = y[1] - x[1]
        return res
    entries = sorted(entries, key=functools.cmp_to_key(order))
    header = 48
    base = header + 24 * len(entries)
    strings = bytearray()
    offsets = {}
    for s in [e[0] for e in entries] + [e[2] for e in entries]:
        if s not in offsets:
            offsets[s] = base + len(strings)
            strings += s.encode() + b'\0'
    out = bytearray(b'glibc-ld.so.cache' + b'1.1')
    out += struct.pack('<IIB3xI12x', len(entries), len(strings), 2, 0)
    for soname, flags, value in entries:
        out += struct.pack('<iIIIQ', flags, offsets[soname], offsets[value], 0, 0)
    out += strings
    Path(path).write_bytes(bytes(out))
    return entries


def verify_ld_so_cache(root, entries):
    """Read the cache back with the tree's own ldconfig."""
    out = subprocess.run([str(root / 'usr/bin/ldconfig'), '-p', '-C', str(root / 'etc/ld.so.cache')],
                         capture_output=True, text=True, check=True).stdout
    listed = sorted((l.split(' (', 1)[0].strip(), l.rsplit('=> ', 1)[1])
                    for l in out.splitlines()[1:])
    if listed != sorted((e[0], e[2]) for e in entries):
        fail('ldconfig -p does not list the written ld.so.cache')


def write_manifest(path, rev, manifest):
    Path(path).write_text(json.dumps(
        {'mesa_revision': rev, 'files': dict(sorted(manifest.items()))}, indent=1) + '\n')


def main():
    if len(sys.argv) != 6:
        fail(__doc__)
    stage_64, stage_32, rev, packages, out = sys.argv[1:]
    stages = {'x86_64': Path(stage_64).resolve(), 'i686': Path(stage_32).resolve()}
    out = Path(out)
    if out.exists():
        fail(f'{out} exists')

    # gravity-x86: Fedora's layout, Mesa only.
    root = out / 'gravity-x86'
    root.mkdir(parents=True)
    manifest = {}
    take_mesa(root, manifest, stages, rev, FEDORA_LIBDIR)
    fix_icds(root, manifest, FEDORA_LIBDIR)
    write_manifest(out / 'MANIFEST-gravity-x86.json', rev, manifest)
    print(f'{root}: {len(manifest)} entries')

    # guestos: Arch-style layout, Mesa plus the Fedora closure.
    root = out / 'guestos'
    root.mkdir()
    manifest = {}
    libs = take_fedora(root, manifest, Path('/'), read_packages(packages))
    gconv_caches(root, manifest)
    take_mesa(root, manifest, stages, rev, GUESTOS_LIBDIR)
    take_libraries(root, manifest, libs)
    fix_icds(root, manifest, GUESTOS_LIBDIR)
    for rel, target in TOOL_LINKS.items():
        link(root, manifest, rel, target)
    link(root, manifest, f'{GUESTOS_LIBDIR["x86_64"]}/ld-linux.so.2', '../lib32/ld-linux.so.2')
    for rel, target in DIR_LINKS.items():
        link(root, manifest, rel, target)
    check_closure(root, GUESTOS_LIBDIR)
    (root / 'etc').mkdir()
    (root / 'etc/ld.so.conf').write_text('/usr/lib\n/usr/lib32\n')
    manifest['etc/ld.so.conf'] = {'source': 'generated'}
    entries = write_ld_so_cache(root / 'etc/ld.so.cache', cache_entries(root, ['/usr/lib', '/usr/lib32']))
    verify_ld_so_cache(root, entries)
    manifest['etc/ld.so.cache'] = {'source': 'generated', 'sha256': sha256(root / 'etc/ld.so.cache')}
    (root / 'graphics_provider.json').write_text(json.dumps(PROVIDER, indent=2) + '\n')
    manifest['graphics_provider.json'] = {'source': 'generated'}
    write_manifest(out / 'MANIFEST-guestos.json', rev, manifest)
    print(f'{root}: {len(manifest)} entries, {len(entries)} ld.so.cache entries')


if __name__ == '__main__':
    main()
