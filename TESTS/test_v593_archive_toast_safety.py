"""v5.25.0: downloadable archive rename tolerance + no menu-covering toasts.

Offline mocked Oak2 and Unreal only. No live gameplay claims.
"""
from pathlib import Path
from types import SimpleNamespace
import runpy, sys, tempfile, zipfile
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v593_test'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'v593_source','exec'),ns)
 st=ns['State']
 assert ns['RELEASE_VERSION']=='5.26.0'
 art=(root/'CROWN_CC0_ASSETS/NEON_WORDMARK_COMPACT.png').read_bytes()
 source=(root/'SOURCE/__init__.py').read_bytes()
 with tempfile.TemporaryDirectory(prefix='crown_v593_') as td:
  home=Path(td); settings=home/'settings';settings.mkdir()
  ns['SETTINGS_DIR']=settings
  ns['__loader__']=SimpleNamespace(archive=None)
  renamed=home/'CROWNs_Freedom_v5_9_3_Echo_Neon_Archive_and_Toast_Fix (1).sdkmod'
  def archive_to(dst,version='5.26.0',asset=art):
   with zipfile.ZipFile(dst,'w') as z:
    z.writestr('CROWN/__init__.py',source.replace(b'RELEASE_VERSION = "5.26.0"',f'RELEASE_VERSION = "{version}"'.encode()))
    z.writestr('CROWN/CROWN_CC0_ASSETS/NEON_WORDMARK_COMPACT.png',asset)
  archive_to(renamed)
  assert ns['_art_mod_archive']()==renamed,'Safe renamed download must be discovered'
  # Wrong version and tampered art may not masquerade as this release.
  archive_to(renamed,version='5.9.2')
  assert ns['_art_mod_archive']() is None
  archive_to(renamed,asset=art+b'bad')
  assert ns['_art_mod_archive']() is None
  archive_to(renamed)
  duplicate=home/'CROWNs_Freedom_duplicate.sdkmod'
  archive_to(duplicate)
  assert ns['_art_mod_archive']() is None,'Ambiguous renamed installs fail closed'
  duplicate.unlink()
  assert ns['_art_mod_archive']()==renamed
 # A 1080p full menu with a right-hand gap can show its toast.
 ns['viewport']=lambda:(1920.,1080.)
 st.render_scale=1.;st.opened=True;st.panel_rect=(66.,80.,1382.,740.,1920.,1080.)
 assert ns['_toast_has_safe_space']()
 # A 720p near-full-screen menu must defer, NOT cover confirmation buttons.
 ns['viewport']=lambda:(1280.,720.)
 st.panel_rect=(16.,16.,1248.,688.,1280.,720.)
 assert not ns['_toast_has_safe_space']()
 st.toast_widget=None;st.toasts_enabled=True;st.toast_render_failed=False
 st.toast_queue=['TEST'];st.toast_shown=0
 ns['_toast_tick'](11.)
 assert st.toast_queue==['TEST'] and st.toast_widget is None and st.toast_shown==0
 # After closing the menu, the same queued message is rendered as gameplay toast.
 st.opened=False
 ns['_toast_tick'](12.)
 assert not st.toast_queue and st.toast_widget is not None and st.toast_shown==1
 ns['_dismiss_toast'](clear_queue=True)
 print('PASS v5.25.0: verified renamed archives, fail closed on mismatch/duplicates, non-obscuring deferred toast')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
