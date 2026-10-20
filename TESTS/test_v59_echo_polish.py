"""v5.9: game-safe Echo Neon presentation, cached theme colours, and honest toasts.

Offline Oak2/Unreal mock only; does not certify BL4 rendering or gameplay effects.
"""
from pathlib import Path
import runpy, sys, time
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
    sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                        'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
    ns={'__name__':'v59_echo_polish'}
    exec(compile((root/'SOURCE/__init__.py').read_text(),'v59_source','exec'),ns)
    s=ns['State'];calls=len(ctx['pool'].calls)
    assert ns['RELEASE_VERSION']=='5.26.0'
    assert len(ns['_THEME_RGBA'])==len(ns['THEMES'])==7
    assert ns['THEMES'][0]['name']=='CROWN BLACKGLASS'
    for i,theme in enumerate(ns['THEMES']):
        s.theme_idx=i;s.panel_opacity=.82
        for key in ('panel','header','action','accent','border','text','danger'):
            actual=ns['theme_color'](key)
            expected=ns['_hex'](theme[key])
            if key in ('panel','header','action'):
                expected=expected[:3]+(.82,)
            assert actual==expected,(i,key,actual,expected)
    s.theme_idx=0;s.toasts_enabled=True;s.toast_queue=[];s.toast_last_code='';s.toast_last_time=-10
    ns['set_theme'](0)
    assert s.toast_queue==['THEME_APPLIED']
    assert ns['_toast_from_result']('TRAVEL // Slot 04 WAYPOINT saved for valid map')=='BOOKMARK_SAVED'
    assert ns['_toast_from_result']('UI PROFILE 1 SAVED // No character data changed.')=='PROFILE_SAVED'
    assert ns['_toast_from_result']('TRAVEL // Slot 04 denied due to mismatched map') is None
    assert ns['_toast_from_result']('WALLET REQUEST FAILED / API refused')=='BLOCKED'
    assert 'Check your wallet' in ns['TOAST_COPY']['MONEY_REQUEST'][1]
    assert 'Drop not verified' in ns['TOAST_COPY']['SPAWN_REQUEST'][1]
    ns['_dismiss_toast'](clear_queue=True)
    s.toast_last_code='';s.toast_last_time=-10
    previous=s.cursor_aid
    ns['toggle_cursor_aid']()
    assert s.cursor_aid!=previous
    assert s.toast_queue[-1]==('CURSOR_ON' if s.cursor_aid else 'CURSOR_OFF')
    assert len(ctx['pool'].calls)==calls,'A visual-only action must never write inventory'
    assert "('ECHO NEON',lambda:set_theme(0)" in (root/'SOURCE/__init__.py').read_text()
    print('PASS v5.9: six cached palettes, neon theme, non-gameplay actions, honest contextual toasts, legacy-preserving controls')
finally:
    for k,v in old.items():
        if v is None:sys.modules.pop(k,None)
        else:sys.modules[k]=v
