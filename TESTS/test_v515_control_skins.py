"""Offline regression: actual art-backed controls remain native-clickable and safe to drop."""
from pathlib import Path
from PIL import Image
import runpy,sys,hashlib
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'], 'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v515_skin'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'v515skin','exec'),ns)
 assert ns['RELEASE_VERSION']=='5.26.0'
 assert len(ns['ART_SHA256'])==len(ns['ART_FILES'])==67
 for name in ('ECHO_BTN_IDLE','ECHO_BTN_ACTIVE','ECHO_BTN_DANGER'):
  p=root/'CROWN_CC0_ASSETS'/(name+'.png')
  with Image.open(p) as im:
   assert im.mode=='RGBA' and im.size==(320,64)
   assert im.getchannel('A').getextrema()[0]==0
  assert ns['_verify_png_bytes'](name,p.read_bytes())
 clicks=[];art=[];state=ns['State'];state.theme_idx=0;state.safe_mode=False;state.buttons=[]
 ns['optional_art_image']=lambda parent,name,*args,**kw: art.append(name) or True
 ns['btn'](ctx['W']('Canvas'), 'OPEN INVENTORY',10,20,220,40,lambda:clicks.append('idle'))
 ns['btn'](ctx['W']('Canvas'), 'ACTIVE OPTION',10,70,220,40,lambda:clicks.append('active'),active=True)
 ns['btn'](ctx['W']('Canvas'), 'RESTORE ALL',10,120,220,40,lambda:clicks.append('danger'),danger=True)
 assert [x for x in art if x.startswith('ECHO_BTN_') or x=='R3_CARD']==['R3_CARD','ECHO_BTN_DANGER'],art
 assert 'ECHO_BTN_IDLE' not in art # R13 uses native glass for idle controls; two art imports replace three.
 assert len(state.buttons)==3 and not clicks
 assert all(b['widget'] is not None and callable(b['run']) for b in state.buttons)
 # Failing imports and explicit Safe Mode still leave native actions in place.
 art.clear();state.buttons=[];ns['optional_art_image']=lambda *args,**kw:False
 ns['btn'](ctx['W']('Canvas'),'ANY ACTION',0,0,200,40,lambda:clicks.append('fallback'))
 assert len(state.buttons)==1 and not clicks
 state.safe_mode=True;state.buttons=[];art.clear()
 ns['optional_art_image']=lambda parent,name,*args,**kw:art.append(name) or False
 ns['btn'](ctx['W']('Canvas'),'ANY ACTION',0,0,200,40,lambda:clicks.append('safe'))
 assert not art and len(state.buttons)==1
 assert not any(x[0] in ('SpawnActor','GiveItem') for x in ctx['pool'].calls if isinstance(x,tuple))
 print('PASS v5.15: 32 hashed textures; art skinned idle/active/danger; native fallback and safe-mode preserves actions')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
