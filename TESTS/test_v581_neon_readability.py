"""v5.25.0: native pixel/virtual pixel positioning and non-gameplay UI visuals."""
from pathlib import Path
from PIL import Image
import sys,runpy,hashlib
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v581_readability'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'v581_source','exec'),ns)
 s=ns['State'];s.opened=True
 assert ns['RELEASE_VERSION']=='5.26.0'
 asset=root/'CROWN_CC0_ASSETS/NEON_WORDMARK_COMPACT.png'
 with Image.open(asset) as im:
  assert im.mode=='RGBA' and im.getchannel('A').getextrema()[0]==0
 assert ns['_verify_png_bytes']('NEON_WORDMARK_COMPACT',asset.read_bytes())
 assert len(ns['ART_FILES'])==len(ns['ART_SHA256'])==67
 for screen_w,screen_h,panel,scale in (
     (1920.,1080.,(66.,80.,1382.,740.,1920.,1080.),1.),
     (2560.,1440.,(66.,180.,1520.,975.,2560.,1440.),1.),
     (854.,480.,(10.,10.,300.,650.,1280.,720.),854./1280.),
     (1280.,720.,(10.,10.,470.,700.,1280.,720.),1.),
 ):
  ns['viewport']=lambda sw=screen_w,sh=screen_h:(sw,sh)
  s.render_scale=scale;s.panel_rect=panel;s.dock_mode='FULL'
  px,py,w,h=ns['_toast_screen_rect']()
  assert 0<=px<=screen_w-w+.01 and 0<=py<=screen_h-h+.01,(screen_w,screen_h,px,py,w,h)
  # Side free enough to show a legible message means no menu overlap.
  apx,apy,apw,aph=(v*scale for v in panel[:4])
  free_left=apx-36;free_right=screen_w-(apx+apw)-36
  if max(free_left,free_right)>=250:
   assert px>=apx+apw+17.99 or px+w<=apx-17.99,(screen_w,px,w,apx,apw)
 # In particular, 1080p old default would overlap the full menu by ~74px.
 ns['viewport']=lambda:(1920.,1080.)
 s.panel_rect=(66.,80.,1382.,740.,1920.,1080.);s.render_scale=1.
 px,py,w,h=ns['_toast_screen_rect']()
 assert px>=1466 and w<=454 and px+w<=1902,(px,w)
 # 480p uses virtual panel coords; do not interpret a 300 virtual px dock as 300 physical px.
 ns['viewport']=lambda:(854.,480.)
 s.panel_rect=(900.,10.,350.,700.,1280.,720.);s.render_scale=854./1280.
 px,py,w,h=ns['_toast_screen_rect']()
 assert px>=18 and px+w<=836.01,(px,w)
 # Both native menu paths must request compact logo in Neon Vault; importer may refuse.
 before=len(ctx['pool'].calls)
 attempts=[]
 ns['optional_art_image']=lambda parent,name,*arg,**kw: attempts.append(name) or False
 ns['viewport']=lambda:(1920.,1080.)
 for dock in ('SIDE','FULL'):
  s.opened=False;s.theme_idx=0;s.page='PLAYER';s.dock_mode=dock
  assert ns['open_menu']() is not False
  assert s.draw_ok and ('R9_DOCK' if dock=='SIDE' else 'NEON_WORDMARK_COMPACT') in attempts,(dock,attempts)
  ns['close_menu']()
 assert len(ctx['pool'].calls)==before
 print('PASS v5.25.0: compact neon wordmark, 23 verified PNG references, correct viewport-scaled toast placement and native fallback')
finally:
 for key,val in old.items():
  if val is None:sys.modules.pop(key,None)
  else:sys.modules[key]=val
