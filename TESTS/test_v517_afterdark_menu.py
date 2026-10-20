"""v5.17: selectable coherent dark-pink theme, six-result finder, UI-only safety."""
from pathlib import Path
import ast,hashlib
from PIL import Image
import runpy,sys

def run():
    root=Path(__file__).resolve().parents[1]
    ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
    keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
    previous={k:sys.modules.get(k) for k in keys}
    sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                        'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
    try:
        ns={'__name__':'crown_v517_test'}
        exec(compile((root/'SOURCE/__init__.py').read_text(),'<source>','exec'),ns)
        check(ns,ctx,root)
    finally:
        for k,original in previous.items():
            if original is None:sys.modules.pop(k,None)
            else:sys.modules[k]=original

def check(ns,ctx,root):
    st=ns['State']
    assert ns['RELEASE_VERSION']=='5.26.0'
    assert len(ns['THEMES'])==7 and ns['THEMES'][6]['name']=='NEON AFTERDARK'
    assert ns['_THEME_RGBA'][6]['border']==ns['_hex']('#F737A5')
    assert len(ns['ART_FILES'])==len(ns['ART_SHA256'])==67
    for key in ('AFTERDARK_BTN_IDLE','AFTERDARK_BTN_ACTIVE','AFTERDARK_BTN_DANGER',
                'AFTERDARK_TOP_FRAME','AFTERDARK_DOCK_FRAME'):
        data=(root/'CROWN_CC0_ASSETS'/f'{key}.png').read_bytes()
        assert ns['_verify_png_bytes'](key,data)
        with Image.open(root/'CROWN_CC0_ASSETS'/f'{key}.png') as im:
            assert im.mode=='RGBA' and im.getextrema()[3][0]==0
    st.opened=False
    st.theme_idx=0
    ns['set_theme'](6)
    assert st.theme_idx==6
    assert ns['theme_color']('border')[:3]==ns['_hex']('#F737A5')[:3]
    assert not st.expand_theme
    # All saved legacy indices retain their names; the new theme is appended.
    assert ns['THEMES'][0]['name']=='CROWN BLACKGLASS'
    assert ns['THEMES'][5]['name']=='CROWN NOIR'
    st.finder_query='';st.finder_page=0
    assert len(ns['finder_results']())==24 and ns['FINDER_PAGE_SIZE']==6
    ns['finder_change_page'](100)
    assert st.finder_page==3
    ns['finder_change_page'](-100)
    assert st.finder_page==0
    # In new theme, native UI is still rendered if images are disabled.
    st.safe_mode=True;st.art_mode='SHAPES';st.dock_mode='FULL';st.page='STYLE'
    ns['viewport']=lambda:(1280,720)
    assert ns['open_menu']() is not False
    assert st.draw_ok and st.opened
    assert any('THEME /' in b['name'] for b in st.buttons)
    ns['close_menu']()
    # Theme selection and finder must never issue a game write.
    assert not any(isinstance(c,tuple) and c and c[0] in ('SpawnActor','GiveItem','ConsoleCommand') for c in ctx['pool'].calls)
    print('PASS v5.17 pink variant, generated alpha-art, six-at-once finder, UI-only compatibility')

if __name__=='__main__':run()
