"""v4.7: long-hold press/release lifecycle regressions; no inventory requests."""
from pathlib import Path
import runpy,sys,time
from types import SimpleNamespace as NS
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_press_lifecycle_qa'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'press_lifecycle.py','exec'),ns)
 st=ns['State']; before=len(ctx['pool'].calls)
 assert ns['ART_MOD_FILENAME']=='CROWNs_Freedom_v5_26_ECHO_Fieldcraft_R22.sdkmod'
 clock=100.0
 keys={'Gamepad_FaceButton_Bottom'}
 ns['key_down']=lambda pc,key:key in keys
 native=object()
 item={'widget':native,'pressed':False}
 ns['_arm_native_click_guard'](item,clock)
 assert ns['_native_release_is_duplicate'](item,None,clock+.01,False,True)==False
 # After the old 350-ms expiry, even a full 5-second hold still suppresses
 # every native UMG release associated with the same raw press.
 assert ns['_native_release_is_duplicate'](item,None,clock+5.0,True,False)
 assert st.native_activation_widget is native
 assert ns['_native_release_is_duplicate'](item,None,clock+5.1,False,True)==False
 assert ns['_native_release_is_duplicate'](item,None,clock+5.2,True,False)
 keys.clear()
 assert ns['_native_release_is_duplicate'](item,None,clock+5.25,False,False)==False
 assert st.native_activation_widget is native
 assert ns['_native_release_is_duplicate'](item,None,clock+5.5,True,False)
 assert ns['_native_release_is_duplicate'](item,None,clock+5.95,False,False)==False
 assert st.native_activation_widget is None
 # A genuinely new press, including the same widget, must still work.
 keys.add('Gamepad_FaceButton_Bottom')
 ns['_arm_native_click_guard'](item,clock+6.0)
 assert ns['_native_release_is_duplicate'](item,None,clock+8.0,True,False)
 ns['_clear_native_click_guard']()
 assert not ns['_native_release_is_duplicate'](item,None,clock+8.1,True,False)
 # Raw Enter and raw controller activation are separately tracked.
 keys.clear();keys.add('Enter')
 ns['_arm_native_click_guard'](item,clock+10,'Enter')
 assert st.native_activation_source=='Enter'
 assert ns['_native_release_is_duplicate'](item,None,clock+12,True,False)
 # Widget identity, not label, decides whether a native release is duplicated.
 another={'widget':object()}
 assert not ns['_native_release_is_duplicate'](another,None,clock+12,True,False)
 ns['_clear_native_click_guard']()
 assert st.duplicate_native_releases_blocked>=4
 assert len(ctx['pool'].calls)==before,'Input suite must not spawn items'
 print('PASS v4.7: 5-second controller/Enter holds, repeated release callbacks, correct mouse/new press, isolated widget identities')
finally:
 for key,v in old.items():
  if v is None:sys.modules.pop(key,None)
  else:sys.modules[key]=v
