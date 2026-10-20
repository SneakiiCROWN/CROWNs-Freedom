"""v5.8 Neon Vault art/theme and native fallback smoke; no live BL4 assertion."""
import runpy,sys,hashlib
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v58_theme'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_v58','exec'),ns)
 st=ns['State'];pool_calls_at_start=len(ctx['pool'].calls)
 assert ns['RELEASE_VERSION']=='5.26.0'
 assert ns['THEMES'][0]['name']=='CROWN BLACKGLASS'
 assert ns['THEMES'][5]['name']=='CROWN NOIR' # existing theme indexes stable
 assert len(ns['ART_FILES'])==67 and len(ns['ART_SHA256'])==67
 for name in ('NEON_HEADER','NEON_SIDEPANEL','NEON_CIRCUITS','NEON_STRIP'):
  path=root/'CROWN_CC0_ASSETS'/(name+'.png')
  raw=path.read_bytes();assert ns['_verify_png_bytes'](name,raw)
  with Image.open(path) as image:
   assert image.mode=='RGBA'
   low,high=image.getchannel('A').getextrema()
   assert low==0 and (high>30 if name=='NEON_CIRCUITS' else high>100),(name,low,high)
 # Native UMG fallback must remain complete if every optional image import is refused.
 attempts=[]
 ns['optional_art_image']=lambda parent,name,*args,**kw: attempts.append(name) or False
 for actual_size in ((1280.,720.),(1920.,1080.),(2560.,1440.)):
  ns['viewport']=lambda size=actual_size:size
  for dock in ('SIDE','FULL'):
   st.theme_idx=0;st.page='PLAYER';st.dock_mode=dock
   assert ns['open_menu']() is not False
   assert st.draw_ok and st.buttons
   required=('R9_DOCK',) if dock=='SIDE' else ('R9_EXPEDITION',)
   assert all(item in attempts for item in required),(dock,attempts)
   if dock=='SIDE':assert 'R9_DOCK' in attempts
   else:assert 'ECHO_CONTENT_GLASS' in attempts
   ns['close_menu']()
 assert len(ctx['pool'].calls)==pool_calls_at_start,'art/menu tests must never trigger game inventory writes'
 print('PASS v5.8: 23 PNG hashes, 4 original transparent assets, stable theme indices, native UMG fallback at three resolutions both modes')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
