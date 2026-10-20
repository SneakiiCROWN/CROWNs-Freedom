"""Stricter Unreal visibility and toast/menu geometry regression tests.

Epic documents ESlateVisibility: 3=HitTestInvisible (entire subtree),
4=SelfHitTestInvisible (children can still intercept clicks).
These checks use a recording widget rather than permissive noop Unreal mocks.
"""
from pathlib import Path
from types import SimpleNamespace
import runpy,sys,time
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'v571_toast_hit_safety'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'v571_source','exec'),ns)
 st=ns['State']
 assert ns['RELEASE_VERSION']=='5.26.0'
 for w,h in ((2560,1440),(1920,1080),(1280,720),(854,480)):
  ns['viewport']=lambda w=w,h=h:(w,h)
  for opened,side in ((False,'FULL'),(True,'SIDE'),(True,'FULL')):
   st.opened=opened
   for x,pw in ((10,300),(w-310,300)):
    st.panel_rect=(x,10,pw,min(h-20,820),w,h)
    px,py,tw,th=ns['_toast_screen_rect']()
    assert tw<=w and 0<=px<=w-tw+0.1,(w,h,x,px,tw)
    assert 0<=py<=h-th+0.1,(w,h,py,th)
    if opened and w>=1280 and side=='SIDE':
     assert px>=x+pw+18 or px+tw<=x-18 or px>=18
 st.opened=True
 st.panel_rect=(10,10,320,780,1920,1080)
 ns['viewport']=lambda:(1920,1080)
 st.toasts_enabled=True
 st.toast_render_failed=False
 records=[]
 class Widget(ctx['W']):
  def __init__(self,path):
   super().__init__(path)
   self.vis=None;self.viewport_added=False;self.placement=None;self.removed=False
   records.append(self)
  def SetVisibility(self,value):
   self.vis=value
  def AddToViewport(self,*args):
   assert self.vis==3,('Toast root must be entirely non-hit-testable',self.vis)
   self.viewport_added=True
  def SetPositionInViewport(self,pos,*args):
   self.placement=(pos.X,pos.Y)
  def RemoveFromParent(self):
   self.removed=True
 ns['create']=lambda path,outer:Widget(path)
 start=time.monotonic()
 assert ns['_create_toast']('TEST',start)
 root_widget=st.toast_widget
 assert root_widget.vis==3 and root_widget.viewport_added
 canvas=next(w for w in records if 'CanvasPanel' in w.name)
 assert canvas.vis==3
 assert root_widget.placement[0]>=348,root_widget.placement
 ns['_dismiss_toast'](clear_queue=True)
 assert root_widget.removed
 # Refusal in native Unreal must fail closed before AddToViewport.
 records.clear()
 class RejectWidget(Widget):
  def SetVisibility(self,value):
   self.vis=value
   if 'CanvasPanel' in self.name:return False
 ns['create']=lambda path,outer:RejectWidget(path)
 st.toast_render_failed=False
 assert not ns['_create_toast']('TEST',start)
 assert st.toast_render_failed
 assert not any(w.viewport_added for w in records)
 print('PASS v5.25.0: full-subtree hit-test invisibility, no invalid popup attach, viewport clamp, menu-aware positioning')
finally:
 for key,val in old.items():
  if val is None:sys.modules.pop(key,None)
  else:sys.modules[key]=val
