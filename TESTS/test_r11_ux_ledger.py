"""Pure R11 source/layout semantics; does not import native game modules."""
import ast,runpy,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'SOURCE/__init__.py').read_text(encoding='utf-8')
TREE=ast.parse(SOURCE)
ns={}
for node in TREE.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='R11_RETURN_LABELS' for t in node.targets):
        exec(compile(ast.Module(body=[node],type_ignores=[]),'r11','exec'),ns)
    if isinstance(node,ast.FunctionDef) and node.name=='r11_last_workspace':
        exec(compile(ast.Module(body=[node],type_ignores=[]),'r11','exec'),ns)
class TestR11(unittest.TestCase):
    def test_return_to_last_valid_workspace(self):
        fn=ns['r11_last_workspace'];known={'DASHBOARD','SPAWN','LOOT','BOOSTS'}
        self.assertEqual(fn(['DASHBOARD','SPAWN','LOOT'],known),('SPAWN','FORGE'))
        self.assertEqual(fn(['BOGUS','BOOSTS'],known),('BOOSTS','FLIGHT'))
        self.assertIsNone(fn(['DASHBOARD','not_registered'],known))
        self.assertIsNone(fn('LOOT',known))
        self.assertIsNone(fn(None,known))
        self.assertIsNone(fn([{'danger':'delete'}],known))
        self.assertEqual(fn(['DASHBOARD']*6+['SPAWN'],known),None)
    def test_recent_navigation_only_routes_to_pages(self):
        self.assertIn('BACK TO ',SOURCE)
        self.assertIn('show_page(p)',SOURCE)
        self.assertNotIn('RESTORE ALL",restore',SOURCE)
        self.assertIn('("RESTORE TEMP",restore,False)',SOURCE)
        self.assertIn('SAVE: TEMP',SOURCE)
    def test_identity_and_local_readability(self):
        self.assertIn('BUILD_ID = "5.26.0-echo-fieldcraft-r22"', SOURCE)
        self.assertIn('ART_MOD_FILENAME="CROWNs_Freedom_v5_26_ECHO_Fieldcraft_R22.sdkmod"', SOURCE)
        self.assertIn('ratio is not proof', SOURCE.lower())
        self.assertNotIn('Permanent level/skill-point editing requires separately installed and tested Save Editor', SOURCE)
    def test_source_remains_parseable(self):ast.parse(SOURCE)
if __name__=='__main__':unittest.main(argv=[__file__],verbosity=2)
