"""v5.25 STUDIO milestone: actual mocked UMG button positions and Forge logic.

These checks DO NOT certify image rendering, input capture, item delivery, or
native BL4 memory behaviour. Only game-side acceptance can do that.
"""
from pathlib import Path
import sys,runpy,time
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
previous={k:sys.modules.get(k) for k in keys}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_studio_overhaul'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_source','exec'),ns)
 s=ns['State'];pages=ns['UI_CATEGORY_PAGES'];g=ns
 assert ns['RELEASE_VERSION']=='5.26.0'
 assert len(pages)==6
 # Full command-centre rail exposes supported sections without overlap.
 for viewport in ((1280.,720.),(1920.,1080.),(2560.,1440.)):
  g['viewport']=lambda screen=viewport:screen
  for category,subpages in g['STUDIO_SECTIONS'].items():
   s.page=subpages[-1];s.dock_mode='FULL';s.opened=False;s.safe_mode=True
   s.window_x=s.window_y=None;s.panel_scale=1.0
   g['open_menu']();assert s.draw_ok,(viewport,category,s.runtime_failures[-4:])
   x,y,w,h,*_=s.panel_rect
   departments=[b for b in s.buttons if b['name'] in {n.upper() for n in g['STUDIO_SECTIONS']} and b['rect'][0]<x+min(234,max(160,w*.20))-1]
   assert len(departments)==9,(viewport,category,len(departments))
   for i,a in enumerate(departments):
    ax,ay,aw,ah=a['rect'];assert aw>=140 and ah>=20
    assert ay+ah<y+h-160 and callable(a['run'])
    for b in departments[i+1:]:
     bx,by,bw,bh=b['rect']
     assert ax+aw<=bx or bx+bw<=ax or ay+ah<=by or by+bh<=ay
   g['close_menu']()
 # New Forge tools are real command bindings. Each quantity step must clear
 # a pending request and never invoke the native pool spawn method.
 s.page='SPAWN';s.spawn_view='TOOLS';s.safe_mode=True;s.opened=False;s.spawn_count=2
 s.dock_mode='FULL';g['viewport']=lambda:(1920.,1080.)
 g['open_menu']()
 assert s.draw_ok
 names=[b['name'] for b in s.buttons]
 # Quantity now uses the shared native slider + exact/controller editor.
 quantity=next(ref for ref in s.sliders if ref.name=='QUANTITY')
 assert quantity.minimum==1 and quantity.maximum==3 and quantity.step==1
 assert any(b.get('slider') is quantity for b in s.buttons)
 assert 'COMPARE' in names
 assert 'CANCEL REQUEST' in names
 # Inspection is a dedicated real UMG screen, not a simulated render.
 assert g['forge_open_inspector']()
 assert s.spawn_view=='INSPECT' and s.draw_ok
 inspector_buttons=[b for b in s.buttons if b['name'] in ('PREVIOUS ITEM', 'NEXT ITEM',
     'CHECK REAL FORGE API', 'REQUEST DROP / TWO PRESSES')]
 assert len(inspector_buttons)==4
 assert g['forge_inspector_values']()['verified'] is False
 assert g['forge_inspector_values']()['name']
 # Card controls cannot overlap and must remain above the footer at 720p.
 for a in inspector_buttons:
  ax,ay,aw,ah=a['rect']; panel=s.panel_rect
  assert ax>=panel[0] and ay+ah<panel[1]+panel[3]-141, (a,panel)
 for i,a in enumerate(inspector_buttons):
  ax,ay,aw,ah=a['rect']
  for b in inspector_buttons[i+1:]:
   bx,by,bw,bh=b['rect']
   assert ax+aw<=bx or bx+bw<=ax or ay+ah<=by or by+bh<=ay,(a,b)
 assert g['forge_close_inspector']() and s.spawn_view=='TOOLS'
 # Actual UMG widget created, not a fake drawing; no world method invoked.
 called=[];g['_spawn_api']=lambda:called.append('WRONG')
 s.spawn_pending=('armed',);s.spawn_expires=time.monotonic()+8
 assert g['adjust_spawn_count'](-1)
 assert s.spawn_count==1 and s.spawn_pending is None and s.spawn_expires==0
 assert not g['adjust_spawn_count'](-999) and s.spawn_count==1
 assert g['adjust_spawn_count'](+999) and s.spawn_count==3
 assert not g['adjust_spawn_count'](True)
 assert not called
 g['close_menu']()
 print('PASS studio source-layout: 18 UMG category/resolution combinations, direct tools, Forge steppers safely stage only')
finally:
 for k,v in previous.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
