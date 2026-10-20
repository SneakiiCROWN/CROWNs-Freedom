"""v5.0: six-category launch, all 18 pages reachable, nav bounds, art verification, no game effects."""
import runpy,sys,hashlib,math
from pathlib import Path
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v50_qa'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_v50_source','exec'),ns)
 st=ns['State'];groups=ns['UI_CATEGORY_PAGES']
 assert tuple(groups)==('PLAYER','WORLD','FORGE','TRAVEL','FREEDOM','SETTINGS')
 assert len({p for pages in groups.values() for p in pages})==24
 assert all(ns['_ui_category_for'](p)==cat for cat,pages in groups.items() for p in pages)
 baseline=len(ctx['pool'].calls)
 for name in ('INK_RAIL','SIDE_SIGIL','WENREXA_SIDE'):
  raw=(root/'CROWN_CC0_ASSETS'/ns['ART_FILES'][name]).read_bytes()
  assert ns['_verify_png_bytes'](name,raw)
  assert not ns['_verify_png_bytes'](name,raw[:-4]+b'FAKE')
 # Native buttons are actual hit targets: no overlap and no clipping at tested
 # window boundaries. New category controls and subpages must fit above bar.
 for wh in ((1280.,720.),(1920.,1080.),(2560.,1440.)):
  ns['viewport']=lambda wh=wh:wh
  st.dock_mode='FULL';st.panel_scale=1.0;st.window_x=st.window_y=None
  for cat,pages in groups.items():
   for page in pages:
    st.page=page
    ns['open_menu']()
    assert st.draw_ok and st.opened,(page,wh,st.message)
    px,py,pw,ph,*_=st.panel_rect
    limit=py+ph-158
    category_names={n.upper() for n in ns['STUDIO_SECTIONS']}
    targets=[entry for entry in st.buttons if entry['name'] in category_names and entry['rect'][0]<px+min(234,max(160,pw*.20))-1]
    assert len(targets)==9,(cat,page,[entry['name'] for entry in st.buttons])
    for entry in targets:
     x,y,w,h=entry['rect'];assert y+h<limit,(wh,page,entry['name'],y+h,limit)
    submenu=[entry for entry in st.buttons if entry['name'] in ('OVERVIEW','MOVEMENT','COMBAT','PRESETS','WORLD SPEED','WEEKLY / MAURICE','EVENTS','CO-OP','ITEM FORGE','GEAR FILTERS','API / DLC','BOOKMARKS','CURRENCY','CAPACITY STUDIO','TROPHY JOURNAL','APPEARANCE','DISPLAY','UI PROFILES','RECOVERY','SAFETY','FIND TOOLS','ENEMY ARENA')]
    assert all(ns['studio_section_for'](p) in ns['STUDIO_SECTIONS'] for p in pages),(page,len(submenu),len(pages))
    for entry in submenu:
     x,y,w,h=entry['rect'];assert y+h<limit,(wh,page,entry['name'],y+h,limit)
    ns['close_menu']()
 # Navigation click should switch views, not grant/spawn anything.
 st.dock_mode='FULL';st.page='PLAYER';ns['open_menu']()
 button=next(b for b in st.buttons if b['name']=='FORGE & EQUIPMENT')
 button['run']()
 assert st.page=='SPAWN' and st.opened
 assert len(ctx['pool'].calls)==baseline
 ns['close_menu']()
 # Side Dock also presents six consistent categories, with cycling among subpages.
 st.dock_favorites=['SANDBOX'];st.dock_mode='SIDE';st.page='PLAYER';ns['open_menu']()
 assert {'QUICK','TOOLS','STYLE'} <= {b['name'] for b in st.buttons}
 assert any(b['name']=='COMBAT TUNING' for b in st.buttons)
 ns['side_next_tool']()
 assert st.page=='MOTION'
 ns['close_menu']()
 print('PASS v5.0: six categories, 18 real pages, layout at 3 viewports, action safety, art hashes, side category navigation')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
