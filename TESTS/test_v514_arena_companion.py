"""v5.14 arena controls are meaningful but cannot falsely assert external spawn success."""
from pathlib import Path
import runpy,sys,math,tempfile,json
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v514_arena_test'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_v514','exec'),ns)
 st=ns['State'];st.encounter_route='BMS' # This legacy dependency fixture models BMS, not Arena.
 assert ns['RELEASE_VERSION']=='5.26.0'
 class PC:
  def __init__(self):self.calls=[]
  def ConsoleCommand(self,command):self.calls.append(command)
 controller=PC()
 ns['session_role']=lambda:'SOLO'
 original_pc=ns['get_pc']
 ns['get_pc']=lambda **kw:controller
 with tempfile.TemporaryDirectory() as temp:
  sdkmods=Path(temp)/'sdk_mods';settings=sdkmods/'settings';settings.mkdir(parents=True)
  ns['SETTINGS_DIR']=settings
  assert ns['_arena_local_mod_files']()=={'bms_file':False,'blimgui_file':False,'oak_spawner_file':False}
  assert ns['arena_backend_check']() is False
  (sdkmods/'mob_spawner.sdkmod').write_bytes(b'placeholder')
  (sdkmods/'oak_spawner.sdkmod').write_bytes(b'placeholder')
  assert ns['_arena_local_mod_files']()['bms_file'] and ns['_arena_local_mod_files']()['oak_spawner_file']
  # File presence alone never calls the other mod or verifies its live status.
  assert ns['arena_backend_check']() is True and not controller.calls
  assert ns['arena_set_planned_batch'](3)
  assert st.arena_planned_batch==3 and not controller.calls
  saved=json.loads((settings/'CROWNs_Freedom_UI.json').read_text())
  assert saved['arena_planned_batch']==3
  assert not ns['arena_set_planned_batch'](999)
  assert not ns['arena_set_planned_batch']('bms_spawn monster')
  assert st.arena_planned_batch==3
  assert ns['export_qa_report']()
  report=json.loads((settings/'CROWNs_Freedom_QA_Report.json').read_text())
  assert report['external_arena']['recommended_batch_only']==3
  assert report['external_arena']['installed_files_not_enabled']['bms_file']
  assert not controller.calls
  ns['load_preferences']()
  assert st.arena_planned_batch==3
  # Migrate malformed and prior release preferences without unsafe counts.
  saved['arena_planned_batch']='nan'
  (settings/'CROWNs_Freedom_UI.json').write_text(json.dumps(saved))
  ns['load_preferences']()
  assert st.arena_planned_batch==1
  # Both views expose direct access; no implicit spawning from rendering.
  ns['get_pc']=original_pc
  start=len(ctx['pool'].calls)
  ns['viewport']=lambda:(1280,720)
  st.dock_favorites=['DIRECTOR','SANDBOX']
  for dock in ('SIDE','FULL'):
   st.opened=False;st.dock_mode=dock;st.page='ARENA'
   assert ns['open_menu']() is not False
   names=[b['name'] for b in st.buttons]
   if dock=='FULL':
    assert 'STATUS / CLEANUP' in names
    st.encounter_view='STATUS';ns['redraw']();names=[b['name'] for b in st.buttons]
    assert 'CHECK BACKEND FILES' in names and 'CLEAN OWNED / 2 PRESSES' in names
   else:
    assert ('ENCOUNTER DIRECTOR' in names or 'ENEMY / BOSS TOOLS' in names or 'ENCOUNTERS' in names) and 'FULL STUDIO' in names
   ns['close_menu']()
  assert len(ctx['pool'].calls)==start
  # The ONLY allowed third party requests are documented UI/help commands.
  ns['get_pc']=lambda **kw:controller
  assert ns['open_bms_interface']()
  assert controller.calls==['bms_gui']
  assert not ns['_request_bms_console']('bms_spawn 1 Char_Enemy')
  assert controller.calls==['bms_gui']
 print('PASS v5.14: bounded solo arena plan, read-only backend detection, persisted prefs, truthful export, UI layout and no spawn writes')
finally:
 for key,value in old.items():
  if value is None:sys.modules.pop(key,None)
  else:sys.modules[key]=value
