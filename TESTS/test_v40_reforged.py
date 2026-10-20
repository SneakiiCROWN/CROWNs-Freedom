"""Focused v4.0 offline acceptance. Simulated Oak2 only; NOT live BL4."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys,runpy,hashlib,time as pytime
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_reforged_qa'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crowns_reforged.py','exec'),ns)
 st=ns['State'];pc=ctx['pc']
 assert ns['ART_MOD_FILENAME']=='CROWNs_Freedom_v5_26_ECHO_Fieldcraft_R22.sdkmod'
 assert len(ns['ART_FILES'])>=14
 assert st.theme_idx==0 and st.cursor_aid and st.panel_opacity==.91
 assert ns['CONTROLLER_CHORD']==('Gamepad_LeftThumbstick','Gamepad_RightThumbstick')
 assert ns['LEGACY_CONTROLLER_CHORD']==('Gamepad_LeftShoulder','Gamepad_RightShoulder','Gamepad_DPad_Up')
 names=set()
 keys=set();actions=[]
 pc.IsInputKeyDown=lambda key:getattr(key,'KeyName',key) in keys
 pc.GetMousePosition=lambda:(550.,400.)
 ns['viewport']=lambda:(1920.,1080.)
 clock=[100.]
 ns['time']=NS(monotonic=lambda:clock[0],perf_counter=pytime.perf_counter,time=pytime.time)
 # L3+R3 background chord is simultaneous and held. One frame must not open.
 keys.update(ns['CONTROLLER_CHORD'])
 st.controller_poll_last=0
 ns['controller_watch_tick']()
 assert not st.opened
 clock[0]+=0.77
 ns['controller_watch_tick']()
 assert st.opened and st.draw_ok
 assert st.controller_mode and st.controller_open_latched
 assert pc.bShowMouseCursor
 assert len(st.cursor_shapes)==5
 assert st.input_pc is pc
 # The menu must not instantly close from the original opening chord.
 st.controller_open_block_until=0
 ns['controller_ui_tick'](pc,clock[0]+.01)
 assert st.opened
 keys.clear()
 ns['controller_ui_tick'](pc,clock[0]+.02)
 assert not st.controller_open_latched
 # Mouse movement outside browser capture must return to mouse mode and show aid.
 st.controller_mode=True;st.mouse_last=(150.,130.)
 st.mouse_refresh_at=0
 pc.bShowMouseCursor=False
 ns['update_mouse_cursor_aid'](pc,clock[0]+.03)
 assert pc.bShowMouseCursor and not st.controller_mode
 assert st.cursor_last is not None
 # User F9 focus recovery should be non-gameplay and not touch spawn pool.
 before=st.spawn_requests
 assert ns['recover_ui_focus']()
 assert st.spawn_requests==before and st.opened
 st.page='SPAWN';st.spawn_view='SEARCH'
 assert ns['recover_ui_focus']() is False  # don't steal keyboard from editor
 st.page='PLAYER';st.spawn_view='BROWSE'
 # Hold stick clicks again for 0.72s to close.
 keys.update(ns['CONTROLLER_CHORD'])
 ns['controller_ui_tick'](pc,clock[0]+.50)
 assert st.opened
 ns['controller_ui_tick'](pc,clock[0]+1.27)
 assert not st.opened and st.input_pc is None and not st.cursor_shapes
 # Safest fallback still exists for controllers which don't report stick click.
 keys.clear();keys.update(ns['LEGACY_CONTROLLER_CHORD'])
 assert ns['_controller_chord'](pc)
 keys.clear()
 # User can toggle cursor aid, select Noir and keep numeric theme migration.
 st.opened=False
 ns['apply_noir_preset']()
 assert st.theme_idx==5 and abs(st.panel_opacity-.89)<1e-9
 assert st.cursor_aid
 ns['toggle_cursor_aid']();assert not st.cursor_aid
 ns['toggle_cursor_aid']();assert st.cursor_aid
 for theme in (0,5):
  st.theme_idx=theme
  for wh in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
   ns['viewport']=lambda wh=wh:wh
   ns['open_menu']();assert st.draw_ok
   for page in ('PLAYER','MOTION','SPAWN','WORLD','WAYPOINTS','COMBAT','CONTENT','STYLE'):
    ns['show_page'](page);assert st.draw_ok,(theme,wh,page,st.message)
    x,y,w,h,*_=st.panel_rect
    assert len(st.buttons)>=7 and all(
        x-4<=entry['rect'][0] and y-4<=entry['rect'][1] and
        entry['rect'][0]+entry['rect'][2]<=x+w+4 and
        entry['rect'][1]+entry['rect'][3]<=y+h+4 for entry in st.buttons)
   ns['close_menu']()
 # Auditable real PNGs: cannot convert a missing or modified image into an asset.
 for asset in ('PAD_L3','PAD_R3'):
  raw=(root/'CROWN_CC0_ASSETS'/ns['ART_FILES'][asset]).read_bytes()
  assert ns['_verify_png_bytes'](asset,raw)
  assert not ns['_verify_png_bytes'](asset,raw+b'X')
 assert 'ROUTE_STRIP' in ns['ART_FILES']  # unchanged source retained, just no longer draws opaque strip
 assert not any('optional_art_image(layout,\'ROUTE_STRIP\'' in ln for ln in
                (root/'SOURCE/__init__.py').read_text().splitlines())
 print('PASS v4.0: L3/R3 hold open-close, legacy fallback, mouse focus recovery, visible cursor aid, editors, Noir, 64 view/page configurations, PNG integrity, no white travel strip')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
