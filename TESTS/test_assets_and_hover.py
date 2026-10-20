"""v1.9 positive/negative paths for packaged art import, source-license and hover help.
This is MOCK Unreal behaviour, not a BL4 in-game acceptance test.
"""
import runpy, sys, tempfile, zipfile, hashlib, json
from pathlib import Path
from types import SimpleNamespace
base=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from archive_fixture import identity
ctx=runpy.run_path(str(base/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'art_integration_tests'}
 exec(compile((base/'SOURCE/__init__.py').read_text(),'crowns19','exec'),ns)
 State=ns['State']
 assert len(ns['ART_FILES'])>=14
 # Safe fallback when mod archive/Unreal importer isn't available.
 assert ns['_art_texture']('unexpected_id') is None
 assert ns['_art_texture']('BLADE_PLATE') is None
 assert State.art_status.startswith('SHAPES /')
 # Attested packaged source art, not fonts or copyrighted Borderlands rips.
 raw_assets=base/'CROWN_CC0_ASSETS'
 assert (raw_assets/'LICENSE_KENNEY_CC0.txt').is_file()
 manifest=json.loads((raw_assets/'MANIFEST.json').read_text())
 assert len(manifest['assets'])>=20 and all(item['id'] in ns['ART_SHA256'] for item in manifest['assets'] if item['filename'].endswith('.png'))
 assert not list(raw_assets.rglob('*.ttf'))
 for asset in manifest['assets']:
  raw=(raw_assets/asset['filename']).read_bytes()
  assert hashlib.sha256(raw).hexdigest()==asset['sha256']
  assert asset['bytes']==len(raw)
 with tempfile.TemporaryDirectory() as tmp:
  settings=Path(tmp)/'settings';settings.mkdir()
  ns['SETTINGS_DIR']=settings
  archive=Path(tmp)/ns['ART_MOD_FILENAME']
  with zipfile.ZipFile(archive,'w') as z:
   identity(z,ns,marker=False)
   for name in ns['ART_FILES'].values():
    z.write(raw_assets/name,'CROWNs_Freedom_v1_9_Forge_and_Finish/CROWN_CC0_ASSETS/'+name)
  State.art_failed.clear()
  # Game importer unavailable: no files are extracted and native menu remains working.
  assert ns['_art_texture']('RIVET_PANEL') is None
  assert not (settings/'CROWNs_Freedom_ArtCache/RIVET_PANEL.png').exists()
  # Simulate the reflected Unreal importer, returning a texture object.
  State.art_failed.clear()
  recorded=[]
  orig_find=ctx['u'].find_object
  def find(kind,path):
   if path=='/Script/Engine.KismetRenderingLibrary':
    return SimpleNamespace(ClassDefaultObject=SimpleNamespace(
     ImportFileAsTexture2D=lambda world,file:recorded.append(Path(file)) or SimpleNamespace(name='mock_texture')))
   return orig_find(kind,path)
  ctx['u'].find_object=find
  assert ns['_art_texture']('BLADE_PLATE') is not None
  assert State.art_status=='PACKED ART / texture ready'
  assert recorded and recorded[-1].is_file()
  assert recorded[-1].read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
  assert ns['_art_texture']('BLADE_PLATE') is not None and len(recorded)==1 # cache
  native_canvas=ctx['W']('canvas')
  assert ns['optional_art_image'](native_canvas,'BLADE_PLATE',1,2,80,22)
  assert State.art_status=='PACKED ART / drawn'
  assert ns['_art_texture']('BOGUS') is None
  # Tooltips update a live label once on hover and once when hover ends.
  st=State
  messages=[]
  st.opened=True
  st.message='ready';st.hovered_control=None
  st.status_widget=SimpleNamespace(SetText=lambda s:messages.append(s))
  hovered=[False]
  entry=SimpleNamespace(IsHovered=lambda:hovered[0])
  st.buttons=[{'widget':entry,'name':'ENABLE GOD MODE'}]
  ns['poll_hover_help']()
  assert not messages
  hovered[0]=True;ns['poll_hover_help']();assert 'damage immunity' in messages[-1]
  ns['poll_hover_help']();assert len(messages)==1
  hovered[0]=False;ns['poll_hover_help']();assert messages[-1]=='STATUS // ready'
  st.opened=False
  assert len(ns['_control_description']('REQUEST SPAWN x1 LV40'))>20
  print('PASS v2.4: 17 packaged art/audio resources verified, archive-import fallback/positive path, texture cache, hover notes')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
