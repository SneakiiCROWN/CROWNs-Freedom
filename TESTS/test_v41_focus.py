"""v4.1 keyboard/mouse/gamepad and Forge browse UX regression (Oak2 simulated)."""
from pathlib import Path
import runpy, sys, time as pytime
from types import SimpleNamespace as NS
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_focus_qa'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crowns_focus.py','exec'),ns)
 st=ns['State'];pc=ctx['pc']
 assert ns['FORGE_PAGE_SIZE']==4 and ns['forge_page_capacity']()==4
 st.panel_rect=(5,5,1230,690,1366,768)
 assert ns['forge_page_capacity']()==4
 st.panel_rect=(5,5,1230,799,1920,1080)
 assert ns['forge_page_capacity']()==6
 st.panel_rect=(5,5,1400,900,1920,1080)
 assert ns['forge_page_capacity']()==8
 st.compact=True
 assert ns['forge_page_capacity']()==4
 st.compact=False
 st.spawn_page=0;st.spawn_search='';st.spawn_category_idx=0
 assert len(ns['forge_page_indices']())==8
 assert ns['forge_pages']()==9
 assert ns['forge_choose'](7)
 assert st.spawn_view=='TOOLS' and st.spawn_pool_idx==7
 ns['forge_toggle_view']()
 assert st.spawn_view=='BROWSE' and st.spawn_page==0
 # Hover highlight never steals input and always has exactly four movable outlines.
 ns['viewport']=lambda:(1920.,1080.)
 ns['open_menu']();assert st.draw_ok
 assert len(st.mouse_hover_frame)==4
 assert len(st.cursor_shapes)==5
 assert all(b['rect'][2]>=80 for b in st.buttons)
 # Cursor leaving and returning to SAME screen position MUST be redrawn.
 pc.GetMousePosition=lambda:(540.,400.)
 st.mouse_refresh_at=0;st.cursor_last=None
 ns['update_mouse_cursor_aid'](pc,100.)
 previous=st.cursor_last
 assert previous is not None,st.panel_rect
 pc.GetMousePosition=lambda:(0.,0.)
 ns['update_mouse_cursor_aid'](pc,101.)
 assert st.cursor_last is None
 pc.GetMousePosition=lambda:(540.,400.)
 ns['update_mouse_cursor_aid'](pc,102.)
 assert st.cursor_last==previous
 # Larger Forge fits all its new click targets with no footer collision.
 for wh in ((854.,480.),(1280.,720.),(1600.,900.),(1920.,1080.),(2560.,1440.)):
  ns['viewport']=lambda wh=wh:wh
  ns['redraw']();ns['show_page']('SPAWN')
  st.spawn_view='BROWSE';ns['redraw']()
  x,y,w,h,*_=st.panel_rect
  for button in st.buttons:
   bx,by,bw,bh=button['rect']
   assert x-4<=bx and by>=y-4
   assert bx+bw<=x+w+4 and by+bh<=y+h-55,(wh,button['name'],button['rect'],st.panel_rect)
  visible=ns['forge_page_capacity']()
  assert visible in (4,6,8)
  names=[item['name'] for item in st.buttons]
  assert sum(name[:2].strip().strip('.').isdigit() for name in names)>=visible
 ns['close_menu']()
 assert not st.cursor_shapes and not st.mouse_hover_frame
 print('PASS v4.1: 4/6/8 responsive Forge, visible mouse-hover frame, returning cursor, focus geometry at five viewports')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
