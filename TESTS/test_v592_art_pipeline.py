"""v5.25.0: art recovery must restore AUTO, preflight and PNG widgets fail closed.

This is an offline Oak2/Unreal mock. It cannot certify BL4 drawing.
"""
from pathlib import Path
import runpy,sys
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'], 'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v592_art_pipeline'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_v592_source','exec'),ns)
 s=ns['State']
 assert ns['RELEASE_VERSION']=='5.26.0'
 before=len(ctx['pool'].calls)
 s.opened=False;s.safe_mode=True;s.art_mode='SHAPES'
 s.art_failed={'NEON_WORDMARK_COMPACT'};s.art_fail_reasons={'NEON_WORDMARK_COMPACT':'bad importer'}
 ns['save_preferences']=lambda:None
 assert ns['resume_custom_art']()
 assert not s.safe_mode and s.art_mode=='AUTO'
 assert not s.art_failed and not s.art_fail_reasons
 assert 'RESUME CUSTOM ART' not in {label for label,fn,active in ns['_dock_quick_choices']('STYLE')}
 s.safe_mode=True
 assert ns['retry_art']() is False and s.safe_mode
 assert ns['art_preflight']() is False
 s.safe_mode=False;s.art_mode='SHAPES'
 assert ns['art_preflight']() is False
 # Preflight does not need the real game if a verified cached texture is available.
 s.art_mode='AUTO'; s.art_failed.clear();s.art_fail_reasons.clear()
 ns['_art_mod_archive']=lambda: Path('/mocked/installed.sdkmod')
 ns['_art_png_path']=lambda name:Path('/mocked/cache/NEON_WORDMARK_COMPACT.png')
 magic_texture=object();ns['_art_texture']=lambda name:magic_texture
 assert ns['art_preflight']() is True
 # No image should be mounted until the UMG widget is non-clickable.
 art_widget=object();mounted=[];called=[]
 ns['widget']=lambda name:art_widget
 ns['linear']=lambda values:values
 ns['put']=lambda parent,image:mounted.append(image)
 ns['size_position']=lambda *args:None
 ns['attempt']=lambda obj,method,*args:called.append(method) or method!='SetVisibility'
 s.art_drawn_count=0;s.art_failed.clear();s.art_fail_reasons.clear()
 assert ns['optional_art_image'](object(),'NEON_WORDMARK_COMPACT',0,0,80,30) is False
 assert not mounted and 'NEON_WORDMARK_COMPACT' in s.art_failed
 assert called==['SetBrushFromTexture','SetColorAndOpacity','SetVisibility']
 # A known broken UMG visibility API must not be retried every redraw.
 attempts=[]
 def blocked_texture(asset):
  attempts.append(asset)
  return None if asset in s.art_failed else magic_texture
 ns['_art_texture']=blocked_texture
 assert ns['optional_art_image'](object(),'NEON_WORDMARK_COMPACT',0,0,80,30) is False
 assert len(attempts)==1 and len(mounted)==0
 # If all required cosmetic APIs succeed, visibility must precede mounting.
 s.art_failed.clear();s.art_fail_reasons.clear()
 calls=[]
 ns['_art_texture']=lambda name:magic_texture
 ns['attempt']=lambda obj,method,*args:calls.append(method) or True
 ns['put']=lambda parent,image:calls.append('mount')
 assert ns['optional_art_image'](object(),'NEON_WORDMARK_COMPACT',0,0,80,30)
 assert calls.index('SetVisibility')<calls.index('mount')
 assert s.art_drawn_count==1
 assert len(ctx['pool'].calls)==before,'UI checks must not write gameplay state'
 print('PASS v5.25.0: art resume unblocks AUTO, opt-in preflight, rejected image invisibility fail-closed and cached, no gameplay writes')
finally:
 for key,val in old.items():
  if val is None:sys.modules.pop(key,None)
  else:sys.modules[key]=val
