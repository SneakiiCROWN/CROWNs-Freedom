"""v5.6 weekly rotation age, bookmarked same-map travel and DLC/art checks.
All game interfaces are mocked. Does not validate player arrival in live BL4.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import runpy,sys,hashlib
r=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(r/'TESTS/test_arsenal_events.py'))
keys=('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')
old={k:sys.modules.get(k) for k in keys}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'], 'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crown_v56_weekly'}
 exec(compile((r/'SOURCE/__init__.py').read_text(),'crown_v56_source','exec'),ns)
 st=ns['State'];weekly=ns['_weekly_snapshot']
 assert weekly(datetime(2026,10,14,8,tzinfo=timezone.utc))['maurice_region']=='Terminus Range'
 assert weekly(datetime(2026,10,7,23,59,tzinfo=timezone.utc)) is None
 assert weekly(datetime(2026,10,15,16,59,tzinfo=timezone.utc)) is not None
 assert weekly(datetime(2026,10,15,17,tzinfo=timezone.utc)) is None
 assert weekly(datetime(2027,10,14,tzinfo=timezone.utc)) is None
 assert weekly(datetime(2026,10,14,8)) is None
 assert ns['WEEKLY_SNAPSHOT']['encore_boss']=='Mimicron'
 assert ns['WEEKLY_SNAPSHOT']['wildcard']=='Savage Salvage'
 assert len(ns['UI_CATEGORY_PAGES'])==6
 assert 'WEEKLY' in ns['UI_CATEGORY_PAGES']['WORLD']
 assert len({x for p in ns['UI_CATEGORY_PAGES'].values() for x in p})==24
 assert st.maurice_slot_week==''
 st.checkpoints[4]=('valid map',(123.0,456.0,789.0))
 st.maurice_slot_week='2026-10-01'   # stale tag
 ns['_weekly_snapshot']=lambda now=None:ns['WEEKLY_SNAPSHOT']
 ns['map_tag']=lambda:'valid map'
 calls=[]
 ns['bookmark_go']=lambda index:calls.append(index) or True
 assert ns['weekly_go_vendor']() is False and not calls
 st.maurice_slot_week='2026-10-08'
 assert ns['weekly_go_vendor']() and calls==[4]
 ns['map_tag']=lambda:'different map'
 assert ns['weekly_go_vendor']() is False and calls==[4]
 # After expiry, even the previously tagged vendor anchor must not be offered.
 ns['_weekly_snapshot']=lambda now=None:None
 ns['map_tag']=lambda:'valid map'
 assert ns['weekly_go_vendor']() is False and calls==[4]
 assert ns['weekly_save_vendor']() is False
 assert ns['weekly_summary']() is False
 assert all(ns['weekly_dlc_info'](i) for i in range(4))
 assert not ns['weekly_dlc_info'](99)
 s=(r/'SOURCE/__init__.py').read_text()
 assert '#07090C' in s and '#101821' in s
 asset=r/'CROWN_CC0_ASSETS/BLACK_MARKET_SKIN.png'
 raw=asset.read_bytes()
 assert ns['_verify_png_bytes']('BLACK_MARKET_SKIN',raw)
 assert len(ns['ART_FILES'])==67
 assert ns['RELEASE_VERSION']=='5.26.0'
 print('PASS v5.6: UTC expiry, safe weekly vendor slot, read-only DLC, 19 pages, native ink skin')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
