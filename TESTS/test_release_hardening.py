"""v2.3 crash-safe preferences, noclip readback and privacy-safe QA export.
Only mock objects; this is not a live Borderlands 4 acceptance test.
"""
import json,runpy,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
    sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
      'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
    ns={'__name__':'crown_v23_test'}
    src=(root/'SOURCE/__init__.py').read_text(encoding='utf-8')
    exec(compile(src,'crown.py','exec'),ns)
    state=ns['State']
    pawn=ctx['pawn']
    # Unusual initial collision state should not cause a false failed restore.
    pawn.bActorEnableCollision=False
    pawn.bCanBeDamaged=True
    state.saved_char=None;state.collision_original=None;state.damage_original=None
    state.noclip=False;state.god=False
    assert ns['set_noclip'](True) is True
    assert pawn.bActorEnableCollision is False
    assert pawn.bCanBeDamaged is False
    assert ns['set_noclip'](False) is True
    assert state.noclip is False
    assert pawn.bActorEnableCollision is False
    assert pawn.bCanBeDamaged is True
    # A rejected collision write is detected, prior state is retained.
    class RejectCollision:
        def __init__(self):
            self.bActorEnableCollision=True
            self.bCanBeDamaged=True
            self.OakCharacterMovement=SimpleNamespace(MovementMode=1,SetMovementMode=lambda *a:None)
        def __setattr__(self,k,v):
            if k=='bActorEnableCollision' and k in self.__dict__:
                return
            self.__dict__[k]=v
    rejected=RejectCollision()
    ns['ensure_pawn']=lambda:rejected
    state.saved_char=None;state.noclip=False;state.god=False
    assert ns['set_noclip'](True) is False
    assert state.noclip is False
    assert rejected.bCanBeDamaged is True
    assert rejected.bActorEnableCollision is True
    # Restore real pawn route for later tests.
    ns['ensure_pawn']=lambda: pawn
    state.saved_char=None
    with tempfile.TemporaryDirectory() as temp:
        settings=Path(temp); ns['SETTINGS_DIR']=settings
        state.spawn_favorites=set();state.spawn_search=''
        ns['save_preferences']()
        prefs=settings/'CROWNs_Freedom_UI.json'
        assert prefs.exists() and not (settings/'CROWNs_Freedom_UI.json.tmp').exists()
        data=json.loads(prefs.read_text(encoding='utf-8'))
        data['text_scale']=float('nan')
        data['opacity']=float('inf')
        data['scale']=-float('inf')
        data['window_x']=float('nan')
        data['window_y']=float('inf')
        prefs.write_text(json.dumps(data),encoding='utf-8')
        ns['load_preferences']()
        assert state.font_scale==1.0 and state.panel_opacity==.94
        assert state.panel_scale==1.0 and state.window_x is None and state.window_y is None
        ns['log']('A previous friend name: NEVER_EXPORT_THIS')
        ns['viewport']=lambda:(2560,1440)
        assert ns['export_qa_report']()
        report_file=settings/'CROWNs_Freedom_QA_Report.json'
        report=json.loads(report_file.read_text(encoding='utf-8'))
        assert report['version']=='5.26.0'
        assert report['display']=={'width':2560,'height':1440}
        assert report['forge']['catalogue_size']==68
        assert 'NEVER_EXPORT_THIS' not in report_file.read_text(encoding='utf-8')
        assert not (settings/'CROWNs_Freedom_QA_Report.json.tmp').exists()
    ns['SETTINGS_DIR']=None
    assert not ns['export_qa_report']()
    # Draw timing and diagnostics must be measurable, not made-up.
    state.god=False
    ns['viewport']=lambda:(1920,1080)
    ns['open_menu']()
    assert state.opened and state.draw_ok and state.ui_rebuild_count>=1
    assert state.ui_last_ms>=0 and state.ui_peak_ms>=state.ui_last_ms
    assert 'EXPORT QA REPORT' in [b['name'] for b in state.buttons] if state.page=='DEV' else True
    ns['show_page']('DEV')
    assert 'EXPORT QA REPORT' in [b['name'] for b in state.buttons]
    # If subsequent redraw throws, the menu must release mouse ownership.
    previous=ns['widget']
    def break_render(path):
        if path=='Border':raise RuntimeError('synthetic render failure')
        return previous(path)
    ns['widget']=break_render
    ns['redraw']()
    assert not state.opened
    assert state.ui_error_count>=1
    assert not ctx['pc'].bShowMouseCursor
    print('PASS v2.3: original-disabled collision, rejected write rollback, atomic prefs, NaN sanitization, private QA report, UI timing and render-failure input cleanup')
finally:
    for k,v in old.items():
        if v is None:sys.modules.pop(k,None)
        else:sys.modules[k]=v
