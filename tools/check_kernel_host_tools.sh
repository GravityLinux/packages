#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-only
# Build the actual bpftool callers without compiling a kernel image.
set -euo pipefail
package_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
kernel_source=$(realpath "${1:?kernel source directory required}")
output_root=$(realpath -m "${2:?output directory required}")
shift 2
roles=("$@")
if [ "${#roles[@]}" -eq 0 ]; then
    roles=(standalone perf selftests-bpf)
fi
jobs=${JOBS:-$(( $(nproc) / ${#roles[@]} ))}
if [ "$jobs" -lt 1 ]; then jobs=1; fi
mkdir -p "$output_root"
# bpftool does not track all flag changes in its object prerequisites.
# Fresh objects make this a policy check rather than a cached link check.
output=$(mktemp -d "$output_root/run-XXXXXX")
printf '%s\n' "$output" > "$output_root/latest-run.txt"
printf 'Host-tool preflight output: %s\n' "$output"
python3 - "$package_root/kernel/kernel.spec" > "$output/rpm-flags.nul" <<'PY'
import re
import shlex
import subprocess
import sys
arch = subprocess.check_output(['rpm', '-E', '%{_target_cpu}'], text=True).strip()
options = ['--target', arch, '--define', 'fedora 44', '--define', 'dist .fc44']
expanded = subprocess.check_output(['rpmspec', *options, '-P', sys.argv[1]], text=True)
policies = [shlex.split(line) for line in expanded.splitlines()
            if line.startswith('. ') and 'host-tool-flags.sh' in line]
assert len(policies) == 1 and len(policies[0]) == 3
linker = re.search(r'HOSTLDFLAGS="([^"]*)"', expanded)
assert linker
metadata = subprocess.check_output([
    'rpmspec', *options, '--srpm', '-q', '--queryformat',
    '%{NAME}\n%{VERSION}\n%{RELEASE}\n', sys.argv[1]], text=True).splitlines()
assert len(metadata) == 3
for value in [policies[0][2], linker.group(1), arch, *metadata]:
    sys.stdout.buffer.write(value.encode() + b'\0')
PY
mapfile -d '' -t policy_flags < "$output/rpm-flags.nul"
compiler_flags=${policy_flags[0]}
linker_flags=${policy_flags[1]}
# Fedora's package-notes linker specs require the standard RPM build metadata.
export RPM_ARCH=${policy_flags[2]} RPM_PACKAGE_NAME=${policy_flags[3]}
export RPM_PACKAGE_VERSION=${policy_flags[4]} RPM_PACKAGE_RELEASE=${policy_flags[5]}
. "$package_root/kernel/host-tool-flags.sh" "$compiler_flags"
printf '%s\n' "$HOST_EXTRACFLAGS" > "$output/host-cflags.txt"

build_role() {
    local role=$1 directory="$output/$1" target
    mkdir -p "$directory"
    case "$role" in
        standalone)
            CFLAGS= LDFLAGS= make -C "$kernel_source/tools/bpf/bpftool" \
                OUTPUT="$directory/" EXTRA_CFLAGS="$compiler_flags" \
                EXTRA_LDFLAGS="$linker_flags" -j"$jobs" bootstrap
            target="$directory/bootstrap/bpftool"
            ;;
        perf)
            # Exercise perf's recursive recipe and BTF reader using host BTF;
            # no perf programs or kernel images are compiled by this target.
            target="$directory/util/bpf_skel/.tmp/bootstrap/bpftool"
            make -C "$kernel_source/tools/perf" OUTPUT="$directory/" \
                EXTRA_CFLAGS="$compiler_flags" LDFLAGS="$linker_flags -Wl,-E" \
                CONFIG_PERF_BPF_SKEL=y VMLINUX_BTF=/sys/kernel/btf/vmlinux \
                WERROR=0 NO_LIBUNWIND=1 HAVE_CPLUS_DEMANGLE=1 NO_GTK2=1 \
                NO_STRLCPY=1 NO_BIONIC=1 LIBTRACEEVENT_DYNAMIC=1 \
                -j"$jobs" bpf-skel-prepare
            ;;
        selftests-bpf|selftests-hid|selftests-sched_ext)
            local subtree=${role#selftests-}
            local options=(-C "$kernel_source/tools/testing/selftests/$subtree"
                OUTPUT="$directory" EXTRA_CFLAGS="$compiler_flags"
                EXTRA_LDFLAGS="$linker_flags" VMLINUX_BTF=/sys/kernel/btf/vmlinux)
            target=$(make "${options[@]}" --no-print-directory \
                --eval='gravity-print-bpftool:;@printf "%s\n" "$(DEFAULT_BPFTOOL)"' \
                gravity-print-bpftool | tail -n1)
            test -n "$target"
            make "${options[@]}" -j"$jobs" "$target"
            ;;
        *) printf 'Unknown role: %s\n' "$role" >&2; return 2 ;;
    esac
    "$target" version
    readelf -h "$target" > "$directory/bpftool.elf"
    printf '%s\n' "$target" > "$directory/binary-path.txt"
}

pids=()
for role in "${roles[@]}"; do
    (build_role "$role") > "$output/$role.log" 2>&1 &
    pids+=("$!")
done
failed=0
for i in "${!roles[@]}"; do
    if wait "${pids[$i]}"; then
        printf '%s: PASS\n' "${roles[$i]}"
    else
        printf '%s: FAIL (%s/%s.log)\n' "${roles[$i]}" "$output" "${roles[$i]}" >&2
        failed=1
    fi
done
exit "$failed"
