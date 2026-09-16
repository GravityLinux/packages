#!/usr/bin/env python3
"""Prepare pinned RPM sources and build SRPMs for Gravity Linux (Python 3.11+)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def read_json(name):
    return json.loads((ROOT / name).read_text())


def run(*args, cwd=None, capture=False):
    return subprocess.run(
        [str(x) for x in args], cwd=cwd, check=True,
        stdout=subprocess.PIPE if capture else None,
        text=True,
    ).stdout


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def download(url, target, expected, accept, updates):
    if not expected and not accept:
        raise ValueError(f"Unpinned download: {url}\nRun prepare --update-lock, review downloads.lock.json, then commit it.")
    cache = ROOT / ".work" / "downloads"
    cache.mkdir(parents=True, exist_ok=True)
    item = cache / hashlib.sha256(url.encode()).hexdigest()
    if not item.exists():
        with tempfile.NamedTemporaryFile(dir=cache, delete=False) as out:
            temp = Path(out.name)
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "GravityLinux-packages/1"})
                with urllib.request.urlopen(request, timeout=120) as response:
                    shutil.copyfileobj(response, out)
            except BaseException:
                temp.unlink(missing_ok=True)
                raise
        temp.replace(item)
    actual = checksum(item)
    if expected and actual != expected:
        raise ValueError(f"SHA256 mismatch for {url}: expected {expected}, got {actual}")
    if not expected:
        updates[url] = actual
    shutil.copyfile(item, target)


def blockers(name, recipe, release):
    result = []
    if recipe["kind"] == "git" and not recipe.get("ref"):
        result.append(recipe.get("note", "Pin source commit in sources.json"))
    if name in ("gravity-logos", "bootloader") and not release["artwork_license"]:
        result.append("Set release.json artwork_license (bootloader BuildRequires gravity-logos)")
    if name == "gravity-repos":
        if not release["copr_owner"] or not release["copr_project"]:
            result.append("Set copr_owner and copr_project in release.json")
        if not (ROOT / name / "RPM-GPG-KEY-gravity").is_file():
            result.append("Add the verified COPR public key as gravity-repos/RPM-GPG-KEY-gravity")
    return result


def check(recipes, release):
    for name, recipe in recipes.items():
        spec = ROOT / name / (name + ".spec")
        if not spec.is_file():
            raise ValueError(f"Missing {spec}")
        if recipe["kind"] not in ("git", "local", "spec"):
            raise ValueError(f"Unknown source kind for {name}")
        if recipe["kind"] == "git":
            for field in ("ref", "base_ref"):
                ref = recipe.get(field)
                if ref and not re.fullmatch(r"[0-9a-f]{40}", ref):
                    raise ValueError(f"{name}: pin a full Git commit hash for {field}")
        for field in ("archive", "root"):
            if field in recipe and ("/" in recipe[field] or recipe[field] in (".", "..")):
                raise ValueError(f"Unsafe {field} for {name}")
        if "%autorelease" in spec.read_text() or "%autochangelog" in spec.read_text():
            raise ValueError(f"{name}: unresolved rpmautospec macro")
    for url, digest in read_json("downloads.lock.json").items():
        if not url.startswith("https://") or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"Invalid download lock: {url}")
    if release["fedora"] != 44:
        raise ValueError("Only Fedora 44 has been configured; rebase specs before changing the target")
    print(f"OK: {len(recipes)} package definitions; run status for pending release inputs.")


def snapshot(recipe, destination, source_dir=None):
    ref = recipe["ref"]
    if not ref:
        raise ValueError("Pin the source commit in sources.json first")
    if source_dir:
        repo = Path(source_dir).resolve()
        if run("git", "status", "--porcelain", cwd=repo, capture=True).strip():
            raise ValueError(f"{repo} has uncommitted changes; commit them and pin the resulting revision")
    else:
        repo = destination.parent / "git-source"
        run("git", "init", "-q", repo)
        run("git", "-C", repo, "remote", "add", "origin", recipe["url"])
        run("git", "-C", repo, "fetch", "--depth=1", "origin", ref)
        if recipe.get("base_ref"):
            run("git", "-C", repo, "fetch", "--depth=1", "origin", recipe["base_ref"])
    resolved = run("git", "-C", repo, "rev-parse", ref + "^{commit}", capture=True).strip()
    if resolved != ref:
        raise ValueError(f"Source ref mismatch: {resolved} != {ref}")
    if recipe.get("base_ref"):
        with destination.open("wb") as out:
            subprocess.run(
                # Two context lines avoid overlapping Fedora's adjacent
                # iomfb-surfaces fix in dcp_platform_probe; retain that fix.
                ["git", "-C", str(repo), "diff", "--no-ext-diff", "--no-textconv",
                 "--binary", "--full-index", "--unified=2",
                 recipe["base_ref"], ref, "--"], stdout=out, check=True,
            )
        return
    # Git archives do not include submodule contents. Refuse silent omissions.
    tree = run("git", "-C", repo, "ls-tree", "-r", ref, capture=True)
    submodules = {line.split("\t", 1)[1] for line in tree.splitlines() if line.startswith("160000 ")}
    if submodules - set(recipe.get("omit_submodules", [])):
        raise ValueError("Source contains unhandled submodules; explicitly vendor or omit them before packaging")
    command = ["git", "-C", str(repo), "archive", "--format=tar", "--prefix=" + recipe["root"] + "/", ref]
    compress = ["xz", "-T2", "-1", "-c"] if destination.name.endswith(".xz") else ["gzip", "-n", "-c"]
    with destination.open("wb") as out:
        archive = subprocess.Popen(command, stdout=subprocess.PIPE)
        try:
            packed = subprocess.run(compress, stdin=archive.stdout, stdout=out, check=False)
        finally:
            archive.stdout.close()
        rc = archive.wait()
    if rc or packed.returncode:
        raise ValueError("Failed to create source archive")


def local_snapshot(package_dir, recipe, destination):
    # Fixed metadata makes the archive reproducible from package contents.
    with tempfile.TemporaryFile() as raw:
        with tarfile.open(fileobj=raw, mode="w") as archive:
            for path in sorted(package_dir.iterdir()):
                if not path.is_file() or path.name.endswith(".spec"):
                    continue
                info = archive.gettarinfo(str(path), recipe["root"] + "/" + path.name)
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ""
                info.mode = 0o755 if path.suffix == ".sh" else 0o644
                with path.open("rb") as stream:
                    archive.addfile(info, stream)
        raw.seek(0)
        with destination.open("wb") as out:
            subprocess.run(["gzip", "-n", "-c"], stdin=raw, stdout=out, check=True)


def unpack_srpm(srpm, destination):
    # Source RPMs in our pinned baseline have flat payloads.
    listing = subprocess.Popen(["rpm2cpio", str(srpm)], stdout=subprocess.PIPE)
    names = subprocess.run(["cpio", "-t", "--quiet"], stdin=listing.stdout, capture_output=True, text=True)
    listing.stdout.close()
    if listing.wait() or names.returncode:
        raise ValueError("Cannot list baseline SRPM")
    for name in names.stdout.splitlines():
        normalized = name.removeprefix("./")
        if "/" in normalized or normalized in (".", ".."):
            raise ValueError(f"Unexpected baseline payload path: {name}")
    converter = subprocess.Popen(["rpm2cpio", str(srpm)], stdout=subprocess.PIPE)
    unpack = subprocess.run(
        ["cpio", "-idm", "--quiet", "--no-absolute-filenames"],
        stdin=converter.stdout, cwd=destination, check=False,
    )
    converter.stdout.close()
    if converter.wait() or unpack.returncode:
        raise ValueError("Cannot unpack baseline SRPM")


def overlay_kernel_configs(sources):
    fragment = (ROOT / "kernel" / "gravity.config").read_text().splitlines()
    for config in sources.glob("kernel-aarch64-16k*-fedora.config"):
        contents = config.read_text()
        for line in fragment:
            if not line.startswith("CONFIG_"):
                continue
            key = line.split("=", 1)[0]
            contents = re.sub(r"^(?:" + key + r"=.*|# " + key + r" is not set)\n", "", contents, flags=re.M)
            contents += line + "\n"
        config.write_text(contents)


def macros(work, release):
    values = {
        "_topdir": str(work), "_sourcedir": str(work / "SOURCES"),
        "_specdir": str(work / "SPECS"),
        "fedora": str(release["fedora"]), "fc44": "1", "dist": ".fc44",
    }
    if release["artwork_license"]:
        values["gravity_artwork_license"] = release["artwork_license"]
    args = ["--target", "aarch64"]
    for key, value in values.items():
        args += ["--define", key + " " + value]
    return args


def prepare(name, recipe, release, args):
    problems = blockers(name, recipe, release)
    # A bootloader SRPM can be prepared before its logo build dependency exists.
    if name == "bootloader":
        problems = []
    if problems:
        raise ValueError("\n".join(problems))
    for command in ("rpmspec", "rpmbuild", "git", "gzip", "xz", "cpio", "rpm2cpio"):
        if not shutil.which(command):
            raise ValueError(f"Missing {command}; use the Fedora environment documented in README.md")
    parent = ROOT / ".work"
    parent.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=name + "-", dir=parent))
    for directory in ("SOURCES", "SPECS", "BUILD", "BUILDROOT", "RPMS", "SRPMS"):
        (work / directory).mkdir()
    sources = work / "SOURCES"
    locks = read_json("downloads.lock.json")
    updates = {}
    base = recipe.get("base_srpm")
    if base:
        srpm = work / "baseline.src.rpm"
        download(base["url"], srpm, base["sha256"], False, updates)
        unpack_srpm(srpm, sources)
        overlay_kernel_configs(sources)
    package_dir = ROOT / name
    for file in package_dir.iterdir():
        if file.is_file() and not file.name.endswith(".spec"):
            shutil.copyfile(file, sources / file.name)
    if not (sources / "LICENSE").exists():
        shutil.copyfile(ROOT / "LICENSE", sources / "LICENSE")
    spec = work / "SPECS" / (name + ".spec")
    shutil.copyfile(package_dir / spec.name, spec)
    if name == "gravity-logos":
        # CLI RPM definitions are not persisted inside an SRPM. Carry the
        # reviewed license into the spec that COPR will rebuild.
        license_value = release["artwork_license"]
        if "\n" in license_value or "%" in license_value:
            raise ValueError("Expected a single-line SPDX license expression")
        spec.write_text("%global gravity_artwork_license " + license_value + "\n" + spec.read_text())
    if name == "gravity-repos":
        owner, project = release["copr_owner"], release["copr_project"]
        if not re.fullmatch(r"@?[A-Za-z0-9_.-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", project):
            raise ValueError("Invalid COPR owner/project")
        template = (sources / "gravity.repo.in").read_text()
        (sources / "gravity.repo").write_text(template.replace("@COPR_OWNER@", owner).replace("@COPR_PROJECT@", project))
        key = (sources / "RPM-GPG-KEY-gravity").read_text()
        if "-----BEGIN PGP PUBLIC KEY BLOCK-----" not in key:
            raise ValueError("Expected an ASCII-armored COPR public key")
    if recipe["kind"] == "git":
        snapshot(recipe, sources / recipe["archive"], args.source_dir)
    elif recipe["kind"] == "local":
        local_snapshot(package_dir, recipe, sources / recipe["archive"])
    opts = macros(work, release)
    expanded = run("rpmspec", *opts, "-P", spec, capture=True)
    for source in re.findall(r"^(?:Source|Patch)\d*:\s*(\S+)", expanded, re.M):
        url = urllib.parse.urlsplit(source)
        filename = Path(url.fragment if url.fragment else url.path).name
        if not filename or "%" in filename:
            raise ValueError(f"Unresolved RPM source: {source}")
        target = sources / filename
        if url.scheme:
            if url.scheme != "https":
                raise ValueError(f"Expected HTTPS source: {source}")
            # Checked-in patch bytes are already pinned by this packaging repo.
            if not target.exists():
                clean_url = urllib.parse.urlunsplit(url._replace(fragment=""))
                download(clean_url, target, locks.get(clean_url), args.update_lock, updates)
        elif not target.is_file():
            raise ValueError(f"Missing RPM source: {filename}")
    if updates:
        locks.update(updates)
        write_json(ROOT / "downloads.lock.json", locks)
    write_json(work / "source-manifest.json", {
        "package": name, "recipe": recipe, "release": release,
        "files": {p.name: checksum(p) for p in sorted(sources.iterdir()) if p.is_file()},
    })
    print(f"Prepared {spec}", flush=True)
    return work, spec, opts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "status", "prepare", "srpm"))
    parser.add_argument("package", nargs="?")
    parser.add_argument("--source-dir", help="Use a clean local checkout of the pinned source commit")
    parser.add_argument("--update-lock", action="store_true", help="Record SHA256 for previously unpinned HTTPS inputs; review before committing")
    parser.add_argument("--outdir", default=str(ROOT / "dist"))
    args = parser.parse_args()
    recipes, release = read_json("sources.json"), read_json("release.json")
    if args.command == "check":
        check(recipes, release)
        return
    if args.command == "status":
        for name, recipe in recipes.items():
            pending = blockers(name, recipe, release)
            print(name + ": " + ("; ".join(pending) if pending else "inputs configured; build validation pending"))
        return
    if args.package not in recipes:
        parser.error("Select a package from: " + ", ".join(recipes))
    work, spec, opts = prepare(args.package, recipes[args.package], release, args)
    if args.command == "srpm":
        # -bs builds source RPMs only; binary BuildRequires belong to mock/COPR.
        run("rpmbuild", *opts, "-bs", spec)
        outdir = Path(args.outdir).resolve()
        outdir.mkdir(parents=True, exist_ok=True)
        artifacts = list((work / "SRPMS").glob("*.src.rpm"))
        if len(artifacts) != 1:
            raise ValueError("Expected exactly one SRPM")
        target = outdir / artifacts[0].name
        if target.exists():
            raise ValueError(f"Refusing to overwrite {target}; bump Release or select a fresh outdir")
        shutil.copyfile(artifacts[0], target)
        shutil.copyfile(work / "source-manifest.json", outdir / (target.name + ".sources.json"))
        print(target)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
