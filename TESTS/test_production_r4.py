"""R4 regressions: staged transfer, atomic refusal, ownership and real draw integration."""
from pathlib import Path
from types import SimpleNamespace as NS
import unittest,runpy,tempfile,json,math,hashlib
R=Path(__file__).resolve().parents[1]
R3=runpy.run_path(str(R/'TESTS/test_echo_full_studio_r3.py'))
class ProductionR4(unittest.TestCase):
 setUp=R3['FullStudioR3'].setUp
 def call(self,name,*args,**kwargs):return self.g[name](*args,**kwargs)
 weapon=R3['FullStudioR3'].weapon
 bounds=R3['FullStudioR3'].bounds
 def movement(self):
  component=NS(_get_address=lambda:500,MinAnalogWalkSpeed=100.,MaxWalkSpeed=500.,JumpZVelocity=400.,GravityScale=1.)
  self.g['movement_obj']=lambda:(self.actor,component)
  return component
 def test_all_recipe_schemas_reject_unknown_and_nonfinite_values(self):
  for kind in self.g['RECIPE_KINDS']:
   with self.assertRaises(ValueError):self.call('_recipe_validate',kind,{'arbitrary_command':'spawn'})
  for value in (True,float('nan'),float('inf'),-1.,4.):
   with self.assertRaises(ValueError):self.call('_recipe_validate','MOVEMENT',{'speed':value})
 def test_recipe_weapon_stages_on_same_actor_then_uses_existing_confirm(self):
  w,b=self.weapon();self.assertTrue(self.call('recipe_stage','WEAPON',{'RATE':1.5,'RELOAD':.8}))
  self.assertEqual(b.firerate,4.);self.assertTrue(self.s.weapon_view)
  self.assertFalse(self.call('weapon_apply'));self.assertTrue(self.call('weapon_apply'));self.assertEqual(b.firerate,6.)
  self.assertTrue(self.call('weapon_restore'));self.assertEqual(b.firerate,4.)
 def test_recipe_weapon_missing_field_rejects_entire_draft(self):
  w,b=self.weapon();self.s.weapon_draft={'RATE':1.2};del b.RecoilScale
  self.assertFalse(self.call('recipe_stage','WEAPON',{'RATE':2.,'RECOIL':.5}));self.assertEqual(self.s.weapon_draft,{'RATE':1.2})
 def test_recipe_xp_route_change_cannot_escape_an_owned_modifier(self):
  self.s.xp_route='NATIVE';self.s.xp_owner={};self.s.xp_draft=1.
  self.assertFalse(self.call('recipe_stage','XP',{'scale':2.,'source':'BL4LIVE'}));self.assertEqual(self.s.xp_route,'NATIVE');self.assertEqual(self.s.xp_draft,1.)
 def test_recipe_xp_reopens_correct_workspace_without_applying(self):
  self.call('recipe_open','XP');self.assertTrue(self.call('recipe_stage','XP',{'scale':2.,'source':'NATIVE'}))
  self.assertEqual(self.s.page,'LOOT');self.assertTrue(self.s.xp_view);self.assertIsNone(self.s.xp_read);self.assertIsNone(self.s.xp_owner)
 def test_recipe_combat_preflight_keeps_old_draft_if_any_field_missing(self):
  self.s.sandbox_stage={'OUTGOING':1.};self.g['combat_pair']=lambda k:None
  self.assertFalse(self.call('recipe_stage','COMBAT',{'OUTGOING':2.,'CRITICAL':3.}));self.assertEqual(self.s.sandbox_stage,{'OUTGOING':1.})
 def test_forge_recipe_never_dispatches_and_reveals_selection(self):
  pool=self.g['SPAWN_POOLS'][4];self.s.spawn_search='hidden';self.s.spawn_pending=('old',)
  self.assertTrue(self.call('recipe_stage','FORGE',{'pool':pool[1],'level':33,'count':2}))
  self.assertEqual((self.s.spawn_pool_idx,self.s.spawn_level,self.s.spawn_count),(4,33,2));self.assertEqual(self.s.spawn_search,'');self.assertIsNone(self.s.spawn_pending)
 def test_encounter_recipe_rejects_boss_quantity_and_preserves_pending(self):
  row=next(r for r in self.g['ENCOUNTER_CATALOGUE'] if r[2]=='BOSSES')
  self.assertFalse(self.call('recipe_stage','ENCOUNTER',{'code':row[0],'quantity':2,'distance':1000.}))
  self.s.encounter_job={};old=self.s.encounter_selected
  self.assertFalse(self.call('recipe_stage','ENCOUNTER',{'code':row[0],'quantity':1,'distance':1000.}));self.assertEqual(old,self.s.encounter_selected)
 def test_capacity_recipe_keeps_separate_containers_and_no_bridge(self):
  self.assertTrue(self.call('recipe_stage','CAPACITY',{'container':'BANK','slots':1234}))
  self.assertEqual(self.s.capacity_drafts['BANK'],1234);self.assertEqual(self.s.capacity_drafts['BACKPACK'],40);self.assertIsNone(self.s.capacity_bridge_job)
 def test_recipe_save_overwrite_and_delete_are_revision_bound(self):
  self.g['save_preferences']=lambda:None;self.s.recipe_kind='XP';self.s.xp_route='NATIVE';self.s.xp_draft=2.
  self.assertTrue(self.call('recipe_action','SAVE'));self.s.xp_draft=3.
  self.assertFalse(self.call('recipe_action','SAVE'));self.s.xp_draft=4.
  self.assertFalse(self.call('recipe_action','SAVE'));self.assertEqual(self.s.recipe_library['XP']['1']['values']['scale'],2.)
  self.assertTrue(self.call('recipe_action','SAVE'));self.assertFalse(self.call('recipe_action','DELETE'));self.assertTrue(self.call('recipe_action','DELETE'))
 def test_import_is_validated_reviewed_and_never_auto_applied(self):
  with tempfile.TemporaryDirectory() as td:
   self.g['SETTINGS_DIR']=Path(td);self.s.recipe_kind='XP';self.s.xp_route='NATIVE';self.s.xp_draft=3.
   self.call('recipe_action','SAVE');self.assertTrue(self.call('recipe_transfer',True));self.s.recipe_library={};self.s.xp_draft=1.
   self.assertTrue(self.call('recipe_transfer'));self.assertEqual(self.s.recipe_library,{});self.assertEqual(self.s.xp_draft,1.)
   self.assertTrue(self.call('recipe_transfer',accept=True));self.assertEqual(self.s.recipe_library['XP']['1']['values']['scale'],3.);self.assertEqual(self.s.xp_draft,1.)
 def test_import_stale_preview_and_corrupt_payload_do_not_mutate_library(self):
  with tempfile.TemporaryDirectory() as td:
   self.g['SETTINGS_DIR']=Path(td);p=Path(td)/'CROWNs_Freedom_Recipes.json';p.write_text(json.dumps({'format':'CROWN_RECIPES_1','library':{}}))
   self.assertTrue(self.call('recipe_transfer'));self.s.recipe_library={'XP':{}}
   self.assertFalse(self.call('recipe_transfer',accept=True));self.assertEqual(self.s.recipe_library,{'XP':{}})
   p.write_text('{"format":"CROWN_RECIPES_1","library":{"XP":{"1":{"name":"x","values":{"scale":NaN,"source":"NATIVE"}}}}}')
   self.assertFalse(self.call('recipe_transfer'));self.assertEqual(self.s.recipe_library,{'XP':{}})
 def test_library_round_trips_sdk_preferences(self):
  with tempfile.TemporaryDirectory() as td:
   self.g['SETTINGS_DIR']=Path(td);self.s.recipe_kind='XP';self.s.xp_route='NATIVE';self.s.xp_draft=2.
   self.assertTrue(self.call('recipe_action','SAVE'));self.s.recipe_library={};self.call('load_preferences')
   self.assertEqual(self.s.recipe_library['XP']['1']['values']['scale'],2.)
 def test_motion_staging_has_no_writes_and_batch_applies_then_restores(self):
  c=self.movement();self.call('motion_stage','speed',2.);self.call('motion_stage','jump',1.5);self.assertEqual(c.MaxWalkSpeed,500.)
  self.assertTrue(self.call('motion_apply'));self.assertEqual(c.MaxWalkSpeed,1000.);self.assertEqual(c.JumpZVelocity,600.)
  self.assertTrue(self.call('restore_motion'));self.assertEqual(c.MaxWalkSpeed,500.);self.assertEqual(c.JumpZVelocity,400.);self.assertFalse(self.s.motion_originals)
 def test_motion_restore_does_not_overwrite_external_change(self):
  c=self.movement();self.call('tune_motion','speed',2.);c.MaxWalkSpeed=1500.
  self.call('restore_motion');self.assertEqual(c.MaxWalkSpeed,1500.);self.assertIn('MaxWalkSpeed',self.s.motion_originals)
  self.assertFalse(self.call('tune_motion','jump',2.));self.assertEqual(c.JumpZVelocity,400.)
 def test_motion_partial_batch_failure_rolls_back_owned_fields(self):
  c=self.movement();native=self.g['_motion_tune_r3'];self.g['_motion_tune_r3']=lambda mode,value:False if mode=='jump' else native(mode,value)
  self.s.motion_draft={'speed':2.,'jump':2.};self.assertFalse(self.call('motion_apply'));self.assertEqual(c.MaxWalkSpeed,500.);self.assertFalse(self.s.motion_originals);self.assertEqual(self.s.motion_draft,{'speed':2.,'jump':2.})
 def test_motion_context_change_does_not_touch_old_component(self):
  c=self.movement();self.call('tune_motion','gravity',.5);self.g['_session_anchor']=lambda:('new','pawn')
  self.assertFalse(self.call('restore_motion'));self.assertEqual(c.GravityScale,.5);self.assertFalse(self.s.motion_originals)
 def sample(self):
  state=NS(ExperiencePoints=100,ExperienceLevel=3);pc=NS(PlayerState=NS(ExperienceState=[state]));self.g['get_pc']=lambda **kw:pc
  return state
 def test_farm_observes_xp_and_manual_drops_without_changing_game_state(self):
  xp=self.sample();self.assertTrue(self.call('farm_action','START'));xp.ExperiencePoints=220
  self.call('farm_action','DROP');self.call('farm_action','LAP');self.assertEqual(self.s.farm_run['xp'],120);self.assertEqual(xp.ExperiencePoints,220)
  self.call('farm_action','STOP');self.assertFalse(self.s.farm_run['running']);self.assertEqual(self.s.farm_history[-1]['drops'],1)
 def test_farm_level_or_context_change_invalidates_xp(self):
  xp=self.sample();self.call('farm_action','START');xp.ExperienceLevel=4;self.call('farm_action','STOP');self.assertIsNone(self.s.farm_history[-1]['xp'])
  self.call('farm_action','START');self.g['_session_anchor']=lambda:('new','pawn');self.call('farm_action','LAP');self.assertFalse(self.s.farm_run['running']);self.assertIsNone(self.s.farm_history[-1]['xp'])
 def test_farm_bounds_and_clear_requires_stopped_run(self):
  self.sample();self.call('farm_action','START');self.assertFalse(self.call('farm_action','CLEAR'));self.call('farm_action','UNDO');self.assertEqual(self.s.farm_run['drops'],0)
  for i in range(30):self.call('farm_action','LAP')
  self.assertEqual(len(self.s.farm_run['laps']),20);self.call('farm_action','STOP');self.assertTrue(self.call('farm_action','CLEAR'))
 def test_all_new_workspaces_fit_and_native_controls_do_not_overlap(self):
  for w,h in ((2560,1440),(1920,1080),(1280,720),(854,480)):
   self.g['viewport']=lambda w=w,h=h:(w,h)
   self.call('recipe_open','FORGE');self.assertTrue(self.s.draw_ok,self.s.message);self.bounds()
   self.call('farm_open');self.assertTrue(self.s.draw_ok,self.s.message);self.bounds()
   self.s.recipe_open=False;self.s.farm_view=False;self.call('show_page','MOTION');self.assertTrue(self.s.draw_ok,self.s.message);self.bounds()
   self.s.dock_mode='SIDE';self.s.dock_view='FARM';self.call('redraw');self.assertTrue(self.s.draw_ok,self.s.message);self.bounds();self.assertEqual(self.s.farm_generation,self.s.frame_generation)
   self.s.dock_mode='FULL'
 def test_controller_back_closes_library_and_farm_without_closing_menu(self):
  self.call('show_page','SPAWN');self.call('recipe_open','FORGE');self.call('_controller_back');self.assertEqual(self.s.page,'SPAWN');self.assertTrue(self.s.opened)
  self.call('farm_open');self.call('_controller_back');self.assertFalse(self.s.farm_view);self.assertTrue(self.s.opened)
 def test_dock_profiles_include_layout_and_reject_invalid_atomically(self):
  self.g['save_preferences']=lambda:None;self.s.dock_width=510.;self.s.dock_right=True;self.call('save_ui_profile',1);self.s.dock_width=400.;self.s.dock_right=False
  self.assertTrue(self.call('load_ui_profile',1));self.assertEqual(self.s.dock_width,510.);self.assertTrue(self.s.dock_right)
  self.s.ui_profiles['1']['studio_dock']['width']=900.;old=self.s.theme_idx;self.assertFalse(self.call('load_ui_profile',1));self.assertEqual(self.s.theme_idx,old);self.assertEqual(self.s.dock_width,510.)
 def test_dependencies_missing_return_specific_status_without_importing(self):
  before=set(R3['sys'].modules);lines=self.call('encounter_dependency_readback');self.assertTrue(any('MISSING' in x for x in lines));self.assertEqual(set(R3['sys'].modules),before)
 def test_r4_art_bytes_and_main_and_dock_draw_paths(self):
  for key in self.g['ART_FILES']:
   if key.startswith('R4_'):self.assertTrue(self.call('_verify_png_bytes',key,(R/'CROWN_CC0_ASSETS'/self.g['ART_FILES'][key]).read_bytes()))
  calls=[];self.g['optional_art_image']=lambda parent,key,*a,**kw:calls.append(key) or True
  self.call('show_page','DASHBOARD');self.assertIn('R9_EXPEDITION',calls);self.assertIn('R9_FORGE',calls)
  self.s.dock_mode='SIDE';self.call('redraw');self.assertIn('R9_DOCK',calls)
if __name__=='__main__':unittest.main(argv=[__file__],verbosity=2)
