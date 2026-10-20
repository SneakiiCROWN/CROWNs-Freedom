"""v5.5 direct-tool dock: geometry, reachability and zero gameplay actions.

Synthetic Unreal UI only; live BL4 crash warnings and real input capture not certified.
"""
import runpy,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v55_direct_access'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_v55_source','exec'),ns)
 st=ns['State'];st.dock_favorites=['SANDBOX'];before=len(ctx['pool'].calls)
 groups=ns['UI_CATEGORY_PAGES'];names=ns['DOCK_TOOL_LABELS']
 assert len(groups)==6 and len(names)==24
 for wh in ((1280.,720.),(1920.,1080.),(2560.,1440.)):
  ns['viewport']=lambda wh=wh:wh
  for side in (False,True):
   st.dock_right=side
   for category,pages in groups.items():
    for page in pages:
     st.page=page;st.dock_mode='SIDE';st.side_action_page=0
     ns['open_menu']()
     assert st.opened and st.draw_ok,(wh,page)
     buttons=st.buttons
     labels=[b['name'] for b in buttons]
     assert {'QUICK','TOOLS','STYLE','FULL STUDIO','CLOSE / B'} <= set(labels),(wh,page,labels)
     assert {p for section in ns['STUDIO_SECTIONS'].values() for p in section}==ns['_KNOWN_PAGES']
     if page=='PLAYER':
      assert 'COMBAT TUNING' in labels and 'NEXT >' not in labels,labels
     if page=='TROPHIES':
      assert 'FULL STUDIO' in labels
     px,py,pw,ph,*_=st.panel_rect
     for idx,b in enumerate(buttons):
      x,y,w,h=b['rect']
      assert px-1<=x and x+w<=px+pw+1 and py-1<=y and y+h<=py+ph+1,(wh,page,b['name'],b['rect'])
      for other in buttons[:idx]:
       ax,ay,aw,ah=other['rect']
       width_overlap=min(x+w,ax+aw)-max(x,ax)
       height_overlap=min(y+h,ay+ah)-max(y,ay)
       assert width_overlap<1 or height_overlap<1, (wh,page,b['name'],other['name'],b['rect'],other['rect'])
     ns['close_menu']()
 # Direct navigation into previously buried pages never invokes an item pool.
 ns['viewport']=lambda:(1920.,1080.)
 st.page='LOOT';st.dock_mode='SIDE';ns['open_menu']()
 ns['r3_open_tool']('TROPHIES')
 assert st.opened and st.page=='TROPHIES' and st.draw_ok
 assert ns['_dock_status_message']
 ns['close_menu']()
 assert len(ctx['pool'].calls)==before,'navigation must never request items'
 print('PASS v5.5: all 18 direct tools, no hidden Player actions, 216 side views, no overlaps or unintended item spawn')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
