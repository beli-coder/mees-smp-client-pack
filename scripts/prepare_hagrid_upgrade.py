#!/usr/bin/env python3
"""Create an ISOLATED Fabric 26.3 staging server for the Mees SMP v0.4 upgrade.

This NEVER writes to /opt/minecraft/server or restarts systemd services.
The 0.4.0 client lockfile is the source of truth for seven server JARs:
five content mods, their required Forge Config API Port, and Fabric API.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "profiles" / "lite" / "pack.lock.json"
MC_VERSION = "26.3"
STAGE_PORT = "25575"

SERVER_PROJECTS = {
    "7vxePowz": "Farmer's Delight Refabricated",
    "F8BQNPWX": "Naturalist",
    "pezpt98N": "Skniro's Furniture",
    "rlloIFEV": "Traveler's Backpack",
    "mc1uvRn8": "Origins: Legacy",
    "ohNO6lps": "Forge Config API Port (dependency)",
    "P7dR8mSH": "Fabric API",
}

# Only remove replaced versions in the isolated staging copy, NEVER live.
REPLACED_NAME_PATTERNS = (
    re.compile(r"^fabric-api[-_.]", re.I),
    re.compile(r"^forgeconfigapiport[-_.]", re.I),
    re.compile(r"^farmersdelight[-_.]", re.I),
    re.compile(r"^naturalist[-_.]", re.I),
    re.compile(r"^sknirofurniture[-_.]", re.I),
    re.compile(r"^travelersbackpack[-_.]", re.I),
    re.compile(r"^origins-legacy[-_.]", re.I),
)

# Prevent collisions or unwanted side effects with Hagrid's running network
# services, tunnels, voice UDP, and production backup paths.
STAGE_DISABLED_NAME_PATTERNS = (
    re.compile(r"^geyser", re.I),
    re.compile(r"^floodgate", re.I),
    re.compile(r"^(?:voicechat|simple[-_.]?voice[-_.]?chat)", re.I),
    re.compile(r"^bluemap", re.I),
    re.compile(r"^just[-_.]?enough[-_.]?backups", re.I),
    re.compile(r"^serverpassword", re.I),
    re.compile(r"^chunky", re.I),
)

def load_server_pins(lock_path=LOCK):
    lock = json.loads(Path(lock_path).read_text())
    if lock.get("minecraft") != MC_VERSION or lock.get("version") != "0.4.0":
        raise ValueError("Expected the pinned 0.4.0 / Fabric 26.3 lockfile")
    matches = {entry["project_id"]: entry for entry in lock["mods"]
               if entry.get("project_id") in SERVER_PROJECTS}
    if set(matches) != set(SERVER_PROJECTS):
        raise ValueError(f"Missing locked server mods: {set(SERVER_PROJECTS) - set(matches)}")
    for project_id, entry in matches.items():
        url = urllib.parse.urlparse(entry["url"])
        if url.scheme != "https" or url.hostname != "cdn.modrinth.com":
            raise ValueError(f"Unsafe download URL for {SERVER_PROJECTS[project_id]}")
        if not re.fullmatch(r"[a-fA-F0-9]{128}", entry["sha512"]):
            raise ValueError(f"Missing SHA512 pin for {entry['filename']}")
        if Path(entry["filename"]).name != entry["filename"] or not entry["filename"].endswith(".jar"):
            raise ValueError("Unsafe or non-JAR filename")
    return matches

def read_properties(path):
    props = {}
    if path.exists():
        for raw in path.read_text(errors="replace").splitlines():
            if raw.lstrip().startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            props[key.strip()] = value.strip()
    return props

def isolated_properties(path):
    lines = path.read_text(errors="replace").splitlines() if path.exists() else []
    overrides = {
        "server-ip": "127.0.0.1",
        "server-port": STAGE_PORT,
        "level-name": "mees-upgrade-smoke",
        "enable-rcon": "false",
        "enable-query": "false",
        "query.port": "25576",
        "motd": "Mees SMP 0.4 STAGING — NOT THE LIVE SERVER",
    }
    written = set()
    new_lines = []
    for line in lines:
        if line.lstrip().startswith("#") or "=" not in line:
            new_lines.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in overrides:
            if key not in written:
                new_lines.append(f"{key}={overrides[key]}")
                written.add(key)
        else:
            new_lines.append(line)
    new_lines.extend(f"{k}={v}" for k,v in overrides.items() if k not in written)
    path.write_text("\n".join(new_lines) + "\n")

def should_skip_root(name, level):
    # No live world data is copied during a running-server staging preparation.
    key = name.casefold()
    return (
        name in {".git", ".venv"}
        or key in {"world", "world_nether", "world_the_end", "logs", "crash-reports",
                   "backups", "backup", "bluemap", "cache", "debug"}
        or key.startswith(("world_", "world-", "mees-upgrade-smoke", "web-map"))
        or name == level or name.startswith(level + "_")
    )

def fetch_verified(entry, dest):
    req = urllib.request.Request(entry["url"], headers={
        "User-Agent": "MeesSMP-ServerUpgrade/0.4 (pinned Modrinth downloads)"
    })
    with urllib.request.urlopen(req, timeout=50) as response:
        data = response.read(150_000_001)
    if len(data) > 150_000_000:
        raise ValueError(f"Refusing oversized JAR: {entry['filename']}")
    actual = hashlib.sha512(data).hexdigest()
    if actual.lower() != entry["sha512"].lower():
        raise ValueError(f"SHA512 mismatch for {entry['filename']}; download discarded")
    if entry.get("size") is not None and int(entry["size"]) != len(data):
        raise ValueError(f"Size mismatch for {entry['filename']}; download discarded")
    dest.write_bytes(data)

def make_stage(server, stage, pins):
    server = Path(server).expanduser().resolve(strict=True)
    stage = Path(stage).expanduser().absolute()
    if stage.exists():
        raise ValueError(f"Stage already exists; refusing to overwrite: {stage}")
    if stage == server or server in stage.parents or stage in server.parents:
        raise ValueError("Stage and live server locations must be separate")
    if not (server / "mods").is_dir():
        raise ValueError(f"Missing mods directory under {server}")
    if not (server / "server.properties").exists():
        raise ValueError(f"Missing server.properties under {server}")
    level = read_properties(server / "server.properties").get("level-name", "world")
    if "/" in level or "\\" in level or level in {".", "..", ""}:
        raise ValueError("Unexpected level-name; inspect server.properties manually")

    stage.parent.mkdir(parents=True, exist_ok=True)
    # Protect any copied configuration containing the existing server password.
    old_umask = os.umask(0o077)
    try:
        def ignore(directory, names):
            if Path(directory).resolve() == server:
                return [n for n in names if should_skip_root(n, level)]
            return []
        shutil.copytree(server, stage, ignore=ignore, symlinks=False)
        stage.chmod(0o700)
        isolated_properties(stage / "server.properties")
        moddir = stage / "mods"
        disabled_dir = stage / "mods-disabled-in-staging"
        disabled_dir.mkdir(exist_ok=True)
        replaced, disabled = [], []
        for jar in sorted(moddir.glob("*.jar")):
            if any(p.match(jar.name) for p in STAGE_DISABLED_NAME_PATTERNS):
                shutil.move(str(jar), str(disabled_dir / jar.name))
                disabled.append(jar.name)
            elif any(p.match(jar.name) for p in REPLACED_NAME_PATTERNS):
                jar.unlink()
                replaced.append(jar.name)
        for project_id, entry in pins.items():
            target = moddir / entry["filename"]
            print(f"Downloading and verifying {SERVER_PROJECTS[project_id]}: {target.name}", flush=True)
            fetch_verified(entry, target)
        report = {
            "minecraft": MC_VERSION,
            "stage": str(stage),
            "live_server_unmodified": True,
            "port": int(STAGE_PORT),
            "no_live_world_copied": True,
            "installed": {SERVER_PROJECTS[k]: v["filename"] for k,v in pins.items()},
            "replaced_old_staging_jars": replaced,
            "disabled_staging_only": disabled,
        }
        (stage / "upgrade-staging-report.json").write_text(json.dumps(report, indent=2) + "\n")
        return report
    except Exception:
        # A failed download must NEVER leave a misleading, partly prepared stage.
        if stage.exists():
            shutil.rmtree(stage)
        raise
    finally:
        os.umask(old_umask)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default="/opt/minecraft/server")
    parser.add_argument("--stage", default="~/mees-0.4-staging")
    parser.add_argument("--verify-only", action="store_true",
                        help="Validate pinned dependency list without accessing live files or downloading")
    args = parser.parse_args()
    try:
        pins = load_server_pins()
        print("Verified pinned Fabric 26.3 server-side modules:")
        for project_id, entry in pins.items():
            print(f"  {SERVER_PROJECTS[project_id]}: {entry['filename']}")
        if args.verify_only:
            return 0
        result = make_stage(args.server, args.stage, pins)
        print(f"\nISOLATED STAGE READY: {result['stage']}")
        print(f"Stage server is bound to 127.0.0.1:{STAGE_PORT}, with a FRESH TEST WORLD.")
        print("Hagrid's running server, real world, mod folder and services were NOT changed.")
        print("Now inspect 'systemctl cat minecraft' to identify the installed Fabric launcher.")
        print("Do not copy modded-world content into production until staging tests pass.")
        return 0
    except (ValueError, OSError, KeyError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
