"""R15 source-level recovery flows. No BL4 process or optional mod code executed."""
from pathlib import Path
from types import SimpleNamespace as N
import runpy, unittest
R=Path(__file__).resolve().parents[1]
P=runpy.run_path(str(R/'TESTS/test_operations_r13.py'))

class RecoveryR15(P['Operations']):
    def test_release_identity(self):
        self.assertIn('fieldcraft-r', self.g['BUILD_ID'])
        self.assertIn('ECHO FIELDCRAFT', self.g['RELEASE_LABEL'])
        self.assertTrue(self.g['ART_MOD_FILENAME'].endswith('ECHO_Fieldcraft_R22.sdkmod'))
    def test_empty_forge_workbench_has_recovery_action(self):
        self.g['_forge_selection']=lambda:None
        self.g['redraw']=self.native_redraw
        self.s.forge_compare_view=False;self.s.spawn_view='TOOLS'
        for size in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
            self.g['viewport']=lambda size=size:size
            self.call('show_page','SPAWN')
            self.assertTrue(self.s.draw_ok,self.s.runtime_failures)
            self.assertIn('SHOW ALL ITEMS',[b['name'] for b in self.s.buttons])
            self.bounds()
    def test_recover_forge_filters_clears_only_local_drafts(self):
        self.s.spawn_search='does-not-exist';self.s.spawn_search_draft=self.s.spawn_search
        self.s.spawn_category_idx=self.g['SPAWN_CATEGORIES'].index('FAVORITES')
        self.s.spawn_pending=('armed',);self.s.spawn_expires=100.
        self.s.forge_blueprint_pending=('armed',)
        self.s.forge_request_history=[{'status':'UNCERTAIN'}]
        self.s.forge_uncertain_anchor=('unresolved','native')
        self.assertTrue(self.call('forge_recover_catalogue'))
        self.assertEqual(self.s.spawn_search,'')
        self.assertEqual(self.s.spawn_category_idx,self.g['SPAWN_CATEGORIES'].index('ALL'))
        self.assertIsNone(self.s.spawn_pending)
        self.assertEqual(self.s.spawn_view,'BROWSE')
        self.assertEqual(self.s.forge_uncertain_anchor,('unresolved','native'))
        self.assertEqual(len(self.s.forge_request_history),1)
    def test_preflight_keeps_native_uncertainty_quarantined(self):
        self.s.forge_uncertain_anchor=self.call('_session_anchor')
        self.g['_spawn_api']=lambda:self.fail('must not query item pool while quarantined')
        self.assertFalse(self.call('forge_preflight'))
        self.assertEqual(self.s.forge_stage,'UNCERTAIN_REQUEST_QUARANTINED')
        self.assertIsNotNone(self.s.forge_uncertain_anchor)
    def test_arena_dependency_change_has_actionable_status(self):
        self.s.arena_bridge_issued={'anchor':self.call('_session_anchor'),'backend':{'sentinel':object()},'uncertain':True,'slots':[]}
        self.g['arena_bridge_backend']=lambda:None
        self.assertFalse(self.call('arena_bridge_read',quiet=True))
        self.assertIn('BACKEND CHANGED',self.s.arena_bridge_status)
        self.assertIsNotNone(self.s.arena_bridge_issued)
    def test_tracked_arena_launch_is_readable_outside_controls_view(self):
        self.arena()
        self.s.arena_bridge_issued={'anchor':self.call('_session_anchor'),'slots':[]}
        self.s.encounter_route='ARENA';self.s.encounter_view='CATALOGUE'
        self.g['redraw']=self.native_redraw
        self.g['viewport']=lambda:(1920.,1080.)
        self.call('show_page','ARENA')
        self.assertTrue(self.s.draw_ok,self.s.runtime_failures)
        self.assertIn('READ TRACKED LAUNCH',[b['name'] for b in self.s.buttons])
        self.bounds()

if __name__=='__main__':unittest.main(argv=[__file__],verbosity=2)
