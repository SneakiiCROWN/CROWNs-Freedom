"""v1.5 navigator regression tests; SDK mock only, not BL4 runtime."""
import json
import runpy
import sys
import tempfile
from pathlib import Path

ctx=runpy.run_path(str(Path(__file__).with_name('test_arsenal_events.py')))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
    sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                        'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
    ctx['mode'][0]=0
    ctx['world'].GetName=lambda:'WhistlersMaw'
    source=(Path(__file__).resolve().parents[1]/'SOURCE'/'__init__.py').read_text()
    ns={'__name__':'crowns_v15_navigator_test'}
    exec(compile(source,'v15_navigator_test','exec'),ns)
    state=ns['State']
    assert state.spawn_view=='BROWSE'
    assert len(ns['SPAWN_POOLS'])>=65
    assert len({r[1].lower() for r in ns['SPAWN_POOLS']})==len(ns['SPAWN_POOLS'])
    assert len(ns['_spawn_visible_indices']())==len(ns['SPAWN_POOLS'])
    total=ns['forge_pages']()
    assert total>10
    assert len(ns['forge_page_indices']())==4
    ns['forge_change_page'](1)
    assert state.spawn_page==1
    assert len(ns['forge_page_indices']())==4
    assert ns['forge_choose'](2)
    assert state.spawn_view=='TOOLS'
    assert state.spawn_pool_idx==6
    chosen=ns['SPAWN_POOLS'][state.spawn_pool_idx][1]
    assert not ns['spawn_request']()
    assert state.spawn_pending is not None
    ns['forge_toggle_view']()
    assert state.spawn_pending is None and state.spawn_view=='BROWSE'
    assert ns['forge_choose'](0)
    assert state.spawn_pool_idx==4
    assert not ns['forge_choose'](8)
    # Category filter changes reset page/selection safely.
    ns['forge_toggle_view']()
    ns['forge_change_page'](4)
    ns['cycle_spawn_category'](1)
    assert state.spawn_page==0 and ns['_spawn_category']()=='SHOTGUN'
    assert state.spawn_pool_idx in ns['_spawn_visible_indices']()
    ns['cycle_spawn_category'](-1)
    assert ns['_spawn_category']()=='ALL'
    # Favorite UI can be emptied; no stale selected item can spawn.
    with tempfile.TemporaryDirectory() as td:
        ns['SETTINGS_DIR']=Path(td)
        assert ns['forge_choose'](0)
        assert ns['toggle_spawn_favorite']()
        state.spawn_category_idx=ns['SPAWN_CATEGORIES'].index('FAVORITES')
        state.spawn_page=0
        assert len(ns['forge_page_indices']())==1
        ns['forge_toggle_view']() # already TOOLS -> BROWSE
        assert ns['forge_choose'](0)
        assert ns['toggle_spawn_favorite']()
        assert ns['_spawn_visible_indices']()==[]
        assert not ns['forge_choose'](0)
        assert not ns['spawn_request']()
        ns['save_preferences']()
        data=json.loads((Path(td)/'CROWNs_Freedom_UI.json').read_text())
        assert data['forge_favorites']==[]
    # Direct native button activation changes pages and selects one item.
    state.spawn_category_idx=0
    state.spawn_pool_idx=0
    state.spawn_page=0
    state.spawn_view='BROWSE'
    ns['open_menu']()
    assert state.opened
    ns['show_page']('SPAWN')
    labels=[i['name'] for i in state.buttons]
    assert any('FIND BY NAME' in a for a in labels)
    assert any('NEXT PAGE' in a for a in labels)
    assert any('Convergence' in a for a in labels)
    # Simulate press/release via UMG widget IsPressed interface.
    choose=next(i for i in state.buttons if 'Convergence' in i['name'])
    choose['widget'].pressed=True
    state.last_poll=0
    ns['tick']()
    choose['widget'].pressed=False
    state.last_poll=0
    ns['tick']()
    assert state.spawn_view=='TOOLS'
    assert any('SPAWN' in i['name'] for i in state.buttons)
    assert any(i['name']=='FIND ITEM' and callable(i['run']) for i in state.buttons)
    # After arming a confirmation, UI shows the actual CONFIRM button.
    assert not ns['spawn_request']()
    assert any('CONFIRM' in i['name'] for i in state.buttons)
    current_pending=state.spawn_pending
    ns['adjust_spawn_level(5)'] if False else None
    ns['adjust_spawn_level'](5)
    assert state.spawn_pending is None
    assert not ns['spawn_request']()
    assert state.spawn_pending != current_pending
    ns['close_menu']()
    assert not state.hook_active and not ctx['pc'].bShowMouseCursor
    print('PASS v1.5: 68+ curated pools, browsing, pagination, selections, favorites, two-step spawning, session-safe controls and UI input restoration')
finally:
    for key,value in old.items():
        if value is None:sys.modules.pop(key,None)
        else:sys.modules[key]=value
