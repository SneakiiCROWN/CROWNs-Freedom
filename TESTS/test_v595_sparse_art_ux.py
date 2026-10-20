"""v5.25.0 screenshot-driven sparse Echo Neon art / menu UX; offline mocks only."""
from pathlib import Path
from PIL import Image
import hashlib,runpy,sys
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
    sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                        'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
    ns={'__name__':'crown_sparse_art_test'}
    exec(compile((root/'SOURCE/__init__.py').read_text(), 'crown_sparse_test_source','exec'),ns)
    assert ns['RELEASE_VERSION']=='5.26.0'
    assert len(ns['ART_FILES'])==len(ns['ART_SHA256'])==67
    # 3 formerly busy native backgrounds now intentionally transparent and sparse.
    for name,limit in (('NEON_HEADER',.065),('NEON_STRIP',.15),('NEON_CIRCUITS',.032)):
        path=root/'CROWN_CC0_ASSETS'/(name+'.png')
        raw=path.read_bytes()
        assert ns['_verify_png_bytes'](name,raw)
        with Image.open(path) as im:
            assert im.mode=='RGBA'
            alpha=im.getchannel('A')
            assert alpha.getextrema()[0]==0 and alpha.getextrema()[1]>30
            occupied=sum(n for value,n in enumerate(alpha.histogram()) if value>=18)/(im.width*im.height)
            assert occupied<limit,(name,occupied,limit)
    # Never use the tall, densely striped INK_RAIL behind Echo Neon controls.
    state=ns['State'];state.theme_idx=0
    ns['viewport']=lambda:(1920.,1080.)
    before=len(ctx['pool'].calls)
    for mode in ('SIDE','FULL'):
        captured=[]
        ns['optional_art_image']=lambda parent,name,*args,**kwargs: captured.append(name) or False
        state.opened=False;state.page='PLAYER';state.dock_mode=mode
        assert ns['open_menu']() is not False
        assert state.draw_ok and ('R9_DOCK' if mode=='SIDE' else 'R9_EXPEDITION') in captured
        assert 'INK_RAIL' not in captured,(mode,captured)
        ns['close_menu']()
    assert len(ctx['pool'].calls)==before
    state.message='STATUS // Welcome to the black market'
    assert ns['_dock_status_message']()=='READY / Choose a tool'
    state.page='WAYPOINTS'
    assert any('ALL 12 SLOTS' in name for name,*_ in ns['_dock_quick_choices']('WAYPOINTS'))
    assert any('RETURN / SWAP' in name for name,*_ in ns['_dock_quick_choices']('WORLD'))
    print('PASS v5.25.0: sparse art hashes/alpha, no doubled ink rails, real dock captions and native-fallback menus')
finally:
    for k,v in old.items():
        if v is None:sys.modules.pop(k,None)
        else:sys.modules[k]=v
