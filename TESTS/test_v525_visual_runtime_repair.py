"""v5.25 visual-runtime repair: source-based mock acceptance, NOT live BL4."""
from pathlib import Path
import sys,runpy
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                    'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
ns={'__name__':'crown_ui_runtime_acceptance'}
exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_source','exec'),ns)
st=ns['State'];g=ns
assert ns['RELEASE_VERSION']=='5.26.0'
assert ns['ART_MOD_FILENAME'].endswith('_R23.sdkmod')
# FULL panel gets real extra artwork mounts, larger navigation and a one-click
# SAFE UI toggle. Mounted images remain optional/non-hit-testable.
recorded=[]
real_image=g['optional_art_image']
g['optional_art_image']=lambda parent,asset,*args,**kw:(recorded.append(asset) or False)
st.opened=False;st.page='PLAYER';st.dock_mode='FULL';st.safe_mode=False
st.theme_idx=0;st.panel_scale=1.14;st.window_x=st.window_y=None
g['viewport']=lambda:(2560.0,1440.0)
ns['open_menu']()
assert st.opened and st.draw_ok,(st.message,st.runtime_failures,st.input_mode_used,st.input_pc)
assert {'R9_EXPEDITION','NEON_SIDEPANEL','NEON_CIRCUITS','ECHO_CONTENT_GLASS','NEON_WORDMARK_COMPACT','ECHO_BTN_DANGER'} <= set(recorded), set(recorded)
assert 'ECHO_BTN_IDLE' not in recorded # Idle buttons now use native glass; active/danger keep imported artwork.
buttons={b['name']:b for b in st.buttons}
assert min((b for b in st.buttons if b['name']=='PLAYER & COMBAT'),key=lambda b:b['rect'][0])['rect'][3]>=30.0
assert 'SAFE UI' in buttons
assert buttons['ENABLE GOD MODE']['rect'][3]>=43
ns['close_menu']()
# Native Forge card gains a real read-only API preflight shortcut; no spawn.
st.page='SPAWN';st.spawn_view='TOOLS';st.opened=False
ns['open_menu']()
assert st.draw_ok
next(b for b in st.buttons if b['name']=='COMPARE')['run']()
assert st.forge_compare_view and st.draw_ok
assert any(b['name']=='CHECK FORGE API' for b in st.buttons)
next(b for b in st.buttons if b['name']=='INSPECT POOL')['run']()
assert st.spawn_view=='INSPECT' and not st.forge_compare_view
ns['close_menu']()
# At small viewports, safe button must not collide with title, close or dock.
st.page='PLAYER';st.dock_mode='FULL';st.safe_mode=False
st.window_x=st.window_y=None
g['viewport']=lambda:(1280.0,720.0)
ns['open_menu']()
assert st.draw_ok and 'SAFE UI' in {b['name'] for b in st.buttons}
assert any(b['name']=='QUICK DOCK' for b in st.buttons)
ns['close_menu']()
g['optional_art_image']=real_image
# Cold Unreal texture imports are throttled; keep essential title + button
# skins ahead of ornamental frames. Do not invent actual successful imports.
class Library:
 def __init__(self):self.calls=[]
 def ImportFileAsTexture2D(self,world,path):
  self.calls.append(path)
  return object()
class KClass:
 def __init__(self,lib):self.ClassDefaultObject=lib
library=Library()
g['cls']=lambda *_:KClass(library)
g['world_and_state']=lambda:(object(),None)
g['_art_png_path']=lambda aid:Path('/fake/'+aid+'.png')
g['_set_native_phase']=lambda phase:None
st.safe_mode=False;st.art_mode='AUTO';st.art_failed.clear();st.art_textures.clear()
st.art_imports_this_frame=0;st.art_ambient_imports_this_frame=0;st.art_deferred.clear()
for asset in ('NEON_STRIP','ECHO_CONTENT_GLASS','TRADER_LEFT','NEON_SIDEPANEL','ECHO_NAV_FRAME'):
 g['_art_texture'](asset)
assert st.art_ambient_imports_this_frame==3
assert {'NEON_SIDEPANEL','ECHO_NAV_FRAME'}<=st.art_deferred
for asset in ('NEON_WORDMARK_COMPACT','ECHO_TOP_FRAME','ECHO_BTN_IDLE','ECHO_BTN_ACTIVE'):
 assert g['_art_texture'](asset) is not None,asset
assert len(library.calls)==7
# Total cold importer calls never exceeds 8 until a deliberate next redraw.
for asset in ('SIDE_SIGIL','TITLE_WORDMARK','AFTERDARK_BTN_IDLE','PAD_A'):
 g['_art_texture'](asset)
assert len(library.calls)==8
assert st.art_imports_this_frame==8
assert st.art_deferred
print('PASS visual runtime repair: genuine art mount paths, 1440p sidebar/large labels, safe mode button, controlled cold-import budget')
