"""v5.3.1 live traceback regression: validate actual mods_base keybind contract.

The old mock returned a bare function, masking the invalid keybinds list.
This stub mirrors the public mods_base.keybind decorator contract: decorated
functions become KeybindType-like objects, and each registry entry has an
identifier/key/callback. The test runs without actual BL4.
"""
import runpy,sys,types
from pathlib import Path
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
mods=ctx['mods']
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
class KeybindType:
    def __init__(self,identifier,key,callback):
        self.identifier=identifier;self.key=key;self.callback=callback
        self.is_rebindable=True;self.display_name=identifier
        self.description='';self.description_title=identifier
        self.is_hidden=False;self.default_key=key

def keybind(identifier,key,event_filter=None):
    return lambda callback:KeybindType(identifier,key,callback)

def strict_build_mod(**kwargs):
    binds=kwargs['keybinds']
    assert len(binds)==7
    for bind in binds:
        # Mirrors exactly where the user's real Oak2 crashed:
        # KeybindOption.from_keybind(bind) accesses bind.identifier, etc.
        assert isinstance(bind,KeybindType),f'Invalid registered bind: {bind!r}'
        assert isinstance(bind.identifier,str) and bind.identifier
        assert isinstance(bind.key,str) and bind.key
        assert callable(bind.callback)
    return types.SimpleNamespace(**kwargs)
mods.keybind=keybind
mods.build_mod=strict_build_mod
try:
    sys.modules.update({'mods_base':mods,'unrealsdk':ctx['u'],
                        'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
    ns={'__name__':'crown_v531_strict_contract'}
    exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_v531_source','exec'),ns)
    mod=ns['CROWNS_MOD']
    by_key={b.key:b for b in mod.keybinds}
    assert set(by_key)=={'F5','F6','F7','F8','F9','F10','F11'}
    # F10 must be the action, NOT the two-argument cleanup helper.
    assert by_key['F10'].callback.__name__=='restore_hotkey'
    assert not isinstance(ns['_cleanup_safely'],KeybindType)
    assert callable(ns['reset_all'])
    assert by_key['F7'].callback.__name__=='toggle'
    actions=[]
    ns['reset_all']=lambda:actions.append('restore')
    by_key['F10'].callback()
    assert actions==['restore']
    assert callable(mod.on_enable) and callable(mod.on_disable)
    print('PASS v5.3.1: all six registered binds are KeybindType objects; F10 dispatch and internal reset_all remain callable')
finally:
    for k,v in old.items():
        if v is None:sys.modules.pop(k,None)
        else:sys.modules[k]=v
