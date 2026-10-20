"""Real mods_base autostart semantics modeled with fake Oak2 controls; NOT in-game certification."""
import runpy,sys,json,tempfile,time,types
from pathlib import Path
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=set();calls=[];hooks_added=[];original_pool_count=len(ctx['pool'].calls)
original={name:sys.modules.get(name) for name in ('unrealsdk','unrealsdk.hooks','unrealsdk.unreal','mods_base','mods_base.settings')}
try:
 with tempfile.TemporaryDirectory() as tmp:
  folder=Path(tmp)
  settings_mod=types.ModuleType('mods_base.settings');settings_mod.SETTINGS_DIR=folder
  def build_mod(**kw):
   calls.append(('registered',kw))
   class Mod:
    def __init__(self):
     self.is_enabled=False
     if kw['settings_file'].exists() and json.loads(kw['settings_file'].read_text()).get('enabled') is True:
      self.enable()
    def enable(self):
     if self.is_enabled:return
     self.is_enabled=True
     kw['settings_file'].write_text(json.dumps({'enabled':True}))
     if kw.get('on_enable'):kw['on_enable']()
    def disable(self):
     self.is_enabled=False
     kw['settings_file'].write_text(json.dumps({'enabled':False}))
     if kw.get('on_disable'):kw['on_disable']()
   return Mod()
  ctx['mods'].build_mod=build_mod
  ctx['pc'].IsInputKeyDown=lambda key:getattr(key,'KeyName',key) in keys
  ctx['hooks'].add_hook=lambda *arg:hooks_added.append(arg)
  ctx['hooks'].remove_hook=lambda *arg:None
  sys.modules.update({'unrealsdk':ctx['u'],'unrealsdk.hooks':ctx['hooks'],
                      'unrealsdk.unreal':ctx['unreal'],'mods_base':ctx['mods'],
                      'mods_base.settings':settings_mod})
  source=(root/'SOURCE/__init__.py').read_text()
  ns={'__name__':'crowns_v32_test'}
  exec(compile(source,'CROWNS_v32.py','exec'),ns)
  state=ns['State'];mod=ns['CROWNS_MOD']
  assert mod.is_enabled and calls[-1][1]['auto_enable'] is True
  assert calls[-1][1]['settings_file']==folder/'CROWNs_Freedom_ModState.json'
  assert len(hooks_added)==1 and state.controller_watcher_installed
  assert json.loads((folder/'CROWNs_Freedom_ModState.json').read_text())['enabled'] is True
  # Startup watcher must NOT open the overlay or invoke actions for a stray A button.
  keys.add('Gamepad_FaceButton_Bottom')
  state.controller_poll_last=0
  ns['controller_watch_tick']()
  assert not state.opened and not state.controller_open_latched
  keys.clear()
  # Opening requires ALL THREE buttons and 0.72s hold; a partial combo is insufficient.
  keys.update(('Gamepad_LeftShoulder','Gamepad_RightShoulder'))
  state.controller_poll_last=0;ns['controller_watch_tick']()
  assert not state.opened
  keys.add('Gamepad_DPad_Up')
  state.controller_poll_last=0;ns['controller_watch_tick']()
  assert not state.opened and state.controller_hold_start>0
  state.controller_hold_start=time.monotonic()-.85
  state.controller_poll_last=0;ns['controller_watch_tick']()
  assert state.opened and state.draw_ok and state.controller_focus>=0
  assert len(hooks_added)>=2
  # Freshly opened held chord cannot select a control even with trigger held.
  idx=state.controller_focus
  action_log=[]
  state.buttons[idx]['run']=lambda:action_log.append('selected')
  ns['controller_ui_tick'](ctx['pc'],time.monotonic())
  assert not action_log
  # With navigation unblocked, DPad changes focused button; A runs only the focused action on edge.
  keys.clear();state.controller_open_block_until=0;state.controller_last_keys={}
  oldidx=state.controller_focus
  initial_rebuilds=state.ui_rebuild_count
  keys.add('Gamepad_DPad_Down')
  ns['controller_ui_tick'](ctx['pc'],time.monotonic())
  assert state.controller_focus!=oldidx and state.draw_ok
  assert state.ui_rebuild_count==initial_rebuilds  # focus border moved without full UI rebuild
  keys.clear();state.controller_last_keys={}
  pos=state.controller_focus
  state.buttons[pos]['run']=lambda:action_log.append('selected')
  keys.add('Gamepad_FaceButton_Bottom')
  ns['controller_ui_tick'](ctx['pc'],time.monotonic())
  ns['controller_ui_tick'](ctx['pc'],time.monotonic())
  assert action_log==['selected']
  # B closes without restoring permanent currency or spawning anything.
  keys.clear();state.controller_last_keys={}
  keys.add('Gamepad_FaceButton_Right')
  ns['controller_ui_tick'](ctx['pc'],time.monotonic())
  assert not state.opened and len(ctx['pool'].calls)==original_pool_count  # no unintended item generation
  # Controller OFF prevents opening, while keyboard F7 remains registered.
  keys.clear();ns['toggle_controller_enabled']()
  assert not state.controller_enabled
  keys.update(ns['CONTROLLER_CHORD']);state.controller_poll_last=0
  state.controller_hold_start=time.monotonic()-1
  ns['controller_watch_tick']()
  assert not state.opened
  # Explicitly disabled mods must remain disabled after restart (stable settings path).
  mod.disable()
  ns2={'__name__':'crowns_v32_test_again'}
  exec(compile(source,'CROWNS_v32.py','exec'),ns2)
  assert not ns2['CROWNS_MOD'].is_enabled
  assert calls[-1][1]['settings_file']==folder/'CROWNs_Freedom_ModState.json'
  assert json.loads((folder/'CROWNs_Freedom_ModState.json').read_text())['enabled'] is False
  print('PASS v3.2: startup auto-enable + stable persisted off; hold-to-open controller; D-pad focus; A edge action; B close; disabled gamepad; no accidental spawn')
finally:
 for key,value in original.items():
  if value is None:sys.modules.pop(key,None)
  else:sys.modules[key]=value
