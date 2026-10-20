"""Verify Search, Level, Browse, Activity controls cannot overlap quick bar (mock)."""
import runpy,sys
from pathlib import Path
ctx=runpy.run_path(str(Path(__file__).with_name('test_arsenal_events.py')))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 source=(Path(__file__).resolve().parents[1]/'SOURCE'/'__init__.py').read_text()
 ns={'__name__':'crowns_v16_layout_test'}
 exec(compile(source,'layout_test','exec'),ns)
 state=ns['State']
 old_btn=ns['btn']
 buttons=[]
 def tracking(parent,caption,x,y,w,h,*args,**kwargs):
  buttons.append((caption,x,y,w,h))
  return old_btn(parent,caption,x,y,w,h,*args,**kwargs)
 ns['btn']=tracking
 ns['open_menu']()
 for vw,vh in ((2560,1440),(1920,1080),(1280,720),(854,480)):
  ns['viewport']=lambda vw=vw,vh=vh:(vw,vh)
  ns['show_page']('SPAWN')
  for view in ('SEARCH','LEVEL','BROWSE','TOOLS'):
   state.spawn_view=view
   buttons.clear()
   ns['redraw']()
   assert state.draw_ok,(vw,vh,view,state.message)
   x,y,w,h,_,_=state.panel_rect
   foot=y+h-141
   sidebar=min(185.,max(152.,w*.21))
   main_x=x+sidebar+18
   row_y=y+223
   for label,bx,by,bw,bh in buttons:
    if bx>=main_x-1 and row_y-1<=by<foot:
     assert by+bh<=foot-5,(vw,vh,view,label,by+bh,foot)
   if view in ('SEARCH','LEVEL'):
    assert (state.search_widget if view=='SEARCH' else state.level_widget) is not None
  ns['show_page']('DEV')
  state.activity_open=True
  for n in range(7):ns['log']('Checking activity row '+str(n))
  ns['redraw']()
  assert state.draw_ok
 ns['close_menu']()
 assert not state.hook_active and not ctx['pc'].bShowMouseCursor
 print('PASS v1.6 layout: Search/Level/Browse/Tools button bounds at four resolutions, DEV activity and cleanup')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
