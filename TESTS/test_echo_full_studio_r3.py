"""R3 behavior/ownership checks. Synthetic SDK only; no native game claims."""
from pathlib import Path
from types import SimpleNamespace as NS
import runpy,sys,unittest,tempfile,math,json,zipfile,wave
R=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(R/'TESTS/test_arsenal_events.py'))
SOURCE=(R/'SOURCE/__init__.py').read_text(encoding='utf-8')
class AttributeLibrary:
 def __init__(self):self.base=2.;self.handles={};self.calls=[];self.fail_add=False;self.bad_return=False;self.fail_remove=False;self.stale=False
 def GetValueOfAttribute(self,**kw):
  value=self.base
  for scale in self.handles.values():value*=scale
  return 8. if self.stale else value
 def AddModifierToGbxAttribute(self,**kw):
  self.calls.append(('ADD',kw));handle=object();self.handles[handle]=kw['modifiervalue']
  return handle if self.bad_return else (handle,1 if self.fail_add else 0)
 def RemoveModifierFromGbxAttribute(self,**kw):
  self.calls.append(('REMOVE',kw));handle=kw['ModifierHandle']
  if self.fail_remove:return handle,1
  self.handles.pop(handle,None);return handle,0
class FullStudioR3(unittest.TestCase):
 def setUp(self):
  sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
  self.g={'__name__':'crown_r3_test'};exec(compile(SOURCE,'crown_r3','exec'),self.g)
  self.s=self.g['State'];self.s.safe_mode=True;self.s.dock_mode='FULL';self.g['open_menu']();self.assertTrue(self.s.draw_ok)
  self.actor=NS(_get_address=lambda:42,HasAuthority=lambda:True)
  self.g['pawn']=lambda:self.actor;self.g['_session_anchor']=lambda:('map','pawn');self.g['session_role']=lambda:'SOLO'
 def call(self,name,*args):return self.g[name](*args)
 def native(self):
  library=AttributeLibrary();a=self.g['NativeCombatXP'](self.actor,('map','pawn'),library,object())
  self.s.native_xp_adapter=a;self.s.xp_route='NATIVE';return a,library
 def weapon(self):
  b=NS(_get_address=lambda:900,Class=NS(Name='WeaponFireReloadBehavior'),firerate=4.,ReloadTime=2.,heatimpulse=1.,RecoilScale=.5,spread=.8,accuracyimpulse=.3)
  weapon=NS(_get_address=lambda:800,Owner=self.actor,behaviors=[b])
  self.g['unrealsdk'].find_all=lambda cls,exact:[weapon] if cls=='Weapon' else []
  self.assertTrue(self.call('weapon_read'));return weapon,b
 def bounds(self):
  x,y,w,h,*_=self.s.panel_rect
  for i,a in enumerate(self.s.buttons):
   ax,ay,aw,ah=a['rect'];self.assertTrue(x-1<=ax and ax+aw<=x+w+1 and y-1<=ay and ay+ah<=y+h+1,a['name'])
   for b in self.s.buttons[i+1:]:
    bx,by,bw,bh=b['rect'];self.assertTrue(min(ax+aw,bx+bw)-max(ax,bx)<=1 or min(ay+ah,by+bh)-max(ay,by)<=1,(a['name'],b['name']))
 def test_navigation_preserves_every_registered_page(self):
  pages=[p for ps in self.g['STUDIO_SECTIONS'].values() for p in ps]
  self.assertEqual(set(pages),self.g['_KNOWN_PAGES']);self.assertEqual(len(pages),len(set(pages)));self.assertEqual(len(self.g['STUDIO_SECTIONS']),9)
 def test_all_workspaces_and_dock_modes_fit(self):
  for wh in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
   self.g['viewport']=lambda view=wh:view;self.s.dock_mode='FULL'
   for page in ('DASHBOARD','PLAYER','MOTION','COMBAT','LOOT','ARENA','CAPACITY','SPAWN','STYLE','PROFILES','WORLD','GEAR'):
    self.call('show_page',page);self.assertTrue(self.s.draw_ok,self.s.message);self.bounds()
   self.s.dock_mode='SIDE'
   for view in ('QUICK','TOOLS','STYLE'):
    for compact in (False,True):
     self.s.dock_view=view;self.s.dock_compact=compact;self.call('redraw');self.assertTrue(self.s.draw_ok,self.s.message);self.bounds()
 def test_dock_numeric_editor_fits_and_applies(self):
  self.s.dock_mode='SIDE';self.s.dock_view='STYLE';self.call('redraw')
  ref=self.s.sliders[0];self.call('numeric_open',ref);self.assertIn('APPLY VALUE',[b['name'] for b in self.s.buttons]);self.bounds()
  self.s.numeric_widget=NS(GetText=lambda:'500');self.assertTrue(self.call('numeric_apply'));self.assertEqual(self.s.dock_width,500.)
 def test_dock_settings_validate_and_persist(self):
  self.assertFalse(self.call('dock_stage','width',float('nan')));self.assertFalse(self.call('dock_stage','width',900))
  with tempfile.TemporaryDirectory() as td:
   self.g['SETTINGS_DIR']=Path(td);self.call('dock_stage','width',500.);self.call('dock_stage','vertical',.8);self.call('dock_stage','opacity',.4)
   self.s.dock_favorites=['XP','FORGE','bad','XP'];self.call('save_preferences');self.s.dock_width=430.;self.call('load_preferences')
   self.assertEqual(self.s.dock_width,500.);self.assertEqual(self.s.dock_favorites,['XP','FORGE']);self.assertAlmostEqual(self.s.dock_vertical,.8)
 def test_saved_actions_cannot_inject_commands(self):
  values=self.call('_dock_favorites_valid',['__import__','GOD','GOD',{},True,'XP']);self.assertEqual(values,['GOD','XP'])
 def test_dock_shoulders_switch_modes_and_back_returns_quick(self):
  self.s.dock_mode='SIDE';self.call('_controller_change_page',1);self.assertEqual(self.s.dock_view,'TOOLS')
  self.call('_controller_back');self.assertEqual(self.s.dock_view,'QUICK');self.assertTrue(self.s.opened)
 def test_dock_tool_opens_full_workspace_without_game_action(self):
  self.s.dock_mode='SIDE';self.call('r3_open_tool','COMBAT','SANDBOX');self.assertEqual(self.s.dock_mode,'FULL');self.assertTrue(self.s.sandbox_view)
 def test_native_xp_apply_change_restore_own_handle(self):
  a,lib=self.native();self.assertTrue(self.call('xp_read'));self.call('xp_stage',3.);self.assertTrue(self.call('xp_apply'));self.assertEqual(lib.GetValueOfAttribute(),6.)
  self.call('xp_stage',2.);self.assertTrue(self.call('xp_apply'));self.assertEqual(len(lib.handles),1);self.assertEqual(lib.GetValueOfAttribute(),4.)
  self.assertTrue(self.call('xp_restore_owned'));self.assertEqual(lib.GetValueOfAttribute(),2.);self.assertEqual(len(lib.handles),0)
 def test_native_xp_missing_sdk_contract_fails_closed(self):
  self.s.xp_route='NATIVE';self.assertFalse(self.call('xp_read'));self.assertIsNone(self.s.native_xp_adapter)
 def test_native_xp_changed_pawn_prevents_native_calls(self):
  a,lib=self.native();self.g['_session_anchor']=lambda:('map','other');self.assertFalse(a._runtime_set_combat_xp_scale(2.)['ok']);self.assertEqual(lib.calls,[])
 def test_native_xp_remote_session_prevents_writes(self):
  a,lib=self.native();self.g['session_role']=lambda:'GUEST';self.assertFalse(a._runtime_set_combat_xp_scale(2.)['ok']);self.assertEqual(lib.calls,[])
 def test_native_xp_unknown_result_never_retries_or_claims_success(self):
  a,lib=self.native();lib.bad_return=True
  self.assertFalse(a._runtime_set_combat_xp_scale(2.)['ok']);self.assertTrue(a.unknown_handle)
  self.assertFalse(a._runtime_set_combat_xp_scale(2.)['ok']);self.assertFalse(a._runtime_set_combat_xp_scale(1.)['ok']);self.assertEqual(len(lib.calls),1)
 def test_native_xp_failed_action_retains_recoverable_handle(self):
  a,lib=self.native();lib.fail_add=True;self.call('xp_read');self.call('xp_stage',3.)
  self.assertFalse(self.call('xp_apply'));self.assertIsNotNone(a.handle);self.assertTrue(self.call('xp_restore_owned'));self.assertEqual(len(lib.handles),0)
 def test_native_xp_refused_remove_retains_ownership(self):
  a,lib=self.native();self.call('xp_read');self.call('xp_stage',3.);self.call('xp_apply');lib.fail_remove=True
  self.assertFalse(self.call('xp_restore_owned'));self.assertIsNotNone(a.handle);self.assertIsNotNone(self.s.xp_owner)
 def test_native_xp_baseline_refresh_failure_stops_new_modifiers(self):
  a,lib=self.native();a._runtime_set_combat_xp_scale(3.);lib.stale=True
  self.assertFalse(a._runtime_set_combat_xp_scale(1.)['ok']);self.assertTrue(a.unresolved);count=len(lib.calls)
  self.assertFalse(a._runtime_set_combat_xp_scale(2.)['ok']);self.assertEqual(len(lib.calls),count)
 def test_native_xp_ignores_other_mod_handles_on_restore(self):
  a,lib=self.native();other=object();lib.handles[other]=1.5
  self.assertTrue(a._runtime_set_combat_xp_scale(2.)['ok']);self.assertTrue(a._runtime_set_combat_xp_scale(1.)['ok']);self.assertIn(other,lib.handles)
 def test_native_xp_refuses_external_attribute_change_on_adjust(self):
  a,lib=self.native();a._runtime_set_combat_xp_scale(2.);other=object();lib.handles[other]=2.;count=len(lib.calls)
  self.assertFalse(a._runtime_set_combat_xp_scale(3.)['ok']);self.assertEqual(len(lib.calls),count)
 def test_xp_source_cannot_switch_while_owned(self):
  self.native();self.call('xp_read');self.call('xp_stage',2.);self.call('xp_apply');self.assertFalse(self.call('xp_route_toggle'));self.assertEqual(self.s.xp_route,'NATIVE')
 def test_xp_samples_are_actual_counter_deltas(self):
  row=NS(ExperiencePoints=100,ExperienceLevel=5);self.g['get_pc']=lambda **kw:NS(PlayerState=NS(ExperienceState=[row]))
  self.assertTrue(self.call('xp_sample'));row.ExperiencePoints=130;self.assertTrue(self.call('xp_sample'));self.assertIn('+30 XP',self.s.xp_observation_status)
  row.ExperienceLevel=6;row.ExperiencePoints=2;self.call('xp_sample');self.assertIn('COUNTER CHANGED',self.s.xp_observation_status)
 def test_xp_sample_new_character_does_not_subtract_old(self):
  row=NS(ExperiencePoints=100,ExperienceLevel=5);self.g['get_pc']=lambda **kw:NS(PlayerState=NS(ExperienceState=[row]));self.call('xp_sample')
  self.g['_session_anchor']=lambda:('newmap','newpawn');row.ExperiencePoints=180;self.call('xp_sample');self.assertIn('BASELINE',self.s.xp_observation_status)
 def test_forge_comparison_pins_copy_not_mutable_selection(self):
  self.call('show_page','SPAWN');self.s.spawn_view='TOOLS';self.call('forge_pin_compare');old=self.s.forge_compare['level'];self.s.spawn_level=75
  self.assertEqual(self.s.forge_compare['level'],old);self.call('redraw');self.bounds();self.assertIn('BACK TO WORKBENCH',[b['name'] for b in self.s.buttons])
 def test_same_direction_dpad_and_analog_do_not_cancel(self):
  held={'Gamepad_DPad_Up','Gamepad_LeftStick_Up'};calls=[];self.g['key_down']=lambda pc,key:key in held;self.g['_controller_focus_direction']=lambda direction:calls.append(direction)
  self.s.controller_last_keys={};self.s.controller_open_block_until=0;self.call('controller_ui_tick',None,100.)
  self.assertEqual(calls,['UP']);held.remove('Gamepad_DPad_Up');self.call('controller_ui_tick',None,100.5);self.assertEqual(calls,['UP','UP'])
 def test_analog_plus_confirm_never_leaves_delayed_action(self):
  held={'Gamepad_LeftStick_Right','Gamepad_FaceButton_Bottom'};calls=[];self.g['key_down']=lambda pc,key:key in held
  self.s.controller_focus=0;self.s.buttons[0]['run']=lambda:calls.append(1);self.s.controller_last_keys={};self.s.controller_open_block_until=0
  self.call('controller_ui_tick',None,100.);held.remove('Gamepad_LeftStick_Right');self.call('controller_ui_tick',None,100.2);self.assertEqual(calls,[])
 def test_move_look_capture_readback_refusal_closes_safely(self):
  self.call('release_input');pc=ctx['PC']();pc.IsMoveInputIgnored=lambda:False;pc.SetIgnoreMoveInput=lambda value:None
  self.g['get_pc']=lambda **kw:pc
  with self.assertRaises(RuntimeError):self.call('save_input',pc)
  self.assertIsNone(self.s.input_pc);self.assertFalse(pc.bBlockInput)
 def test_owned_move_look_guard_loss_closes_menu(self):
  pc=self.s.input_pc;self.s.input_move_ignored_original=False;pc.IsMoveInputIgnored=lambda:False;self.s.input_guard_check_at=0
  self.assertFalse(self.call('r3_input_watch',pc,100.));self.assertFalse(self.s.opened)
 def test_original_game_ignore_not_decremented_on_close(self):
  pc=self.s.input_pc;calls=[];self.s.input_move_ignored_original=True;pc.SetIgnoreMoveInput=lambda value:calls.append(value)
  self.call('close_menu');self.assertEqual(calls,[])
 def test_new_art_is_hash_verified_and_rendered(self):
  for key in ('R3_HEADER','R3_CARD','R3_DOCK','R3_HOLO','R3_PAD_NAV'):
   p=R/'CROWN_CC0_ASSETS'/self.g['ART_FILES'][key];self.assertTrue(self.call('_verify_png_bytes',key,p.read_bytes()))
  calls=[];self.g['optional_art_image']=lambda parent,key,*args,**kw:calls.append(key) or True
  self.s.controller_mode=True;self.call('show_page','PLAYER');self.assertIn('R9_EXPEDITION',calls);self.assertIn('R3_HOLO',calls);self.assertIn('R3_PAD_NAV',calls);self.s.dock_mode='SIDE';self.call('redraw');self.assertIn('R9_DOCK',calls)
 def test_curated_echo_audio_cache_and_tamper_refusal(self):
  with tempfile.TemporaryDirectory() as td:
   settings=Path(td);archive=settings/'candidate.sdkmod';self.g['SETTINGS_DIR']=settings
   self.g['_art_mod_archive']=lambda:archive;self.s.sfx_set='ECHO'
   with zipfile.ZipFile(archive,'w') as z:
    for cue in ('open','close'):
     for level in ('low','normal','high'):
      name='r3_'+level+'_'+cue+'.wav';p=R/'CROWN_CC0_ASSETS/UI_WAV'/name
      with wave.open(str(p)) as w:self.assertLessEqual(w.getnframes()/w.getframerate(),.46)
      z.writestr('candidate/CROWN_CC0_ASSETS/UI_WAV/'+name,p.read_bytes())
   for cue in ('open','close'):
    for level in ('LOW','NORMAL','HIGH'):
     path=self.call('_sound_file',cue,level);self.assertIsNotNone(path)
     self.assertTrue(path.name.startswith('r3_'));path.write_bytes(b'tampered')
     repaired=self.call('_sound_file',cue,level);self.assertTrue(self.call('_sound_bytes_valid',path.name,repaired.read_bytes()))
   self.assertIsNone(self.call('_sound_file','open','OFF'))
   self.s.sfx_set='CLASSIC';self.assertIsNone(self.call('_sound_file','open','LOW'))
 def test_weapon_draft_confirm_apply_and_restore(self):
  weapon,b=self.weapon();self.assertTrue(self.call('weapon_stage','RATE',2.));self.assertEqual(b.firerate,4.)
  self.assertFalse(self.call('weapon_apply'));self.assertTrue(self.call('weapon_apply'));self.assertEqual(b.firerate,8.)
  self.assertTrue(self.call('weapon_restore'));self.assertEqual(b.firerate,4.)
 def test_weapon_primitive_pair_preserves_both_components(self):
  weapon,b=self.weapon();b.firerate=NS(Value=4.,BaseValue=2.);self.call('weapon_read');self.call('weapon_stage','RATE',2.)
  self.call('weapon_apply');self.assertTrue(self.call('weapon_apply'));self.assertEqual((b.firerate.Value,b.firerate.BaseValue),(8.,4.))
  self.call('weapon_restore');self.assertEqual((b.firerate.Value,b.firerate.BaseValue),(4.,2.))
 def test_weapon_external_change_is_not_overwritten(self):
  weapon,b=self.weapon();self.call('weapon_stage','RATE',2.);b.firerate=5.
  self.assertFalse(self.call('weapon_apply'));self.assertEqual(b.firerate,5.)
 def test_weapon_owner_change_prevents_apply_and_restore(self):
  weapon,b=self.weapon();self.call('weapon_stage','RATE',2.);self.call('weapon_apply');self.call('weapon_apply')
  weapon.Owner=NS(_get_address=lambda:200);self.assertFalse(self.call('weapon_restore'));self.assertEqual(b.firerate,8.)
 def test_weapon_batch_failure_rolls_back(self):
  weapon,b=self.weapon();self.call('weapon_stage','RATE',2.);self.call('weapon_stage','RECOIL',0.)
  original=self.g['_weapon_assign']
  def assign(row,values):
   if row['identity'][2]=='RECOIL' and values==(0.,):raise RuntimeError('refused')
   return original(row,values)
  self.g['_weapon_assign']=assign;self.call('weapon_apply');self.assertFalse(self.call('weapon_apply'));self.assertEqual(b.firerate,4.);self.assertEqual(b.RecoilScale,.5)
 def test_weapon_editor_and_restore_never_touch_other_players(self):
  weapon,b=self.weapon();weapon.Owner=NS(_get_address=lambda:200)
  self.assertFalse(self.call('weapon_read'));self.assertEqual(self.s.weapon_baselines,{})
 def test_weapon_limits_and_stale_anchor(self):
  weapon,b=self.weapon();self.assertFalse(self.call('weapon_stage','RATE',float('nan')));self.assertFalse(self.call('weapon_stage','RATE',4.))
  self.g['_session_anchor']=lambda:('other','pawn');self.assertFalse(self.call('weapon_stage','RATE',2.))
 def test_weapon_views_fit_with_live_candidate_data(self):
  self.weapon();self.call('show_page','GEAR');self.s.weapon_view=True
  for wh in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
   self.g['viewport']=lambda view=wh:view
   for group in (0,1):self.s.weapon_group=group;self.call('redraw');self.assertTrue(self.s.draw_ok,self.s.message);self.bounds()

if __name__=='__main__':unittest.main(argv=['echo_full_studio_r3'])
