"""Version 5.3 offline unit checks, NOT live Borderlands 4 integration tests."""
import json,runpy,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v53_test'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'v53_source','exec'),ns)
 st=ns['State']
 with tempfile.TemporaryDirectory() as tmp:
  ns['SETTINGS_DIR']=Path(tmp)
  st.page='SPAWN';st.dock_mode='SIDE';st.art_mode='SHAPES';st.safe_mode=False
  st.opened=True
  ns['_mark_menu_opened']()
  marker=Path(tmp)/'CROWNs_Freedom_Menu_Active.json'
  data=json.loads(marker.read_text())
  assert data=={'schema':2,'version':'5.26.0','state':'open','page':'SPAWN',
                'dock':'SIDE','art':'SHAPES','safe_mode':False,'phase':'START'}
  assert len(marker.read_bytes())<250 and 'player' not in marker.read_text().lower()
  st.opened=False;st.previous_menu_unclean=False;st.previous_unclean_page='UNKNOWN'
  assert ns['_detect_unclean_menu_close']()
  assert st.safe_mode and st.previous_menu_unclean and st.previous_unclean_page=='SPAWN'
  # Handles old schema-1 marker from an earlier v5.2 crash safely.
  marker.write_text('{"schema":1,"version":"5.2","state":"open"}')
  st.safe_mode=False;st.previous_unclean_page='NOT_SET'
  assert ns['_detect_unclean_menu_close']() and st.previous_unclean_page=='UNKNOWN'
  # Untrusted page values never appear as arbitrary private strings in QA.
  marker.write_text('{"schema":2,"version":"5.3","state":"open","page":"PRIVATE_PATH"}')
  st.previous_unclean_page='NOT_SET'
  assert ns['_detect_unclean_menu_close']() and st.previous_unclean_page=='UNKNOWN'
  ns['_clear_menu_marker']()
  # Closing the UI may not be possible after failed AddToViewport; F9 now
  # emits the safe QA report without needing an onscreen button.
  st.opened=False;st.previous_unclean_page='UNKNOWN'
  ns['viewport']=lambda:(1920,1080)
  ns['session_role']=lambda:'SOLO'
  result=ns['focus_hotkey']()
  assert result is True
  qa=json.loads((Path(tmp)/'CROWNs_Freedom_QA_Report.json').read_text())
  assert qa['version']=='5.26.0' and qa['ui']['previous_unclean_menu_page']=='UNKNOWN'
  assert 'friend_name' not in json.dumps(qa)
  # When active, F9 still invokes input focus recovery and NOT QA export.
  st.opened=True
  st.f9_last_action=-1e6  # independent subsequent F9 keypress, not SDK+raw duplicate
  called=[]
  ns['recover_ui_focus']=lambda:called.append(1) or True
  assert ns['focus_hotkey']() is True and called==[1]
  # Failure of one unload/restore step must not skip subsequent cleanup.
  st.opened=False
  stages=[]
  def blow():
   stages.append('close')
   raise RuntimeError('sensitive path suppressed')
  ns['close_menu']=blow
  ns['release_input']=lambda:stages.append('input_fallback')
  ns['uninstall_controller_hook']=lambda:stages.append('hook')
  ns['hide_hud']=lambda:stages.append('hud')
  ns['restore']=lambda:stages.append('restore')
  ns['on_disable']()
  assert stages==['close','input_fallback','hook','hud','restore']
  assert st.runtime_failures[-1]=={'stage':'DISABLE_CLOSE','kind':'RuntimeError'}
  assert 'sensitive path' not in str(st.runtime_failures)
  stages.clear()
  ns['wallet_clear']=lambda:stages.append('wallet')
  ns['reset_all']()
  assert stages==['close','input_fallback','hud','wallet','restore']
  assert st.runtime_failures[-1]=={'stage':'RESET_CLOSE','kind':'RuntimeError'}
 print('PASS v5.3: safe crash context, v5.2 marker compatibility, menu-closed F9 QA, independent teardown recovery')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
