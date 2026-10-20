"""v4.7: collision-swept requests, partial-move recovery and explicit False API reports."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys,runpy
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={name:sys.modules.get(name) for name in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v47_swept_test'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'v47-source','exec'),ns)
 st=ns['State']; actor=ctx['pawn']; coord=[0.,0.,400.]; initial_drops=len(ctx['pool'].calls)
 actor.K2_GetActorLocation=lambda:NS(X=coord[0],Y=coord[1],Z=coord[2])
 calls=[]
 def good_move(vector,sweep,*args):
  calls.append(sweep);assert sweep is True,'Unsafe non-swept movement is forbidden'
  coord[:]=[vector.X,vector.Y,vector.Z];return True
 actor.K2_SetActorLocation=good_move
 assert ns['_teleport_actor'](actor,(500.,100.,420.))
 assert st.travel_last_state=='ARRIVAL_READBACK_CONFIRMED_SWEPT'
 assert calls==[True]
 # API rejection cannot fall back to no-sweep.
 coord[:]=[0.,0.,400.];calls.clear()
 def reject(vector,sweep,*args):
  calls.append(sweep);return False
 actor.K2_SetActorLocation=reject
 assert not ns['_teleport_actor'](actor,(2000.,0.,400.))
 assert coord==[0.,0.,400.] and calls==[True]
 assert st.travel_last_state=='ENGINE_REJECTED_SWEPT_MOVE'
 # A blocked sweep that partially moves the player triggers a swept rollback.
 def partial_then_restore(vector,sweep,*args):
  calls.append(sweep)
  if len(calls)==1:
   coord[:]=[vector.X/3.,vector.Y/3.,vector.Z];return False
  coord[:]=[vector.X,vector.Y,vector.Z];return True
 calls.clear(); actor.K2_SetActorLocation=partial_then_restore
 assert not ns['_teleport_actor'](actor,(1200.,0.,400.))
 assert coord==[0.,0.,400.]
 assert st.travel_last_state=='PARTIAL_MOVE_ROLLBACK_CONFIRMED'
 assert calls==[True,True]
 # Both requests rejected: keep emergency local-player return anchor.
 coord[:]=[0.,0.,400.];calls.clear();st.travel_recovery_anchor=None
 def partial_no_rollback(vector,sweep,*args):
  calls.append(sweep)
  if len(calls)==1:
   coord[:]=[400.,0.,400.]
  return False
 actor.K2_SetActorLocation=partial_no_rollback
 assert not ns['_teleport_actor'](actor,(1200.,0.,400.))
 assert st.travel_last_state=='PARTIAL_MOVE_RETURN_UNCONFIRMED'
 assert st.travel_recovery_anchor is not None
 assert st.travel_recovery_anchor[1]==(0.,0.,400.)
 # The user can try RETURN even without a preceding successful teleport.
 actor.K2_SetActorLocation=good_move
 assert ns['bookmark_back']()
 assert coord==[0.,0.,400.] and st.travel_recovery_anchor is None
 # Make sure explicit False return cannot be mistaken for UI-only acceptance.
 assert ns['attempt'](NS(SetInputMode_UIOnly=lambda *a:False),'SetInputMode_UIOnly',None) is False
 assert ns['attempt'](NS(SetInputMode_UIOnly=lambda *a:None),'SetInputMode_UIOnly',None) is True
 assert ns['attempt'](NS(SetInputMode_UIOnly=lambda *a:True),'SetInputMode_UIOnly',None) is True
 # Existing loot and platform achievement APIs untouched.
 assert len(ctx['pool'].calls)==initial_drops
 assert 'SetAchievement(' not in (root/'SOURCE/__init__.py').read_text()
 print('PASS v4.7: swept travel, no unsafe fallback, rollback, emergency return and explicit UIOnly rejection')
finally:
 for name,value in old.items():
  if value is None:sys.modules.pop(name,None)
  else:sys.modules[name]=value
