"""Roadrunner acceptance: synthetic SDK calls only; never claims real BL4 map compatibility."""
from pathlib import Path
from types import SimpleNamespace as NS
import json,sys,runpy,tempfile,time,hashlib,math
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={name:sys.modules.get(name) for name in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'test_v33'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'v33-source','exec'),ns)
 st=ns['State']
 coords=[1000.,2000.,200.]
 pawn=ctx['pawn']
 pawn.K2_GetActorLocation=lambda:NS(X=coords[0],Y=coords[1],Z=coords[2])
 pawn.K2_SetActorLocation=lambda vector,*args:(coords.__setitem__(slice(None),[vector.X,vector.Y,vector.Z]) or True)
 # One world has a stable tag, but different worlds must fail closed.
 assert ns['map_tag']()=='WhistlersMaw'
 with tempfile.TemporaryDirectory() as tmp:
  ns['SETTINGS_DIR']=Path(tmp)
  st.checkpoints={};st.travel_save_pending=None;st.travel_cooldown_until=0
  for index in range(1,13):
   coords[:]=[1000.+index*10,2000.,200.]
   assert ns['bookmark_save'](index)
  assert len(st.checkpoints)==12
  assert not ns['bookmark_save'](13)
  pref=json.loads((Path(tmp)/'CROWNs_Freedom_UI.json').read_text())
  assert pref['prefs_schema']==4 and len(pref['travel_slots'])==12
  assert [entry['slot'] for entry in pref['travel_slots']]==list(range(1,13))
  # Overwrites require two clicks, stored coords survive until confirmed.
  before=st.checkpoints[1]
  coords[:]=[9191.,9090.,355.]
  assert not ns['bookmark_save'](1) and st.checkpoints[1]==before
  assert st.travel_save_pending==1
  assert ns['bookmark_save'](1) and st.checkpoints[1][1]==(9191.,9090.,355.)
  # Save data is validated on cold reload; invalid/map-injection entries are discarded.
  fresh=json.loads((Path(tmp)/'CROWNs_Freedom_UI.json').read_text())
  fresh['travel_slots'].extend([{'slot':400,'map':'WhistlersMaw','xyz':[1,2,3]},
                                {'slot':3,'map':'WhistlersMaw','xyz':['x',0,0]},
                                {'slot':3,'map':'Bad\nMap','xyz':[1,2,3]}])
  (Path(tmp)/'CROWNs_Freedom_UI.json').write_text(json.dumps(fresh))
  st.checkpoints={}
  ns['load_preferences']()
  assert len(st.checkpoints)==12 and st.checkpoints[1][1]==(9191.,9090.,355.)
  assert ns['_valid_travel_record'](3,('WhistlersMaw',[1,2,3]))
  for x in (float('nan'),float('inf'),10000001.,'hi'):
   assert not ns['_valid_travel_record'](3,('WhistlersMaw',[1,2,x]))
  # Travel moves only on current map; successful move makes reverse available.
  coords[:]=[0.,0.,300.]
  assert ns['bookmark_go'](1) and coords==[9191.,9090.,355.]
  assert st.checkpoint_return[1]==(0.,0.,300.)
  assert ns['bookmark_back']() and coords==[0.,0.,300.]
  # Same destination needs cooldown to avoid rapid accidental re-entry.
  assert not ns['bookmark_go'](1)
  st.travel_cooldown_until=0
  oldworld=ctx['world'].GetName
  ctx['world'].GetName=lambda:'UnknownMap'
  assert not ns['bookmark_go'](2) and coords==[0.,0.,300.]
  ctx['world'].GetName=oldworld
  # Readback failure: game write request is NOT misreported as confirmed teleport.
  oldread=pawn.K2_GetActorLocation
  pawn.K2_GetActorLocation=lambda:None
  assert not ns['_teleport_actor'](pawn,(1.,2.,3.))
  pawn.K2_GetActorLocation=oldread
  # Startup shouldn't produce writes to achievements/game saves.
  assert 'SteamAPI_ISteamUserStats' not in (root/'SOURCE/__init__.py').read_text()
  assert 'SetAchievement(' not in (root/'SOURCE/__init__.py').read_text()
  # F8 direct opens travel, preserving the live-menu setup and recovery.
  st.opened=False
  ns['open_travel_hub']()
  assert st.opened and st.page=='WAYPOINTS' and st.nav_group=='VAULT'
  ns['close_menu']()
  # Check route selection and layout at 4 simulated resolutions.
  for wh in ((2560.,1440.),(1920.,1080.),(1280.,720.),(854.,480.)):
   ns['viewport']=lambda wh=wh:wh
   ns['open_travel_hub']()
   assert st.opened and st.draw_ok and st.page=='WAYPOINTS'
   st.waypoint_mode='TRAVEL';st.waypoint_page=0
   ns['redraw']()
   assert any('GO 01' in str(b['name']) for b in st.buttons),wh
   ns['travel_next_page']();assert st.waypoint_page==1
   assert any('GO 12' in str(b['name']) for b in st.buttons),wh
   assert st.draw_ok
   px,py,pw,ph,*_=st.panel_rect
   for b in st.buttons:
    bx,by,bw,bh=b['rect'];assert by>=py+12 and by+bh<py+ph-8,(wh,b['name'])
   ns['close_menu']()
  assert ns['_verify_png_bytes']('ROUTE_STRIP',(root/'CROWN_CC0_ASSETS/ROUTE_STRIP.png').read_bytes())
  # Controller chord DOWN opens travel directly; no teleport or spawn on opening.
  keys=set()
  ctx['pc'].IsInputKeyDown=lambda key:getattr(key,'KeyName',key) in keys
  st.controller_enabled=True;st.controller_poll_last=0
  st.controller_open_latched=False
  keys.update(ns['CONTROLLER_TRAVEL_CHORD'])
  st.controller_hold_start=time.monotonic()-.9
  n_before=len(ctx['pool'].calls)
  ns['controller_watch_tick']()
  assert st.opened and st.page=='WAYPOINTS' and st.nav_group=='VAULT'
  assert len(ctx['pool'].calls)==n_before
  ns['close_menu']()
 print('PASS v3.3: twelve persistent validated safe same-map bookmarks, overwrite guard, emergency reverse, F8 and gamepad shortcut, art checks, layout x4, no achievement changes')
finally:
 for name,value in old.items():
  if value is None:sys.modules.pop(name,None)
  else:sys.modules[name]=value
