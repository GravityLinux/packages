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
import urllib.error
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


COPR_API = "https://copr.fedorainfracloud.org/api_3"


def resolve(name, recipes):
    """A recipe with "source" builds from another git recipe's pinned source."""
    recipe = recipes[name]
    if "source" not in recipe:
        return recipe
    base = recipes.get(recipe["source"])
    if not base or base["kind"] != "git" or "source" in base:
        raise ValueError(f"{name}: source must name a git recipe")
    return {**base, **recipe}


def spec_version(name):
    """(Version, Release without %{?dist}) of a package spec in this repository."""
    text = (ROOT / name / (name + ".spec")).read_text()
    version = re.search(r"^Version:\s*(\S+)\s*$", text, re.M)
    release = re.search(r"^Release:\s*(\S+?)(?:%\{\?dist\})?\s*$", text, re.M)
    if not version or not release or "%" in version[1] + release[1]:
        raise ValueError(f"{name}: expected literal Version and Release")
    return version[1], release[1]


def rpm_nvr(filename, release):
    """(name, version, release without the dist tag) from an RPM file name."""
    stem = re.fullmatch(r"(.+)\.[A-Za-z0-9_]+\.rpm", filename)
    parts = stem[1].rsplit("-", 2) if stem else []
    if len(parts) != 3:
        raise ValueError(f"Not an RPM file name: {filename}")
    return parts[0], parts[1], parts[2].removesuffix(f".fc{release['fedora']}")


def rpm_git_ref(path, package):
    """The source commit an RPM declares with Provides: PACKAGE(git-ref) = COMMIT."""
    if not shutil.which("rpm"):
        raise ValueError("Missing rpm; use the Fedora environment documented in README.md")
    provides = run("rpm", "-qp", "--qf", "[%{PROVIDES} %{PROVIDEVERSION}\n]", path, capture=True)
    for line in provides.splitlines():
        key, _, value = line.partition(" ")
        if key == f"{package}(git-ref)" and re.fullmatch(r"[0-9a-f]{40}", value):
            return value
    raise ValueError(f"{path.name} does not provide {package}(git-ref)")


def copr_get(path, **query):
    url = f"{COPR_API}/{path}?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(url, headers={"User-Agent": "GravityLinux-packages/1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


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


def rpm_blockers(name, recipe, recipes):
    package = recipe["copr_package"]
    want = resolve(package, recipes)["ref"]
    how = f"build {package} in COPR ({recipe['copr_chroot']}), then run `make pin`"
    if not recipe.get("rpm"):
        return [f"No {package} RPM pinned: {how}"]
    if recipe.get("ref") != want:
        return [f"The pinned {package} RPM is from {recipe.get('ref', '')[:10] or 'an unknown commit'}, "
                f"sources.json {resolve(package, recipes).get('source', package)} is at {want[:10]}: {how}"]
    if recipe["rpm"] not in read_json("downloads.lock.json"):
        return [f"{recipe['rpm']} has no downloads.lock.json hash: run `make pin`"]
    return []


def blockers(name, recipe, release, recipes=None):
    result = []
    if recipe["kind"] == "rpm" and recipes is not None:
        result += rpm_blockers(name, recipe, recipes)
    if recipe["kind"] == "git" and not recipe.get("ref"):
        result.append(recipe.get("note", "Pin source commit in sources.json"))
    if name in ("gravity-logos", "gravity-bootloader") and not release["artwork_license"]:
        result.append("Set release.json artwork_license (gravity-bootloader BuildRequires gravity-logos)")
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
        if recipe["kind"] not in ("git", "local", "spec", "rpm"):
            raise ValueError(f"Unknown source kind for {name}")
        if "source" in recipe:
            resolve(name, recipes)
            spec_version(recipe["source"])
        if recipe["kind"] == "rpm":
            package = recipe.get("copr_package")
            if package not in recipes or "source" not in recipes[package]:
                raise ValueError(f"{name}: copr_package must name a recipe that builds from a git source")
            if not re.fullmatch(r"fedora-\d+-(x86_64|i386|aarch64)", recipe.get("copr_chroot", "")):
                raise ValueError(f"{name}: invalid copr_chroot")
            url = recipe.get("rpm", "")
            if url and not (url.startswith("https://") and Path(urllib.parse.urlsplit(url).path).name.startswith(package + "-")):
                raise ValueError(f"{name}: rpm must be an HTTPS URL of a {package} RPM")
            if recipe.get("ref") and not re.fullmatch(r"[0-9a-f]{40}", recipe["ref"]):
                raise ValueError(f"{name}: pin a full Git commit hash for ref")
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


def verbatim_snapshot(package_dir, recipe, destination):
    # For packages that keep a complete upstream tree here: subdirectories, the
    # spec (a test may read it) and executable bits (Git's 0755/0644) are
    # archived as they are; ownership and times stay fixed.
    with tempfile.TemporaryFile() as raw:
        with tarfile.open(fileobj=raw, mode="w") as archive:
            root = recipe["root"]
            info = tarfile.TarInfo(root)
            info.type, info.mode = tarfile.DIRTYPE, 0o755
            archive.addfile(info)
            for path in sorted(package_dir.rglob("*")):
                name = root + "/" + path.relative_to(package_dir).as_posix()
                if path.is_dir():
                    info = tarfile.TarInfo(name)
                    info.type, info.mode = tarfile.DIRTYPE, 0o755
                    archive.addfile(info)
                    continue
                if not path.is_file():
                    raise ValueError(f"Unsupported entry in {package_dir}: {path}")
                info = archive.gettarinfo(str(path), name)
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ""
                info.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                with path.open("rb") as stream:
                    archive.addfile(info, stream)
        raw.seek(0)
        with destination.open("wb") as out:
            subprocess.run(["gzip", "-n", "-c"], stdin=raw, stdout=out, check=True)


def local_snapshot(package_dir, recipe, destination):
    if recipe.get("verbatim"):
        return verbatim_snapshot(package_dir, recipe, destination)
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
    common = (ROOT / "kernel" / "gravity-aarch64.config").read_text().splitlines()
    apple_16k = (ROOT / "kernel" / "gravity.config").read_text().splitlines()
    apple_16k += (ROOT / "kernel" / "gravity-trim.config").read_text().splitlines()
    other = (ROOT / "kernel" / "gravity-other.config").read_text().splitlines()
    # Fedora checks all config variants of every architecture in %prep, not
    # just the shipped 16K one.
    for config in sources.glob("kernel-*-fedora.config"):
        fragment = common if config.match("kernel-aarch64*-fedora.config") else other
        if config.match("kernel-aarch64-16k*-fedora.config"):
            fragment = common + apple_16k
        contents = config.read_text()
        for line in fragment:
            if not line.startswith("CONFIG_"):
                continue
            key = line.split("=", 1)[0]
            # Fedora compares the spelling too, not just Kconfig semantics.
            if line == key + "=n":
                line = f"# {key} is not set"
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
    if args.rpm and recipe["kind"] != "rpm":
        raise ValueError("--rpm applies to packages that repack a COPR-built RPM")
    # A local --rpm stands in for the pin (test builds).
    problems = blockers(name, recipe, release, None if args.rpm else read_json("sources.json"))
    # A bootloader SRPM can be prepared before its logo build dependency exists.
    if name == "gravity-bootloader":
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
    defines = {}
    if recipe["kind"] == "git" and recipe.get("ref"):
        # Lets a spec name its pinned source commit (e.g. Mesa's version string).
        defines["gravity_git_ref"] = recipe["ref"]
    if recipe.get("source"):
        # Builds of another package's source follow its Version and Release.
        defines["gravity_source_version"], defines["gravity_source_release"] = spec_version(recipe["source"])
    if recipe["kind"] == "rpm":
        # A repack of one RPM built by COPR: its URL (hash in downloads.lock.json),
        # version, release and source commit.
        url = recipe.get("rpm", "")
        if args.rpm:
            local = Path(args.rpm).resolve()
            if not url or Path(urllib.parse.urlsplit(url).path).name != local.name:
                url = (f"https://download.copr.fedorainfracloud.org/results/{release['copr_owner']}/"
                       f"{release['copr_project']}/{recipe['copr_chroot']}/local/{local.name}")
            expected = locks.get(url)
            if expected and checksum(local) != expected:
                raise ValueError(f"{local} does not match the downloads.lock.json hash of {url}")
            shutil.copyfile(local, sources / local.name)
            ref = rpm_git_ref(local, recipe["copr_package"])
            want = resolve(recipe["copr_package"], read_json("sources.json"))["ref"]
            if ref != want:
                raise ValueError(f"{local.name} is from {ref[:10]}, sources.json pins {want[:10]}")
            print(f"Using local {local.name}" + ("" if expected else " (not pinned; test build only)"), flush=True)
        else:
            ref = recipe["ref"]
        package, version, rpm_release = rpm_nvr(Path(urllib.parse.urlsplit(url).path).name, release)
        if package != recipe["copr_package"]:
            raise ValueError(f"{url} is not a {recipe['copr_package']} RPM")
        defines.update(gravity_rpm_url=url, gravity_rpm_version=version,
                       gravity_rpm_release=rpm_release, gravity_git_ref=ref)
    for key, value in defines.items():
        if not re.fullmatch(r"[A-Za-z0-9_.~:/+-]+", value):
            raise ValueError(f"Unexpected characters in {key}: {value}")
    if defines:
        spec.write_text("".join(f"%global {k} {v}\n" for k, v in defines.items()) + spec.read_text())
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


def set_recipe_fields(name, fields):
    """Rewrite string fields of one sources.json recipe in place, keeping the
    file's formatting."""
    path = ROOT / "sources.json"
    text = path.read_text()
    start = text.index(f'\n  "{name}": {{')
    end = text.index("\n  }", start)
    block = text[start:end]
    for key, value in fields.items():
        block, count = re.subn(rf'("{key}": )"[^"]*"', lambda m: m[1] + json.dumps(value), block)
        if count != 1:
            raise ValueError(f"sources.json {name} has no {key} field")
    expected = json.loads(text)
    expected[name].update(fields)
    if json.loads(text[:start] + block + text[end:]) != expected:
        raise ValueError("sources.json update failed")
    path.write_text(text[:start] + block + text[end:])


def pin(name, recipes, release):
    """Pin the newest successful COPR build of the RPM a repack package uses
    that was built from the current source pin."""
    recipe = recipes[name]
    package, chroot = recipe["copr_package"], recipe["copr_chroot"]
    want = resolve(package, recipes)["ref"]
    owner, project = release["copr_owner"], release["copr_project"]
    version, source_release = spec_version(recipes[package]["source"])
    prefix = f"{version}-{source_release}."
    arch = chroot.rsplit("-", 1)[1].replace("i386", "i686")
    builds = copr_get("build/list", ownername=owner, projectname=project, packagename=package,
                      limit=30, order="id", order_type="DESC")["items"]
    for build in builds:
        if not (build.get("source_package") or {}).get("version", "").startswith(prefix):
            continue
        if chroot not in build.get("chroots", []):
            continue
        result = copr_get("build-chroot", build_id=build["id"], chrootname=chroot)
        if result.get("state") != "succeeded":
            continue
        built = copr_get("build-chroot/built-packages", build_id=build["id"], chrootname=chroot)["packages"]
        names = [f"{p['name']}-{p['version']}-{p['release']}.{p['arch']}.rpm" for p in built
                 if p["name"] == package and p["arch"] == arch and not p.get("epoch")]
        if len(names) != 1:
            raise ValueError(f"COPR build {build['id']}: expected one {package}.{arch} RPM, found {names}")
        # The build's result directory. In a project that publishes its
        # repositories by hand, a build is only served from the chroot's
        # devel repository until then; that URL keeps working afterwards.
        file = urllib.parse.quote(names[0], safe="~+")
        candidates = [result["result_url"].rstrip("/") + "/" + file,
                      f"{build['repo_url'].rstrip('/')}/{chroot}/devel/Packages/{file[0].lower()}/{file}"]
        updates = {}
        (ROOT / ".work").mkdir(exist_ok=True)
        target = Path(tempfile.mkdtemp(prefix="pin-", dir=ROOT / ".work")) / names[0]
        for url in candidates:
            try:
                download(url, target, None, True, updates)
                break
            except urllib.error.HTTPError as error:
                print(f"{url}: {error}")
        else:
            raise ValueError(f"Cannot download {names[0]} from COPR build {build['id']}")
        ref = rpm_git_ref(target, package)
        shutil.rmtree(target.parent)
        if ref != want:
            print(f"COPR build {build['id']} ({names[0]}) is from {ref[:10]}, not {want[:10]}; skipped")
            continue
        locks = read_json("downloads.lock.json")
        old = recipe.get("rpm")
        if old and old != url:
            locks.pop(old, None)
        locks[url] = updates[url]
        write_json(ROOT / "downloads.lock.json", locks)
        set_recipe_fields(name, {"rpm": url, "ref": ref})
        print(f"{name}: pinned COPR build {build['id']}, {names[0]} (sha256 {updates[url]})")
        return
    raise ValueError(f"No successful {chroot} COPR build of {package} {prefix}* from {want[:10]}; "
                     "build it first (COPR.md)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "status", "prepare", "srpm", "pin"))
    parser.add_argument("package", nargs="?")
    parser.add_argument("--source-dir", help="Use a clean local checkout of the pinned source commit")
    parser.add_argument("--update-lock", action="store_true", help="Record SHA256 for previously unpinned HTTPS inputs; review before committing")
    parser.add_argument("--rpm", help="Use a local copy of the RPM a repack package pins (test builds)")
    parser.add_argument("--outdir", default=str(ROOT / "dist"))
    args = parser.parse_args()
    recipes, release = read_json("sources.json"), read_json("release.json")
    if args.command == "check":
        check(recipes, release)
        return
    if args.command == "status":
        for name, recipe in recipes.items():
            pending = blockers(name, resolve(name, recipes), release, recipes)
            print(name + ": " + ("; ".join(pending) if pending else "inputs configured; build validation pending"))
        return
    if args.command == "pin":
        names = [args.package] if args.package else [n for n, r in recipes.items() if r["kind"] == "rpm"]
        for name in names:
            if recipes.get(name, {}).get("kind") != "rpm":
                parser.error(f"{name} does not repack a COPR-built RPM")
            pin(name, recipes, release)
        return
    if args.package not in recipes:
        parser.error("Select a package from: " + ", ".join(recipes))
    work, spec, opts = prepare(args.package, resolve(args.package, recipes), release, args)
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
