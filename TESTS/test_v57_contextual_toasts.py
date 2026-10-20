"""Contextual UMG toasts: offline Oak2 mock and strict result-status contracts.
No real BL4 input, rendering or inventory delivery is verified here.
"""
from pathlib import Path
import runpy, sys, time, tempfile, json
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
    sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                        'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
    ns={'__name__':'v57_contextual_toasts'}
    exec(compile((root/'SOURCE/__init__.py').read_text(),'v57_source','exec'),ns)
    st=ns['State'];spec=ns['TOAST_COPY']
    assert ns['RELEASE_VERSION']=='5.26.0'
    assert len(spec)>=10
    assert 'Good luck dying' in spec['GOD_ON'][1]
    assert 'Ooo, a piece of money' in spec['MONEY_REQUEST'][1]
    assert 'Check your wallet' in spec['MONEY_REQUEST'][1]
    assert 'Drop not verified' in spec['SPAWN_REQUEST'][1]
    examples={
        'GOD MODE ON (readback OK)':'GOD_ON',
        'GOD MODE OFF (readback OK)':'GOD_OFF',
        'NOCLIP ON (collision/damage readback OK; movement requested)':'NOCLIP_ON',
        'NOCLIP OFF (collision/damage readback OK; movement requested)':'NOCLIP_OFF',
        'WALLET REQUEST ACCEPTED / cash +100 (verify in game)':'MONEY_REQUEST',
        'WALLET REQUEST ACCEPTED / eridium +100 (verify in game)':'ERIDIUM_REQUEST',
        'CONFIRM / cash +100 - click again in 6s':'CONFIRM',
        'SPAWN REQUEST ACCEPTED // 1 Hellwalker; check the ground':'SPAWN_REQUEST',
        'TRAVEL // Slot 04 swept arrival confirmed; RETURN goes back.':'TRAVEL',
        'CROWN EVENT // BULLET BALLET (solo session modifiers)':'EVENT',
        'RESTORE LOCAL settings requested. Ammo/server perks NOT auto-reversed.':'RESTORE',
        'MAURICE BLOCKED / No current-week same-map vendor bookmark.':'BLOCKED',
    }
    for message,code in examples.items():
        assert ns['_toast_from_result'](message)==code,(message,ns['_toast_from_result'](message))
    # An attempted but rejected API call, first confirmation press, and mere
    # status probe must NEVER produce celebratory success popups.
    for message in ('WALLET REQUEST FAILED / API error',
                    'CONFIRM / cash +100 - click again in 6s',
                    'SPAWN BLOCKED // missing API',
                    'GOD MODE unavailable: no pawn',
                    'WILDCARD / Savage Salvage',
                    'UI ONLY / FOCUS REQUESTED'):
        assert ns['_toast_from_result'](message) not in ('GOD_ON','MONEY_REQUEST','SPAWN_REQUEST','TRAVEL')
    st.toasts_enabled=True
    ns['_dismiss_toast'](clear_queue=True)
    st.toast_last_code='';st.toast_last_time=-10
    ns['log']('GOD MODE ON (readback OK)')
    assert st.toast_queue==['GOD_ON'],st.toast_queue
    # Duplicate SDK/native activation should not create repeated feedback.
    ns['log']('GOD MODE ON (readback OK)')
    assert st.toast_queue==['GOD_ON']
    ns['_toast_tick'](time.monotonic())
    assert st.toast_widget is not None and st.toast_shown==1
    assert st.toast_expires>0 and not st.toast_render_failed
    # Toast has its own widget tree; opening menu elements should remain intact.
    assert st.toast_widget.WidgetTree is not None
    ns['_toast_tick'](st.toast_expires+.01)
    assert st.toast_widget is None
    # Toggle must not alter game status, movement or item pools.
    prev=(st.god,st.noclip,len(ctx['pool'].calls))
    assert ns['toggle_toasts']() is False
    assert not ns['_queue_toast']('GOD_ON')
    assert ns['test_toast']() is False
    assert ns['toggle_toasts']() is True
    st.toast_last_code='';st.toast_last_time=-10
    assert ns['test_toast']() and st.toast_queue==['TEST']
    assert prev==(st.god,st.noclip,len(ctx['pool'].calls))
    # Unknown keys must not appear. Queue bounded on repeated distinct events.
    for code in ('GOD_ON','GOD_OFF','EVENT','SPAWN_REQUEST','TRAVEL'):
        st.toast_last_code='';st.toast_last_time=-10
        ns['_queue_toast'](code)
    assert len(st.toast_queue)<=3
    st.toast_suppress_restore=True
    assert ns['_toast_from_result']('RESTORE LOCAL settings requested.') is None
    st.toast_suppress_restore=False
    assert ns['_toast_from_result']('RESTORE LOCAL settings requested.')=='RESTORE'
    # A failed optional art or UMG path should degrade without affecting actions.
    ns['_dismiss_toast'](clear_queue=True)
    st.toast_last_code='';st.toast_last_time=-10
    ns['create']=lambda *a: (_ for _ in ()).throw(RuntimeError('No UMG renderer'))
    assert ns['_queue_toast']('TEST')
    ns['_toast_tick'](time.monotonic())
    assert st.toast_widget is None and st.toast_render_failed
    assert st.runtime_failures[-1]['stage']=='TOAST_WIDGET'
    assert st.toasts_enabled
    ns['_dismiss_toast'](clear_queue=True)
    # Hook remains capable of retiring toast even with gamepad disabled.
    code=(root/'SOURCE/__init__.py').read_text()
    before=code.index('if State.toast_widget is not None or State.toast_queue:_toast_tick(now)')
    after=code.index('if State.opened or not State.controller_enabled:return',before)
    assert before<after
    assert "attempt(canvas,'SetVisibility',3)" in code
    assert "attempt(root_ui,'SetVisibility',3)" in code
    assert 'RemoveFromParent' in code
    # Persistence is preferences-only; no player/save edits.
    with tempfile.TemporaryDirectory() as temp:
        ns['SETTINGS_DIR']=Path(temp)
        st.toasts_enabled=False
        ns['save_preferences']()
        data=json.loads((Path(temp)/'CROWNs_Freedom_UI.json').read_text())
        assert data['toasts_enabled'] is False
        st.toasts_enabled=True
        ns['load_preferences']()
        assert st.toasts_enabled is False
    print('PASS v5.7: UMG toast lifecycle, witty semantic results, no false grants, dedup, no input, fallback and persistence')
finally:
    for k,v in old.items():
        if v is None:sys.modules.pop(k,None)
        else:sys.modules[k]=v
