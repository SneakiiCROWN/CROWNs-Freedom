"""PlayStation/Xbox artwork selection changes native UI hints only, never gameplay."""
from pathlib import Path
from PIL import Image
import runpy,sys
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v5162_test'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'<source>','exec'),ns)
 assert ns['RELEASE_VERSION']=='5.26.0'
 assert len(ns['ART_FILES'])==len(ns['ART_SHA256'])==67
 for asset in ('PS_CROSS','PS_CIRCLE','PS_L3','PS_R3'):
  path=root/'CROWN_CC0_ASSETS'/(asset+'.png')
  with Image.open(path) as image:
   assert image.size==(96,96) and image.mode=='RGBA'
  assert ns['_verify_png_bytes'](asset,path.read_bytes())
 st=ns['State']
 st.gamepad_icons='XBOX';st.opened=False
 assert [ns['_gamepad_art'](v) for v in ('PAD_A','PAD_B','PAD_L3','PAD_R3')]==['PAD_A','PAD_B','PAD_L3','PAD_R3']
 calls=[];ns['save_preferences']=lambda:calls.append('saved')
 assert ns['cycle_gamepad_icons']()=='PLAYSTATION'
 assert [ns['_gamepad_art'](v) for v in ('PAD_A','PAD_B','PAD_L3','PAD_R3')]==['PS_CROSS','PS_CIRCLE','PS_L3','PS_R3']
 assert ns['profile_snapshot']()['gamepad_icons']=='PLAYSTATION'
 assert ns['cycle_gamepad_icons']()=='XBOX'
 assert calls==['saved','saved']
 # A cosmetic selection may not request an enemy or item spawn, give currency, or modify gamepad binds.
 forbidden=('SpawnActor','GiveItem','SetInputMode')
 assert not any(isinstance(v,tuple) and len(v)>0 and v[0] in forbidden for v in ctx['pool'].calls)
 print('PASS v5.25.0 selectable hash-checked PS glyphs; profile persistence; no gameplay writes')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
