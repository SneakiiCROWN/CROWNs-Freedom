"""V5.13 UX features under synthetic Oak2; no native BL4 spawn certification."""
from pathlib import Path
import runpy,sys,math
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v513_test'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_v513_source','exec'),ns)
 st=ns['State'];st.encounter_route='BMS';categories=ns['UI_CATEGORY_PAGES'] # Exercise the preserved BMS workspace.
 assert len(categories)==6
 pages={page for group in categories.values() for page in group}
 assert len(pages)==24 and {'FINDER','ARENA','WEEKLY','SPAWN','WAYPOINTS'} <= pages
 assert set(ns['FINDER_TERMS'])==pages
 assert len(ns['finder_results']())==24
 st.finder_query='god mode'; assert [row[0] for row in ns['finder_results']()]==['PLAYER']
 st.finder_query='Maurice'; assert [row[0] for row in ns['finder_results']()]==['WEEKLY']
 st.finder_query='teleport'; assert [row[0] for row in ns['finder_results']()]==['WAYPOINTS']
 st.finder_query='xxxx'; assert ns['finder_results']()==[]
 ns['clear_finder_search'](); assert len(ns['finder_results']())==24
 ns['finder_change_page'](200);assert st.finder_page==math.ceil(21/6)-1
 ns['finder_change_page'](-100);assert st.finder_page==0
 # All new buttons render as native UMG and leave existing game calls alone.
 pre=len(ctx['pool'].calls)
 for wh in ((1280,720),(1920,1080),(2560,1440)):
  ns['viewport']=lambda wh=wh:wh
  for page in ('FINDER','DISPLAY','ARENA'):
   st.opened=False;st.dock_mode='FULL';st.page=page;st.finder_mode='BROWSE'
   assert ns['open_menu']() is not False
   assert st.draw_ok and st.opened
   names=[b['name'] for b in st.buttons]
   assert 'QUICK DOCK' in names and 'FIND / SEARCH' in names, names
   if page=='FINDER':assert 'TYPE TO SEARCH' in names and 'NEXT RESULTS >>' in names
   if page=='DISPLAY':assert any(x.startswith('POPUPS:') for x in names)
   if page=='ARENA':assert 'STATUS / CLEANUP' in names
   ns['close_menu']()
 assert len(ctx['pool'].calls)==pre
 # Top screen, not the far-left side; popup blocks neither gameplay nor clicks.
 st.opened=False;st.toast_position='TOP_CENTRE';st.toast_duration=6.0
 ns['viewport']=lambda:(1920.,1080.)
 x,y,w,h=ns['_toast_screen_rect']()
 assert abs(x-(1920-w)/2)<0.1 and 30<=y<=112 and h>=70,(x,y,w,h)
 st.toast_position='TOP_RIGHT';assert ns['_toast_screen_rect']()[0]>x
 st.toast_position='TOP_LEFT';assert ns['_toast_screen_rect']()[0]<x
 ns['set_toast_duration'](100);assert st.toast_duration==8.0
 ns['set_toast_duration'](-10);assert st.toast_duration==2.0
 # Optional third-party bridge is gated and NEVER uses a spawning command.
 class Controller:
  def __init__(self):self.calls=[]
  def ConsoleCommand(self,c):self.calls.append(c)
 fake=Controller()
 ns['session_role']=lambda:'COOP'
 ns['get_pc']=lambda **kw:fake
 assert ns['open_bms_interface']() is False and fake.calls==[]
 ns['session_role']=lambda:'SOLO'
 assert ns['open_bms_interface']() is True and fake.calls==['bms_gui']
 assert ns['show_bms_help']() is False and fake.calls==['bms_gui'] # cooldown
 assert ns['_request_bms_console']('bms_spawn') is False and fake.calls==['bms_gui']
 print('PASS v5.13: 21-page search/jump, solid top toast & adjustable duration, solo-only UI companion, no game spawn writes')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
