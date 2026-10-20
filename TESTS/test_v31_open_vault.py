"""Standalone synthetic Oak2 v3.1 test. Not a BL4 live-game substitute."""
from pathlib import Path
from types import SimpleNamespace
import json,runpy,tempfile,sys
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crowns_v31_test'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),str(root/'SOURCE/__init__.py'),'exec'),ns)
 st=ns['State']
 assert len(ns['ACHIEVEMENT_NAMES'])==63
 assert len(set(ns['ACHIEVEMENT_NAMES']))==63
 assert '.SetAchievement(' not in (root/'SOURCE/__init__.py').read_text()
 assert 'SteamAPI_ISteamUserStats' not in (root/'SOURCE/__init__.py').read_text()
 # Journal only alters local settings, never gameplay or Steam achievement state.
 with tempfile.TemporaryDirectory() as folder:
  ns['SETTINGS_DIR']=Path(folder)
  calls_before=len(ctx['pool'].calls)
  assert ns['trophy_mark'](10)
  assert 10 in st.trophy_marked
  assert ns['trophy_mark'](10)
  assert 10 not in st.trophy_marked
  assert ns['trophy_mark'](-1) is False and ns['trophy_mark'](63) is False
  assert len(ctx['pool'].calls)==calls_before
  assert ns['trophy_mark'](62)
  ns['trophy_change_page'](100)
  assert st.trophy_page==10
  ns['trophy_change_page'](-200)
  assert st.trophy_page==0
  baseline_scale=st.panel_scale
  assert ns['save_ui_profile'](1)
  st.theme_idx=4;st.panel_scale=1.65;st.audio_mode='OFF';st.spawn_search='foo'
  assert ns['save_ui_profile'](2)
  assert ns['load_ui_profile'](1)
  assert st.panel_scale==baseline_scale and st.audio_mode!='OFF' and st.theme_idx!=4
  assert ns['load_ui_profile'](2)
  assert st.panel_scale==1.65 and st.audio_mode=='OFF'
  assert ns['save_ui_profile'](4) is False and ns['load_ui_profile'](4) is False
  ns['save_preferences']()
  pref=json.loads((Path(folder)/'CROWNs_Freedom_UI.json').read_text())
  assert pref['trophy_marked']==[62]
  assert len(pref['ui_profiles'])==2
  st.trophy_marked.clear();st.ui_profiles={}
  ns['load_preferences']()
  assert st.trophy_marked=={62} and set(st.ui_profiles)=={'1','2'}
 # Six saved same-map locations. Never move across maps.
 st.checkpoints={}
 for index in range(1,7):ns['bookmark_save'](index)
 assert len(st.checkpoints)==6
 assert ns['bookmark_go'](2) in (True,False)
 before=ctx['pawn'].K2_GetActorLocation()
 # The mock test harness does not certify teleport movement; just stage guards.
 assert st.waypoint_mode=='TRAVEL'
 ns['waypoint_cycle_mode']();assert st.waypoint_mode=='SAVE'
 ns['waypoint_cycle_mode']();assert st.waypoint_mode=='TRAVEL'
 # Launcher can still navigate CORE -> MORE -> VAULT -> CORE.
 st.nav_group='CORE';st.opened=False
 ns['toggle_nav_group']();assert st.nav_group=='MORE' and st.page=='SPAWN'
 ns['toggle_nav_group']();assert st.nav_group=='VAULT' and st.page=='TROPHIES'
 ns['toggle_nav_group']();assert st.nav_group=='CORE' and st.page=='PLAYER'
 for cat in ('RIFLE','FAVORITES','RECENT','ALL'):
  assert ns['gear_jump'](cat) is True
  assert ns['_spawn_category']()==cat and st.spawn_view=='BROWSE'
 assert ns['gear_jump']('untrusted_itempool') is False
 assert ns['set_panel_scale'](float('nan')) is None and st.panel_scale==1.0
 ns['set_panel_scale'](5.0);assert st.panel_scale==2.0
 ns['set_panel_scale'](-5.0);assert st.panel_scale==.72
 ns['set_panel_scale'](1.0)
 # Every new page, Help and nested view: bounds and overflow.
 base_btn=ns['btn'];base_note=ns['note_panel'];calls=[];notes=[]
 def audit_btn(parent,label,x,y,w,h,fn,*args,**kwargs):
  calls.append((str(label),float(x),float(y),float(w),float(h)))
  return base_btn(parent,label,x,y,w,h,fn,*args,**kwargs)
 def audit_note(parent,title,body,x,y,w,h,*args,**kwargs):
  notes.append((str(title),float(x),float(y),float(w),float(h)))
  return base_note(parent,title,body,x,y,w,h,*args,**kwargs)
 ns['btn']=audit_btn;ns['note_panel']=audit_note
 pages=('TROPHIES','WAYPOINTS','PROFILES','GEAR','DISPLAY','GUIDE')
 for wh in ((2560,1440),(1920,1080),(1280,720),(854,480)):
  ns['viewport']=lambda s=wh:s
  ns['open_menu']()
  assert st.opened and st.draw_ok,wh
  for scale in (1.0,2.0):
   st.panel_scale=scale
   for pg in pages:
    calls.clear();notes.clear();st.help_open=False
    ns['show_page'](pg)
    assert st.draw_ok and st.nav_group=='VAULT',(wh,scale,pg)
    xx,yy,ww,hh,*_=st.panel_rect
    foot=yy+hh-141
    assert xx>=7 and yy>=7 and xx+ww<=st.panel_rect[4]+2,(wh,scale,pg,st.panel_rect)
    for label,bx,by,bw,bh in calls:
     assert by>=yy+15 and by+bh<=yy+hh-12,(wh,scale,pg,label,'panel overflow')
     if bx>=xx+201 and by>=yy+214 and by<foot:
      assert by+bh<=foot-2,(wh,scale,pg,label,'footer overlap')
    for title,nx,ny,nw,nh in notes:
     assert ny+nh<=foot-2,(wh,scale,pg,title,'note/footer overlap')
    ns['toggle_page_help']()
    assert st.help_open and st.draw_ok,(wh,pg)
  ns['close_menu']()
 print('PASS v3.1: 63-item read-only journal, 6 waypoints, 3 UI profiles, third nav group, Forge filters, XXL 72-200%, six new pages x four resolutions')
finally:
 for name,item in old.items():
  if item is None:sys.modules.pop(name,None)
  else:sys.modules[name]=item
