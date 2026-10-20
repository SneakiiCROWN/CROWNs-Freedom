"""Command Centre acceptance against synthetic Oak2 only, never native crash proof."""
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import runpy,sys,json,math
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
g={'__name__':'crown_command_acceptance'}
exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_source','exec'),g)
st=g['State'];st.dock_mode='FULL';st.safe_mode=True
g['open_menu']();assert st.draw_ok and st.page=='DASHBOARD'
assert len(g['STUDIO_SECTIONS'])==9
# All actual hit targets: bounds and pairwise intersections, across supported
# pages, typed editors, expanded/compact geometry and four viewport sizes.
for screen in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
 g['viewport']=lambda wh=screen:wh
 for page in ('DASHBOARD','MOTION','STYLE','SPAWN','CAPACITY','PROFILES'):
  g['show_page'](page);assert st.draw_ok,(screen,page,st.message)
  x,y,w,h,*_=st.panel_rect
  for i,a in enumerate(st.buttons):
   ax,ay,aw,ah=a['rect']
   assert x-1<=ax and ax+aw<=x+w+1 and y-1<=ay and ay+ah<=y+h+1,(screen,page,a['name'],a['rect'])
   for b in st.buttons[i+1:]:
    bx,by,bw,bh=b['rect']
    assert min(ax+aw,bx+bw)-max(ax,bx)<=1 or min(ay+ah,by+bh)-max(ay,by)<=1,(screen,page,a['name'],b['name'])
# Staging appearance does not change settings, save or rebuild on drag.
g['show_page']('STYLE');old=g['_appearance_snapshot']();builds=st.ui_rebuild_count
assert len(st.sliders)==3
g['appearance_stage']('opacity',.72);g['appearance_stage']('theme',3)
assert g['_appearance_snapshot']()==old and st.ui_rebuild_count==builds
g['appearance_apply']()
assert st.panel_opacity==.72 and st.theme_idx==3
assert st.ui_rebuild_count==builds,'Pure palette apply must not rebuild'
g['appearance_stage']('scale',1.2);g['appearance_cancel']()
assert st.panel_scale==old['scale']
# Exact typed validation; invalid input has NO callback; coarse/fine and reset
# stage values without invoking any game request.
g['show_page']('MOTION');ref=st.sliders[0];calls=[];ref.apply=lambda v:calls.append(v)
g['numeric_open'](ref)
field=SimpleNamespace(GetText=lambda:'nan')
st.numeric_widget=field
assert not g['numeric_apply']() and not calls and st.numeric_editor
st.numeric_widget=SimpleNamespace(GetText=lambda:'2.375')
assert g['numeric_apply']() and calls==[2.375]
g['numeric_open'](st.sliders[0]);value=st.numeric_editor['value']
st.numeric_widget=None;g['numeric_step'](1,True)
assert math.isclose(st.numeric_editor['value'],value+.1)
g['numeric_reset']();assert st.numeric_editor['value']==value
g['numeric_cancel']();assert st.numeric_editor is None
# Direct controller focus on real slider alters the same bounded value.
g['show_page']('STYLE');idx=next(i for i,b in enumerate(st.buttons) if b.get('slider'))
st.controller_focus=idx;before=st.sliders[0].value
g['_controller_focus_direction']('LEFT')
assert math.isclose(st.appearance_draft['opacity'],before-.01)
# Polling action requests only ONE frame at the tick boundary, keeping the
# active native registry alive until all input handling returns.
canvas=st.canvas;builds=st.ui_rebuild_count
original=g['_tick_impl']
def action(*args):
 g['show_page']('MOTION');g['redraw']();g['redraw']()
 assert st.canvas is canvas and st.ui_rebuild_count==builds
g['_tick_impl']=action;g['tick']();g['_tick_impl']=original
assert st.canvas is not canvas and st.ui_rebuild_count==builds+1
# Repeated Shapes/Auto and preset/colour changes keep bounded registries.
for i in range(60):
 g['show_page']('STYLE');g['appearance_stage']('art','AUTO' if i%2 else 'SHAPES')
 g['appearance_stage']('theme',i%len(g['THEMES']));g['appearance_apply']()
 g['show_page']('MOTION' if i%2 else 'DASHBOARD')
 assert st.draw_ok and len(st.palette_bindings)<1000 and len(st.buttons)<80,(i,st.page,st.draw_ok,len(st.palette_bindings),len(st.buttons),st.message)
# Real independent persistence round-trip, named profiles and draft isolation.
with TemporaryDirectory() as td:
 g['SETTINGS_DIR']=Path(td);g['show_page']('PROFILES')
 g['save_ui_profile'](2);g['profile_rename_open']()
 st.profile_name_widget=SimpleNamespace(GetText=lambda:'Controller Lab')
 assert g['profile_rename_apply']()
 raw=json.loads((Path(td)/'CROWNs_Freedom_UI.json').read_text())
 assert raw['profile_names']['2']=='Controller Lab' and raw['presentation_revision']==526
 st.profile_names={};g['load_preferences']();assert st.profile_names['2']=='Controller Lab'
# Three reviewed combat fields: unavailable fields never create game sliders;
# writes require local solo, exact paired readback, same-pawn ownership.
actor=ctx['pawn'];actor.DamageCauserData=SimpleNamespace(DamageDealtMultiplier=SimpleNamespace(Value=1.,BaseValue=1.),DefaultCriticalHitMultiplier=SimpleNamespace(Value=2.,BaseValue=2.))
actor.DamageState=SimpleNamespace(DamageTakenMultiplier=SimpleNamespace(Value=1.,BaseValue=1.))
ctx['mode'][0]=0
assert g['combat_tune']('OUTGOING',2.5)
assert actor.DamageCauserData.DamageDealtMultiplier.Value==2.5
assert not g['combat_tune']('OUTGOING',float('nan'))
ctx['mode'][0]=3;assert not g['combat_tune']('INCOMING',0.)
ctx['mode'][0]=0
assert g['restore_combat_tuning']()==1
assert actor.DamageCauserData.DamageDealtMultiplier.Value==1.
assert g['combat_tune']('INCOMING',.5)
actor.DamageState.DamageTakenMultiplier.Value=.75
assert g['restore_combat_tuning']()==0 and actor.DamageState.DamageTakenMultiplier.Value==.75
st.safe_mode=False;g['show_page']('COMBAT');g['combat_toggle_view']()
assert len(st.sliders)==3 and st.draw_ok
g['close_menu']();assert not st.input_mode_owned and not st.sliders and not st.palette_bindings
print('PASS Command Centre: 4-resolution hit targets; 60-cycle appearance/navigation; zero-rebuild palettes; exact/controller edits; coalesced callback rebuilds; persistence; guarded combat readback/restore')
