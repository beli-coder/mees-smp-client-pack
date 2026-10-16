"""Offline resolver regression tests: pinned dependencies and manifest drift."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ORIGINAL = Path(__file__).resolve().parent.parent


def fake_version(pid, vid, name, deps=()):
    return {
        "id": vid, "project_id": pid, "name": name, "version_number": "1.0.0",
        "version_type": "release", "date_published": "2026-10-16T00:00:00Z",
        "game_versions": ["26.3"], "loaders": ["fabric"],
        "dependencies": list(deps),
        "files": [{
            "filename": f"{name}-{vid}.jar", "primary": True,
            "url": f"https://cdn.modrinth.com/data/{pid}/versions/{vid}/{name}.jar",
            "hashes": {"sha1": "1" * 40, "sha512": "2" * 128}, "size": 100,
        }],
    }


class ResolverTests(unittest.TestCase):
    def _run(self, dependency_id="sodium-pinned"):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            script = root / "scripts" / "modpack.py"
            script.write_text((ORIGINAL / "scripts" / "modpack.py").read_text())
            manifest = {"name": "Test", "summary": "testing", "version": "0.2.0",
                        "minecraft": "26.3", "fabric_loader": "0.19.5",
                        "mods": [{"project": "iris"}, {"project": "sodium"}]}
            (root / "manifest.json").write_text(json.dumps(manifest))
            spec = importlib.util.spec_from_file_location("pack_builder_testing", script)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            versions = {
                "iris": fake_version("iris-id", "iris-version", "iris",
                                     [{"dependency_type": "required", "project_id": "sodium-id",
                                       "version_id": dependency_id}]),
                "sodium": fake_version("sodium-id", "sodium-latest", "sodium"),
            }
            pinned = fake_version("sodium-id", "sodium-pinned", "sodium")
            def fake_api(path, params=None):
                if path.startswith("/project/") and path.endswith("/version"):
                    slug = path[len("/project/"):-len("/version")]
                    return [versions[slug]]
                if path.startswith("/project/"):
                    slug = path.split("/")[-1]
                    return {"id": {"iris": "iris-id", "sodium": "sodium-id", "sodium-id": "sodium-id"}[slug]}
                if path == "/version/sodium-pinned":
                    return pinned
                if path == "/version/sodium-other":
                    return fake_version("sodium-id", "sodium-other", "sodium")
                raise AssertionError(f"Unexpected API {path}")
            with patch.object(module, "api", fake_api):
                module.lock()
            locked = json.loads((root / "pack.lock.json").read_text())
            self.assertEqual(len(locked["mods"]), 2)
            self.assertEqual(next(m["version_id"] for m in locked["mods"] if m["project_id"]=="sodium-id"), "sodium-pinned")
            module.build()
            self.assertTrue((root/"dist"/"Mees-SMP-Client-0.2.0.mrpack").exists())
            manifest["mods"].append({"project": "another-mod"})
            (root / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "Manifest changed"):
                module.build()

    def test_uses_hard_pinned_dependency_even_if_root_newer(self):
        self._run()


if __name__ == "__main__":
    unittest.main()
