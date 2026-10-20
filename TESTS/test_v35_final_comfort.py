"""v3.5 acceptance: comfort first run, native editing, Enter, panel/navigation geometry."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys,runpy,time
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crowns_final_comfort_test'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),str(root/'SOURCE/__init__.py'),'exec'),ns)
 st=ns['State']
 assert abs(st.panel_scale-1.14)<.01 and abs(st.panel_opacity-.91)<.01
 assert abs(st.font_scale-1.06)<.01 and not st.compact
 assert ns['ART_MOD_FILENAME']=='CROWNs_Freedom_v5_26_ECHO_Fieldcraft_R23.sdkmod'
 # A redraw while an editor is open must retain the unsaved draft.
 ns['viewport']=lambda:(1920.,1080.)
 ns['open_menu']();assert st.opened and st.draw_ok
 st.page='SPAWN';st.nav_group='MORE';st.spawn_view='SEARCH'
 ns['redraw']();assert st.draw_ok
 st.search_widget=NS(GetText=lambda:'laser rifle')
 ns['redraw']()
 assert st.spawn_search_draft=='laser rifle',st.spawn_search_draft
 assert st.search_widget is not None
 st.spawn_view='LEVEL';st.level_draft='40'
 ns['redraw']();st.level_widget=NS(GetText=lambda:'87')
 ns['redraw']()
 assert st.level_draft=='87'
 # Enter applies only a safe editor; it cannot activate a spawn action.
 st.spawn_view='SEARCH';st.search_widget=NS(GetText=lambda:'shotgun')
 st.spawn_pending=None
 st.last_poll=0;st.session_last_check=time.monotonic()
 ns['key_down']=lambda pc,key:key=='Enter'
 ns['tick']()
 assert st.spawn_search=='shotgun' and st.spawn_view=='BROWSE'
 assert st.spawn_pending is None and st.spawn_requests==0
 ns['key_down']=lambda pc,key:False
 ns['tick']()
 # Changing the panel look must not override existing saved preferences.
 st.theme_idx=1;st.panel_scale=1.35;st.font_scale=1.14;st.panel_opacity=.92
 ns['redraw']()
 assert (st.theme_idx,st.panel_scale,st.font_scale,st.panel_opacity)==(1,1.35,1.14,.92)
 # Small and big native hitboxes stay unique (including active search and help).
 for display in ((854,480),(1280,720),(1920,1080),(2560,1440)):
  ns['viewport']=lambda display=display:display
  for scale in (.72,1.06,2.0):
   st.panel_scale=scale
   for page,view in (('PLAYER','BROWSE'),('STYLE','BROWSE'),('SPAWN','SEARCH'),('SPAWN','LEVEL'),('WAYPOINTS','BROWSE')):
    st.page=page;st.spawn_view=view;st.style_audio_open=False;st.help_open=False
    ns['redraw']();assert st.draw_ok,(display,scale,page,view)
    x,y,w,h,*_=st.panel_rect
    for i,item in enumerate(st.buttons):
     px,py,pw,ph=item['rect']
     assert px>=x-3 and py>=y-3 and px+pw<=x+w+3 and py+ph<=y+h+3
     for later in st.buttons[i+1:]:
      qx,qy,qw,qh=later['rect']
      assert not (min(px+pw,qx+qw)-max(px,qx)>1 and min(py+ph,qy+qh)-max(py,qy)>1),(page,item['name'],later['name'])
 ns['close_menu']()
 print('PASS v3.5: readable defaults, retained text drafts, safe Enter, existing settings, 60 UI scenarios, non-overlapping click areas')
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
