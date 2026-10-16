"""Regression: Zoomify's NeoForge-only metadata must not break Fabric locks."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "modpack.py"

class ZoomifyDependencyTest(unittest.TestCase):
    def test_skips_only_neoforge_kotlin(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scripts").mkdir()
            local = root / "scripts" / "modpack.py"
            local.write_text(SOURCE.read_text())
            (root / "manifest.json").write_text(json.dumps({
                "name": "Zoomify test", "version": "0.2.2",
                "minecraft": "26.3", "fabric_loader": "0.19.5",
                "mods": [{"project": "zoomify"}]
            }))
            spec = importlib.util.spec_from_file_location("test_pack_zoomi", local)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            def version(pid, vid, deps):
                return {"id":vid,"project_id":pid,"name":vid,"version_number":"1",
                        "loaders":["fabric"],"game_versions":["26.3"],"version_type":"release",
                        "dependencies":deps,"files":[{
                          "filename":vid+".jar","primary":True,
                          "url":"https://cdn.modrinth.com/"+vid+".jar",
                          "hashes":{"sha1":"1"*40,"sha512":"2"*128},"size":123}]}
            zoom=version("zoom-id","zoom-1",[
                {"dependency_type":"required","project_id":"1vrSzlao"},
                {"dependency_type":"required","project_id":"kotlin-id","version_id":"kotlin-1"}])
            kotlin=version("kotlin-id","kotlin-1",[])
            def fake_api(path, params=None):
                if path=="/project/zoomify": return {"id":"zoom-id"}
                if path=="/project/zoomify/version": return [zoom]
                if path=="/project/kotlin-id": return {"id":"kotlin-id"}
                if path=="/version/kotlin-1": return kotlin
                raise AssertionError("Unexpected API: "+path)
            with patch.object(mod,"api",fake_api):
                mod.lock()
            locked=json.loads((root/"pack.lock.json").read_text())
            self.assertEqual({x["project_id"] for x in locked["mods"]},
                             {"zoom-id","kotlin-id"})
            mod.build()

if __name__=="__main__":
    unittest.main()
