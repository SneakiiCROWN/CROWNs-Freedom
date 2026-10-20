"""v5.18: user-selectable quick page, search prioritisation, safe persistence, UI controls."""
from pathlib import Path
import json,runpy,sys,tempfile

def run():
 root=Path(__file__).resolve().parents[1]
 ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
 names=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
 prior={k:sys.modules.get(k) for k in names}
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 try:
  ns={'__name__':'crown_v518_test'}
  exec(compile((root/'SOURCE/__init__.py').read_text(),'<source>','exec'),ns)
  check(ns,ctx)
 finally:
  for k,v in prior.items():
   if v is None:sys.modules.pop(k,None)
   else:sys.modules[k]=v

def check(ns,ctx):
 st=ns['State']
 assert ns['RELEASE_VERSION']=='5.26.0'
 assert ns['_validate_tool_pins'](['SPAWN','SPAWN','MOTION','X','FINDER','WAYPOINTS','STYLE']) == ['SPAWN','MOTION','WAYPOINTS']
 assert ns['_validate_tool_pins']('GOD MODE')==[]
 assert ns['_validate_tool_pins'](['__import__("os")',None,15])==[]
 st.opened=False; st.tool_pins=[];st.recent_tools=[];st.page='PLAYER'
 assert ns['_quick_pin_caption']()=='REFILL ACTION SKILL'
 assert ns['toggle_tool_pin']('SPAWN')
 assert ns['toggle_tool_pin']('WAYPOINTS')
 assert ns['toggle_tool_pin']('MOTION')
 assert st.tool_pins==['MOTION','WAYPOINTS','SPAWN']
 assert ns['toggle_tool_pin']('STYLE') and st.tool_pins==['STYLE','MOTION','WAYPOINTS']
 assert ns['toggle_tool_pin']('MOTION') and st.tool_pins==['STYLE','WAYPOINTS']
 assert not ns['toggle_tool_pin']('FINDER')
 assert ns['_quick_pin_caption']()=='PIN  /  APPEARANCE'
 assert ns['open_quick_pin']()
 assert st.page=='STYLE' and st.recent_tools[0]=='STYLE'
 assert ns['show_page']('WAYPOINTS')
 assert ns['show_page']('SPAWN')
 assert st.recent_tools[:3]==['SPAWN','WAYPOINTS','STYLE']
 assert not ns['show_page']('../../not-a-tool')
 st.finder_query=''
 results=ns['finder_results']()
 assert len(results)==24 and len({x[0] for x in results})==24
 assert [x[0] for x in results[:2]]==['STYLE','WAYPOINTS']
 st.finder_query='teleport'; found=ns['finder_results']()
 assert any(x[0]=='WAYPOINTS' for x in found)
 with tempfile.TemporaryDirectory() as tmp:
  from pathlib import Path
  ns['SETTINGS_DIR']=Path(tmp)
  assert ns['save_preferences']() is None
  raw=json.loads((Path(tmp)/'CROWNs_Freedom_UI.json').read_text())
  assert raw['tool_pins']==['STYLE','WAYPOINTS']
  ns['save_ui_profile'](1)
  assert st.ui_profiles['1']['tool_pins']==['STYLE','WAYPOINTS']
  st.tool_pins=[]
  assert ns['load_ui_profile'](1) and st.tool_pins==['STYLE','WAYPOINTS']
  st.tool_pins=[];ns['load_preferences']()
  assert st.tool_pins==['STYLE','WAYPOINTS']
  raw['tool_pins']=['BOGUS','BOGUS','FINDER','SPAWN','SPAWN','MOTION','WAYPOINTS','LOOT']
  (Path(tmp)/'CROWNs_Freedom_UI.json').write_text(json.dumps(raw))
  ns['load_preferences']()
  assert st.tool_pins==['SPAWN','MOTION','WAYPOINTS']
 # Actual simulated UMG menu, including pin affordance and quick bar.
 st.tool_pins=['SPAWN'];st.page='WORLD';st.recent_tools=[]
 st.safe_mode=True;st.art_mode='SHAPES';st.dock_mode='FULL'
 ns['viewport']=lambda:(1280,720)
 assert ns['open_menu']() is not False
 assert st.opened and st.draw_ok
 names=[b['name'] for b in st.buttons]
 assert 'PIN TOOL' in names and 'PIN  /  ITEM FORGE' in names and 'FIND / SEARCH' in names
 assert 'RESTORE TEMP' in names
 st.page='STYLE';ns['redraw']()
 assert st.draw_ok and st.opened
 assert any(b['name']=='PIN TOOL' for b in st.buttons)
 st.dock_mode='SIDE';ns['redraw']()
 assert st.draw_ok and any(b['name']=='QUICK' for b in st.buttons)
 assert any(b['name']=='ITEM FORGE' for b in st.buttons)
 ns['close_menu']()
 # No gameplay writes happen simply from bookmarking or searching.
 assert not any(isinstance(c,tuple) and c and c[0] in ('SpawnActor','GiveItem','ConsoleCommand') for c in ctx['pool'].calls)
 print('PASS v5.18: safe quick pins, MRU search, profile/preferences, layouts at 720p, no gameplay writes')

if __name__=='__main__':run()
