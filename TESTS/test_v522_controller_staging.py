"""v5.22 controller stage-only UX and live-capacity read validation.

Mocks deliberately do not talk to the game or BL4Live. UI actions must
be legible and reversible before any real backend write is considered.
"""
from pathlib import Path
import runpy, time


def run():
    root=Path(__file__).resolve().parents[1]
    ns=runpy.run_path(str(root/'TESTS/test_core.py'))['ns']
    st=ns['State']
    env=ns['capacity_queue_request'].__globals__
    assert ns['RELEASE_VERSION']=='5.26.0'
    assert 'v5_26' in ns['ART_MOD_FILENAME']
    st.opened=False;st.controller_mode=True;st.page='PLAYER';st.dock_mode='FULL';st.help_open=False;st.diag_open=False;st.style_audio_open=False
    st.capacity_mode='BACKPACK';st.capacity_draft=40
    st.capacity_drafts={'BACKPACK':40,'BANK':40}
    st.capacity_view='BROWSE'
    env['viewport']=lambda:(1920.0,1080.0)
    env['_session_anchor']=lambda:('map','pawn')
    ns['open_menu']()
    assert st.opened and st.draw_ok, (st.message,st.ui_error_count,st.runtime_failures[-2:])
    st.page='CAPACITY'
    ns['capacity_edit_open']()
    assert st.capacity_view=='EDIT'
    labels={i['name'] for i in st.buttons}
    assert 'USE THIS STAGED VALUE' in labels and 'CANCEL / KEEP OLD VALUE' in labels
    assert any('-100 SLOTS' in n for n in labels)
    assert st.capacity_input is None, 'Gamepad path must not require a native keyboard'
    assert ns['capacity_step'](27) and st.capacity_draft==67
    assert not ns['capacity_step']('oops')
    assert ns['capacity_step_commit']()
    assert st.capacity_view=='BROWSE'
    assert st.capacity_draft==67
    assert 'APPLY BACKPACK 67' in {i['name'] for i in st.buttons}
    # The staged bank and backpack values are separate; switches never write.
    ns['capacity_mode_toggle']()
    assert st.capacity_mode=='BANK' and st.capacity_draft==40
    ns['capacity_set_draft'](325)
    ns['capacity_mode_toggle']()
    assert st.capacity_mode=='BACKPACK' and st.capacity_draft==67
    ns['capacity_mode_toggle']()
    assert st.capacity_draft==325
    ns['capacity_edit_open']()
    assert ns['capacity_step'](100) and st.capacity_draft==425
    ns['_controller_back']()
    assert st.capacity_view=='BROWSE' and st.capacity_draft==325
    # Full controller staging of an exact Forge item level is also possible.
    st.page='SPAWN';st.spawn_view='LEVEL';st.level_draft='45'
    ns['redraw']()
    names={x['name'] for x in st.buttons}
    assert 'USE THIS LEVEL' in names and '+1 LEVEL' in names
    assert ns['forge_controller_step'](1) and st.level_draft=='46'
    assert ns['forge_controller_step'](-999) and st.level_draft=='1'
    assert ns['forge_controller_step'](1000) and st.level_draft=='100'
    assert ns['forge_controller_commit']() and st.spawn_level==100
    assert st.spawn_view=='TOOLS'
    st.spawn_view='LEVEL';st.level_draft='46'
    ns['_controller_back']()
    assert st.spawn_view=='TOOLS' and st.spawn_level==100
    # A successful live READ containing a conflicting duplicate container
    # must not approve any edits to that container.
    ns['close_menu']()
    env.update(session_role=lambda:'SOLO',_session_anchor=lambda:('world','pawn'))
    st.capacity_bridge_generation=17
    st.capacity_bridge_job={'kind':'READ','mode':'BACKPACK','token':17,
        'anchor':('world','pawn'),'finished':True,'result':{'ok':True,'containers':[
           {'container':'BackpackItems','max_size':200,'slots':90},
           {'container':'BackpackItems','max_size':100,'slots':90}]}}
    assert ns['capacity_consume_result']()
    assert 'BackpackItems' not in st.capacity_occupied
    assert not ns['capacity_queue_request']('APPLY',150)
    st.capacity_bridge_job={'kind':'READ','mode':'BACKPACK','token':17,
        'anchor':('world','pawn'),'finished':True,'result':{'ok':True,'containers':[
            {'container':'BackpackItems','max_size':9999,'slots':20}]}}
    assert ns['capacity_consume_result']()
    assert st.capacity_readback_at==0
    assert 'CONFLICT' in st.capacity_status
    assert not ns['capacity_queue_request']('APPLY',100)
    print('PASS v5.22: gamepad Capacity and Forge steps, cancel/return, independent modes, duplicate/9999 read guards')

if __name__=='__main__':run()
