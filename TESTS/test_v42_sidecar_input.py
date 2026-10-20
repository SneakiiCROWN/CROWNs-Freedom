"""v4.2 Sidecar and fail-closed gameplay input isolation: offline engine mock.
Never claims to demonstrate game-side suppression of grenade/ability events.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import runpy,sys,time
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keep={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_sidecar_qa'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crowns_sidecar.py','exec'),ns)
 st=ns['State'];pc=ctx['pc'];actions=[];keys=set();pool_before=len(ctx['pool'].calls)
 pc.IsInputKeyDown=lambda k:getattr(k,'KeyName',k) in keys
 assert ns['ART_MOD_FILENAME']=='CROWNs_Freedom_v5_26_ECHO_Fieldcraft_R22.sdkmod'
 assert 'UIOnly' in (root/'SOURCE/__init__.py').read_text()
 assert st.dock_mode=='FULL'
 def inspect_view(wh,page):
  ns['viewport']=lambda:wh
  st.dock_mode='SIDE';st.page=page
  ns['open_menu']()
  assert st.opened and st.draw_ok,(wh,page,st.message)
  assert st.input_guard_confirmed and st.input_mode_used.startswith('UI ONLY')
  # At >=720p, PIN and JUMP PIN add two explicit, fully bounded hit targets.
  assert 10 <= len(st.buttons) <= 28,(wh,page,len(st.buttons))
  assert st.status_widget is not None  # no invisible error/status in Side Dock
  x,y,w,h,*_=st.panel_rect
  assert 400<=w<=480 and h<=830,(wh,st.panel_rect)
  for b in st.buttons:
   bx,by,bw,bh=b['rect']
   assert bx>=x-1 and bx+bw<=x+w+1 and by>=y-1 and by+bh<=y+h+1,(page,b['name'],b['rect'])
  rects=[b['rect'] for b in st.buttons]
  for i,a in enumerate(rects):
   for b in rects[i+1:]:
    overlap=min(a[0]+a[2],b[0]+b[2])-max(a[0],b[0])
    vertical=min(a[1]+a[3],b[1]+b[3])-max(a[1],b[1])
    assert overlap<=.2 or vertical<=.2,(wh,page,a,b)
  ns['close_menu']()
  assert st.input_guard_confirmed is False and pc.bShowMouseCursor is False
 for wh in ((854.,480.),(1280.,720.),(1366.,768.),(1920.,1080.),(2560.,1440.)):
  for page in ('PLAYER','MOTION','COMBAT','LOOT','WORLD','PARTY',
               'SPAWN','EVENTS','CONTENT','PRESETS','STYLE','DEV',
               'TROPHIES','WAYPOINTS','PROFILES','GEAR','DISPLAY','GUIDE'):
   inspect_view(wh,page)
 # Hotkey side/full is a functional renderer swap, without losing the active page.
 ns['viewport']=lambda:(1920.,1080.)
 st.page='PLAYER';st.dock_mode='SIDE';ns['open_menu']()
 assert any(b['name'].startswith('GOD MODE /') for b in st.buttons)
 assert st.buttons[ns['_controller_initial_focus']()]['name'].startswith('GOD MODE')
 old=st.ui_rebuild_count
 ns['dock_hotkey']()
 assert st.dock_mode=='FULL' and st.draw_ok and st.ui_rebuild_count>old
 ns['dock_hotkey']()
 assert st.dock_mode=='SIDE' and st.opened
 # Mouse/keyboard: arrow focus and Enter trigger precisely one chosen action.
 st.controller_focus=ns['_controller_initial_focus']()
 idx=st.controller_focus
 st.buttons[idx]['run']=lambda:actions.append('one')
 st.editor_enter_down=False;st.arrow_keys_down={};st.last_poll=0
 keys.add('Enter')
 ns['tick']()
 assert actions==['one'] and st.opened
 st.last_poll=0;ns['tick']()
 assert actions==['one']
 keys.clear();st.last_poll=0;ns['tick']()
 # Input safety: GameAndUI exists, but without UIOnly CROWN MUST refuse to open.
 ns['close_menu']()
 normal_cls=ns['cls']
 class Unsafe:
  def SetInputMode_GameAndUIEx(self,*a):return None
  def SetInputMode_GameOnly(self,*a):return None
  def SetFocusToGameViewport(self,*a):return None
 ns['cls']=lambda path:NS(ClassDefaultObject=Unsafe()) if path.endswith('WidgetBlueprintLibrary') else normal_cls(path)
 st.dock_mode='SIDE'
 ns['open_menu']()
 assert not st.opened and st.input_pc is None and not st.input_guard_confirmed
 assert 'SAFE INPUT UNAVAILABLE' in st.message or 'UIOnly' in st.message,(st.message,)
 ns['cls']=normal_cls
 ns['open_menu']()
 assert st.opened and st.input_guard_confirmed
 # No unsafe item/economy actions are executed by this suite.
 assert len(ctx['pool'].calls)==pool_before
 ns['close_menu']()
 st.dock_mode='FULL'
 ns['dock_hotkey']()
 assert st.opened and st.dock_mode=='SIDE' and st.input_guard_confirmed
 ns['close_menu']()
 print('PASS v4.2: 90 side-dock page/viewport layouts; visible status; input guard\n '
       'fail-closed when UIOnly absent; F11 renderer swap; keyboard Enter edge safety; rollback')
finally:
 for k,v in keep.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
