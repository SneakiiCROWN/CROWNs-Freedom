"""v5.25 Studio stabilisation: atomic native-frame swap & honest 22-page status.

All checks use mocks. Nothing here certifies real UE object safety or BL4 effects.
"""
from pathlib import Path
import sys,runpy
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
prior={k:sys.modules.get(k) for k in keys}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_frame_commit_test'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),str(root/'SOURCE/__init__.py'),'exec'),ns)
 st=ns['State'];ns['viewport']=lambda:(1920.,1080.)
 st.safe_mode=True;st.panel_scale=1.0;st.opened=False;st.dock_mode='FULL'
 ns['open_menu']();assert st.draw_ok and st.canvas is not None
 old=st.canvas;events=[]
 parent=st.tree.RootWidget
 original_add=parent.AddChild
 original_remove=old.RemoveFromParent
 def observed_add(child):
  events.append(('mount',child))
  result=original_add(child)
  # The real frame sizes the returned/attached CanvasPanelSlot, not the
  # detached candidate. Record the size setter directly.
  slot=child.slot
  native_size=slot.SetSize
  def observed_size(*args):
   events.append(('sized',child))
   return native_size(*args)
  slot.SetSize=observed_size
  return result
 def observed_remove():
  events.append(('retire',old))
  return original_remove()
 parent.AddChild=observed_add;old.RemoveFromParent=observed_remove
 ns['redraw']()
 assert st.draw_ok and st.canvas is not old,events
 assert len(events)>=3 and [event[0] for event in events[:3]]==['mount','sized','retire'],events
 parent.AddChild=original_add;old.RemoveFromParent=original_remove
 # Every one of the 22 advertised pages has a source capability label and
 # explicit missing live proof. None is marked game-verified by a mock.
 page_set={p for pages in ns['UI_CATEGORY_PAGES'].values() for p in pages}
 ledger=ns['PAGE_CAPABILITY_LEDGER']
 assert len(ledger)==24 and set(ledger)==page_set
 assert all(len(record)==3 and all(isinstance(t,str) and t for t in record) for record in ledger.values())
 assert not any('GAME VERIFIED' in record[0] for record in ledger.values())
 ns['show_page']('DEV')
 ns['toggle_feature_ledger']()
 assert st.feature_ledger_open and st.draw_ok
 assert 'OPEN SELECTED TOOL' in [x['name'] for x in st.buttons]
 assert 'PREVIOUS TOOL' in [x['name'] for x in st.buttons]
 visited=set()
 for _ in range(len(ledger)):
  visited.add(ns['feature_ledger_selected_page']())
  ns['feature_ledger_step'](1)
 assert visited==page_set
 assert ns['open_feature_ledger_page']() and not st.feature_ledger_open
 ns['show_page']('DEV');ns['toggle_feature_ledger']()
 assert st.feature_ledger_open
 ns['show_page']('PLAYER')
 assert not st.feature_ledger_open
 # Failure to mount a staged frame must close CROWN without leaving input
 # capture or claiming that a partially constructed frame is ready.
 assert st.opened and st.canvas is not None
 failure_parent=st.tree.RootWidget;good_add=failure_parent.AddChild
 def broken_add(child):
  raise RuntimeError('simulated native frame mount failure')
 failure_parent.AddChild=broken_add
 ns['redraw']()
 assert not st.opened and st.canvas is None and st.root is None
 assert not st.input_mode_owned and st.input_pc is None
 failure_parent.AddChild=good_add
 # Exception removing an already-mounted old frame must also close safely.
 ns['open_menu']();assert st.draw_ok
 retiring=st.canvas
 good_remove=retiring.RemoveFromParent
 def broken_remove():
  raise RuntimeError('simulated stale canvas')
 retiring.RemoveFromParent=broken_remove
 ns['redraw']()
 assert not st.opened and st.canvas is None and not st.input_mode_owned
 retiring.RemoveFromParent=good_remove
 print('PASS v5.25 frame swap commit before retire, fail-closed exception paths, 22 page capability ledger, no fabricated live status')
finally:
 for k,val in prior.items():
  if val is None:sys.modules.pop(k,None)
  else:sys.modules[k]=val
