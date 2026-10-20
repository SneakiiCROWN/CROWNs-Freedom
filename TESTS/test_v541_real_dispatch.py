"""Real mods_base-like keybind objects must never be called as Python functions.

Mocked Unreal for offline testing. Does not establish live BL4 behaviour.
"""
import runpy,sys,time,types,tempfile,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
mods=ctx['mods']
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
class KeybindType:
    def __init__(self,identifier,key,callback):
        self.identifier,self.key,self.callback=identifier,key,callback
        self.is_rebindable=True;self.display_name=identifier
        self.description='';self.description_title=identifier
        self.is_hidden=False;self.default_key=key
    # Deliberately no __call__. Real mods_base returns an object, not a function.

def keybind(identifier,key,event_filter=None):
    return lambda cb:KeybindType(identifier,key,cb)

def build_mod(**kw):
    assert len(kw['keybinds'])==7
    assert all(isinstance(x,KeybindType) for x in kw['keybinds'])
    return types.SimpleNamespace(**kw)
mods.keybind=keybind;mods.build_mod=build_mod
try:
    sys.modules.update({'mods_base':mods,'unrealsdk':ctx['u'],
                        'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
    ns={'__name__':'crown_v541_strict_dispatch'}
    exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_v541_source','exec'),ns)
    st=ns['State']
    binds={b.key:b for b in ns['CROWNS_MOD'].keybinds}
    assert set(binds)=={'F5','F6','F7','F8','F9','F10','F11'}
    assert not callable(binds['F9'])
    assert not callable(ns['focus_hotkey'])
    assert callable(ns['_focus_recovery_action'])
    # Raw UIOnly F9 must call the undecorated implementation, not the object.
    pc=object()
    st.opened=True
    st.input_pc=pc
    st.session_anchor='stable'
    st.session_last_check=1e20;st.viewport_last_check=1e20;st.last_poll=0.0
    st.f9_down=False;st.f9_last_action=-10
    ns['get_pc']=lambda **kw:pc
    ns['_session_anchor']=lambda:'stable'
    ns['key_down']=lambda pc,key:key=='F9'
    called=[]
    def recovered():
        called.append('RAW F9')
        st.opened=False
        return True
    ns['recover_ui_focus']=recovered
    ns['tick']()
    assert called==['RAW F9'],called
    # SDK F9 callback reaches the same routine and is subject to one-press debounce.
    binds['F9'].callback()
    assert called==['RAW F9']
    st.f9_last_action=-10
    ns['export_qa_report']=lambda:called.append('SDK F9') or True
    binds['F9'].callback()
    assert called==['RAW F9','SDK F9'],called
    # Previous versions' unclean-menu markers must survive upgrade for safe mode.
    with tempfile.TemporaryDirectory() as d:
        ns['SETTINGS_DIR']=Path(d)
        marker=Path(d)/'CROWNs_Freedom_Menu_Active.json'
        for ver in ('5.2.0','5.3.0','5.3.1','5.4.0','5.4.1'):
            marker.write_text(json.dumps({'version':ver,'state':'open','page':'SPAWN'}))
            st.safe_mode=False;st.previous_menu_unclean=False
            assert ns['_detect_unclean_menu_close'](),ver
            assert st.safe_mode and st.previous_unclean_page=='SPAWN',ver
    assert ns['RELEASE_VERSION']=='5.26.0'
    print('PASS v5.4.1: real keybind object vs raw F9 dispatch, debounce, older marker upgrade')
finally:
    for k,v in old.items():
        if v is None:sys.modules.pop(k,None)
        else:sys.modules[k]=v
