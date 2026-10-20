"""v5.23 analog gamepad and shared capacity reset safety: synthetic only."""
from pathlib import Path
import runpy, sys, time
from types import SimpleNamespace

def run():
    root=Path(__file__).resolve().parents[1]
    ns=runpy.run_path(str(root/'TESTS/test_core.py'))['ns']
    st=ns['State']; env=ns['key_down'].__globals__
    assert ns['RELEASE_VERSION']=='5.26.0'
    # Native controller polling must see four analog directions as first-class
    # focus inputs. Allow triggerless analog navigation, but no 2-way diagonals.
    directions=ns['CONTROLLER_DIRECTIONS']
    assert directions['Gamepad_LeftStick_Up']=='UP'
    assert directions['Gamepad_LeftStick_Right']=='RIGHT'
    ticks=[];held=set()
    env['key_down']=lambda pc,key:key in held
    env['_controller_focus_direction']=lambda direction:ticks.append(direction)
    env['_controller_update_focus_outline']=lambda:None
    st.controller_enabled=True;st.root=None;st.controller_last_keys={}
    st.controller_open_block_until=0;st.controller_open_latched=False
    st.controller_repeat_key=None;st.controller_repeat_due=0
    st.opened=True;st.help_open=False
    held.add('Gamepad_LeftStick_Up')
    ns['controller_ui_tick'](None,100)
    assert ticks==['UP'], ticks
    ns['controller_ui_tick'](None,100.15)
    assert ticks==['UP'], 'one action per initial press'
    ns['controller_ui_tick'](None,100.44)
    assert ticks==['UP','UP'], 'held repeat after first delay'
    held.add('Gamepad_LeftStick_Right')
    ns['controller_ui_tick'](None,101)
    assert ticks==['UP','UP'], 'diagonal must not move two focus directions'
    held.clear();ns['controller_ui_tick'](None,101.01)
    held.add('Gamepad_LeftStick_Right');ns['controller_ui_tick'](None,101.10)
    assert ticks[-1]=='RIGHT'
    # XInput source's native threshold, dominant-axis logic and global focus
    # guard are tested with an isolated fake XInput packet (not BL4 itself).
    import ctypes
    class Pad(ctypes.Structure):
        _fields_=[('buttons',ctypes.c_ushort),('left_trigger',ctypes.c_byte),('right_trigger',ctypes.c_byte),('left_x',ctypes.c_short),('left_y',ctypes.c_short),('right_x',ctypes.c_short),('right_y',ctypes.c_short)]
    class Packet(ctypes.Structure):
        _fields_=[('packet',ctypes.c_uint),('pad',Pad)]
    axis={'x':0,'y':0};calls=[]
    def get_state(index, pointer):
        calls.append(index)
        pointer._obj.pad.left_x=axis['x'];pointer._obj.pad.left_y=axis['y'];pointer._obj.pad.buttons=0
        return 0
    get_state.argtypes=[];get_state.restype=None
    env['_xinput_dll']=SimpleNamespace(XInputGetState=get_state)
    env['_xinput_last_at']=-10
    env['_game_window_foreground']=lambda:True
    original_platform=sys.platform
    try:
        sys.platform='win32'
        axis.update(x=0,y=27000)
        assert ns['_windows_raw_key']('Gamepad_LeftStick_Up') is True
        assert ns['_windows_raw_key']('Gamepad_LeftStick_Down') is False
        axis.update(x=26500,y=26500);env['_xinput_last_at']=-10
        assert not ns['_windows_raw_key']('Gamepad_LeftStick_Up')
        assert not ns['_windows_raw_key']('Gamepad_LeftStick_Right')
        axis.update(x=-29000,y=3000);env['_xinput_last_at']=-10
        assert ns['_windows_raw_key']('Gamepad_LeftStick_Left')
        axis.update(x=4000,y=4000);env['_xinput_last_at']=-10
        assert not ns['_windows_raw_key']('Gamepad_LeftStick_Up')
        env['_game_window_foreground']=lambda:False
        assert ns['_windows_raw_key']('Gamepad_LeftStick_Left') is False
    finally:
        sys.platform=original_platform
    # Direct queued writes cannot bypass the same reset protections as UI.
    env['session_role']=lambda:'SOLO'
    env['_session_anchor']=lambda:('world','actor')
    env['_capacity_bridge_exchange']=lambda req:{'ok':False,'error':'mock bridge refused'}
    st.capacity_bridge_job=None;st.capacity_mode='BACKPACK'
    st.capacity_readback_anchor=('world','actor')
    st.capacity_readback_at=time.monotonic()
    st.capacity_readback={'BackpackItems':220}
    st.capacity_occupied={'BackpackItems':80}
    st.capacity_bag_original=None
    assert not ns['capacity_queue_request']('APPLY',0)
    st.capacity_bag_original=40
    assert not ns['capacity_queue_request']('APPLY',0)
    st.capacity_bag_original=220
    assert ns['capacity_queue_request']('APPLY',0)
    for _ in range(100):
        if st.capacity_bridge_job and st.capacity_bridge_job['finished']:break
        time.sleep(.01)
    assert ns['capacity_consume_result']()
    assert st.capacity_status.startswith('BACKEND REFUSED')
    st.capacity_bridge_job=None
    st.capacity_readback['BackpackItems']=70  # invalid below item-array slots
    assert not ns['capacity_queue_request']('APPLY',200)
    print('PASS v5.23 analog focus + diagonal guards + foreground + backend reset invariants')

if __name__=='__main__':run()
