"""v3.6 release safety: atomic UI profiles, persistent prefs recovery, live resize, editor lifecycle."""
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile, json, sys,runpy,time
base=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(base/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
  'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crowns_stability_test'}
 exec(compile((base/'SOURCE/__init__.py').read_text(),str(base/'SOURCE/__init__.py'),'exec'),ns)
 st=ns['State']
 assert ns['ART_MOD_FILENAME']=='CROWNs_Freedom_v5_26_ECHO_Fieldcraft_R22.sdkmod'
 with tempfile.TemporaryDirectory() as folder:
  ns['SETTINGS_DIR']=Path(folder)
  prefs=Path(folder)/'CROWNs_Freedom_UI.json'; bak=prefs.with_name(prefs.name+'.bak')
  st.theme_idx=1;st.spawn_search='road';st.checkpoints={1:('TestMap',(102.,203.,304.))}
  ns['save_preferences']();assert prefs.exists() and not bak.exists()
  st.theme_idx=2;st.spawn_search='boss';ns['save_preferences']()
  assert bak.exists() and json.loads(bak.read_text())['theme_index']==1
  assert json.loads(prefs.read_text())['theme_index']==2
  prefs.write_text('{interrupted write',encoding='utf-8')
  st.theme_idx=4;st.checkpoints={}
  ns['load_preferences']()
  assert st.prefs_recovered and st.theme_idx==1
  assert st.checkpoints[1]==('TestMap',(102.,203.,304.))
  ns['save_preferences']()
  assert json.loads(prefs.read_text())['theme_index']==1
  assert json.loads(bak.read_text())['theme_index']==1
  # Reject an oversized or malformed backup; do not apply it.
  prefs.write_text('broken',encoding='utf8');bak.write_text('garbage',encoding='utf8')
  assert ns['_read_preferences_with_backup'](prefs) is None
  assert not st.prefs_recovered
  # No partial profile mutations when one field is missing.
  st.theme_idx=1;st.font_scale=1.14;st.panel_scale=1.22;st.panel_opacity=.90
  st.ui_profiles['1']={'theme_index':4,'text_scale':1.2,'scale':1.9}
  assert not ns['load_ui_profile'](1)
  assert (st.theme_idx,st.font_scale,st.panel_scale,st.panel_opacity)==(1,1.14,1.22,.90)
  st.ui_profiles['1']={'theme_index':3,'text_scale':1.2,'scale':1.5,'opacity':.96,'forge_search':'pistol'}
  assert ns['load_ui_profile'](1)
  assert (st.theme_idx,st.font_scale,st.panel_scale,st.panel_opacity)==(3,1.2,1.5,.96)
  # Start a native UI with mock viewport. Force a live resize and confirm panel fits.
  ns['viewport']=lambda:(1920.,1080.)
  ns['open_menu']();assert st.opened and st.draw_ok
  assert st.viewport_signature==(1920.,1080.)
  ns['viewport']=lambda:(1280.,720.)
  st.last_poll=0.0;st.viewport_last_check=0.0;st.session_last_check=time.monotonic()
  ns['key_down']=lambda pc,name:False
  before=st.ui_rebuild_count
  ns['tick']()
  assert st.ui_rebuild_count==before+1 and st.viewport_signature==(1280.,720.)
  assert st.draw_ok
  x,y,w,h,*_=st.panel_rect
  assert x>=0 and y>=0 and x+w<=1280/ min(1.0,1280/1280,720/720)+1
  # Read draft while it is still parented. Simulate widgets losing GetText
  # the moment the old canvas is removed.
  st.page='SPAWN';st.nav_group='MORE';st.spawn_view='SEARCH'
  ns['redraw']()
  old_canvas=st.canvas
  state={'detached':False}
  st.search_widget=NS(GetText=lambda:None if state['detached'] else 'laser rifle')
  old_remove=old_canvas.RemoveFromParent
  def watched_remove():
   state['detached']=True
   return old_remove()
  old_canvas.RemoveFromParent=watched_remove
  ns['redraw']()
  assert state['detached'] and st.spawn_search_draft=='laser rifle'
  old_canvas.RemoveFromParent=old_remove
  ns['close_menu']()
 print('PASS v3.6: preference backup recovery, migration-safe profile load, viewport resize, detached-editor draft retention')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
