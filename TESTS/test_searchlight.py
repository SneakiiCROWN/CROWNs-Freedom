"""v1.6 Searchlight regression: SDK mocked; not a real Borderlands 4 test."""
import sys,runpy,json,tempfile,time
from pathlib import Path
from types import SimpleNamespace
c=runpy.run_path(str(Path(__file__).with_name('test_arsenal_events.py')))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':c['mods'],'unrealsdk':c['u'],
                     'unrealsdk.hooks':c['hooks'],'unrealsdk.unreal':c['unreal']})
 source=(Path(__file__).resolve().parents[1]/'SOURCE'/'__init__.py').read_text()
 ns={'__name__':'crowns_v16_searchlight_test'}
 exec(compile(source,'v16_searchlight_test','exec'),ns)
 state=ns['State']
 c['pool'].calls.clear()  # Base harness deliberately issued test spawns first.
 with tempfile.TemporaryDirectory() as tmp:
  ns['SETTINGS_DIR']=Path(tmp)
  ns['open_menu']()
  assert state.opened
  ns['show_page']('SPAWN')
  ns['forge_open_search']()
  assert state.spawn_view=='SEARCH' and state.search_widget is not None
  # SDK GetText must be read explicitly on APPLY, not each frame.
  assert not ns['forge_apply_search']()  # Fake UMG widget lacks GetText, safe failure.
  assert state.spawn_view=='SEARCH' and not state.spawn_search
  state.search_widget=SimpleNamespace(GetText=lambda:'  HELlfiRE   ')
  assert ns['forge_apply_search']()
  assert state.spawn_search=='hellfire'
  filtered=ns['_spawn_visible_indices']()
  assert filtered and all('hellfire' in ns['SPAWN_POOLS'][i][0].lower()
                          or 'hellfire' in ns['SPAWN_POOLS'][i][1].lower()
                          for i in filtered)
  assert len(filtered)<len(ns['SPAWN_POOLS'])
  # Search only filters the fixed catalogue; no native spawning occurs.
  assert not c['pool'].calls
  assert ns['forge_lucky_pick']()
  assert state.spawn_pool_idx in filtered and state.spawn_view=='TOOLS'
  assert not state.spawn_pending
  assert not c['pool'].calls
  assert not ns['spawn_request']()
  assert state.spawn_pending is not None
  ns['forge_open_search']()
  state.search_widget=SimpleNamespace(GetText=lambda:'impossible_nonexistent_item')
  assert ns['forge_apply_search']()
  assert ns['_spawn_visible_indices']()==[]
  assert state.spawn_pool_idx==-1
  assert state.spawn_pending is None
  assert not ns['forge_lucky_pick']()
  assert not ns['spawn_request']()
  ns['save_preferences']()
  preferences=json.loads((Path(tmp)/'CROWNs_Freedom_UI.json').read_text())
  assert preferences['forge_search']=='impossible_nonexistent_item'
  ns['forge_clear_search']()
  assert len(ns['_spawn_visible_indices']())==len(ns['SPAWN_POOLS'])
  # A second native text input edits numeric item level (no spawn or side effects).
  ns['forge_choose'](0)
  assert ns['forge_open_level']()
  assert state.spawn_view=='LEVEL' and state.level_widget is not None
  state.level_widget=SimpleNamespace(GetText=lambda:'999')
  assert not ns['forge_apply_level']()
  assert state.spawn_level==40 and state.spawn_view=='LEVEL'
  state.level_widget=SimpleNamespace(GetText=lambda:'xx')
  assert not ns['forge_apply_level']()
  state.level_widget=SimpleNamespace(GetText=lambda:'53')
  assert ns['forge_apply_level']()
  assert state.spawn_view=='TOOLS' and state.spawn_level==53
  assert not state.spawn_pending and not c['pool'].calls
  ns['forge_open_level']()
  assert ns['forge_set_level_preset'](70) and state.spawn_level==70
  assert not ns['forge_set_level_preset'](999)

  assert state.spawn_search==''
  ns['forge_open_search']()
  ns['_invalidate_pending_session']('test map transition')
  assert state.spawn_view=='BROWSE' and state.search_widget is None
  assert not state.opened and not c['pc'].bShowMouseCursor
  # Activity is bounded; contains no persistent file records.
  for i in range(40):ns['log']('diagnostic '+str(i))
  assert len(state.activity_history)==16
  assert state.activity_history[-1]=='diagnostic 39'
  ns['open_menu']();ns['show_page']('DEV');ns['toggle_activity']()
  assert state.activity_open
  for resolution in ((2560,1440),(1920,1080),(1280,720),(854,480)):
   ns['viewport']=lambda resolution=resolution:resolution
   ns['redraw']()
   assert state.draw_ok
  ns['clear_activity']()
  assert len(state.activity_history)==1
  ns['close_menu']()
  # In-menu F10 should restore even if the high-level SDK hotkey is swallowed.
  ns['viewport']=lambda:(1920,1080)
  ns['open_menu']()
  ns['set_world_time'](2.0)
  assert c['world'].TimeDilation==2.0
  c['pc'].IsInputKeyDown=lambda key:getattr(key,'KeyName',key)=='F10'
  state.last_poll=0
  state.session_last_check=time.monotonic()
  ns['tick']()
  assert not state.opened and not state.hook_active
  assert c['world'].TimeDilation==1.0
  assert not c['pc'].bShowMouseCursor
  print('PASS v1.6: native search safe-fail, name filtering, empty results, no accidental spawns,')
  print('preferences, capped activity, 4-resolution DEV log and captured F10 restore.')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
