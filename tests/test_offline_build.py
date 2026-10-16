import importlib.util
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ORIGINAL = Path(__file__).resolve().parent.parent

class PackBuildTests(unittest.TestCase):
    def test_offline_build(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'scripts').mkdir()
            script = root / 'scripts' / 'modpack.py'
            script.write_text((ORIGINAL / 'scripts/modpack.py').read_text())
            manifest = {'name':'Test Pack','summary':'test','version':'0.1.0', 'minecraft':'26.3',
                        'fabric_loader':'0.19.5', 'mods':[{'project':'test'}]}
            (root / 'manifest.json').write_text(json.dumps(manifest))
            file = {'project_id':'fake', 'project_name':'Test Mod', 'version_id':'v1', 'version_number':'1.0.0',
                    'filename':'test.jar', 'url':'https://cdn.modrinth.com/data/test/versions/1/test.jar',
                    'sha1':'1'*40, 'sha512':'2'*128, 'size':100}
            (root / 'pack.lock.json').write_text(json.dumps({
                'schema':1, 'name': 'Test Pack', 'summary':'test', 'version':'0.1.0',
                'manifest_sha256':hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest(),
                'minecraft':'26.3','fabric_loader':'0.19.5', 'mods':[file]}))
            spec = importlib.util.spec_from_file_location('modpack', script)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.build()
            pack = root/'dist'/'Mees-SMP-Client-0.1.0.mrpack'
            before=pack.read_bytes()
            mod.build()
            self.assertEqual(before, pack.read_bytes())
            with zipfile.ZipFile(pack) as z:
                d = json.loads(z.read('modrinth.index.json'))
                self.assertEqual(d['dependencies']['minecraft'],'26.3')
                self.assertEqual(d['files'][0]['env'],{'client':'required','server':'unsupported'})
                self.assertEqual(d['files'][0]['path'],'mods/test.jar')

if __name__=='__main__':
    unittest.main()
