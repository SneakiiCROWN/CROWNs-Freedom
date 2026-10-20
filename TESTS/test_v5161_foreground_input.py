"""Foreground loss and input-release safety on the actual mod source."""
from pathlib import Path
from types import SimpleNamespace as NS
import runpy,sys
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_foreground_qa'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crowns_foreground.py','exec'),ns)
 st=ns['State'];pc=ctx['pc']
 assert ns['RELEASE_VERSION']=='5.26.0'
 # An in-progress drag must be thrown away, not accidentally saved.
 state={'foreground':False,'mouse':False,'pad':False,'pressed':True}
 ns['_game_window_foreground']=lambda:state['foreground']
 ns['key_down']=lambda pc,name:state['mouse'] if name=='LeftMouseButton' else (state['pad'] if name=='Gamepad_FaceButton_Bottom' else False)
 st.opened=True;st.panel_rect=(20.,20.,800.,500.,1800.,1000.)
 st.canvas=ctx['W']('canvas')
 moves=[]
 st.canvas.SetRenderTranslation=lambda v:moves.append((v.X,v.Y))
 st.drag_armed=True
 st.drag_last=(400.,80.)
 st.drag_origin=(20.,20.)
 st.drag_start=(100.,100.)
 st.window_x=20.;st.window_y=20.
 run={'n':0}
 widget=NS(IsPressed=lambda:state['pressed'])
 st.buttons=[{'pressed':True,'widget':widget,'run':lambda:run.__setitem__('n',run['n']+1),'name':'DELETE'}]
 assert ns['_menu_foreground_guard'](pc,100.0) is True
 assert st.foreground_suspended and not st.drag_armed
 assert moves[-1]==(0.,0.)
 assert st.window_x==20. and st.window_y==20. and not st.buttons[0]['pressed']
 assert st.foreground_guard_count==1
 # Returning with held mouse must not leak a release to the item.
 state.update(foreground=True,mouse=True)
 assert ns['_menu_foreground_guard'](pc,100.2) is True
 assert ns['_menu_foreground_guard'](pc,101.) is True
 state.update(mouse=False,pressed=False)
 assert ns['_menu_foreground_guard'](pc,101.05) is True
 assert ns['_menu_foreground_guard'](pc,101.2) is False
 assert not st.buttons[0]['pressed'] and run['n']==0
 # Repeated loss preserves the pad edge until it is released.
 state.update(foreground=False,pad=True)
 assert ns['_menu_foreground_guard'](pc,102.) is True
 state['foreground']=True
 assert ns['_menu_foreground_guard'](pc,102.1) is True
 assert ns['_menu_foreground_guard'](pc,102.5) is True
 assert st.controller_last_keys['Gamepad_FaceButton_Bottom']
 state['pad']=False
 assert ns['_menu_foreground_guard'](pc,102.6) is True
 assert ns['_menu_foreground_guard'](pc,102.75) is False
 assert st.foreground_guard_count==2
 # Missing IsPressed support must not deadlock the guard forever.
 state['foreground']=False
 assert ns['_menu_foreground_guard'](pc,104.) is True
 state['foreground']=True
 st.buttons[0]['widget']=NS()
 assert ns['_menu_foreground_guard'](pc,104.1)
 assert not ns['_menu_foreground_guard'](pc,104.5)
 # QA report now provides aggregate, nonidentifying data.
 assert "'foreground_focus_guards':State.foreground_guard_count" in (root/'SOURCE/__init__.py').read_text()
 print('PASS v5.25.0 focus: interrupted drag canceled, held mouse/pad release blocked, no tooltip actions, QA counters')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
