"""Offline checks for direct-ID Modrinth publishing without read/lookup calls."""
import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "publish_modrinth.py"

class PublisherTests(unittest.TestCase):
    def test_both_variant_requests_use_project_id_directly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "profiles/lite").mkdir(parents=True)
            (root / "dist").mkdir()
            local = root / "scripts/publish_modrinth.py"
            local.write_text(SOURCE.read_text())
            spec = importlib.util.spec_from_file_location("fake_modrinth_publisher", local)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for profile in ("technical", "lite"):
                entry = mod.PROFILES[profile]
                manifest = {"version": "0.3.0", "minecraft": "26.3"}
                (root / entry["manifest"]).write_text(json.dumps(manifest))
                output = root / "dist" / f'{entry["prefix"]}-0.3.0.mrpack'
                with zipfile.ZipFile(output, "w") as z:
                    z.writestr("modrinth.index.json", json.dumps({
                        "versionId":"0.3.0", "dependencies":{"minecraft":"26.3"}}))
                request, data, _ = mod.create_request(profile, "fake-token")
                self.assertEqual(request.full_url, "https://api.modrinth.com/v2/version")
                self.assertEqual(request.get_method(), "POST")
                self.assertEqual(data["project_id"], "UaH8nSXH")
                self.assertEqual(data["version_number"], f"0.3.0-{profile}")
                self.assertIn(b'"project_id":"UaH8nSXH"', request.data)
                self.assertIn(entry["prefix"].encode(), request.data)
                self.assertIn(b'name="file"', request.data)
                self.assertEqual(data["file_parts"],["file"])
                self.assertEqual(data["primary_file"],"file")
