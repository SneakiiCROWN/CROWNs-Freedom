"""v2.0 ART/UX acceptance tests; simulated Oak2 SDK only, not live BL4."""
import runpy, sys, tempfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
    sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                        'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
    ns={'__name__':'crowns_acceptance_lab_qa'}
    exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_v20','exec'),ns)
    st=ns['State']
    assert st.art_mode=='AUTO' and not st.art_failed
    assert ns['_art_texture']('NON_EXISTENT') is None

    # During a load screen, no permanent failure is recorded.
    original_world=ns['world_and_state']
    ns['world_and_state']=lambda:(None,None)
    assert ns['_art_texture']('RIVET_PANEL') is None
    assert 'RIVET_PANEL' not in st.art_failed
    assert 'waiting for playable map' in st.art_status
    ns['world_and_state']=original_world

    # Missing importer gets a specific failure; retry clears it.
    assert ns['_art_texture']('RIVET_PANEL') is None
    assert 'RIVET_PANEL' in st.art_failed
    assert 'RIVET_PANEL' in st.art_fail_reasons
    ns['retry_art']()
    assert not st.art_failed and not st.art_fail_reasons and st.art_mode=='AUTO'

    # Lite mode makes no import attempt, and survives preference round-trips.
    with tempfile.TemporaryDirectory() as tmp:
        st.opened=False
        ns['SETTINGS_DIR']=Path(tmp)
        ns['toggle_art_mode']()
        assert st.art_mode=='SHAPES'
        must_not_read=lambda asset:(_ for _ in ()).throw(AssertionError('art read in SHAPES mode'))
        original_png=ns['_art_png_path']
        ns['_art_png_path']=must_not_read
        assert ns['_art_texture']('BLADE_PLATE') is None
        assert not st.art_failed
        ns['_art_png_path']=original_png
        st.art_mode='AUTO'
        ns['load_preferences']()
        assert st.art_mode=='SHAPES'
        ns['toggle_art_mode']()
        assert st.art_mode=='AUTO'
        ns['load_preferences']()
        assert st.art_mode=='AUTO'

        report=ns['ui_diagnostic_lines']()
        assert len(report)>=6
        assert any('IMPORTER' in ln for ln in report)
        assert any('ART MODE:' in ln for ln in report)
        assert any('TEXTURES IN CACHE:' in ln for ln in report)

        # Both new buttons fit above footer at wide, 720p and compact sizes.
        for resolution in ((2560,1440),(1920,1080),(1280,720),(854,480)):
            ns['viewport']=lambda resolution=resolution:resolution
            ns['open_menu']()
            assert st.opened and st.draw_ok,(resolution,st.message)
            captured=[]
            real_btn=ns['btn']
            def trace(parent,label,x,y,w,h,action,*args,**kwargs):
                captured.append((str(label),float(x),float(y),float(w),float(h)))
                return real_btn(parent,label,x,y,w,h,action,*args,**kwargs)
            ns['btn']=trace
            ns['show_page']('STYLE')
            lab=[item for item in captured if item[0]=='ART / AUTO']
            retry=[item for item in captured if item[0]=='MOTION / REDUCED']
            foot=[item for item in captured if item[0]=='RESTORE TEMP']
            assert len(lab)==1 and len(retry)==1 and len(foot)==1,(resolution,captured)
            assert max(lab[0][2]+lab[0][4],retry[0][2]+retry[0][4]) < foot[0][2],resolution
            ns['btn']=real_btn
            ns['show_page']('DEV')
            ns['toggle_ui_diagnostics']()
            assert st.diag_open and st.draw_ok,(resolution,st.message)
            assert any('<< BACK TO DEV' in b['name'] for b in st.buttons)
            ns['show_page']('PLAYER')
            assert not st.diag_open
            ns['close_menu']()
            assert not st.opened

    print('PASS v2.0: loading-safe art retry, lightweight mode, saved settings, 7-point diagnostics, UI bounds x4, safe page navigation')
finally:
    for k,v in old.items():
        if v is None:sys.modules.pop(k,None)
        else:sys.modules[k]=v
