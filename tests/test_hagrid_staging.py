"""Offline tests for the safe Hagrid server-upgrade staging helper."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "prepare_hagrid_upgrade.py"
spec=importlib.util.spec_from_file_location("stage_hagrid_test", SOURCE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class HagridStageTests(unittest.TestCase):
    def test_exact_seven_server_pins_no_client_mods(self):
        pins=mod.load_server_pins()
        self.assertEqual(len(pins),7)
        self.assertEqual(set(pins),set(mod.SERVER_PROJECTS))
        self.assertNotIn("uCdwusMi",pins)  # Distant Horizons stays CLIENT only
        self.assertNotIn("YL57xq9U",pins)  # Iris stays CLIENT only

    def test_staging_never_mutates_live_and_disables_network_services(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            server=root/"live"; mods=server/"mods"
            mods.mkdir(parents=True)
            (server/"server.properties").write_text(
                "server-ip=172.29.5.153\nserver-port=25565\nlevel-name=world\n"
                "enable-rcon=true\n"
            )
            (mods/"geyser-fabric.jar").write_bytes(b"network")
            (mods/"fabric-api-old.jar").write_bytes(b"old")
            (mods/"lithium.jar").write_bytes(b"keep")
            (server/"world").mkdir()
            (server/"world"/"level.dat").write_bytes(b"do-not-copy")
            contents=b"fake-mod"
            sha=hashlib.sha512(contents).hexdigest()
            pins={pid:{
                    "project_id":pid,
                    "filename":f"test-{pid}.jar",
                    "url":"https://cdn.modrinth.com/mock",
                    "sha512":sha,"size":len(contents)
                  } for pid in mod.SERVER_PROJECTS}
            with patch.object(mod,"fetch_verified",side_effect=lambda entry,path:path.write_bytes(contents)):
                report=mod.make_stage(server,root/"stage",pins)
            self.assertTrue((mods/"geyser-fabric.jar").exists())
            self.assertTrue((mods/"fabric-api-old.jar").exists())
            self.assertTrue((server/"world"/"level.dat").exists())
            self.assertFalse((root/"stage"/"world").exists())
            self.assertTrue((root/"stage"/"mods-disabled-in-staging"/"geyser-fabric.jar").exists())
            self.assertFalse((root/"stage"/"mods"/"fabric-api-old.jar").exists())
            self.assertTrue((root/"stage"/"mods"/"lithium.jar").exists())
            self.assertEqual(mod.read_properties(root/"stage"/"server.properties")["server-port"],"25575")
            self.assertEqual(mod.read_properties(root/"stage"/"server.properties")["server-ip"],"127.0.0.1")
            self.assertEqual(mod.read_properties(server/"server.properties")["server-port"],"25565")
            self.assertTrue(report["live_server_unmodified"])

    def test_rejects_stage_inside_live(self):
        with tempfile.TemporaryDirectory() as td:
            server=Path(td)/"server"
            (server/"mods").mkdir(parents=True)
            (server/"server.properties").write_text("level-name=world")
            with self.assertRaisesRegex(ValueError,"locations must be separate"):
                mod.make_stage(server,server/"staging",{})
