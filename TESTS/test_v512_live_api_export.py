"""v5.12: only allowlisted reflected names reach an opt-in JSON; no writes."""
import json,runpy,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v512_live_api_export'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_v512','exec'),ns)
 st=ns['State']
 assert ns['RELEASE_VERSION']=='5.26.0'
 with tempfile.TemporaryDirectory() as tmp:
  ns['SETTINGS_DIR']=Path(tmp)
  ns['viewport']=lambda:(2560,1440)
  ns['session_role']=lambda:'SOLO'
  # The first export must clearly indicate NOT_RUN, never invent detected APIs.
  assert ns['export_qa_report']()
  report=json.loads((Path(tmp)/'CROWNs_Freedom_QA_Report.json').read_text())
  assert report['read_only_api_audit']['status']=='NOT_RUN'
  # Mock introspection only: forbidden gameplay API invocations must not happen.
  invoked=[]
  class Actor:
   def GetEquippedInventory(self):invoked.append('inventory');raise AssertionError
   def GetCurrentVehicle(self):invoked.append('vehicle');raise AssertionError
   def GetTargetActor(self):invoked.append('target');raise AssertionError
  ns['pawn']=lambda:Actor()
  ns['world_and_state']=lambda:(object(),None)
  before=len(ctx['pool'].calls)
  assert ns['run_advanced_audit_and_export']()
  assert not invoked and len(ctx['pool'].calls)==before
  report=json.loads((Path(tmp)/'CROWNs_Freedom_QA_Report.json').read_text())
  audit=report['read_only_api_audit']
  assert audit['status']=='RUN' and audit['captured_unix_time'] is not None
  assert audit['character_and_categories']['character']=='loaded'
  assert audit['allowlisted_actor_methods_present']=={
    'weapon_parts':['GetEquippedInventory'],
    'vehicle_spawn':['GetCurrentVehicle'],
    'boss_spawn':['GetTargetActor']}
  assert audit['no_gameplay_write_intended'] is True
  assert audit['character_and_categories']['weapon_parts']=='read_only_refs:1'
  assert 'no operation sent' in st.message.lower() or 'EXPORTED' in st.message
  dumped=json.dumps(report)
  assert 'player_name' not in dumped and 'private_address' not in dumped
  # If no actor/world is available, report must overwrite stale results.
  ns['pawn']=lambda:None
  ns['world_and_state']=lambda:(None,None)
  assert ns['run_advanced_audit_and_export']()
  report=json.loads((Path(tmp)/'CROWNs_Freedom_QA_Report.json').read_text())
  assert report['read_only_api_audit']['character_and_categories']['character']=='missing'
  assert report['read_only_api_audit']['allowlisted_actor_methods_present']=={}
  assert report['read_only_api_audit']['status']=='RUN'
 print('PASS v5.12: opt-in API report saves allowlisted names, no gameplay calls, and clears stale results')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
