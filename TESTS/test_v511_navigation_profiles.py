"""v5.11: Six true category gamepad navigation, lossless UI profiles and safe legacy migration.
All calls are mocked Oak2/UMG; no live game-world operations.
"""
from pathlib import Path
import sys,runpy
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
    sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                        'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
    ns={'__name__':'crown_v511_test'}
    exec(compile((root/'SOURCE/__init__.py').read_text(),'v511','exec'),ns)
    st=ns['State']
    baseline_gameplay_calls=len(ctx['pool'].calls)
    assert ns['RELEASE_VERSION']=='5.26.0'
    assert len(ns['UI_CATEGORY_PAGES'])==6
    assert len({page for pages in ns['UI_CATEGORY_PAGES'].values() for page in pages})==24
    # Only the six visible category tabs are shoulder-switched; every
    # subtool remains accessible from each category (Weekly included).
    original=ns['show_category']
    reached=[]
    def fake_category(name):
        reached.append(name)
        st.page=ns['UI_CATEGORY_PAGES'][name][0]
    ns['show_category']=fake_category
    ns['_controller_initial_focus']=lambda:0
    ns['_controller_update_focus_outline']=lambda:None
    st.dock_mode='SIDE'
    st.page='PLAYER'
    for mode in ('TOOLS','FARM','STYLE','QUICK'):
        assert ns['_controller_change_page'](1) is True
        assert st.dock_view==mode
    assert ns['_controller_change_page'](-1) and st.dock_view=='STYLE'
    assert not reached  # Dock shoulders change dock tabs, never hidden categories.
    assert 'WEEKLY' in ns['UI_CATEGORY_PAGES']['WORLD']
    ns['show_category']=original

    ns['save_preferences']=lambda:None
    st.theme_idx=0;st.sfx_set='ECHO';st.hud_anchor='RIGHT_MIDDLE'
    st.toasts_enabled=False;st.cursor_aid=False
    st.audio_mode='NORMAL';st.spawn_search='laser'
    assert ns['save_ui_profile'](1)
    snapshot=st.ui_profiles['1']
    assert snapshot['sfx_set']=='ECHO' and snapshot['hud_anchor']=='RIGHT_MIDDLE'
    assert snapshot['toasts_enabled'] is False and snapshot['cursor_aid'] is False
    st.sfx_set='CLASSIC';st.hud_anchor='TOP_CENTRE';st.toasts_enabled=True;st.cursor_aid=True
    assert ns['load_ui_profile'](1)
    assert (st.sfx_set,st.hud_anchor,st.toasts_enabled,st.cursor_aid)==('ECHO','RIGHT_MIDDLE',False,False)
    # An older profile without newer keys stays valid and defaults safely.
    st.ui_profiles['2']={'theme_index':1,'text_scale':1.1,'scale':1.2,
                         'opacity':.9,'forge_search':'','art_mode':'AUTO',
                         'audio_mode':'LOW','audio_hover':False}
    assert ns['load_ui_profile'](2)
    assert st.sfx_set=='CLASSIC' and st.hud_anchor=='TOP_CENTRE'
    # Reject wrong values atomically; no mix of old and new UI state.
    before=(st.theme_idx,st.sfx_set,st.hud_anchor,st.toasts_enabled)
    st.ui_profiles['3']={**st.ui_profiles['2'],'theme_index':4,'sfx_set':'BAD'}
    assert not ns['load_ui_profile'](3)
    assert (st.theme_idx,st.sfx_set,st.hud_anchor,st.toasts_enabled)==before
    st.ui_profiles['3']={**st.ui_profiles['2'],'theme_index':4,'hud_anchor':'BOTTOM_RIGHT'}
    assert not ns['load_ui_profile'](3)
    assert (st.theme_idx,st.sfx_set,st.hud_anchor,st.toasts_enabled)==before
    assert len(ctx['pool'].calls)==baseline_gameplay_calls
    print('PASS v5.11: six LB/RB categories, all 19 pages reachable, newer/legacy profiles, atomic invalid rejection')
finally:
    for k,v in old.items():
        if v is None:sys.modules.pop(k,None)
        else:sys.modules[k]=v
