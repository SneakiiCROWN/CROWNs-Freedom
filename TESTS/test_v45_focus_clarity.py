"""v4.5: production regression for input dedup, hover target, focus, dock refresh and version."""
from pathlib import Path
from types import SimpleNamespace as NS
import runpy,sys,time,re
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
    'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'focus_clarity_qa'}
 source=(root/'SOURCE/__init__.py').read_text()
 exec(compile(source,'focus_clarity_source','exec'),ns)
 st=ns['State'];st.controller_mode=False;st.opened=True
 spawn_baseline=len(ctx['pool'].calls)
 assert 'version=RELEASE_VERSION' in source and 'v5.26.0' in source
 assert 'version = "5.26.0"' in (root/'SOURCE/pyproject.toml').read_text()
 assert ns['ART_MOD_FILENAME']=='CROWNs_Freedom_v5_26_ECHO_Fieldcraft_R22.sdkmod'
 # Duplicate visible captions must highlight the actual widget at index 1.
 b0=NS(IsHovered=lambda:False);b1=NS(IsHovered=lambda:True)
 st.buttons=[{'name':'CLOSE','widget':b0,'rect':(10,10,130,44),'disabled':False},
             {'name':'CLOSE','widget':b1,'rect':(270,200,130,44),'disabled':False}]
 st.mouse_hover_frame=[object() for _ in range(4)];st.hovered_control=None
 st.status_widget=NS(SetText=lambda *a:None);st.status_chars=60
 recorded=[]; original_position=ns['size_position']
 ns['size_position']=lambda _,x,y,w,h,z=0:recorded.append((x,y,w,h,z))
 ns['poll_hover_help']()
 assert recorded[0][0]==267 and recorded[0][1]==197,recorded
 assert st.hovered_control==id(b1)
 ns['size_position']=original_position
 # Controller focus restoration picks closest *matching action*, not first.
 st.buttons=[{'name':'RESTORE','rect':(15,20,150,42),'disabled':False},
             {'name':'RESTORE','rect':(550,480,150,42),'disabled':False},
             {'name':'OTHER','rect':(535,460,150,42),'disabled':False}]
 assert ns['_restore_focus_index']('RESTORE',(540,482,160,42))==1
 assert ns['_restore_focus_index']('NOT_PRESENT',None) in (0,1,2)
 # Menu input must not trigger the same native button AGAIN after A/Enter.
 calls=[];st.opened=True;st.controller_enabled=False
 ns['get_pc']=lambda **kw:ctx['pc'];ns['viewport']=lambda:(1920.,1080.)
 click=ctx['W']('Button');click.pressed=False
 entry={'name':'MONEY CONFIRM','widget':click,'run':lambda:calls.append('executed'),
        'pressed':True,'rect':(20,20,250,43),'disabled':False}
 st.buttons=[entry];st.sliders=[];st.input_pc=ctx['pc'];st.root=ctx['W']('Root')
 st.session_last_check=time.monotonic();st.viewport_last_check=time.monotonic()
 st.last_poll=0;st.focus_watch_at=time.monotonic()+10
 ns['_arm_native_click_guard'](entry,time.monotonic())
 entry['pressed']=True # Simulate native UMG's stale pressed/released transition.
 ns['tick']()
 assert not calls,'A native mouse-button release repeated a controller action'
 st.native_activation_ignore_until=0
 entry['pressed']=True;st.last_poll=0;st.session_last_check=time.monotonic()
 ns['tick']()
 assert calls==['executed'],'ordinary native mouse release must still work'
 # The side dock must repaint changes to ON/OFF and selected speed, but not
 # redraw twice when the underlying action has already drawn a new page.
 st.opened=True;st.dock_mode='SIDE';st.buttons=[];st.ui_rebuild_count=9
 repaints=[]; original_redraw=ns['redraw']
 ns['redraw']=lambda:repaints.append('draw')
 canvas=ctx['W']('CanvasPanel')
 ns['_side_action'](canvas,'SPEED x2.0',lambda:setattr(st,'motion_scale',2.0),30,50,240)
 assert len(st.buttons)==1
 st.buttons[-1]['run']()
 assert st.motion_scale==2.0 and repaints==['draw']
 ns['redraw']=original_redraw
 assert len(ctx['pool'].calls)==spawn_baseline,'v4.5 checks cannot request or spawn any items'
 print('PASS v4.5: exact hover target, duplicate-name focus restoration, raw/native activation de-duplication, immediate Side Dock refresh, metadata consistency')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
