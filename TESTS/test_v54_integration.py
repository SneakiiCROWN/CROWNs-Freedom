"""v5.4 source-level regression: PC replacement ownership; raw F9; safe Forge
controller shortcuts; implemented visual assets and truthfully scoped HUD.
Uses mocked SDK and DOES NOT certify BL4 gameplay/UI rendering.
"""
import runpy,sys,types,ast
from pathlib import Path
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v54_integration'}
 src=(root/'SOURCE/__init__.py').read_text()
 exec(compile(src,'crown_v54_source','exec'),ns)
 st=ns['State']
 # New PlayerController belongs to BL4; menu teardown must NEVER change flags,
 # input mode, or movement/look ignore state on that replacement.
 class Replacement:
  def __init__(self):
   object.__setattr__(self,'changes',[])
   object.__setattr__(self,'bBlockInput',True)
   object.__setattr__(self,'bShowMouseCursor',True)
  def __setattr__(self,name,value):
   self.changes.append((name,value));object.__setattr__(self,name,value)
 replacement=Replacement()
 st.input_pc=object();st.input_saved={'bBlockInput':False}
 st.opened=False
 ns['get_pc']=lambda **kw: replacement
 ns['_invalidate_pending_session']('test controller switch')
 assert replacement.changes==[],replacement.changes
 assert replacement.bBlockInput and replacement.bShowMouseCursor
 assert st.input_pc is None and st.input_saved is None
 assert 'UNTOUCHED' in st.input_last_status
 # Controller-accessible category buttons DO NOT attempt to type or spawn.
 st.spawn_category_idx=0;st.spawn_view='SEARCH';st.spawn_pending=None
 st.opened=False
 assert ns['forge_search_preset']('PISTOL')
 assert ns['_spawn_category']()=='PISTOL' and ns['_spawn_visible_indices']()
 assert st.spawn_view=='BROWSE' and st.spawn_pending is None
 st.spawn_view='SEARCH'
 assert ns['forge_search_preset']('SHOTGUN')
 assert ns['_spawn_category']()=='SHOTGUN' and ns['_spawn_visible_indices']()
 # F9 raw receives UI-only edge and dispatches undecorated action once per hold.
 st.opened=True
 st.input_pc=replacement
 st.session_anchor='test'
 st.session_last_check=1e20
 st.viewport_last_check=1e20
 st.last_poll=0.0
 st.f9_down=False
 ns['get_pc']=lambda **kw: replacement
 ns['key_down']=lambda pc,key:key=='F9'
 ns['_session_anchor']=lambda:'test'
 ns['controller_ui_tick']=lambda pc,now:None
 ns['monitor_controller_focus']=lambda pc,now:None
 ns['update_mouse_cursor_aid']=lambda pc,now:None
 ns['_poll_move']=lambda pc:False
 ns['poll_hover_help']=lambda:None
 calls=[]
 def f9_once():calls.append('F9');st.opened=False
 ns['_focus_recovery_action']=f9_once
 ns['tick']()
 assert calls==['F9'],calls
 # Verify bound checks are in source rather than assuming UI-only dispatch.
 assert "f9=key_down(pc,'F9')" in src
 assert 'State.f9_last_action' in src
 assert 'RELEASE_LABEL' in src
 assert "optional_art_image(parent,'CHECK'" in src
 assert "optional_art_image(parent,'DROP_ARROW'" in src
 assert 'ROUTE_STRIP' in ns['ART_FILES']  # reserved; not drawn due prior white-strip regression
 assert 'else:text(layout,r12_input_prompt()' in src and "btn(layout,'CLOSE / B'" in src
 for device,expected in (('KEYBOARD','TAB FOCUS'),('MOUSE','CLICK SELECT'),('CONTROLLER','A SELECT')):
  st.r10_device=device;st.controller_mode=device=='CONTROLLER';st.controller_enabled=True
  assert expected in ns['r12_input_prompt'](),device
 assert len(ns['UI_CATEGORY_PAGES'])==6
 assert len({name for arr in ns['UI_CATEGORY_PAGES'].values() for name in arr})==24
 assert ns['RELEASE_VERSION']=='5.26.0'
 # Widget removal can throw on a stale Unreal wrapper after a map change.
 # It MUST NOT escape the close handler or skip remaining input recovery.
 st.opened=True;st.root=object();st.input_pc=None;st.input_saved=None
 old_call=ns['call']
 ns['call']=lambda obj,name,*a: (_ for _ in ()).throw(RuntimeError('stale Unreal widget')) if name=='RemoveFromParent' else old_call(obj,name,*a)
 ns['close_menu']()
 assert not st.opened and st.root is None and st.input_pc is None
 assert st.runtime_failures[-1]['stage']=='MENU_REMOVE'
 ns['call']=old_call
 assert ns['ART_MOD_FILENAME']=='CROWNs_Freedom_v5_26_ECHO_Fieldcraft_R22.sdkmod'
 print('PASS v5.4: replacement PC never mutated; F9 raw UI edge; controller Forge category presets; truthful UI art and version')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
