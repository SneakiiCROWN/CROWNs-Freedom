"""Scrap King v1.8 tests for page help, safe text scaling and legacy UI prefs."""
import json, runpy, sys, tempfile
from pathlib import Path
ctx=runpy.run_path(str(Path(__file__).with_name('test_arsenal_events.py')))
src=Path(__file__).resolve().parents[1].joinpath('SOURCE/__init__.py').read_text('utf-8')
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ctx['mode'][0]=0
 ctx['world'].GetName=lambda:'WhistlersMaw'
 ns={'__name__':'crowns_v18_help_test'}
 exec(compile(src,'v18test','exec'),ns)
 st=ns['State']
 assert ns['PAGE_HELP'].keys()>=set(('PLAYER','MOTION','COMBAT','LOOT','WORLD','PARTY','SPAWN','EVENTS','CONTENT','PRESETS','STYLE','DEV'))
 # Text effective area is bounded by its caller allocation, rather than
 # leaking horizontally when scaled (as seen in screenshots).
 seen=[]
 position=ns['size_position']
 def trace(widget,x,y,w,h,z=0):
  seen.append((widget,x,y,w,h,z))
  return position(widget,x,y,w,h,z)
 ns['size_position']=trace
 for font in (.85,1.0,1.25):
  st.font_scale=font
  for scale in (.52,.65,.88,1.03,1.3):
   seen.clear()
   ns['text'](ctx['W']('parent'),'SAMPLE TEXT',20,30,270,50,scale=scale)
   assert seen
   elem,x,y,vw,vh,z=seen[-1]
   effective_scale=max(.60,min(1.50,scale*font))
   assert abs(vw*effective_scale-270)<.01,(font,scale,vw)
   assert abs(vh*effective_scale-50)<.01,(font,scale,vh)
   assert x==20 and y==30
 ns['size_position']=position
 # Help must open and close without performing any game actions.
 for size in ((2560,1440),(1920,1080),(1280,720),(854,480)):
  ns['viewport']=lambda size=size:size
  ns['open_menu'](); assert st.opened
  for page in ns['PAGE_HELP']:
   ns['show_page'](page)
   assert not st.help_open
   before=len(ctx['pool'].calls)
   ns['toggle_page_help']()
   assert st.help_open and st.draw_ok
   assert len(ctx['pool'].calls)==before
   btn_labels=[b['name'] for b in st.buttons]
   assert 'HIDE HELP' in btn_labels,(size,page,btn_labels)
   ns['toggle_page_help']()
   assert not st.help_open
   assert any(b['name']=='? HELP' for b in st.buttons)
  ns['toggle_page_help']()
  assert st.help_open
  ns['show_page']('PLAYER')
  assert not st.help_open
  ns['close_menu'](); assert not st.opened
 # Existing Forge metadata remains after migrating old layout preferences.
 with tempfile.TemporaryDirectory() as tmp:
  ns['SETTINGS_DIR']=Path(tmp)
  save=Path(tmp)/'CROWNs_Freedom_UI.json'
  token=ns['SPAWN_POOLS'][3][1]
  save.write_text(json.dumps({'theme_index':0,'text_scale':1.25,'opacity':.65,'scale':1.22,
                             'window_x':700.0,'window_y':800.0,
                             'forge_favorites':[token],'forge_search':'Hellfire'}),encoding='utf-8')
  ns['load_preferences']()
  assert st.theme_idx==0 and st.window_x is None and st.window_y is None
  assert st.font_scale==1.0 and st.panel_scale==1.0
  assert st.spawn_search=='hellfire' and token in st.spawn_favorites
  ns['save_preferences']()
  assert json.loads(save.read_text())['prefs_schema']==4
  st.font_scale=1.22; st.theme_idx=3; st.window_x=99.
  ns['save_preferences']()
  st.font_scale=.85;st.theme_idx=0;st.window_x=None
  ns['load_preferences']()
  assert abs(st.font_scale-1.22)<1e-4 and st.theme_idx==3 and st.window_x==99
 print('PASS v1.8: help across 12 pages x 4 resolutions; text bounds and legacy prefs migration')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
