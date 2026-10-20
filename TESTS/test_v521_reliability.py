"""v5.21 offline regression of fresh capacity snapshots and editor navigation.
Synthetic mocks only; does not certify BL4 runtime or modify game saves.
"""
from pathlib import Path
import runpy, time

def run():
    root=Path(__file__).resolve().parents[1]
    ns=runpy.run_path(str(root/'TESTS/test_core.py'))['ns']
    st=ns['State']; env=ns['capacity_queue_request'].__globals__
    assert ns['RELEASE_VERSION']=='5.26.0'
    events=[]
    env.update(session_role=lambda:'SOLO',_session_anchor=lambda:('mapA','local'),log=events.append)
    st.opened=False
    st.capacity_bridge_job=None
    st.capacity_mode='BACKPACK';st.capacity_draft=160
    st.capacity_readback_anchor=('mapA','local')
    st.capacity_occupied={'BackpackItems':60}
    st.capacity_readback={'BackpackItems':120}
    st.capacity_readback_at=time.monotonic()-40
    assert not ns['capacity_apply_request']() and 'expire' in events[-1].lower()
    assert not ns['capacity_queue_request']('APPLY',160) and 'fresh' in events[-1].lower()
    # A changed character/map must not inherit the other one's original capacity.
    st.capacity_bag_original=120
    st.capacity_bank_original=140
    st.capacity_bridge_generation=10
    st.session_resets=0
    ns['_invalidate_pending_session']('test only')
    assert st.capacity_bag_original is None and st.capacity_bank_original is None
    assert not st.capacity_occupied and not st.capacity_readback and st.capacity_readback_anchor is None
    assert st.capacity_readback_at==0.0 and st.capacity_bridge_generation==11
    # Malformed / empty reads must not authorize a future write.
    st.capacity_bridge_job={'kind':'READ','value':None,'mode':'BACKPACK','anchor':('mapA','local'),
        'token':11,'finished':True,'result':{'ok':True,'containers':[{'container':'BackpackItems','max_size':90,'slots':120}]}}
    assert ns['capacity_consume_result']()
    assert st.capacity_readback_anchor is None and st.capacity_status.startswith('READ INCOMPLETE')
    assert not ns['capacity_queue_request']('APPLY',200)
    # Valid readback opens a short 30-second confirmation window.
    st.capacity_bridge_job={'kind':'READ','value':None,'mode':'BACKPACK','anchor':('mapA','local'),
        'token':11,'finished':True,'result':{'ok':True,'containers':[{'container':'BackpackItems','max_size':200,'slots':70}]}}
    assert ns['capacity_consume_result']()
    assert st.capacity_readback_anchor==('mapA','local') and st.capacity_readback_at>0
    assert st.capacity_bag_original==200
    # Successful backend acceptance forces verification, not another blind write.
    st.capacity_bridge_job={'kind':'APPLY','value':160,'mode':'BACKPACK','anchor':('mapA','local'),
        'token':11,'finished':True,'result':{'ok':True,'actual':160}}
    assert ns['capacity_consume_result']()
    assert st.capacity_readback_at==0.0 and st.capacity_readback_anchor is None
    assert 'READ AGAIN' in st.capacity_status
    # On gamepad Back should close the editor, not the entire CROWN menu.
    st.help_open=False;st.style_audio_open=False;st.diag_open=False;st.activity_open=False
    st.page='CAPACITY';st.capacity_view='EDIT';st.capacity_input=object()
    ns['_controller_back']()
    assert st.capacity_view=='BROWSE' and st.capacity_input is None
    st.page='FINDER';st.finder_mode='EDIT'
    ns['_controller_back']()
    assert st.finder_mode=='BROWSE'
    # A refused UIOnly call must never force GameOnly onto an input mode
    # CROWN didn't own. A previously accepted UIOnly must be released even
    # if a subsequent focus recovery failed.
    from types import SimpleNamespace
    input_calls=[]
    api=SimpleNamespace(SetInputMode_GameOnly=lambda *a:input_calls.append('GameOnly'),
                        SetFocusToGameViewport=lambda *a:input_calls.append('Focus'))
    env['cls']=lambda name:SimpleNamespace(ClassDefaultObject=api)
    def check_release(owned):
        st.input_pc=SimpleNamespace()
        st.input_saved={}
        st.input_move_ignored_original=None
        st.input_look_ignored_original=None
        st.input_mode_owned=owned
        env['get_pc']=lambda **kwargs:st.input_pc  # same live controller during release
        ns['release_input']()
    check_release(False)
    assert input_calls==[],input_calls
    check_release(True)
    assert 'GameOnly' in input_calls and st.input_mode_owned is False
    # A successful transport ACK without actual size is NOT a verified change.
    st.capacity_bridge_job={'kind':'APPLY','value':160,'mode':'BACKPACK','anchor':('mapA','local'),
        'token':11,'finished':True,'result':{'ok':True,'actual':None}}
    assert ns['capacity_consume_result']()
    assert 'UNVERIFIED' in st.capacity_status
    print('PASS v5.21: snapshot/session guards, input-mode ownership, unverified ACK, controller Back editors')

if __name__=='__main__':run()
