"""v2.5 Forge safe preflight, readable live-state flags and privacy-safe stage codes.
Runs with fake SDK objects: NEVER interpreted as proof of actual in-game drops.
"""
from pathlib import Path
from types import SimpleNamespace
import runpy,sys,tempfile,json
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
   'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v25_test'}
 exec(compile((root/'SOURCE/__init__.py').read_text(encoding='utf-8'),'crown_v25','exec'),ns)
 s=ns['State'];pool=ctx['pool'];pool.calls.clear();ctx['mode'][0]=0
 s.spawn_search='';s.spawn_pool_idx=0;s.spawn_category_idx=0;s.spawn_page=0
 s.spawn_pending=None;s.anti_spam_until=0
 assert ns['forge_preflight'](),s.forge_stage
 assert s.forge_stage=='READY_NOT_SPAWNED'
 assert not pool.calls,'Preflight must be read-only, no spawned items'
 assert s.spawn_pending is None,'Preflight must never arm a request'
 assert not ns['spawn_request']()
 assert s.forge_stage=='ARMED_AWAITING_CONFIRM'
 assert not ns['forge_preflight']() is False
 assert s.spawn_pending is None,'Preflight cancels stale confirmations'
 assert not pool.calls
 ctx['mode'][0]=3
 assert not ns['forge_preflight']()
 assert s.forge_stage=='BLOCKED_NOT_LOCAL_HOST' and not pool.calls
 ctx['mode'][0]=0
 ns['pawn']=lambda:SimpleNamespace(_get_address=lambda:42)
 assert not ns['forge_preflight']()
 assert s.forge_stage=='POSITION_API_UNAVAILABLE'
 assert not pool.calls
 ns['pawn']=lambda:ctx['pawn']
 assert ns['forge_preflight']()
 assert s.forge_stage=='READY_NOT_SPAWNED'
 # Safety badge: destructive combat and gift controls need explicit warnings.
 ns['open_menu']()
 orig_chip=ns['chip'];data=[]
 def capture_chip(parent,label,*args,**kw):
  data.append((str(label),bool(kw.get('danger',False))))
  return orig_chip(parent,label,*args,**kw)
 ns['chip']=capture_chip
 for page in ('COMBAT','LOOT','SPAWN'):
  data.clear();ns['show_page'](page)
  assert ('SAVE: RISK',True) in data,(page,data)
 s.party_mode='GIFTS';data.clear();ns['show_page']('PARTY')
 assert ('SAVE: RISK',True) in data,data
 s.party_mode='BOOSTS';data.clear();ns['show_page']('PARTY')
 assert ('SAVE: TEMP',False) in data,data
 # WORLD selected action and motion speed are visual, not another write.
 s.speed=4.0;ns['show_page']('WORLD')
 speed=next(r for r in s.sliders if r.name=='WORLD SPEED')
 assert speed.value==4.0 and s.draw_ok
 # Confirm user can export stage without leaking actor locations or player names.
 with tempfile.TemporaryDirectory() as d:
  ns['SETTINGS_DIR']=Path(d)
  ns['log']('Private teammate Alice at XYZ 155, 300, 800')
  assert ns['export_qa_report']()
  report=(Path(d)/'CROWNs_Freedom_QA_Report.json').read_text('utf-8')
  assert 'READY_NOT_SPAWNED' in report
  assert 'Alice' not in report and 'XYZ' not in report
  assert json.loads(report)['version']=='5.26.0'
 # Tiny display still renders all pages after telemetry addition.
 for wh in ((2560,1440),(1920,1080),(1280,720),(854,480)):
  ns['viewport']=lambda w=wh:w
  for page in ('PLAYER','MOTION','WORLD','SPAWN','PARTY','COMBAT'):
   ns['show_page'](page)
   assert s.draw_ok,(page,wh)
 ns['close_menu']()
 print('PASS v2.5: preflight no game mutation, pending cancellation, safe authority/position fail, state chips, private failure stage, four viewports')
finally:
 for name,item in old.items():
  if item is None:sys.modules.pop(name,None)
  else:sys.modules[name]=item
