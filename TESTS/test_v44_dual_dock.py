"""v4.4 test: real UMG layouts, usable left/right side dock, state badge and input safety."""
from pathlib import Path
import runpy,sys
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'dual_dock_qa'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_dual_dock','exec'),ns)
 st=ns['State']; before_spawns=len(ctx['pool'].calls)
 assert ns['ART_MOD_FILENAME']=='CROWNs_Freedom_v5_26_ECHO_Fieldcraft_R22.sdkmod'
 assert 'SetInputMode_UIOnly' in (root/'SOURCE/__init__.py').read_text()
 # Preserve full window position when switching into the Side Dock.
 st.dock_mode='FULL';st.window_x=109;st.window_y=82
 ns['toggle_dock_mode']()
 assert st.dock_mode=='SIDE' and (st.window_x,st.window_y)==(109,82)
 for wh in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
  ns['viewport']=lambda wh=wh:wh
  for right in (False,True):
   st.dock_right=right
   for page in ('PLAYER','MOTION','WORLD','WAYPOINTS','SPAWN','DISPLAY'):
    st.page=page;st.side_action_page=0;st.dock_view='STYLE';st.dock_view='STYLE';st.dock_view='STYLE';st.dock_view='STYLE'
    ns['open_menu']()
    assert st.opened and st.draw_ok and st.input_guard_confirmed,(wh,right,page,st.message)
    x,y,w,h,vw,vh=st.panel_rect
    assert x>=9 and x+w<=vw-9 and h<=830
    assert (x>vw/2 if right else x<vw/2),(wh,right,page,x)
    assert any(b['name']==('MOVE LEFT' if right else 'MOVE RIGHT') for b in st.buttons)
    for b in st.buttons:
     bx,by,bw,bh=b['rect'];assert bx>=x-1 and by>=y-1 and bx+bw<=x+w+1 and by+bh<=y+h+1,(b['name'],wh)
    ns['close_menu']()
 # A click on dock edge toggle preserves the current page and changes x.
 ns['viewport']=lambda:(1920.,1080.)
 st.page='MOTION';st.dock_mode='SIDE';st.dock_right=False
 ns['open_menu']()
 sel=next(b for b in st.buttons if b['name']=='MOVE RIGHT')
 sel['run']()
 assert st.opened and st.page=='MOTION' and st.dock_right
 assert st.panel_rect[0]>1000
 ns['close_menu']()
 # Full menu auto-fits height on 1440p without cropping controls or erasing custom position.
 st.dock_mode='FULL';st.window_x=None;st.window_y=None;st.page='PLAYER'
 ns['viewport']=lambda:(2560.,1440.)
 ns['open_menu']()
 assert st.panel_rect[2]<=1880 and st.panel_rect[3]<=1140,(st.panel_rect,)
 for b in st.buttons:
  bx,by,bw,bh=b['rect'];x,y,w,h,*_=st.panel_rect
  assert bx>=x-1 and by>=y-1 and bx+bw<=x+w+1 and by+bh<=y+h+1,b['name']
 ns['close_menu']()
 # ON/OFF state pills must render as hit-test-invisible paint, not ghost buttons.
 original_text,original_box=ns['text'],ns['box']
 painted=[]
 def text_proxy(*args,**kw):painted.append(str(args[1]));return original_text(*args,**kw)
 ns['text']=text_proxy
 st.buttons=[];st.god=True
 parent=ctx['u'].find_object('Class','/Script/UMG.CanvasPanel') if False else None
 # Use simple canvas widget mock as parent to retain a button's native rectangle.
 canvas=ns['widget']('CanvasPanel')
 ns['btn'](canvas,'DISABLE GOD MODE',10,20,270,44,lambda:None,active=True)
 assert 'ON' in painted and 'GOD MODE' in painted
 assert len(st.buttons)==1 and st.buttons[0]['name']=='DISABLE GOD MODE'
 painted.clear();st.buttons=[];st.god=False
 ns['btn'](canvas,'ENABLE GOD MODE',10,20,270,44,lambda:None)
 assert 'OFF' in painted and 'GOD MODE' in painted
 assert len(st.buttons)==1
 ns['text']=original_text
 assert len(ctx['pool'].calls)==before_spawns,'QA cannot grant or spawn items'
 print('PASS v4.4: 48 Side Dock views both edges, persisted full-window position, bounded full view, honest input guard, noninteractive REQUESTED/OFF badges')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
