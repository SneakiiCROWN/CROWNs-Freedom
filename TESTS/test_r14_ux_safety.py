"""R14 stand-in acceptance: UX status, preflight and optional Arena failure paths.

No BL4 process or third-party mod code is executed by these tests.
"""
from pathlib import Path
from types import SimpleNamespace as N
import runpy, unittest, time
ROOT=Path(__file__).resolve().parents[1]
S=runpy.run_path(str(ROOT/'TESTS/test_operations_r13.py'))
class UXSafetyR14(S['Operations']):
    def test_release_identity_and_no_game_verified_claim(self):
        self.assertIn('fieldcraft-r', self.g['BUILD_ID'])
        self.assertIn('ECHO FIELDCRAFT', self.g['RELEASE_LABEL'])
    def test_forge_human_readiness_is_read_only(self):
        self.s.forge_stage='NOT_CHECKED'
        original=self.s.spawn_pending
        head,detail=self.call('r14_forge_status')
        self.assertEqual(head,'BACKEND NOT CHECKED')
        self.assertEqual(original,self.s.spawn_pending)
        self.s.forge_stage='READY_NOT_SPAWNED'
        self.assertIn('not proof',self.call('r14_forge_status')[1])
        self.s.forge_stage='REQUEST_SENT_NOT_VERIFIED'
        self.assertIn('No item receipt',self.call('r14_forge_status')[1])
    def test_forge_arm_and_uncertain_request_take_priority_over_old_readbacks(self):
        self.s.forge_stage='READY_NOT_SPAWNED';self.s.spawn_pending=('armed',)
        self.s.spawn_expires=time.monotonic()+7
        self.assertEqual(self.call('r14_forge_status')[0],'AWAITING SECOND CONFIRMATION')
        self.s.forge_uncertain_anchor=self.call('_session_anchor')
        self.assertEqual(self.call('r14_forge_status')[0],'UNRESOLVED NATIVE REQUEST')
    def test_forge_prominent_readiness_button_and_no_fabricated_delivery(self):
        self.s.spawn_view='TOOLS';self.s.forge_compare_view=False
        self.g['redraw']=self.native_redraw
        for size in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
            self.g['viewport']=lambda size=size:size
            self.call('show_page','SPAWN')
            self.assertTrue(self.s.draw_ok,self.s.runtime_failures);self.bounds()
            names=[b['name'] for b in self.s.buttons]
            self.assertIn('CHECK READINESS',names)
            self.assertIn('REQUEST ITEM',names)
        self.s.spawn_pending=('armed',);self.s.spawn_expires=time.monotonic()+7
        self.g['redraw']=self.native_redraw;self.call('show_page','SPAWN')
        names=[b['name'] for b in self.s.buttons]
        self.assertIn('CANCEL REQUEST',names)
        self.assertIn('CHECK READINESS',names)
    def test_arena_unavailable_choice_exception_blocks_before_launch(self):
        self.arena()
        module=self.g['arena_bridge_backend']()
        launched=[]
        module['bl4_arena.arena'].launch=lambda *args:launched.append(1)
        module['bl4_arena.arena_settings'].choice=lambda count:(_ for _ in ()).throw(RuntimeError('loading settings'))
        self.assertFalse(self.call('arena_bridge_request'))
        self.assertFalse(launched)
        self.assertIsNone(self.s.arena_bridge_confirm)
        self.assertIn('ARENA CONFIG UNAVAILABLE',self.s.arena_bridge_status)
    def test_arena_incompatible_choice_blocks_without_preparing_job(self):
        self.arena();module=self.g['arena_bridge_backend']()
        module['bl4_arena.arena_settings'].choice=lambda count:N(waves='one',lot=9)
        self.assertFalse(self.call('arena_bridge_request'))
        self.assertIsNone(self.s.arena_bridge_issued)
        self.assertIn('CONFIG UNAVAILABLE',self.s.arena_bridge_status)
    def test_arena_catalogue_skips_invalid_entries(self):
        self.arena();module=self.g['arena_bridge_backend']()
        catalogue=module['bl4_arena.catalogue'];good=catalogue.ENTRIES[0]
        catalogue.ENTRIES=[N(side=good.side,name=None,definition='junk'),N(side=good.side,name='broken',definition=None),good]
        rows=self.call('arena_bridge_rows',module)
        self.assertEqual(rows,[good])
    def test_arena_does_not_change_selected_target_mid_launch(self):
        self.arena();self.s.arena_bridge_selected=0
        self.s.arena_bridge_issued={'anchor':'test','slots':[]}
        self.assertFalse(self.call('arena_bridge_select',0))
        self.assertEqual(self.s.arena_bridge_selected,0)
        self.assertIn('READ TRACKED FIRST',self.s.arena_bridge_status)
    def test_xp_status_is_bounded_in_ui_not_truncated_in_source_logs(self):
        self.s.xp_status='STATUS/'+('x'*210)
        self.g['redraw']=self.native_redraw
        self.call('r3_open_tool','LOOT','XP')
        self.assertEqual(len(self.s.xp_status),217)
        self.assertTrue(self.s.draw_ok,self.s.runtime_failures)

if __name__=='__main__':unittest.main(argv=[__file__],verbosity=2)
