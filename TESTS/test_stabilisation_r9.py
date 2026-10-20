"""R9 integration and failure ownership. Synthetic SDK, never native acceptance."""
from pathlib import Path
from types import SimpleNamespace as NS
import runpy,sys,unittest,json,hashlib
R=Path(__file__).resolve().parents[1]
R8=runpy.run_path(str(R/'TESTS/test_reconciled_r8.py'))
R3=R8['R3']
class StabilisationR9(unittest.TestCase):
    setUp=R3['FullStudioR3'].setUp
    bounds=R3['FullStudioR3'].bounds
    arena=R8['ReconciledR8'].arena
    def call(self,name,*args):return self.g[name](*args)
    def test_reused_slot_is_rejected_before_pointer_resolution(self):
        self.arena();self.call('arena_bridge_request');self.call('arena_bridge_request')
        calls=[];self.slot.handed_ns+=1
        self.slot.pointer=lambda:calls.append('unsafe') or NS()
        self.assertFalse(self.call('arena_bridge_read'));self.assertEqual(calls,[])
        self.assertIn('1 unconfirmed',self.s.arena_bridge_status)
    def test_forge_ambiguous_native_exception_quarantines_same_session(self):
        self.g['pawn']=lambda:R3['ctx']['pawn'];calls=[]
        def native(*args):calls.append(args);raise RuntimeError('may already have spawned')
        self.g['_spawn_api']=lambda:NS(SpawnInventoryFromItemPool=native)
        self.s.spawn_pending=None;self.s.anti_spam_until=0
        self.assertFalse(self.call('spawn_request'));self.assertFalse(calls)
        self.assertFalse(self.call('spawn_request'));self.assertEqual(len(calls),1)
        self.s.anti_spam_until=0
        for _ in range(3):self.assertFalse(self.call('spawn_request'))
        self.assertEqual(len(calls),1)
        self.assertEqual(self.s.forge_stage,'UNCERTAIN_REQUEST_QUARANTINED')
        self.assertEqual(self.s.forge_request_history[-1]['status'],'UNCERTAIN_PARTIAL_POSSIBLE')
        self.g['_session_anchor']=lambda:('other-map','pawn')
        self.assertFalse(self.call('spawn_request'));self.assertIsNotNone(self.s.spawn_pending)
        self.assertEqual(len(calls),1)
    def test_fault_sites_preserve_location_without_private_values(self):
        try:raise ValueError('secret player name / private path')
        except ValueError as exc:self.call('record_runtime_fault','test',exc)
        self.assertEqual(self.s.runtime_failures[-1],{'stage':'TEST','kind':'ValueError'})
        report=self.s.runtime_fault_sites
        self.assertTrue(report['sites']);self.assertEqual(report['sites'][-1]['function'],self._testMethodName)
        self.assertNotIn('secret player name',str(report));self.assertNotIn('private path',str(report))
    def test_palette_cache_tracks_theme_and_alpha_changes(self):
        for theme,alpha,accent in ((0,.9,None),(4,.4,'#CCAA77'),(0,.7,None)):
            self.s.theme_idx=theme;self.s.panel_opacity=alpha;self.s.custom_accent=accent
            self.s.palette_bindings=[]
            self.call('_palette_binding',object(),'box',self.call('theme_color','panel'))
            self.assertTrue(self.s.palette_bindings)
            self.assertEqual(self.s.palette_match_signature,(theme,accent,self.s.background_opacity,alpha))
    def test_illustrated_navigation_fallback_fits_and_never_dispatches_gameplay(self):
        calls=[];self.g['_spawn_api']=lambda:calls.append('spawn')
        self.g['optional_art_image']=lambda *a,**kw:False
        for view in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
            self.g['viewport']=lambda view=view:view
            self.call('show_page','DASHBOARD');self.assertTrue(self.s.draw_ok);self.bounds()
            for name,page in (('ITEM FORGE','SPAWN'),('ENCOUNTER DIRECTOR','ARENA'),('PROGRESSION LAB','LOOT'),('MOVEMENT & FLIGHT','MOTION')):
                self.call('show_page','DASHBOARD')
                target=next(b for b in self.s.buttons if b['name']==name)
                target['run']();self.assertEqual(self.s.page,page)
        self.assertFalse(calls)
    def test_new_art_verified_and_original_bytes_preserved(self):
        expected=json.loads((R/'REFERENCE/R8_ASSET_HASHES.json').read_text())
        for name,sha in expected.items():
            self.assertEqual(hashlib.sha256((R/'CROWN_CC0_ASSETS'/name).read_bytes()).hexdigest(),sha,name)
        for name in ('R9_EXPEDITION','R9_FORGE','R9_ARENA','R9_FLIGHT','R9_DOCK'):
            self.assertTrue(self.call('_verify_png_bytes',name,(R/'CROWN_CC0_ASSETS'/self.g['ART_FILES'][name]).read_bytes()))
    def test_dashboard_and_dock_request_real_registered_art(self):
        art=[];self.s.safe_mode=False;self.g['optional_art_image']=lambda p,key,*args,**kw:art.append(key) or True
        self.call('show_page','DASHBOARD')
        for key in ('R9_EXPEDITION','R9_FORGE','R9_ARENA','R9_FLIGHT'):self.assertIn(key,art)
        self.s.dock_mode='SIDE';self.call('redraw');self.assertIn('R9_DOCK',art)

if __name__=='__main__':unittest.main(argv=[__file__],verbosity=2)
