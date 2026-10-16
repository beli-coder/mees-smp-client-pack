#!/usr/bin/env python3
"""Resolve Modrinth project dependencies and create a no-JAR-redistribution mrpack.

Commands:
  python scripts/modpack.py lock   # network: resolves and pins exact release metadata
  python scripts/modpack.py build  # offline: builds distributable from committed lock

No third-party Python dependencies. The lockfile is source-controlled.
"""

import argparse
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest.json"
LOCK = ROOT / "pack.lock.json"
API = "https://api.modrinth.com/v2"
ALLOWED_HOSTS = {"cdn.modrinth.com", "github.com", "raw.githubusercontent.com", "gitlab.com"}


def api(path, params=None):
    query = "?" + urllib.parse.urlencode(params) if params else ""
    url = API + path + query
    req = urllib.request.Request(url, headers={"User-Agent": "MeesSMP-PackBuilder/1.0 (Fabric)"})
    with urllib.request.urlopen(req, timeout=35) as response:
        return json.load(response)


def pick_file(version):
    files = [f for f in version.get("files", []) if f["filename"].lower().endswith(".jar")
             and not re.search(r"(?:-sources|-javadoc|-dev)\.jar$", f["filename"].lower())]
    if not files:
        raise ValueError(f"No installable JAR in Modrinth version {version['id']}")
    selected = next((f for f in files if f.get("primary")), files[0])
    if not selected.get("hashes", {}).get("sha512") or not selected["hashes"].get("sha1"):
        raise ValueError(f"Missing SHA1/SHA512 for {selected['filename']}")
    host = urllib.parse.urlparse(selected["url"]).hostname
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"Unapproved distribution host for {selected['filename']}: {host}")
    if not selected["url"].startswith("https://"):
        raise ValueError("Download URL must use HTTPS")
    if "/" in selected["filename"] or "\\" in selected["filename"] or selected["filename"].startswith("."):
        raise ValueError("Unsafe filename")
    return selected


def choose_version(project, minecraft, allow_beta=False):
    params = {
        "loaders": json.dumps(["fabric"]),
        "game_versions": json.dumps([minecraft]),
    }
    versions = api(f"/project/{urllib.parse.quote(project)}/version", params)
    allowed = {"release", "beta"} if allow_beta else {"release"}
    viable = [v for v in versions if v.get("version_type") in allowed and "fabric" in v.get("loaders", [])
              and minecraft in v.get("game_versions", [])]
    if not viable:
        raise ValueError(f"No {'release/beta' if allow_beta else 'release'} Fabric {minecraft} version for {project}."
                         " Consider -- or explicitly set allow_beta: true in manifest.json")
    # Modrinth returns newest first; sort explicitly to avoid undocumented order changes.
    viable.sort(key=lambda v: (v.get("date_published", ""), v["id"]), reverse=True)
    return viable[0]


def lock():
    manifest = json.loads(MANIFEST.read_text())
    mc = manifest["minecraft"]
    selected = {}
    pending = set()
    project_id_cache = {}

    def resolve_project_id(project):
        # A dependency may already have pinned Sodium (or another library)
        # by Modrinth project ID before its slug appears in the manifest.
        # Comparing slug-vs-ID without resolving it can incorrectly pick a
        # second version and falsely report an incompatibility.
        if project in selected:
            return project
        if project not in project_id_cache:
            metadata = api("/project/" + urllib.parse.quote(project, safe=""))
            project_id_cache[project] = metadata["id"]
        return project_id_cache[project]

    def visit(project, *, version_id=None, beta=False, parent="manifest"):
        # Reuse a previously pinned version for a dependency given only by
        # project ID (or for an explicitly requested root given by slug).
        pid = resolve_project_id(project)
        if pid in pending:
            raise ValueError(f"Circular dependency on {pid}")
        if pid in selected:
            if version_id and selected[pid]["version_id"] != version_id:
                raise ValueError(f"VERSION CONFLICT on {pid}: {selected[pid]['version_id']} "
                                 f"and {version_id} requested by {parent}. Resolve manually; don't ship.")
            return

        if version_id:
            version = api("/version/" + urllib.parse.quote(version_id, safe=""))
        else:
            version = choose_version(project, mc, allow_beta=beta)
        if version.get("project_id") != pid:
            raise ValueError(f"Version/project mismatch for {project}: {version.get('project_id')} != {pid}")
        if "fabric" not in version.get("loaders", []) or mc not in version.get("game_versions", []):
            raise ValueError(f"Incompatible required version for {project}: {version['version_number']}")
        file = pick_file(version)
        pending.add(pid)
        selected[pid] = {
            "project_id": pid,
            "project_name": version.get("name", project),
            "version_id": version["id"],
            "version_number": version["version_number"],
            "filename": file["filename"],
            "url": file["url"],
            "sha1": file["hashes"]["sha1"],
            "sha512": file["hashes"]["sha512"],
            "size": file["size"],
        }
        print(f"Pinned: {version.get('name', project)}  {version['version_number']}")
        for dependency in version.get("dependencies", []):
            if dependency.get("dependency_type") != "required":
                continue
            did, dproj = dependency.get("version_id"), dependency.get("project_id")
            if not dproj:
                # A required dependency without a project ID is ambiguous;
                # don't assume that a version ID can be used as a project slug.
                if not did:
                    raise ValueError(f"Required dependency missing identifiers for {project}")
                dep_version = api("/version/" + urllib.parse.quote(did, safe=""))
                dproj = dep_version["project_id"]
            visit(dproj, version_id=did, parent=project, beta=beta)
        pending.remove(pid)

    projects = [item["project"] for item in manifest["mods"]]
    if len(set(projects)) != len(projects):
        raise ValueError("Duplicate project entries in manifest.json")
    for item in manifest["mods"]:
        visit(item["project"], version_id=item.get("version_id"), beta=item.get("allow_beta", False))

    names = [m["filename"] for m in selected.values()]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate JAR filenames across different mods")
    locked = {
        "schema": 1,
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "name": manifest["name"],
        "summary": manifest.get("summary", ""),
        "version": manifest["version"],
        "minecraft": mc,
        "fabric_loader": manifest["fabric_loader"],
        "mods": sorted(selected.values(), key=lambda x: x["filename"].lower()),
    }
    LOCK.write_text(json.dumps(locked, indent=2, ensure_ascii=False) + "\n")
    print(f"\nWrote {LOCK.name}: {len(selected)} mods, including required dependencies.")
    print("Review and commit pack.lock.json before sharing updates.")


def build():
    if not LOCK.exists():
        raise ValueError("pack.lock.json missing; first run: python scripts/modpack.py lock")
    m = json.loads(MANIFEST.read_text())
    l = json.loads(LOCK.read_text())
    for field, value in (("name", m["name"]), ("version", m["version"]),
                         ("minecraft", m["minecraft"]), ("fabric_loader", m["fabric_loader"])):
        if l[field] != value:
            raise ValueError(f"Outdated lock: {field} differs. Run 'lock' and commit it.")
    if l.get("manifest_sha256") != hashlib.sha256(MANIFEST.read_bytes()).hexdigest():
        raise ValueError("Manifest changed since locking. Re-run 'lock' before building.")
    files = []
    seen = set()
    for f in sorted(l["mods"], key=lambda item: item["filename"].lower()):
        if f["filename"] in seen:
            raise ValueError("Duplicate filename")
        seen.add(f["filename"])
        if urllib.parse.urlparse(f["url"]).hostname not in ALLOWED_HOSTS:
            raise ValueError("Unsupported file host")
        if not re.fullmatch(r"[a-fA-F0-9]{128}", f["sha512"]):
            raise ValueError(f"Bad SHA512 for {f['filename']}")
        if not re.fullmatch(r"[a-fA-F0-9]{40}", f["sha1"]):
            raise ValueError(f"Bad SHA1 for {f['filename']}")
        files.append({
            "path": "mods/" + f["filename"],
            "hashes": {"sha1": f["sha1"], "sha512": f["sha512"]},
            "env": {"client": "required", "server": "unsupported"},
            "downloads": [f["url"]],
            "fileSize": f["size"],
        })
    index = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": m["version"],
        "name": m["name"],
        "summary": m.get("summary", ""),
        "files": files,
        "dependencies": {"minecraft": m["minecraft"], "fabric-loader": m["fabric_loader"]},
    }
    out = ROOT / "dist" / f"Mees-SMP-Client-{m['version']}.mrpack"
    out.parent.mkdir(exist_ok=True)
    data = (json.dumps(index, indent=2, ensure_ascii=False) + "\n").encode()
    # Deterministic file metadata -> reproducible .mrpack for unchanged lock.
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        zi = zipfile.ZipInfo("modrinth.index.json", (2020, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        archive.writestr(zi, data)
    print(f"Built {out} with {len(files)} pinned client mods, no bundled JARs.")
    print("SHA256:", hashlib.sha256(out.read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["lock", "build"])
    args = parser.parse_args()
    if args.command == "lock":
        lock()
    else:
        build()

if __name__ == "__main__":
    try:
        main()
    except (ValueError, urllib.error.URLError, KeyError, IndexError) as exc:
        sys.exit(f"ERROR: {exc}")
