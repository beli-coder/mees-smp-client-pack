#!/usr/bin/env python3
"""Publish an already-built, pinned Mees SMP .mrpack to the same Modrinth project.

Only VERSION_CREATE is necessary for this workflow. We deliberately do not GET
the project or its versions, since draft projects can return 404 without read
scopes. Existing version conflicts are reported rather than overwritten.
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT_ID = "UaH8nSXH"
API = "https://api.modrinth.com/v2/version"
AGENT = "beli-coder/mees-smp-client-pack/1.0 (https://github.com/beli-coder/mees-smp-client-pack)"
PROFILES = {
    "technical": {
        "manifest": "manifest.json",
        "prefix": "Mees-SMP-Client",
        "label": "Mees SMP Technical",
        "details": "Enhanced graphics, Distant Horizons, mapping, inventory QoL, proximity voice chat, Litematica, MiniHUD, JEI, and technical building tools.",
    },
    "lite": {
        "manifest": "profiles/lite/manifest.json",
        "prefix": "Mees-SMP-Lite",
        "label": "Mees SMP Lite",
        "details": "Performance optimizations, Sodium, Iris shader support, Xaero maps, proximity voice chat, and everyday quality-of-life improvements.",
    },
}


def create_request(profile, token):
    spec = PROFILES[profile]
    manifest = json.loads((ROOT / spec["manifest"]).read_text())
    version = manifest["version"]
    filename = f'{spec["prefix"]}-{version}.mrpack'
    pack = ROOT / "dist" / filename
    if not pack.is_file():
        raise ValueError(f"Built pack not found: {pack}")
    with zipfile.ZipFile(pack) as z:
        index = json.loads(z.read("modrinth.index.json"))
    if index.get("versionId") != version or index.get("dependencies", {}).get("minecraft") != manifest["minecraft"]:
        raise ValueError("Built pack metadata does not match manifest")
    release_version = f"{version}-{profile}"
    metadata = {
        "project_id": PROJECT_ID,
        "name": f'{spec["label"]} {version}',
        "version_number": release_version,
        "changelog": f'{spec["label"]} {version}: {spec["details"]}',
        "dependencies": [],
        "game_versions": [manifest["minecraft"]],
        "version_type": "release",
        "loaders": ["fabric"],
        "featured": False,
        "environment": "client_only",
        "file_parts": ["file"],
        "primary_file": "file",
    }

    boundary = "mees-" + uuid.uuid4().hex
    b = boundary.encode("ascii")
    body = (
        b"--" + b + b"\r\n"
        + b'Content-Disposition: form-data; name="data"\r\n'
        + b"Content-Type: application/json\r\n\r\n"
        + json.dumps(metadata, separators=(",", ":")).encode("utf-8")
        + b"\r\n--" + b + b"\r\n"
        + b'Content-Disposition: form-data; name="file"; filename="' + filename.encode("ascii") + b'"\r\n'
        + b"Content-Type: application/octet-stream\r\n\r\n"
        + pack.read_bytes()
        + b"\r\n--" + b + b"--\r\n"
    )
    request = urllib.request.Request(
        API,
        data=body,
        method="POST",
        headers={
            "Authorization": token,
            "User-Agent": AGENT,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    return request, metadata, hashlib.sha256(pack.read_bytes()).hexdigest()


def publish(profile, token):
    if not token:
        raise ValueError("API_TOKEN_MODRINTH repository secret is missing (VERSION_CREATE scope required)")
    request, metadata, checksum = create_request(profile, token)
    print(f'Publishing {metadata["name"]} ({metadata["version_number"]}) to Modrinth project {PROJECT_ID}', flush=True)
    print(f'Validated .mrpack SHA256: {checksum}', flush=True)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read(4000).decode("utf-8", errors="replace")
        try:
            parsed = json.loads(detail)
            detail = str(parsed.get("description") or parsed.get("error") or parsed)
        except ValueError:
            pass
        if error.code in (400, 409) and ("already" in detail.lower() or "exists" in detail.lower() or "duplicate" in detail.lower()):
            raise ValueError(f'Modrinth version {metadata["version_number"]} may already exist; do not overwrite it. API HTTP {error.code}: {detail}') from None
        if error.code in (401, 403, 404):
            raise ValueError(f'Modrinth HTTP {error.code}: {detail}. Verify project ID {PROJECT_ID}, token VERSION_CREATE scope, and membership/access to the project.') from None
        raise ValueError(f"Modrinth upload rejected (HTTP {error.code}): {detail}") from None
    if not isinstance(result, dict) or not result.get("id"):
        raise ValueError("Unexpected Modrinth API response (no version ID)")
    print(f'Modrinth upload succeeded: {metadata["version_number"]}, version ID {result["id"]}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=tuple(PROFILES), required=True)
    args = parser.parse_args()
    try:
        publish(args.profile, os.environ.get("MODRINTH_TOKEN", ""))
    except (ValueError, urllib.error.URLError, OSError, zipfile.BadZipFile, KeyError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
