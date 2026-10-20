"""Optional adapters tested with original stand-ins, never executing supplied third-party source."""
from pathlib import Path
from types import SimpleNamespace as NS
import unittest,runpy,sys,hashlib
R=Path(__file__).resolve().parents[1]
R3=runpy.run_path(str(R/'TESTS/test_echo_full_studio_r3.py'))
class ReconciledR8(unittest.TestCase):
 setUp=R3['FullStudioR3'].setUp
 bounds=R3['FullStudioR3'].bounds
 def call(self,name,*args,**kw):return self.g[name](*args,**kw)
 def arena(self):
  self.entry=NS(side='enemies',name='Test enemy',definition='Char_Test')
  self.count=0;self.dead=False;self.destroyed=[];self.launches=[];self.slot=None
  self.modules={'bl4_arena':NS(mod=NS(is_enabled=True)),
    'bl4_arena.catalogue':NS(ENTRIES=[self.entry]),'bl4_arena.arena_settings':NS(choice=lambda n:NS(lot=n,waves=1)),
    'bl4_arena.cart':NS(Arena=lambda **kw:NS(**kw),Line=lambda *args:args),'bl4_arena.spawners':NS(POOL=[]),
    'bl4_arena.waves':NS(pending=lambda:False,endless=lambda:False)}
  def launch(cart):
   self.launches.append(cart);spawner=NS(SpawnerComponent=NS(GetNumAliveActors=lambda n:self.count,HaveAllDied=lambda n:self.dead),K2_DestroyActor=lambda:self.destroyed.append(1))
   self.slot=NS(handed_ns=1,definition='Char_Test',pointer=lambda:spawner)
   self.modules['bl4_arena.spawners'].POOL.append(self.slot)
   return NS(refusal='',asked=1,wanted=1)
  self.modules['bl4_arena.arena']=NS(launch=launch)
  self.g['arena_bridge_backend']=lambda:self.modules;return self.modules
 def test_reconciliation_contains_both_branches(self):
  for name in ('recipe_stage','motion_apply','farm_action','start_noclip_flight_boost','community_request','community_native_request','_maybe_warmup_art','xp_external_request','arena_bridge_request'):
   self.assertTrue(callable(self.g[name]),name)
  pages=[p for rows in self.g['STUDIO_SECTIONS'].values() for p in rows]
  self.assertEqual(len(pages),len(set(pages)));self.assertIn('BOOSTS',pages);self.assertIn('COMMUNITY',pages)
 def test_arena_first_press_does_not_call_foreign_launch(self):
  self.arena();self.assertFalse(self.call('arena_bridge_request'));self.assertEqual(self.launches,[])
  self.assertTrue(self.call('arena_bridge_request'));self.assertEqual(len(self.launches),1);self.assertIn('not yet confirmed',self.s.arena_bridge_status)
 def test_arena_confirm_invalidated_by_character_or_count(self):
  self.arena();self.call('arena_bridge_request');self.s.encounter_quantity=2;self.assertFalse(self.call('arena_bridge_request'));self.assertFalse(self.launches)
  self.g['_session_anchor']=lambda:('other','pawn');self.assertFalse(self.call('arena_bridge_request'));self.assertFalse(self.launches)
 def test_arena_refuses_endless_preferences_without_modifying_them(self):
  modules=self.arena();choice=NS(lot=1,waves=None);modules['bl4_arena.arena_settings'].choice=lambda n:choice
  self.assertFalse(self.call('arena_bridge_request'));self.assertFalse(self.launches);self.assertIsNone(choice.waves)
 def test_arena_tracks_birth_and_end_without_destroying_actor(self):
  self.arena();self.call('arena_bridge_request');self.call('arena_bridge_request')
  self.assertFalse(self.call('arena_bridge_read'));self.assertIsNotNone(self.s.arena_bridge_issued)
  self.count=1;self.assertTrue(self.call('arena_bridge_read'));self.assertIn('1 live',self.s.arena_bridge_status)
  self.count=0;self.dead=True;self.assertTrue(self.call('arena_bridge_read'));self.assertIsNone(self.s.arena_bridge_issued);self.assertFalse(self.destroyed)
 def test_arena_slot_reuse_never_claims_other_launch(self):
  self.arena();self.call('arena_bridge_request');self.call('arena_bridge_request');self.slot.handed_ns=2;self.count=1
  self.assertFalse(self.call('arena_bridge_read'));self.assertIn('1 unconfirmed',self.s.arena_bridge_status);self.assertFalse(self.destroyed)
 def test_arena_exception_quarantines_retries(self):
  modules=self.arena();modules['bl4_arena.arena'].launch=lambda c:(_ for _ in ()).throw(RuntimeError('partial'))
  self.call('arena_bridge_request');self.assertFalse(self.call('arena_bridge_request'));job=self.s.arena_bridge_issued
  self.assertIsNotNone(job);self.assertFalse(self.call('arena_bridge_request'));self.assertIs(self.s.arena_bridge_issued,job)
 def test_arena_travel_retires_observer_without_native_reads(self):
  self.arena();self.call('arena_bridge_request');self.call('arena_bridge_request');self.slot.pointer=lambda:(_ for _ in ()).throw(AssertionError('stale native read'))
  self.g['_session_anchor']=lambda:('new','pawn');self.assertFalse(self.call('arena_bridge_read'));self.assertIsNone(self.s.arena_bridge_issued)
 def test_arena_true_refusal_allows_fresh_confirmation(self):
  modules=self.arena();modules['bl4_arena.arena'].launch=lambda c:NS(refusal='cap',asked=0,wanted=1)
  self.call('arena_bridge_request');self.assertFalse(self.call('arena_bridge_request'));self.assertIsNone(self.s.arena_bridge_issued)
 def test_arena_backend_requires_every_reviewed_module_and_enabled_state(self):
  real=self.g['arena_bridge_backend'];mods={name:NS() for name in self.g['REVIEWED_OPTIONAL_R8'] if name.startswith('bl4_arena')}
  self.g['_reviewed_module']=lambda names,expected:mods.get(names[0]);mods['bl4_arena'].mod=NS(is_enabled=False)
  self.assertIsNone(real());mods['bl4_arena'].mod.is_enabled=True;mods.pop('bl4_arena.spawners');self.assertIsNone(real())
 def test_arena_all_views_and_controller_bounds(self):
  self.arena();self.s.encounter_route='ARENA'
  for wh in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
   self.g['viewport']=lambda wh=wh:wh
   for view in ('CATALOGUE','CONTROLS','SEARCH'):
    self.s.encounter_view=view;self.call('show_page','ARENA');self.assertTrue(self.s.draw_ok,self.s.message);self.bounds()
 def xp(self):
  player=NS(_get_address=lambda:925)
  self.module=NS(xp_multiplier=NS(value=1.5),mod=NS(is_enabled=True),_player_state=lambda:player);self.commands=[]
  self.g['_reviewed_module']=lambda names,expected:self.module if names==('xp_gain_multiplier',) else None
  self.g['xp_external_backend']=lambda:('XP GAIN MULTIPLIER','xp_mult','xp_mult_status')
  def command(value):
   self.commands.append(value)
   if value.startswith('xp_mult '):self.module.xp_multiplier.value=float(value.split()[1])
  controller=NS(ConsoleCommand=command,PlayerState=player,_get_address=lambda:924)
  self.g['get_pc']=lambda **kw:controller
 def test_external_fractional_xp_draft_separate_and_confirmed(self):
  self.xp();self.assertTrue(self.call('xp_external_stage',.5));self.assertEqual(self.s.xp_draft,1.)
  self.assertFalse(self.call('xp_external_request'));self.assertFalse(self.commands);self.assertTrue(self.call('xp_external_request'))
  self.assertEqual(self.commands,['xp_mult 0.50']);self.assertIn('CONFIG READBACK 0.5x',self.s.xp_external_status);self.assertIn('unverified',self.s.xp_external_status)
 def test_external_xp_owned_conflict_and_disabled_mod_block_commands(self):
  self.xp();self.s.xp_owner={};self.assertFalse(self.call('xp_external_request'));self.assertFalse(self.commands)
  self.s.xp_owner=None;self.module.mod.is_enabled=False;self.assertFalse(self.call('xp_external_request'));self.assertFalse(self.commands)
 def test_native_xp_blocked_by_independent_reward_owner(self):
  before=sys.modules.get('xp_gain_multiplier');sys.modules['xp_gain_multiplier']=NS(mod=NS(is_enabled=True))
  try:self.assertIsNone(self.call('native_xp_backend'))
  finally:
   if before is None:sys.modules.pop('xp_gain_multiplier',None)
   else:sys.modules['xp_gain_multiplier']=before
 def test_foreign_bl4live_xp_owner_blocks_external_requests(self):
  self.xp();old=sys.modules.get('bl4_live');sys.modules['bl4_live']=NS(_RUNTIME_XP_MODIFIERS=[object()],_RUNTIME_STATE={'experience_reward_scale':2.})
  try:self.assertFalse(self.call('xp_external_request'));self.assertFalse(self.commands)
  finally:
   if old is None:sys.modules.pop('bl4_live',None)
   else:sys.modules['bl4_live']=old
 def test_xp_owner_guard_still_allows_explicit_owned_restore_path(self):
  old=sys.modules.get('xp_gain_multiplier');sys.modules['xp_gain_multiplier']=NS(mod=NS(is_enabled=True));sentinel=object();self.g['_xp_backend_r7']=lambda:sentinel
  try:
   self.assertIsNone(self.call('xp_backend'));self.s.r8_xp_restoring=True;self.assertIs(self.call('xp_backend'),sentinel)
  finally:
   if old is None:sys.modules.pop('xp_gain_multiplier',None)
   else:sys.modules['xp_gain_multiplier']=old
 def test_xp_two_track_delta_and_level_change_baseline(self):
  rows=[NS(ExperiencePoints=100,ExperienceLevel=2),NS(ExperiencePoints=200,ExperienceLevel=3)]
  self.g['get_pc']=lambda **kw:NS(PlayerState=NS(ExperienceState=rows))
  self.assertTrue(self.call('xp_tracks_sample'));rows[0].ExperiencePoints=120;rows[1].ExperiencePoints=250
  self.assertTrue(self.call('xp_tracks_sample'));self.assertIn('Character +20 / Specialisation +50',self.s.xp_dual_status)
  rows[0].ExperienceLevel=3;rows[0].ExperiencePoints=0;self.call('xp_tracks_sample');self.assertTrue(self.s.xp_dual_status.startswith('BASELINE'))
 def test_external_xp_surface_and_added_pages_fit(self):
  for wh in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
   self.g['viewport']=lambda wh=wh:wh
   for page in ('BOOSTS','COMMUNITY'):
    self.call('show_page',page);self.assertTrue(self.s.draw_ok,self.s.message);self.bounds()
   self.call('show_page','LOOT');self.s.xp_view=True;self.s.xp_external_view=True;self.call('redraw');self.assertTrue(self.s.draw_ok,self.s.message);self.bounds()
if __name__=='__main__':unittest.main(argv=[__file__],verbosity=2)
