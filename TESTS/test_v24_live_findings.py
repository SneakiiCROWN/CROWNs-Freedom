"""Tests inspired by actual BL4 v2.3 screenshots; still synthetic, not live gameplay."""
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,runpy,sys,math
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
    sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                        'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
    ns={'__name__':'crown_v24_runtime_failure_test'}
    exec(compile((root/'SOURCE/__init__.py').read_text(encoding='utf-8'),'crowns_v24','exec'),ns)
    st=ns['State']
    # Exact user screenshot failure: OakCharacter has location but does not have
    # K2_GetActorTransform. The action MUST NOT assume that method exists.
    class LiveOakCharacter:
        def _get_address(self):return id(self)
        def K2_GetActorLocation(self):return SimpleNamespace(X=1000.,Y=2000.,Z=200.)
        def K2_GetActorRotation(self):return SimpleNamespace(Yaw=0.)
        def GetActorForwardVector(self):return SimpleNamespace(X=0.,Y=1.,Z=0.)
    actor=LiveOakCharacter()
    ns['pawn']=lambda:actor
    st.spawn_search='';st.spawn_pool_idx=0;st.spawn_category_idx=0
    st.spawn_level=40;st.spawn_count=1;st.spawn_pending=None
    st.anti_spam_until=0
    pool=ctx['pool'];pool.calls.clear()
    assert not ns['spawn_request']() # first click arms
    assert not pool.calls
    assert ns['spawn_request']() # second click uses constructed Transform
    assert len(pool.calls)==1
    _world,location,level,name=pool.calls[0]
    assert abs(location.X-1000)<1e-4 and abs(location.Y-2220)<1e-4
    assert abs(location.Z-265)<1e-4
    assert level==40
    # A missing optional forward-vector method falls back to K2 rotation.
    class RotationOnlyOakCharacter:
        def _get_address(self):return id(self)
        def K2_GetActorLocation(self):return SimpleNamespace(X=500.,Y=300.,Z=80.)
        def K2_GetActorRotation(self):return SimpleNamespace(Yaw=180.)
    actor2=RotationOnlyOakCharacter()
    assert all(math.isfinite(x) for x in ns['_actor_forward_xy'](actor2))
    st.spawn_pending=None;st.anti_spam_until=0
    ns['pawn']=lambda:actor2
    assert not ns['spawn_request']()
    assert ns['spawn_request']() and len(pool.calls)==2
    _,loc2,_,_=pool.calls[-1]
    assert abs(loc2.X-280)<1e-4 and abs(loc2.Y-300)<1e-4
    # An unresolvable position blocks before any gameplay spawn API request.
    st.spawn_pending=None;st.anti_spam_until=0
    ns['pawn']=lambda:SimpleNamespace(_get_address=lambda:111)
    assert not ns['spawn_request']()
    assert not ns['spawn_request']()
    assert len(pool.calls)==2
    # Hard-wrapped notes are limited to their allotted width and line count.
    wrapped=ns['_fit_block_text']('A native engine might ignore auto wrapping and this is a lengthy important gameplay warning',18,3)
    assert len(wrapped.split('\n'))<=3
    assert all(len(row)<=18 for row in wrapped.split('\n'))
    assert wrapped.endswith('...')
    assert 'under' not in wrapped
    # Art (including new original wordmark/hazard strip) is hash attested.
    arts=root/'CROWN_CC0_ASSETS'
    manifest=json.loads((arts/'MANIFEST.json').read_text('utf-8'))
    assert len(ns['ART_FILES'])>=14
    for art_id,file_name in ns['ART_FILES'].items():
        raw=(arts/file_name).read_bytes()
        assert ns['_verify_png_bytes'](art_id,raw),(art_id,file_name)
        assert not ns['_verify_png_bytes'](art_id,raw+b'changed'),art_id
    assert any(a['id']=='TITLE_WORDMARK' for a in manifest['assets'])
    assert any(a['id']=='HAZARD_STRIP' for a in manifest['assets'])
    # Capture ACTUAL UI geometry from the source renderer, not a hand-written
    # claim about coordinates. No main page plaque may cover any action button.
    ns['pawn']=lambda:ctx['pawn']
    ns['SETTINGS_DIR']=None
    ns['__loader__']=None
    original_btn,original_note=ns['btn'],ns['note_panel']
    geometry={'buttons':[],'notes':[]}
    def trace_btn(parent,label,x,y,w,h,*args,**kwargs):
        geometry['buttons'].append((str(label),x,y,w,h))
        return original_btn(parent,label,x,y,w,h,*args,**kwargs)
    def trace_note(parent,title,body,x,y,w,h,*args,**kwargs):
        geometry['notes'].append((str(title),x,y,w,h))
        return original_note(parent,title,body,x,y,w,h,*args,**kwargs)
    ns['btn']=trace_btn;ns['note_panel']=trace_note
    for resolution in ((2560,1440),(1920,1080),(1280,720),(854,480)):
        ns['viewport']=lambda r=resolution:r
        st.opened=False
        ns['open_menu']()
        assert st.opened and st.draw_ok,resolution
        for page in ns['PAGE_HELP']:
            geometry['buttons'].clear();geometry['notes'].clear()
            ns['show_page'](page)
            assert st.draw_ok,(resolution,page)
            px,py,pw,ph,*_=st.panel_rect
            split=px+185
            footer=py+ph-141
            main_btn=[b for b in geometry['buttons'] if b[1]>=split and b[2]>py+200 and b[2]<footer]
            for title,x,y,w,h in geometry['notes']:
                assert y+h <= footer-1,(resolution,page,'note crosses footer',title,y+h,footer)
                for label,bx,by,bw,bh in main_btn:
                    hor=x < bx+bw-2 and bx < x+w-2
                    ver=y < by+bh-2 and by < y+h-2
                    assert not (hor and ver),(resolution,page,'note overlaps button',title,label,y,by)
        ns['close_menu']()
    print('PASS v2.4: live OakCharacter transform regression, safe missing-position behavior, original PNG attestations, 12 pages x four resolutions note/button geometry')
finally:
    for key,value in old.items():
        if value is None:sys.modules.pop(key,None)
        else:sys.modules[key]=value
