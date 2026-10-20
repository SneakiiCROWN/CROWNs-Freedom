"""v5.25.0 HUD native safety and read-only advanced capability probe.
These tests use a mocked Unreal renderer; they do not claim live BL4 input or rendering validation.
"""
from pathlib import Path
import runpy,sys,math
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v594_hud'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_v594_source','exec'),ns)
 st=ns['State']
 assert ns['RELEASE_VERSION']=='5.26.0'
 assert len(ns['HUD_ANCHORS'])==3
 for w,h in ((2560,1440),(1920,1080),(1280,720),(854,480),(320,240)):
  for anchor in ns['HUD_ANCHORS']:
   x,y,ww,hh=ns['_hud_rect']((w,h),anchor)
   assert x>=0 and y>=0 and x+ww<=w and y+hh<=h,(w,h,anchor,x,y,ww,hh)
 # New HUD must refuse input interception before mounting.
 records=[]
 class Widget(ctx['W']):
  def __init__(self,path):
   super().__init__(path)
   self.vis=None;self.viewport_added=False;self.removed=False;self.position=None;self.last_text=None
   records.append(self)
  def SetVisibility(self,v):self.vis=v
  def AddToViewport(self,*args):
   assert self.vis==3,('HUD root must ignore input for subtree',self.vis)
   self.viewport_added=True
  def SetPositionInViewport(self,p,*args):self.position=(p.X,p.Y)
  def RemoveFromParent(self):self.removed=True
  def SetText(self,t):self.last_text=str(t)
 ns['create']=lambda path,outer:Widget(path)
 ns['viewport']=lambda:(1920,1080)
 assert ns['toggle_hud']()
 assert st.hud_visible
 ui=st.hud_widget
 assert ui.vis==3 and ui.viewport_added
 canvas=next(w for w in records if 'CanvasPanel' in w.name)
 assert canvas.vis==3
 assert 'GOD ' in st.hud_label.last_text and 'NOCLIP' in st.hud_label.last_text
 first=st.hud_last_summary
 assert ns['update_hud']() and st.hud_last_summary==first
 x_before=ui.position
 assert ns['cycle_hud_position']()=='LEFT_MIDDLE'
 assert ui.position!=x_before
 assert ns['cycle_hud_position']()=='RIGHT_MIDDLE'
 assert ns['cycle_hud_position']()=='TOP_CENTRE'
 ns['_invalidate_pending_session']('mocked world change')
 assert not st.hud_visible and ui.removed
 # Failure to set noninteractivity MUST prevent attaching a HUD.
 records.clear()
 class RejectWidget(Widget):
  def SetVisibility(self,v):
   self.vis=v
   if 'CanvasPanel' in self.name:return False
 ns['create']=lambda path,outer:RejectWidget(path)
 assert ns['toggle_hud']() is False and not st.hud_visible
 assert not any(w.viewport_added for w in records)
 # Advanced feature probe only inspects classes and actor attributes; never writes.
 before_calls=len(ctx['pool'].calls)
 result=ns['advanced_feature_audit']()
 assert set(result)=={'character','weapon_parts','vehicle_spawn','boss_spawn'}
 assert result['weapon_parts'].startswith('read_only_refs:')
 assert result['boss_spawn'].startswith('read_only_refs:')
 assert len(ctx['pool'].calls)==before_calls
 assert 'ADVANCED' in st.message and 'no operation sent' in st.message
 print('PASS v5.25.0 HUD: child hit-test safety, placement, failure cleanup, transition cleanup, read-only capability audit')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
