"""v5.2 regression: preserve controller settings across session replacement.
Offline test double only; not a proof of BL4 input capture or crash resolution.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import runpy,sys
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old_modules={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v51_controller_qa'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_v51_source','exec'),ns)
 st=ns['State']; assert st.dock_mode=='FULL'
 assert ns['THEMES'][5]['bg']=='#0B0909' and ns['THEMES'][5]['accent']=='#FFD08A'
 assert ns['_verify_png_bytes']('BLACK_MARKET_SKIN',(root/'CROWN_CC0_ASSETS/BLACK_MARKET_SKIN.png').read_bytes())
 before=len(ctx['pool'].calls)
 released=[];movement=[]
 class Controller:
  bShowMouseCursor=True
  bEnableMouseOverEvents=True
  bEnableClickEvents=True
  bEnableTouchEvents=True
  bBlockInput=True
  def SetIgnoreMoveInput(self,value):movement.append(('move',value))
  def SetIgnoreLookInput(self,value):movement.append(('look',value))
 current=Controller()
 old=Controller()
 st.opened=True;st.root=None;st.tree=None;st.canvas=None
 st.input_pc=old
 st.input_saved={'bShowMouseCursor':False,'bBlockInput':True}
 st.input_move_ignored_original=False
 st.input_look_ignored_original=False
 ns['get_pc']=lambda possibly_loading=False:current
 ns['cls']=lambda path:NS(ClassDefaultObject=NS(
     SetInputMode_GameOnly=lambda *args:released.append('game') or True,
     SetFocusToGameViewport=lambda *args:True))
 ns['_invalidate_pending_session']('controller changed')
 assert not st.opened and st.input_pc is None
 assert released==[], 'No GameOnly writes to a replacement controller BL4 owns'
 assert current.bShowMouseCursor is True
 assert current.bEnableClickEvents is True
 assert current.bEnableTouchEvents is True
 assert current.bBlockInput is True
 assert movement==[],'Old controller movement state must not be restored to a new controller'
 assert old.bBlockInput is True,'Old/unavailable controller wrapper must not be touched'
 assert len(ctx['pool'].calls)==before
 # Diagnostic export stores fault category/type but NEVER exception message.
 ns['record_runtime_fault']('redraw',ValueError('private/path/player_name'))
 assert st.runtime_failures[-1]=={'stage':'REDRAW','kind':'ValueError'}
 assert 'private' not in str(st.runtime_failures)
 print('PASS v5.4: replacement PC game-owned input state untouched, stale motion ignores discarded, privacy, noir')
finally:
 for k,v in old_modules.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
