"""Offline integration: supplied assets/credits, real native styles, SFX opt-in, no gameplay writes."""
from pathlib import Path
from PIL import Image
import sys,runpy,wave
r=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(r/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v510_supplied'}
 exec(compile((r/'SOURCE/__init__.py').read_text(),'v510source','exec'),ns)
 s=ns['State']
 assert ns['RELEASE_VERSION']=='5.26.0'
 assert len(ns['ART_FILES'])==len(ns['ART_SHA256'])==67
 assert s.sfx_set=='ECHO'
 s.sfx_set='CLASSIC'
 for name in ('ECHO_TOP_FRAME','ECHO_NAV_FRAME','ECHO_CONTENT_GLASS','ECHO_DOCK_PLATE','PAD_A','PAD_B'):
  p=r/'CROWN_CC0_ASSETS'/(name+'.png');raw=p.read_bytes()
  assert len(raw)<250000 and ns['_verify_png_bytes'](name,raw)
  with Image.open(p) as im:
   assert im.mode=='RGBA' and im.getchannel('A').getextrema()[0]==0
 for cue in ns['SOUND_CUES']:
  for level in ('low','normal','high'):
   name='echo_'+level+'_'+cue+'.wav'
   p=r/'CROWN_CC0_ASSETS/UI_WAV'/name;raw=p.read_bytes()
   assert ns['_sound_bytes_valid'](name,raw)
   with wave.open(str(p)) as w:assert w.getnframes()>0 and w.getnchannels()==1 and w.getframerate()==22050
 calls=len(ctx['pool'].calls)
 ns['save_preferences']=lambda:None
 ns['play_ui_sound']=lambda *a,**kw:True
 assert ns['cycle_sfx_set']()=='ECHO'
 assert ns['cycle_sfx_set']()=='CLASSIC'
 assert len(ctx['pool'].calls)==calls
 source=(r/'SOURCE/__init__.py').read_text()
 # Check actual glass fill instead of prescribing an old source expression.
 fills=[];saved_box=ns['box'];saved_art=ns['optional_art_image']
 ns['box']=lambda parent,x,y,w,h,color,z=1:fills.append((w,h,color))
 ns['optional_art_image']=lambda *args,**kw:False
 s.theme_idx=0;s.panel_opacity=1.;s.panel_rect=None
 ns['btn'](ctx['W']('Canvas'),'IDLE',0,0,220,40,lambda:None)
 assert next(color[3] for w,h,color in fills if (w,h)==(220,40))==.64
 fills.clear();ns['btn'](ctx['W']('Canvas'),'ACTIVE',0,0,220,40,lambda:None,active=True)
 assert next(color[3] for w,h,color in fills if (w,h)==(220,40))==.98
 ns['box']=saved_box;ns['optional_art_image']=saved_art
 for mode in ('SIDE','FULL'):
  captured=[];ns['optional_art_image']=lambda parent,name,*args,**kw:captured.append(name) or False
  ns['viewport']=lambda:(1920.,1080.)
  s.opened=False;s.page='PLAYER';s.theme_idx=0;s.dock_mode=mode
  assert ns['open_menu']() is not False and s.draw_ok
  assert ('R9_DOCK' if mode=='SIDE' else 'R9_EXPEDITION') in captured
  assert ('R9_DOCK' if mode=='SIDE' else 'ECHO_CONTENT_GLASS') in captured
  ns['close_menu']()
 assert len(ctx['pool'].calls)==calls
 assert (r/'REFERENCE/THIRD_PARTY_CREDITS_V5_10.md').exists()
 print('PASS v5.10: 32 art hashes, 18 opt-in ECHO WAV hashes, dark native glass, fallback and zero gameplay writes')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
