"""Regression for user-observed BL4 screenshot issues; mocked UMG, not live engine QA."""
from pathlib import Path
import runpy,sys
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={key:sys.modules.get(key) for key in keys}
try:
    sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                        'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
    ns={'__name__':'crown_v591_live_screenshot_layout'}
    exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_source','exec'),ns)
    st=ns['State'];source=(root/'SOURCE/__init__.py').read_text()
    assert ns['RELEASE_VERSION']=='5.26.0'
    st.message='CROWNs Freedom // WELCOME TO THE BLACK MARKET'
    assert ns['_dock_status_message']()=='READY / Choose a tool'
    st.message='CROWN // This is a very long diagnostic message that would otherwise get chopped by the native Side Dock footer'
    assert len(ns['_dock_status_message']())<=42
    assert 'AMBER ACTIVE / CYAN FOCUS / RED RISK' not in source
    assert 'ROADRUNNER // SAVED DESTINATIONS' not in source
    # Ensure a genuinely compact, DIRECT-ACCESS dock in tall game viewports.
    heights={}
    for screen in [(1280.,720.),(1920.,1080.),(2560.,1440.)]:
        ns['viewport']=lambda wh=screen:wh
        for category,pages in ns['UI_CATEGORY_PAGES'].items():
            for page in pages:
                st.safe_mode=False;st.page=page;st.dock_mode='SIDE';st.opened=False
                ns['open_menu']()
                assert st.draw_ok,(screen,page)
                x,y,w,h,*_=st.panel_rect
                heights[(screen,page)]=h
                if screen[1]>=720:
                    labels={b['name'] for b in st.buttons}
                    assert {'QUICK','TOOLS','STYLE','FULL STUDIO','CLOSE / B'} <= labels
                    assert 'PREV TOOL' not in labels and 'NEXT TOOL' not in labels,(screen,page)
                for b in st.buttons:
                    bx,by,bw,bh=b['rect']
                    assert bx>=x-2 and bx+bw<=x+w+2 and by>=y-2 and by+bh<=y+h+2,(screen,page,b)
                ns['close_menu']()
    assert heights[((1920.,1080.),'WAYPOINTS')]<660,heights[((1920.,1080.),'WAYPOINTS')]
    assert heights[((1920.,1080.),'STYLE')]<750
    assert heights[((1920.,1080.),'STYLE')]==heights[((1920.,1080.),'WAYPOINTS')]  # Dedicated dock geometry is independent of selected main tool.
    # No auto-reset of safe mode, but warning AND an explicit action are visible.
    st.safe_mode=True;st.opened=False;st.dock_mode='FULL';st.page='STYLE'
    ns['viewport']=lambda:(1920.,1080.)
    text_calls=[]
    original_text=ns['text']
    def capture_text(parent,label,*args,**kw):
        text_calls.append(str(label))
        return original_text(parent,label,*args,**kw)
    ns['text']=capture_text
    ns['open_menu']()
    assert st.safe_mode and st.draw_ok
    assert any('SAFE MODE / ART OFF' in v for v in text_calls),text_calls[-30:]
    assert any(b['name']=='RESTORE ART' for b in st.buttons)
    assert not any(b['name']=='RESET MENU POSITION' for b in st.buttons)
    ns['close_menu']()
    # The travel context card remains singular after removing overlapping ornament.
    text_calls.clear();st.opened=False;st.safe_mode=False;st.page='WAYPOINTS'
    ns['open_menu']()
    assert st.draw_ok
    assert sum(v=='TRAVEL / SWEPT MOVE CHECK' for v in text_calls)<=1
    assert all('ROADRUNNER // SAVED DESTINATIONS' not in v for v in text_calls)
    ns['close_menu']()
    print('PASS v5.25.0 screenshot-layout: compact dock, direct access, no Roadrunner stack, no header legend collision, explicit Safe Mode/art recovery')
finally:
    for key,val in old.items():
        if val is None:sys.modules.pop(key,None)
        else:sys.modules[key]=val
