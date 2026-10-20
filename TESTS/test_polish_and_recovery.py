"""CROWN v2.1 regression tests: authenticated art bytes, diagnostic paging, slider readouts.
Simulates UnrealSDK/UMG. Does NOT prove in-game rendering or effects.
"""
import runpy, sys, tempfile, zipfile
from pathlib import Path
from types import SimpleNamespace

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from archive_fixture import identity
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
    sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                        'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
    ns={'__name__':'crown_v21_polish_test'}
    source=(root/'SOURCE/__init__.py').read_text('utf-8')
    exec(compile(source,'crown_v21.py','exec'),ns)
    state=ns['State']
    img=(root/'CROWN_CC0_ASSETS/BLADE_PLATE.png').read_bytes()
    assert ns['_verify_png_bytes']('BLADE_PLATE',img)
    assert not ns['_verify_png_bytes']('BLADE_PLATE',img+b'corrupt')
    assert not ns['_verify_png_bytes']('BOGUS',img)

    with tempfile.TemporaryDirectory(prefix='crowns21art_') as tmp:
        settings=Path(tmp)/'settings'
        settings.mkdir()
        ns['SETTINGS_DIR']=settings
        mod=Path(tmp)/ns['ART_MOD_FILENAME']
        def build_archive(contents):
            with zipfile.ZipFile(mod,'w') as z:
                identity(z,ns)
                z.writestr('CROWNs_Freedom_v2_1_Polish_and_Recovery/CROWN_CC0_ASSETS/BLADE_PLATE.png',contents)
                z.writestr('CROWNs_Freedom_v2_1_Polish_and_Recovery/CROWN_CC0_ASSETS/RIVET_PANEL.png',(root/'CROWN_CC0_ASSETS/RIVET_PANEL.png').read_bytes())
        build_archive(img)
        # First extraction, then overwrite a corrupt cache from a trusted archive.
        location=ns['_art_png_path']('BLADE_PLATE')
        assert location is not None and location.read_bytes()==img
        location.write_bytes(b'fake stale data')
        assert ns['_art_png_path']('BLADE_PLATE')==location
        assert location.read_bytes()==img
        # A corrupt archive asset is NOT written to disk, even if it has a PNG header.
        location.write_bytes(b'invalid cache again')
        build_archive(img+b'tampered')
        assert ns['_art_png_path']('BLADE_PLATE') is None
        assert location.read_bytes()==b'invalid cache again'
        # A genuine sprite from the supplied Kenney pack works again.
        build_archive(img)
        assert ns['_art_png_path']('BLADE_PLATE').read_bytes()==img
        # Verify archive identity fallback works when the SDK loader supplies a renamed file.
        renamed=Path(tmp)/'renamed-from-download.sdkmod'
        mod.rename(renamed)
        ns['__loader__']=SimpleNamespace(archive=str(renamed))
        assert ns['_art_mod_archive']()==renamed
        assert ns['_art_png_path']('BLADE_PLATE').read_bytes()==img

    # Readouts: world/movement sliders use multipliers, opacity uses percentages.
    assert ns['_slider_display'](.74,True)=='74%'
    assert ns['_slider_display'](2.4,False)=='x2.40'

    ns['SETTINGS_DIR']=None
    ns['__loader__']=None
    for idx,res in enumerate(((2560,1440),(1280,720),(854,480))):
        ns['viewport']=lambda res=res:res
        ns['open_menu']()
        assert state.opened and state.draw_ok
        ns['show_page']('DEV')
        ns['toggle_ui_diagnostics']()
        assert state.diag_open and state.diag_page==0 and state.draw_ok
        assert any('NEXT DIAGNOSTICS' in b['name'] for b in state.buttons)
        seen=[]
        original_text=ns['text']
        def spy(parent,label,*args,**kwargs):
            seen.append(str(label))
            return original_text(parent,label,*args,**kwargs)
        ns['text']=spy
        try:
            for _ in range(4):
                seen.clear()
                ns['redraw']()
                assert state.draw_ok
                saved='\n'.join(seen)
                if 'LAST ART ISSUE' in saved:
                    break
                ns['next_ui_diagnostics']()
            assert 'LAST ART ISSUE' in '\n'.join(seen),res
            seen.clear()
            ns['next_ui_diagnostics']()
            assert state.draw_ok
        finally:
            ns['text']=original_text
        ns['show_page']('MOTION')
        assert state.sliders
        movement_slider=state.sliders[0]
        assert movement_slider.percentage is False
        motion_value=1.3+idx*.4
        movement_slider.widget.GetValue=lambda val=motion_value:val
        movement_readout=[]
        movement_slider.label.SetText=lambda value:movement_readout.append(value)
        state.last_poll=0
        ns['tick']()
        assert movement_readout and movement_readout[-1]==ns['_slider_display'](motion_value,False), (res,movement_readout)
        ns['show_page']('STYLE')
        opacity_slider=state.sliders[0]
        assert opacity_slider.percentage is True
        opacity_value=.73+idx*.05
        opacity_slider.widget.GetValue=lambda val=opacity_value:val
        opacity_readout=[]
        opacity_slider.label.SetText=lambda value:opacity_readout.append(value)
        state.last_poll=0
        ns['tick']()
        assert opacity_readout and opacity_readout[-1]==ns['_slider_display'](opacity_value,True), (res,opacity_readout)
        ns['close_menu']()
        assert not state.opened
    print('PASS v2.1: asset hash validation, corrupt-cache repair, forged archive rejection, renamed-loader compatibility, paged diagnostics and proper slider formatting')
finally:
    for k,v in old.items():
        if v is None:sys.modules.pop(k,None)
        else:sys.modules[k]=v
