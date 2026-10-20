"""v4.3 release: real Side Dock action pagination + focus recovery (mocked Unreal)."""
from pathlib import Path
from types import SimpleNamespace as NS
import runpy,sys,time
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crowns_refined_qa'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crowns_refined','exec'),ns)
 state=ns['State'];pc=ctx['pc'];pool_calls=len(ctx['pool'].calls)
 assert ns['ART_MOD_FILENAME']=='CROWNs_Freedom_v5_26_ECHO_Fieldcraft_R22.sdkmod'
 for viewport in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
  ns['viewport']=lambda viewport=viewport:viewport
  for page in ('PLAYER','MOTION','WORLD','WAYPOINTS','SPAWN','STYLE','DISPLAY','DEV'):
   state.dock_favorites=['GOD','SANDBOX','DIRECTOR'];state.dock_mode='SIDE'; state.page=page;state.side_action_page=0
   ns['open_menu']();assert state.opened and state.draw_ok,(viewport,page,state.message)
   assert state.input_guard_confirmed
   # All actionable click rectangles remain inside the side viewport.
   x,y,w,h,*_=state.panel_rect
   for b in state.buttons:
    bx,by,bw,bh=b['rect']
    assert x-1<=bx and bx+bw<=x+w+1 and y-1<=by and by+bh<=y+h+1,(viewport,page,b['name'])
   labels={b['name'] for b in state.buttons}
   assert {'QUICK','TOOLS','STYLE','FULL STUDIO','CLOSE / B'}.issubset(labels)
   if page=='PLAYER' and 'NEXT >' in labels:
    assert state.side_action_page==0
    assert 'NEXT >' in labels,'next page missing'
    first=labels.copy()
    ns['side_action_next']()
    second={b['name'] for b in state.buttons}
    assert state.side_action_page==1 and 'PREV' in ' '.join(second)
    assert 'FOV 130' in second or 'RESET FOV' in second,(viewport,second)
    assert 'GOD MODE: OFF' in first or 'GOD MODE: ON' in first
    ns['side_action_previous']()
    assert state.side_action_page==0
   if page=='PLAYER' and 'NEXT >' not in labels:
    assert 'GOD MODE / OFF' in labels or 'GOD MODE / ON' in labels, (viewport,labels)
    assert 'COMBAT TUNING' in labels and 'ENCOUNTERS' in labels
    assert 'NEXT >' not in labels, 'standard dock should not hide the seven player actions'
   ns['close_menu']();assert state.input_pc is None
 # Focus watchdog must not steal mouse focus or editor focus.
 ns['viewport']=lambda:(1920.,1080.)
 state.dock_mode='SIDE';state.page='PLAYER';ns['open_menu']()
 state.controller_mode=True
 state.focus_watch_at=0
 # Mocked root should offer meaningful focus status.
 state.root.HasUserFocus=lambda arg:False
 state.root.HasUserFocusedDescendants=lambda arg:False
 repaired=[];orig=ns['recover_ui_focus'];ns['recover_ui_focus']=lambda:repaired.append(True) or True
 ns['monitor_controller_focus'](pc,100)
 assert not repaired and state.focus_loss_count==1
 ns['monitor_controller_focus'](pc,101)
 assert repaired and state.focus_loss_count==0
 state.page='SPAWN';state.spawn_view='SEARCH';state.focus_watch_at=0
 ns['monitor_controller_focus'](pc,110)
 assert len(repaired)==1,'editor focus must not be stolen'
 state.page='PLAYER';state.spawn_view='BROWSE'
 ns['recover_ui_focus']=orig
 ns['close_menu']()
 assert len(ctx['pool'].calls)==pool_calls,'non-spawning QA only'
 print('PASS v4.3: Side Dock action paging, all-pages button bounds, controller focus watchdog, editor safety')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
