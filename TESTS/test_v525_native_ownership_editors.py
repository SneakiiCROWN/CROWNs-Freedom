"""Regression: native controller identity and editable draft stability.
This only runs against synthetic SDK objects; not a BL4 game certification.
"""
import runpy,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
prior={k:sys.modules.get(k) for k in keys}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'], 'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_ownership_editor_test'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),str(root/'SOURCE/__init__.py'),'exec'),ns)
 st=ns['State']
 same=ns['same_unreal_object']
 class Unknown:
  def _get_address(self):return None
 class Zero:
  def _get_address(self):return 0
 class Known:
  def __init__(self,n):self.n=n
  def _get_address(self):return self.n
 a,b=Unknown(),Unknown()
 assert same(a,a) and not same(a,b) and not same(Zero(),Zero())
 assert same(Known(1000),Known(1000)) and not same(Known(1000),Known(2000))
 assert not same(None,None) and not same(a,None)
 class Unavailable:pass
 assert not same(Unavailable(),Unavailable())
 # An unresolvable replacement PlayerController must not be modified by
 # release_input even though both native addresses are None.
 st.input_pc=a;st.input_saved={'bShowMouseCursor':False};st.input_mode_owned=True
 st.input_move_ignored_original=False
 ns['get_pc']=lambda **kw:b
 ns['release_input']()
 assert st.input_pc is None and not st.input_mode_owned
 assert st.input_mode_used=='STALE PC / NO NATIVE RESTORE'
 # In a genuine redraw, the old text input can be more recent than the
 # staged value. Forge +/- must read it then render the NEW stepped text.
 ns['get_pc']=lambda **kw:ctx['pc']
 ns['open_menu']();assert st.opened
 ns['show_page']('SPAWN')
 st.spawn_view='LEVEL';st.level_draft='40';st.spawn_level=40
 st.level_widget=type('MockEdit',(),{'GetText':lambda _:'51'})()
 assert ns['forge_controller_step'](1)
 assert st.level_draft=='52'
 assert st.spawn_pending is None
 assert st.level_widget is not None
 assert st.level_draft=='52'  # generated mock widget does not implement GetText
 # No Forge operation happened just by editing the value.
 assert st.spawn_level==40
 assert ns['forge_controller_commit']() and st.spawn_level==52
 ns['show_page']('CAPACITY')
 st.capacity_view='EDIT';st.capacity_mode='BACKPACK'
 st.capacity_draft=90;st.capacity_edit_original=90
 st.capacity_text_draft='90';st.capacity_input=type('MockEdit',(),{'GetText':lambda _:'120'})()
 assert ns['capacity_step'](5)
 assert st.capacity_draft==125 and st.capacity_text_draft=='125'
 assert st.capacity_drafts['BACKPACK']==125
 assert st.capacity_confirm is None
 # CANCEL must roll back controller's staged changes; no backend writes.
 ns['capacity_edit_cancel']()
 assert st.capacity_draft==90 and st.capacity_drafts['BACKPACK']==90
 assert st.capacity_view=='BROWSE'
 # Failed critical canvas SetSize must NOT replace prior frame or keep UIOnly.
 old=st.canvas
 orig=st.tree.RootWidget.AddChild
 def reject_size(child):
  result=orig(child)
  child.slot.SetSize=lambda *_:False
  return result
 st.tree.RootWidget.AddChild=reject_size
 ns['redraw']()
 assert not st.opened and st.root is None and st.canvas is None and not st.input_mode_owned
 print('PASS no unknown-controller identity alias, staged Forge/Capacity editing, staged-canvas failure cleanup')
finally:
 for k,val in prior.items():
  if val is None:sys.modules.pop(k,None)
  else:sys.modules[k]=val
