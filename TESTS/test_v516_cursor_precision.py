"""v5.16 precision pointer and focus contract, using real source under Oak2 mocks."""
from pathlib import Path
from types import SimpleNamespace as NS
import runpy,sys,math
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_precision_qa'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crowns_precision.py','exec'),ns)
 st=ns['State']; pc=ctx['pc']
 assert ns['RELEASE_VERSION']=='5.26.0'
 assert ns['_mouse_xy']((False,0,0)) is None
 assert ns['_mouse_xy']((0,123,456)) is None
 assert ns['_mouse_xy']((True,360,240))==(360.,240.)
 assert ns['_mouse_xy']((1,360,240))==(360.,240.)
 assert ns['_mouse_xy']((float('nan'),12)) is None
 assert ns['_mouse_xy'](NS(X=float('inf'),Y=12)) is None
 # Mock 150% scaling; the UMG canvas is sized in logical viewport coordinates.
 class Layout:
  def GetViewportScale(self,pc):return 1.5
  def GetMousePositionOnViewport(self,pc):return NS(X=800.,Y=300.)
 layout=Layout()
 orig_cls=ns['cls']
 ns['cls']=lambda path: NS(ClassDefaultObject=layout) if 'WidgetLayoutLibrary' in path else orig_cls(path)
 pc.GetMousePosition=lambda:(True,900.,450.)
 assert ns['_mouse_position'](pc)==(600.,300.) and st.cursor_source.startswith('PC PIXELS')
 st.cursor_coordinates='NATIVE'
 assert ns['_mouse_position'](pc)==(900.,450.) and st.cursor_source=='PC NATIVE'
 st.cursor_coordinates='AUTO'
 layout.GetMousePositionScaledByDPI=lambda pc:NS(X=595.,Y=305.)
 assert ns['_mouse_position'](pc)==(595.,305.) and st.cursor_source=='UMG DPI'
 layout.GetMousePositionScaledByDPI=lambda pc:None
 assert ns['_mouse_position'](pc)==(600.,300.)
 pc.GetMousePosition=lambda:(False,0.,0.)
 assert ns['_mouse_position'](pc)==(800.,300.) and st.cursor_source=='UMG VIEWPORT'
 layout.GetMousePositionOnViewport=lambda pc:None
 assert ns['_mouse_position'](pc) is None and st.cursor_source=='UNAVAILABLE'
 # Drag uses render scale only. Dividing by DPI again would under-move.
 pc.GetMousePosition=lambda:(True,900.,450.)
 st.cursor_coordinates='AUTO'
 st.render_scale=.5
 st._layout_dpi=1.5
 st.panel_rect=(20.,30.,700.,450.,1800.,1000.)
 st.window_x=20.; st.window_y=30.
 st.canvas=ctx['W']('canvas')
 st.canvas.SetRenderTranslation=lambda v:setattr(st,'_last_translation',v)
 ns['key_down']=lambda pc,key:False
 ns['move_panel']()
 assert st.drag_armed
 pc.GetMousePosition=lambda:(True,975.,480.)
 assert ns['_poll_move'](pc)
 assert tuple(round(getattr(st._last_translation,k),2) for k in ('X','Y'))==(100.,40.)
 assert st.drag_last==(120.,70.)
 st.drag_armed=False
 # Coordinate fallback is persisted inside UI profiles without touching saves.
 st.cursor_coordinates='NATIVE'
 assert ns['profile_snapshot']()['cursor_coordinates']=='NATIVE'
 st.cursor_coordinates='AUTO'
 st.ui_profiles['1']=ns['profile_snapshot']()
 assert ns['cycle_cursor_coordinates']()=='NATIVE'
 assert ns['cycle_cursor_coordinates']()=='AUTO'
 assert ns['recover_ui_focus']() is False  # no open menu; safe guard
 ns['cls']=orig_cls
 print('PASS v5.16: cursor DPI/native/UMG fallbacks, invalid result, drag math, profile/preferences controls')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
