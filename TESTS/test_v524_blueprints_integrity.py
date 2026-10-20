"""v5.24: safe local Forge blueprints, preference recovery, stale inventory failure."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json,runpy,time

def run():
    root=Path(__file__).resolve().parents[1]
    ns=runpy.run_path(str(root/'TESTS/test_core.py'))['ns']
    st=ns['State']
    env=ns['load_preferences'].__globals__
    assert ns['RELEASE_VERSION']=='5.26.0'
    with TemporaryDirectory() as folder:
        env['SETTINGS_DIR']=Path(folder)
        pool=ns['SPAWN_POOLS'][0]
        st.checkpoints={}
        prefs=Path(folder)/'CROWNs_Freedom_UI.json'
        prefs.write_text(json.dumps({'prefs_schema':4,
            'theme_index':{'malformed':'yes'},
            'travel_slots':[{'slot':2,'map':'Providence','xyz':[31,32,33]}],
            'forge_blueprints':{
                '1':{'pool':pool[1],'level':65,'count':3},
                '2':{'pool':'untrusted/path','level':65,'count':1},
                '3':{'pool':pool[1],'level':999,'count':1}}}), encoding='utf-8')
        ns['load_preferences']()
        assert st.theme_idx==0, 'bad theme must not discard the rest of saved settings'
        assert st.checkpoints[2]==('Providence',(31.,32.,33.))
        assert st.forge_blueprints=={'1':{'pool':pool[1],'level':65,'count':3}}
        st.opened=False;st.spawn_view='TOOLS';st.spawn_category_idx=0;st.spawn_pool_idx=0
        st.spawn_search='';st.spawn_level=42;st.spawn_count=2
        st.spawn_pending=('old_armed',)
        assert ns['forge_open_blueprints']()
        assert st.spawn_pending is None and st.spawn_view=='BLUEPRINTS'
        assert ns['forge_save_blueprint'](2)
        stored=json.loads(prefs.read_text())
        assert stored['forge_blueprints']['2']=={'pool':pool[1],'level':42,'count':2}
        assert '3' not in stored['forge_blueprints']
        st.spawn_level=46
        assert not ns['forge_save_blueprint'](2), 'occupied blueprint requires confirmation'
        assert json.loads(prefs.read_text())['forge_blueprints']['2']['level']==42
        assert ns['forge_save_blueprint'](2), 'matching second press overwrites the local recipe'
        assert json.loads(prefs.read_text())['forge_blueprints']['2']['level']==46
        st.spawn_level=42
        assert not ns['forge_save_blueprint'](2)
        assert ns['forge_save_blueprint'](2)
        # Restore is pure staging and clears prior arm. A stale Forge filter
        # must not conceal the newly loaded catalogue item.
        st.spawn_level=100;st.spawn_count=1;st.spawn_pool_idx=1
        st.spawn_search='something unrelated';st.spawn_pending=('old_armed',)
        assert ns['forge_load_blueprint'](2)
        assert (st.spawn_pool_idx,st.spawn_level,st.spawn_count)==(0,42,2)
        assert st.spawn_search=='' and st.spawn_pending is None
        assert st.spawn_view=='TOOLS' and not st.spawn_requests
        before=(st.spawn_level,st.spawn_count,st.spawn_pool_idx)
        st.forge_blueprints['2']['pool']='../../untrusted'
        assert not ns['forge_load_blueprint'](2)
        assert (st.spawn_level,st.spawn_count,st.spawn_pool_idx)==before
        assert not ns['forge_save_blueprint'](99)
        st.forge_blueprints['2']={'pool':pool[1],'level':42,'count':2}
        assert ns['forge_open_blueprints']()
        st.page='SPAWN'
        ns['_controller_back']()
        assert st.spawn_view=='TOOLS', 'B returns to the Forge, not gameplay'
        # Real UI has six explicit save/load actions; each respects disabled state.
        env['viewport']=lambda:(1920.,1080.)
        env['_session_anchor']=lambda:('world','pawn')
        st.dock_mode='FULL';st.controller_mode=True;st.page='SPAWN'
        ns['open_menu']()
        assert st.opened,(st.message,st.ui_error_count,st.runtime_failures,st.input_last_status,st.safe_mode,len(st.buttons),st.page,st.spawn_view,st.draw_ok,st.session_anchor)
        ns['forge_open_blueprints']()
        names={item['name'] for item in st.buttons}
        assert 'SAVE BLUEPRINT 1' in names and 'SAVE BLUEPRINT 3' in names
        assert any(label.startswith('LOAD 2 /') for label in names)
        assert '<< BACK TO FORGE' in names
        # Controller actions remain inside the content area even on a small
        # 720p / 480p viewport (synthetic geometry, not real UE screenshots).
        for resolution in ((2560.,1440.),(1280.,720.),(854.,480.)):
            env['viewport']=lambda r=resolution:r
            ns['redraw']()
            assert st.draw_ok, (resolution, st.message)
            px,py,pw,ph,*_=st.panel_rect
            foot=py+ph-141
            for item in st.buttons:
                name=item.get('name','')
                if name.startswith(('SAVE BLUEPRINT','LOAD ','CONFIRM OVERWRITE')):
                    x,y,w,h=item['rect']
                    assert px<=x<=px+pw and y+h<foot, (resolution,name,item['rect'],foot)
        ns['close_menu']()
        # Failed read or write must invalidate even a recently verified local
        # snapshot: no subsequent write may use those old container counts.
        env['session_role']=lambda:'SOLO'
        env['_session_anchor']=lambda:('map','pawn')
        st.capacity_bridge_generation=34;st.capacity_bridge_job=None
        for kind in ('READ','APPLY'):
            st.capacity_readback={'BackpackItems':250}
            st.capacity_occupied={'BackpackItems':12}
            st.capacity_readback_anchor=('map','pawn')
            st.capacity_readback_at=time.monotonic()
            st.capacity_confirm=('BACKPACK',100,('map','pawn'))
            st.capacity_bridge_job={'kind':kind,'value':100,'mode':'BACKPACK','token':34,
                'anchor':('map','pawn'),'finished':True,
                'result':{'ok':False,'error':'socket timed out'}}
            assert ns['capacity_consume_result']()
            assert not st.capacity_readback and not st.capacity_occupied
            assert st.capacity_readback_at==0 and st.capacity_readback_anchor is None
            assert st.capacity_confirm is None
            assert 'READ AGAIN' in st.capacity_status
            assert not ns['capacity_queue_request']('APPLY',100)
        print('PASS v5.24 local Forge blueprints, corrupted-theme bookmark resilience, read/write stale-authorisation cleanup, controller menu')
if __name__=='__main__':run()
