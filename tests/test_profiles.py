"""Both distribution profiles remain independent and predictable."""
import importlib.util
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / 'scripts' / 'modpack.py'

class ProfilesTests(unittest.TestCase):
    def test_profile_switching_and_independent_builds(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'scripts').mkdir()
            (root/'profiles'/'lite').mkdir(parents=True)
            (root/'scripts'/'modpack.py').write_text(SRC.read_text())
            spec=importlib.util.spec_from_file_location('profile_test', root/'scripts'/'modpack.py')
            module=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for profile, directory in [('technical',root), ('lite',root/'profiles'/'lite')]:
                manifest={'name':'Mees SMP '+profile.title(),'version':'0.3.0',
                          'minecraft':'26.3','fabric_loader':'0.19.5','mods':[{'project':'test'}]}
                mp=directory/'manifest.json';mp.write_text(json.dumps(manifest))
                locked={'schema':1,'name':manifest['name'],'version':'0.3.0','minecraft':'26.3',
                        'fabric_loader':'0.19.5','manifest_sha256':hashlib.sha256(mp.read_bytes()).hexdigest(),
                        'mods':[{'filename':'test.jar','sha1':'1'*40,'sha512':'2'*128,
                                 'url':'https://cdn.modrinth.com/data/test/test.jar','size':120}]}
                (directory/'pack.lock.json').write_text(json.dumps(locked))
                module.set_profile(profile)
                module.build()
            self.assertTrue((root/'dist'/'Mees-SMP-Client-0.3.0.mrpack').exists())
            self.assertTrue((root/'dist'/'Mees-SMP-Lite-0.3.0.mrpack').exists())
            with zipfile.ZipFile(root/'dist'/'Mees-SMP-Lite-0.3.0.mrpack') as z:
                self.assertEqual(json.loads(z.read('modrinth.index.json'))['name'],'Mees SMP Lite')
            module.set_profile('technical')
            self.assertEqual(module.MANIFEST,root/'manifest.json')
