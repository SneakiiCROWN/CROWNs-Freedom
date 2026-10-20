"""Supplemental v1.4 tests. Uses pure fake SDK objects; never claims game acceptance."""
from pathlib import Path
import json, runpy, sys, tempfile, types
ctx=runpy.run_path(str(Path(__file__).with_name('test_arsenal_events.py')))
from pathlib import Path
src=Path(__file__).resolve().parents[1].joinpath('SOURCE/__init__.py').read_text()
old={key:sys.modules.get(key) for key in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 # Reset the synthetic world to solo after the previous regression script.
 ctx['mode'][0]=0
 ctx['world'].GetName=lambda:'WhistlersMaw'
 ns={'__name__':'crown_v14_test'}
 exec(compile(src,'v14_test','exec'),ns)
 state=ns['State']
 with tempfile.TemporaryDirectory() as tmp:
  ns['SETTINGS_DIR']=Path(tmp)
  assert ns['toggle_spawn_favorite']()
  original=next(iter(state.spawn_favorites))
  ns['save_preferences']()
  state.spawn_favorites.clear()
  ns['load_preferences']()
  assert state.spawn_favorites=={original}
  prefs=ns['_prefs_file']()
  content=json.loads(prefs.read_text())
  content['forge_favorites']=['bad_unknown_token',original,'itempool_wrong_dlc']
  prefs.write_text(json.dumps(content))
  state.spawn_favorites.clear()
  ns['load_preferences']()
  assert state.spawn_favorites=={original},state.spawn_favorites
 # Reopen session with an active pending request. Next map invalidates it safely.
 ns['open_menu']()
 assert state.opened
 state.spawn_pending=('something',)
 state.spawn_expires=1e12
 state.wallet_pending=('cash',1000)
 state.party_approved=True
 state.party_selected=121234
 state.last_poll=0
 state.session_last_check=0
 before=state.session_anchor
 ns['tick']()
 assert state.opened and before==state.session_anchor, 'Stable session closed spuriously'
 #  Modifying world time should not change its identity.
 ctx['world'].TimeDilation=2.0
 state.last_poll=0
 state.session_last_check=0
 ns['tick']()
 assert state.opened,'WorldTime value changed and closed UI'
 # Real travel makes a new world name: must close and drop all pending actions.
 ctx['world'].GetName=lambda:'NewMap'
 state.last_poll=0
 state.session_last_check=0
 ns['tick']()
 assert not state.opened
 assert state.spawn_pending is None and state.wallet_pending is None
 assert not state.party_approved and state.party_selected is None
 assert not ctx['pc'].bShowMouseCursor
 assert state.session_resets==1
 print('PASS v1.4: saved/sanitized favorites, fixed world key, session travel cancels actions and restores UI input')
finally:
 for key,value in old.items():
  if value is None:sys.modules.pop(key,None)
  else:sys.modules[key]=value
