"""Failure-oriented offline checks; no native BL4 or physical input claims."""
from pathlib import Path
from types import SimpleNamespace as NS
import runpy,sys,unittest,math,json,tempfile,hashlib
R=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(R/'TESTS/test_arsenal_events.py'))
SOURCE=(R/'SOURCE/__init__.py').read_text(encoding='utf-8')

class SandboxR2(unittest.TestCase):
 def setUp(self):
  sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
  self.g={'__name__':'crown_r2_test'};exec(compile(SOURCE,'crown_r2','exec'),self.g)
  self.s=self.g['State'];self.s.safe_mode=True;self.s.dock_mode='FULL'
  self.g['open_menu']();self.assertTrue(self.s.draw_ok,self.s.message)
  self.actor=NS(HasAuthority=lambda:True,_get_address=lambda:1234)
  self.g['pawn']=lambda:self.actor;self.g['_session_anchor']=lambda:('world','pawn');self.g['session_role']=lambda:'SOLO'
  self.g['echo_feedback']=lambda e:None
  for key,spec in self.g['TUNING_FIELDS'].items():
   node=self.actor
   for segment in spec[0].split('.') if spec[0] else ():
    if not hasattr(node,segment):setattr(node,segment,NS())
    node=getattr(node,segment)
   setattr(node,spec[1],NS(Value=1.,BaseValue=1.))
 def call(self,name,*args):return self.g[name](*args)
 def pair(self,key):return self.call('combat_pair',key)[0]
 def bounds(self):
  x,y,w,h,*_=self.s.panel_rect
  for i,a in enumerate(self.s.buttons):
   ax,ay,aw,ah=a['rect'];self.assertTrue(x-1<=ax and ax+aw<=x+w+1 and y-1<=ay and ay+ah<=y+h+1,a['name'])
   for b in self.s.buttons[i+1:]:
    bx,by,bw,bh=b['rect']
    self.assertTrue(min(ax+aw,bx+bw)-max(ax,bx)<=1 or min(ay+ah,by+bh)-max(ay,by)<=1,(a['name'],b['name']))
 def xp(self):
  self.s.xp_route='BL4LIVE' # This fixture models the reviewed BL4Live backend explicitly.
  m=NS(_RUNTIME_STATE={'experience_reward_scale':1.},_RUNTIME_REGISTRY={'xp_scale':1.},actual=2.)
  def set_scale(v):
   old=m._RUNTIME_STATE['experience_reward_scale'];m.actual=m.actual/old*v
   m._RUNTIME_STATE['experience_reward_scale']=v;m._RUNTIME_REGISTRY['xp_scale']=v
   return {'ok':True,'value':v}
  m._runtime_set_combat_xp_scale=set_scale;m._runtime_combat_xp_value=lambda:m.actual;m._runtime_pawn=lambda:self.actor
  self.g['_reviewed_module']=lambda names,expected:m
  return m
 def encounter(self):
  c=NS(ui=NS(spawn_anchor='party',spawn_distance=777.,unlimited_world_spawns=True,aggro_mode='attack_me',damage_wake=True,spawn_pending=False,summon_fallback=True),tracker=NS(mobs=[]),_spawn_tick_hooks=[1])
  actors={};queue=[];calls=[]
  def spawn(code,**kw):
   calls.append((code,kw,vars(c.ui).copy()))
   for i in range(kw['count']):
    key='actor'+str(len(actors));address=10000+len(actors)
    a=NS(_get_address=lambda addr=address:addr,K2_DestroyActor=lambda k=key:actors.pop(k,None))
    actors[key]=a;c.tracker.mobs.append(NS(key=key,code=code))
   return True,'backend accepted'
  c.spawn_mob=spawn
  m=NS(CONTROLLER=c,prefer_combat_boss_code=lambda code:code)
  stability=NS(make_request=lambda label,fn,**kw:NS(execute=fn))
  core=NS(resolve_live_actor=lambda key:actors.get(key),snapshot_character_keys=lambda:set(actors))
  deferred=NS(queue_action=lambda label,fn:queue.append(fn))
  backend=(m,stability,core,deferred);self.g['encounter_backend']=lambda:backend
  self.s.encounter_selected=next(i for i,row in enumerate(self.g['ENCOUNTER_CATALOGUE']) if row[2]=='ENEMIES')
  return c,actors,queue,calls
 def queue_spawn(self):
  self.assertFalse(self.call('encounter_request'));self.assertTrue(self.call('encounter_request'))
 def test_all_new_pair_paths_resolve(self):
  self.assertEqual(len(self.g['SANDBOX_FIELDS']),18)
  for key in self.g['SANDBOX_FIELDS']:
   self.assertTrue(self.call('combat_tune',key,1.));self.assertEqual(self.pair(key).Value,1.)
 def test_stage_never_writes(self):
  self.call('sandbox_stage_value','FIRE',3.);self.assertEqual(self.pair('FIRE').Value,1.)
 def test_stage_rejects_nonfinite_and_unknown(self):
  for key,v in [('FIRE',float('nan')),('FIRE',float('inf')),('FIRE',11),('BAD',1),('FIRE',True)]:self.assertFalse(self.call('sandbox_stage_value',key,v))
 def test_stage_changed_character_clears(self):
  self.call('sandbox_stage_value','FIRE',3.);self.g['_session_anchor']=lambda:('world','new')
  self.assertFalse(self.call('sandbox_stage_value','SHOCK',2.));self.assertEqual(self.s.sandbox_stage,{})
 def test_apply_two_fields_and_restore(self):
  self.call('sandbox_stage_value','FIRE',3.);self.call('sandbox_stage_value','SHOCK',2.)
  self.assertTrue(self.call('sandbox_apply'));self.assertEqual(self.pair('FIRE').Value,3.)
  self.assertEqual(self.call('restore_combat_tuning'),2);self.assertEqual(self.pair('FIRE').Value,1.)
 def test_apply_missing_field_preflights_whole_batch(self):
  self.call('sandbox_stage_value','FIRE',3.);self.call('sandbox_stage_value','SHOCK',2.)
  del self.actor.DamageCauserData.ElementalDamageModifiers.ShockModifier
  self.assertFalse(self.call('sandbox_apply'));self.assertEqual(self.pair('FIRE').Value,1.)
 def test_partial_failure_rolls_back_prior_and_ownership(self):
  self.call('sandbox_stage_value','FIRE',3.);self.call('sandbox_stage_value','SHOCK',2.)
  original=self.g['combat_tune'];self.g['combat_tune']=lambda k,v:False if k=='SHOCK' else original(k,v)
  self.assertFalse(self.call('sandbox_apply'));self.assertEqual(self.pair('FIRE').Value,1.);self.assertEqual(self.s.combat_last,{})
  self.assertEqual(len(self.s.sandbox_stage),2)
 def test_sandbox_refuses_coop(self):
  self.call('sandbox_stage_value','FIRE',3.);self.g['session_role']=lambda:'HOST'
  self.assertTrue(self.call('sandbox_apply'));self.assertEqual(self.pair('FIRE').Value,3.)
  self.call('restore_combat_tuning');self.g['session_role']=lambda:'CLIENT'
  self.call('sandbox_stage_value','FIRE',5.)
  self.assertFalse(self.call('sandbox_apply'));self.assertEqual(self.pair('FIRE').Value,1.)
 def test_preset_draft_and_saved_allowlist(self):
  self.call('sandbox_preset','GLASS CANNON');self.assertEqual(self.pair('OUTGOING').Value,1.)
  self.assertTrue(self.call('sandbox_save'));self.s.sandbox_stage={};self.assertTrue(self.call('sandbox_load'))
  self.assertEqual(self.s.sandbox_stage['OUTGOING'],3.)
  self.assertEqual(self.call('_sandbox_saved_validate',{'1':{'FIRE':float('nan')},'4':{'FIRE':1},'2':{'BAD':1}}),{})
 def test_xp_missing_module_read_is_false(self):
  self.g['_reviewed_module']=lambda *args:None;self.assertFalse(self.call('xp_read'));self.assertIsNone(self.s.xp_read)
 def test_xp_rejects_other_pawn(self):
  m=self.xp();m._runtime_pawn=lambda:NS(_get_address=lambda:9);self.assertIsNone(self.call('xp_backend'))
 def test_xp_requires_read(self):
  self.xp();self.assertFalse(self.call('xp_apply'))
 def test_xp_apply_and_owned_restore(self):
  m=self.xp();self.assertTrue(self.call('xp_read'));self.call('xp_stage',3.)
  self.assertTrue(self.call('xp_apply'));self.assertEqual(m.actual,6.)
  self.assertTrue(self.call('xp_restore_owned'));self.assertEqual(m.actual,2.);self.assertIsNone(self.s.xp_owner)
 def test_xp_external_change_not_overwritten(self):
  m=self.xp();self.call('xp_read');self.call('xp_stage',3.);m.actual=4.
  self.assertFalse(self.call('xp_apply'));self.assertEqual(m.actual,4.)
 def test_xp_accepted_without_effect_retains_restore_owner(self):
  m=self.xp();self.call('xp_read');self.call('xp_stage',3.)
  def bad(v):m._RUNTIME_STATE['experience_reward_scale']=v;m._RUNTIME_REGISTRY['xp_scale']=v;return {'ok':True}
  m._runtime_set_combat_xp_scale=bad
  self.assertFalse(self.call('xp_apply'));self.assertEqual(self.s.xp_owner['last'],3.);self.assertIsNone(self.s.xp_read)
 def test_xp_refused_setter_does_not_claim_owner(self):
  m=self.xp();self.call('xp_read');self.call('xp_stage',3.);m._runtime_set_combat_xp_scale=lambda v:{'ok':False}
  self.assertFalse(self.call('xp_apply'));self.assertIsNone(self.s.xp_owner)
 def test_xp_stale_and_coop_reject(self):
  self.xp();self.call('xp_read');self.s.xp_read['at']-=31;self.assertFalse(self.call('xp_apply'))
  self.g['session_role']=lambda:'CLIENT';self.assertFalse(self.call('xp_read'))
 def test_xp_stage_range(self):
  for v in (0,11,True,float('nan')):self.assertFalse(self.call('xp_stage',v))
 def test_xp_restore_wont_touch_other_mod_value(self):
  m=self.xp();self.call('xp_read');self.call('xp_stage',3.);self.call('xp_apply');m._RUNTIME_STATE['experience_reward_scale']=2.
  self.assertFalse(self.call('xp_restore_owned'));self.assertEqual(m.actual,6.)
 def test_encounter_missing_backend_never_queues(self):
  self.g['encounter_backend']=lambda:None;self.assertFalse(self.call('encounter_request'));self.assertIsNone(self.s.encounter_job)
 def test_encounter_confirm_queue_then_actor_verification(self):
  c,actors,q,calls=self.encounter();self.call('encounter_stage','quantity',3);self.queue_spawn();self.assertEqual(len(actors),0)
  self.assertTrue(q.pop()()[0]);self.assertEqual(len(self.s.encounter_owned),3);self.assertEqual(self.s.encounter_budget,3)
  self.assertFalse(calls[0][1]['lightweight']);self.assertFalse(calls[0][2]['unlimited_world_spawns'])
  self.assertEqual(c.ui.spawn_anchor,'party');self.assertEqual(c.ui.aggro_mode,'attack_me')
 def test_cancel_invalidates_deferred_closure(self):
  c,a,q,calls=self.encounter();self.queue_spawn();self.call('encounter_cancel');self.assertFalse(q.pop()()[0]);self.assertEqual(calls,[])
 def test_close_invalidates_deferred_closure(self):
  c,a,q,calls=self.encounter();self.queue_spawn();self.call('close_menu');self.assertFalse(q.pop()()[0]);self.assertEqual(calls,[])
 def test_changed_world_and_coop_prevent_deferred_write(self):
  c,a,q,calls=self.encounter();self.queue_spawn();self.g['_session_anchor']=lambda:('new','pawn');self.assertFalse(q.pop()()[0]);self.assertEqual(calls,[])
 def test_pending_bms_request_prevents_spawn(self):
  c,a,q,calls=self.encounter();self.queue_spawn();c.ui.spawn_pending=True
  self.assertFalse(q.pop()()[0]);self.assertEqual(calls,[])
 def test_backend_ok_without_actor_is_unverified_budget_retained(self):
  c,a,q,calls=self.encounter();c.spawn_mob=lambda *args,**kw:(True,'accepted only');self.queue_spawn()
  self.assertFalse(q.pop()()[0]);self.assertIn('UNVERIFIED',self.s.encounter_status);self.assertEqual(self.s.encounter_budget,1)
 def test_existing_world_actor_not_adopted(self):
  c,a,q,calls=self.encounter();a['existing']=NS(_get_address=lambda:999)
  code=self.g['ENCOUNTER_CATALOGUE'][self.s.encounter_selected][0]
  def spawn(*args,**kw):c.tracker.mobs.append(NS(key='existing',code=code));return True,'fallback'
  c.spawn_mob=spawn;self.queue_spawn();self.assertFalse(q.pop()()[0]);self.assertEqual(self.s.encounter_owned,{})
 def test_cleanup_only_owned_and_readback(self):
  c,a,q,calls=self.encounter();self.queue_spawn();q.pop()();a['unrelated']=NS(_get_address=lambda:45)
  self.assertFalse(self.call('encounter_cleanup'));self.assertTrue(self.call('encounter_cleanup'));self.assertIn('unrelated',a);self.assertEqual(self.s.encounter_budget,0)
 def test_cleanup_address_reuse_is_skipped(self):
  c,a,q,calls=self.encounter();self.queue_spawn();q.pop()();key=next(iter(self.s.encounter_owned));a[key]._get_address=lambda:888
  self.call('encounter_cleanup');self.assertFalse(self.call('encounter_cleanup'));self.assertIn(key,a)
 def test_cleanup_refusal_retains_ownership(self):
  c,a,q,calls=self.encounter();self.queue_spawn();q.pop()();key=next(iter(a));a[key].K2_DestroyActor=lambda:None
  self.call('encounter_cleanup');self.assertFalse(self.call('encounter_cleanup'));self.assertIn(key,self.s.encounter_owned)
 def test_limit_and_boss_quantity(self):
  self.encounter();self.call('encounter_reset_context');self.s.encounter_budget=6;self.assertFalse(self.call('encounter_request'))
  self.s.encounter_selected=next(i for i,r in enumerate(self.g['ENCOUNTER_CATALOGUE']) if r[2]=='BOSSES')
  self.assertFalse(self.call('encounter_stage','quantity',2));self.assertFalse(self.call('encounter_stage','distance',float('nan')))
 def test_search_and_favorites(self):
  self.s.encounter_filter='ALL';self.s.encounter_query=self.g['ENCOUNTER_CATALOGUE'][0][0]
  self.assertTrue(self.call('encounter_rows'));self.call('encounter_select',0);self.call('encounter_favorite')
  self.s.encounter_filter='FAVOURITES';self.assertEqual(len(self.call('encounter_rows')),1)
 def test_hash_gate_missing_and_mismatch(self):
  self.assertIsNone(self.call('_reviewed_module',('not_a_mod',),'0'*64))
  fake=NS(__file__='test.py',__loader__=NS(get_data=lambda p:b'wrong'));sys.modules['crown_hash_test']=fake
  try:self.assertIsNone(self.call('_reviewed_module',('crown_hash_test',),'0'*64))
  finally:sys.modules.pop('crown_hash_test',None)
 def test_hash_gate_loader_data(self):
  raw=b'reviewed source';fake=NS(__file__='package.sdkmod/a.py',__loader__=NS(get_data=lambda p:raw));sys.modules['crown_hash_test']=fake
  try:self.assertIs(self.call('_reviewed_module',('crown_hash_test',),hashlib.sha256(raw).hexdigest()),fake)
  finally:sys.modules.pop('crown_hash_test',None)
 def test_new_art_hash_and_real_draw_path(self):
  name=self.g['ART_FILES']['SANDBOX_PLATE'];self.assertTrue(self.call('_verify_png_bytes','SANDBOX_PLATE',(R/'CROWN_CC0_ASSETS'/name).read_bytes()))
  calls=[];self.g['optional_art_image']=lambda *a,**kw:calls.append(a[1]) or True
  self.call('show_page','DASHBOARD');self.assertIn('R9_FORGE',calls)
 def test_all_new_views_bounds(self):
  for screen in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
   self.g['viewport']=lambda wh=screen:wh
   for page,attr,value in [('COMBAT','sandbox_view',True),('LOOT','xp_view',True),('ARENA','encounter_view','CATALOGUE'),('ARENA','encounter_view','CONTROLS'),('ARENA','encounter_view','STATUS'),('ARENA','encounter_view','SEARCH')]:
    self.call('show_page',page);setattr(self.s,attr,value);self.call('redraw');self.assertTrue(self.s.draw_ok,self.s.message);self.bounds()
 def test_search_enter_cannot_trigger_selected_spawn(self):
  self.call('show_page','ARENA');self.call('encounter_search_open');self.s.encounter_input=NS(GetText=lambda:'axemaul')
  ran=[];self.s.buttons[0]['run']=lambda:ran.append('unrelated');self.s.controller_focus=0
  self.s.session_anchor=self.call('_session_anchor');self.s.session_last_check=self.g['time'].monotonic()
  self.g['_menu_foreground_guard']=lambda *args:False;self.g['key_down']=lambda pc,key:key=='Enter'
  self.call('_tick_impl');self.assertEqual(ran,[]);self.assertEqual(self.s.encounter_query,'axemaul');self.assertEqual(self.s.encounter_view,'CATALOGUE')
 def test_search_arrow_isolation_and_back(self):
  self.call('show_page','ARENA');self.call('encounter_search_open');calls=[]
  self.g['_controller_focus_direction']=lambda direction:calls.append(direction)
  self.s.session_anchor=self.call('_session_anchor');self.s.session_last_check=self.g['time'].monotonic()
  self.g['_menu_foreground_guard']=lambda *args:False;self.g['key_down']=lambda pc,key:key=='Right'
  self.call('_tick_impl');self.assertEqual(calls,[])
  self.call('_controller_back');self.assertEqual(self.s.encounter_view,'CATALOGUE');self.assertTrue(self.s.opened)
 def test_search_draft_survives_unrelated_redraw(self):
  self.call('show_page','ARENA');self.call('encounter_search_open');self.s.encounter_input=NS(GetText=lambda:'unsubmitted')
  self.call('redraw');self.assertEqual(self.s.encounter_query_draft,'unsubmitted');self.assertEqual(self.s.encounter_query,'')
 def test_native_authority_refuses_xp_and_encounter(self):
  self.xp();self.actor.HasAuthority=lambda:False;self.assertFalse(self.call('xp_read'))
  self.encounter();self.assertFalse(self.call('encounter_request'))
 def test_expired_encounter_releases_pending_without_write(self):
  c,a,q,calls=self.encounter();self.queue_spawn();self.s.encounter_job['at']-=13
  self.assertFalse(q.pop()()[0]);self.assertEqual(calls,[]);self.assertIsNone(self.s.encounter_job)
 def test_existing_xp_modifier_not_taken_over(self):
  m=self.xp();m._RUNTIME_STATE['experience_reward_scale']=2.;m._RUNTIME_REGISTRY['xp_scale']=2.
  self.assertTrue(self.call('xp_read'));self.call('xp_stage',3.);self.assertFalse(self.call('xp_apply'));self.assertEqual(m.actual,2.)
 def test_reduced_motion_does_not_move_scan(self):
  calls=[];self.s.echo_scan=NS();self.s.echo_scan_generation=self.s.frame_generation
  self.g['size_position']=lambda *args:calls.append(args);self.s.reduced_motion=True;self.s.safe_mode=False
  self.call('echo_scan_tick');self.assertEqual(calls,[])
 def test_preferences_roundtrip_no_gameplay_auto_apply(self):
  with tempfile.TemporaryDirectory() as td:
   self.g['SETTINGS_DIR']=Path(td);self.call('sandbox_preset','GLASS CANNON');self.call('sandbox_save')
   self.s.echo_personality=False;self.call('save_preferences');self.s.sandbox_saved={};self.s.echo_personality=True
   self.call('load_preferences');self.assertIn('1',self.s.sandbox_saved);self.assertFalse(self.s.echo_personality);self.assertEqual(self.pair('OUTGOING').Value,1.)

if __name__=='__main__':unittest.main(argv=['echo_sandbox_r2'])
