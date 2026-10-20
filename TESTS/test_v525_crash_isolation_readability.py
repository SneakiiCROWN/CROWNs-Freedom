"""v5.25: exact-source offline tests, not a substitute for actual BL4 crash dump."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json,runpy
root=Path(__file__).resolve().parents[1]
ns=runpy.run_path(str(root/'TESTS/test_core.py'))['ns']
st=ns['State'];g=ns['save_input'].__globals__
assert ns['RELEASE_VERSION']=='5.26.0'
# Diagnostic marker is privacy constrained and retains native phase when a
# game window vanishes unexpectedly (still not proof of cause).
with TemporaryDirectory() as tmp:
 g['SETTINGS_DIR']=Path(tmp)
 st.opened=True;st.page='SPAWN';st.dock_mode='FULL';st.safe_mode=False
 ns['_set_native_phase']('ART_IMPORT')
 marker=Path(tmp)/'CROWNs_Freedom_Menu_Active.json'
 value=json.loads(marker.read_text())
 assert value['phase']=='ART_IMPORT' and value['page']=='SPAWN'
 assert 'coordinate' not in marker.read_text().lower()
 st.opened=False
 assert ns['_detect_unclean_menu_close']()
 assert st.safe_mode and st.previous_native_phase=='ART_IMPORT'
 ns['_clear_menu_marker']()
 # Unknown or adversarial phases cannot enter the crash breadcrumb.
 st.native_phase='READY'
 ns['_set_native_phase']('../../saves/private')
 assert st.native_phase=='READY'
# A 1440p control center should use the viewport instead of a corner island.
g['SETTINGS_DIR']=None
st.opened=False;st.safe_mode=True;st.dock_mode='FULL';st.panel_scale=1.14
st.window_x=st.window_y=None;st.page='PLAYER'
g['viewport']=lambda:(2560.,1440.)
g['_session_anchor']=lambda:('test world','test pawn')
ns['open_menu']()
assert st.opened,(st.message,st.input_last_status,st.runtime_failures)
x,y,w,h,*_=st.panel_rect
assert 1650<w<2350 and 1000<h<1400,(x,y,w,h)
assert x>200 and y>40,(x,y,w,h)
# Clear A/B testing against a game crash: no undocumented native overrides.
assert st.input_pc.bBlockInput is False
ns['close_menu']()
# Replaced controller: never send mode/flag writes to stale object.
class PC:
 def __init__(self):self.changes=[]
 def __setattr__(self,k,v):
  if k=='changes':object.__setattr__(self,k,v)
  else:self.changes.append((k,v));object.__setattr__(self,k,v)
original=PC();current=PC();st.input_pc=original
st.input_saved={'bShowMouseCursor':True}
st.input_mode_owned=True
restore=g['get_pc']; g['get_pc']=lambda **kw:current
ns['release_input']()
assert not original.changes and not current.changes
assert st.input_pc is None and not st.input_mode_owned
assert st.input_mode_used=='STALE PC / NO NATIVE RESTORE'
g['get_pc']=restore
print('PASS v5.25: private crash phase marker, 1440p larger centered menu, no bBlockInput writes, stale controller isolation')
