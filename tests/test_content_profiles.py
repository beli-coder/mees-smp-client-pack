"""Staged mandatory content appears in both editions without changing older releases."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMON = {"farmers-delight-refabricated", "naturalist", "skniros-furniture", "travelersbackpack", "origins-legacy"}

class ContentProfilesTests(unittest.TestCase):
    def test_shared_required_content(self):
        for p in ("manifest.json", "profiles/lite/manifest.json"):
            m = json.loads((ROOT / p).read_text())
            slugs = [item["project"] for item in m["mods"]]
            self.assertEqual(len(slugs),len(set(slugs)))
            self.assertEqual(m["version"],"0.4.0")
            self.assertTrue(COMMON.issubset(slugs))
            self.assertIn("distanthorizons",slugs)
            self.assertNotIn("packed-up",slugs)
    def test_technical_is_superset_of_lite(self):
        tech={x["project"] for x in json.loads((ROOT/"manifest.json").read_text())["mods"]}
        lite={x["project"] for x in json.loads((ROOT/"profiles/lite/manifest.json").read_text())["mods"]}
        self.assertTrue(lite.issubset(tech))
        self.assertIn("litematica",tech)
        self.assertNotIn("litematica",lite)
