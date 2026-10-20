"""Compare construction count in identical stand-ins, not native frame time."""
from pathlib import Path
import runpy,sys,json
R=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(R/'TESTS/test_arsenal_events.py'))
sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
original=ctx['u'].construct_object;results=[]
for build,path in (('R8',R/'ROLLBACK/RECONCILED_R8_SOURCE.py'),('R9',R/'SOURCE/__init__.py')):
    count=[0]
    def construct(*args,**kw):count[0]+=1;return original(*args,**kw)
    ctx['u'].construct_object=construct
    g={'__name__':'widget_budget'};exec(compile(path.read_text(encoding='utf-8'),'widget_budget_'+build,'exec'),g)
    s=g['State'];s.safe_mode=True;s.dock_mode='FULL';g['viewport']=lambda:(1920.,1080.)
    g['open_menu']()
    for page,dock in (('DASHBOARD','FULL'),('PLAYER','FULL'),('PLAYER','SIDE')):
        s.page=page;s.dock_mode=dock;count[0]=0;g['redraw']()
        assert s.draw_ok,(build,page,s.runtime_failures)
        results.append(dict(build=build,page=page,dock=dock,constructed=count[0],buttons=len(s.buttons)))
    g['close_menu']();ctx['u'].construct_object=original
report=dict(mode='Synthetic UMG construction counts; Shapes/Safe UI; not native performance',results=results)
(R/'REFERENCE/WIDGET_CONSTRUCTION_R9.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
