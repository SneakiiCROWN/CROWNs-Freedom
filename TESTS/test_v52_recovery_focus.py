"""v5.2 tests: persistent graphics/audio safe mode, foreground gated raw input,
reentrant UMG render suppression and preservation of legacy functionality.
These are offline test doubles, not live BL4 gameplay validation.
"""
from pathlib import Path
import json,runpy,sys,tempfile
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v52_test'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_v52_source','exec'),ns)
 st=ns['State']
 with tempfile.TemporaryDirectory() as d:
  ns['SETTINGS_DIR']=Path(d)
  st.opened=False; st.art_mode='AUTO'; st.audio_mode='NORMAL'; st.safe_mode=False
  st.art_textures={'TRADER_LEFT':object()}
  ns['toggle_safe_mode']()
  assert st.safe_mode and not st.art_textures
  assert ns['_art_texture']('TRADER_LEFT') is None
  assert ns['play_ui_sound']('select',force=True) is False
  saved=json.loads((Path(d)/'CROWNs_Freedom_UI.json').read_text())
  assert saved['safe_mode'] is True and saved['art_mode']=='AUTO' and saved['audio_mode']=='NORMAL'
  st.safe_mode=False
  ns['load_preferences']()
  assert st.safe_mode is True
  ns['toggle_safe_mode']()
  assert not st.safe_mode and st.art_mode=='AUTO' and st.audio_mode=='NORMAL'
  st.opened=True;st.page='PLAYER';st.dock_mode='FULL'
  ns['_mark_menu_opened']()
  st.opened=False
  marker=Path(d)/'CROWNs_Freedom_Menu_Active.json'
  assert marker.exists()
  st.safe_mode=False; st.previous_menu_unclean=False
  assert ns['_detect_unclean_menu_close']() is True
  assert st.safe_mode and st.previous_menu_unclean
  assert json.loads(marker.read_text())=={'schema':2,'version':'5.26.0','state':'open','page':'PLAYER','dock':'FULL','art':'AUTO','safe_mode':False,'phase':'START'}
  ns['_clear_menu_marker']()
  assert not marker.exists()
  st.safe_mode=False;st.previous_menu_unclean=False
  assert ns['_detect_unclean_menu_close']() is False
 assert ns['_game_window_foreground']() is True or sys.platform=='win32'
 original=sys.platform
 try:
  sys.platform='win32'
  ns['_game_window_foreground']=lambda:False
  assert ns['_windows_raw_key']('F7') is False
  assert ns['_windows_raw_key']('Gamepad_DPad_Up') is False
 finally:sys.platform=original
 renders=[]
 def fake_redraw():
  renders.append(1)
  ns['redraw']()  # nested call must coalesce and terminate
 st.opened=True
 ns['_redraw_impl']=fake_redraw
 ns['redraw']()
 assert len(renders)==2 and not st.redraw_busy and not st.redraw_pending
 assert ns['ART_MOD_FILENAME']=='CROWNs_Freedom_v5_26_ECHO_Fieldcraft_R22.sdkmod'
 assert len(ns['UI_CATEGORY_PAGES'])==6
 print('PASS v5.2: persistent safe mode, foreground-gated raw input, bounded redraw, existing menu categories')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
