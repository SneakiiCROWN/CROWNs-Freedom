"""v3.4 offline UI and input acceptance tests using synthetic Oak2 objects."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys,runpy,tempfile,json,time,hashlib
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={name:sys.modules.get(name) for name in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'v34_comfort_test'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'CROWNS_v34.py','exec'),ns)
 state=ns['State']
 assert ns['ART_MOD_FILENAME']=='CROWNs_Freedom_v5_26_ECHO_Fieldcraft_R23.sdkmod'
 # SETTINGS_DIR sometimes exists in mods_base before its physical folder.
 with tempfile.TemporaryDirectory() as tmp:
  ns['SETTINGS_DIR']=Path(tmp)/'not-created-yet'
  state.theme_idx=1
  ns['save_preferences']()
  stored=ns['SETTINGS_DIR']/'CROWNs_Freedom_UI.json'
  assert stored.exists()
  assert json.loads(stored.read_text())['theme_index']==1
  state.theme_idx=4
  state.expand_theme=True
  ns['set_theme'](2)
  assert state.theme_idx==2 and not state.expand_theme
  ns['apply_comfort_preset']()
  assert state.font_scale==1.08 and state.panel_scale==1.12
  assert state.window_x is None and state.window_y is None
  assert json.loads(stored.read_text())['scale']==1.12
  # Custom text and fit limits: dynamically shrink long names, never shrink tiny names.
  small=ns['_button_caption_scale']('GO',240,True,44)
  long=ns['_button_caption_scale']('CONFIRM OVERWRITE SLOT 12 / EXPLORATION',240,True,44)
  assert 0.58<=long<small<=.82 # Larger R13 captions retain the same long-name fit bound.
  # Repeat should work after a hold delay, but A requires fresh edge and no
  # mixed input or chord can trigger it.
  state.opened=True;state.controller_enabled=True;state.controller_mode=True
  state.controller_open_block_until=0.0
  state.controller_last_keys={};state.controller_repeat_key=None
  state.buttons=[{'name':str(i),'disabled':False,'run':lambda:None,
                  'rect':(100.,100.+70*i,200.,40.)} for i in range(4)]
  state.controller_focus=0;state.controller_focus_outline=[]
  keys=set()
  ctx['pc'].IsInputKeyDown=lambda key:getattr(key,'KeyName',key) in keys
  keys.add('Gamepad_DPad_Down')
  ns['controller_ui_tick'](ctx['pc'],100.)
  assert state.controller_focus==1
  ns['controller_ui_tick'](ctx['pc'],100.20)
  assert state.controller_focus==1
  ns['controller_ui_tick'](ctx['pc'],100.46)
  assert state.controller_focus==2
  ns['controller_ui_tick'](ctx['pc'],100.61)
  assert state.controller_focus==3
  keys.add('Gamepad_FaceButton_Bottom')
  called=[]
  state.buttons[3]['run']=lambda:called.append('bad')
  ns['controller_ui_tick'](ctx['pc'],100.85)
  assert called==[]
  keys.clear();state.controller_last_keys={}
  ns['controller_ui_tick'](ctx['pc'],101.0)
  assert state.controller_repeat_key is None
  # Every page at each sampled viewport/scale fits its buttons within panel.
  state.opened=False
  state.controller_mode=False
  ns['viewport']=lambda:(1280.,720.)
  ns['open_menu']()
  assert state.opened and state.root is not None
  for wh in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
   ns['viewport']=lambda wh=wh:wh
   for zoom in (.72,1.12,2.0):
    state.panel_scale=zoom
    state.font_scale=1.08
    for page in ('PLAYER','MOTION','COMBAT','LOOT','WORLD','PARTY','SPAWN','EVENTS',
                 'CONTENT','PRESETS','STYLE','DEV','TROPHIES','WAYPOINTS','PROFILES',
                 'GEAR','DISPLAY','GUIDE'):
     state.help_open=False;state.style_audio_open=False;state.diag_open=False;state.activity_open=False
     state.page=page;state.opened=True
     state.controller_mode=False
     ns['redraw']()
     assert state.draw_ok,(wh,zoom,page)
     px,py,pw,ph,vw,vh=state.panel_rect
     assert px>=0 and py>=0 and px+pw<=vw and py+ph<=vh,(wh,zoom,page,'panel')
     for entry in state.buttons:
      x,y,w,h=entry['rect']
      assert px-2<=x and py<=y and x+w<=px+pw+2 and y+h<=py+ph,(wh,zoom,page,entry['name'])
     # Every click target is isolated: no two buttons should compete for a tap.
     for i,a in enumerate(state.buttons):
      x1,y1,w1,h1=a['rect']
      for b in state.buttons[i+1:]:
       x2,y2,w2,h2=b['rect']
       overlap=(min(x1+w1,x2+w2)-max(x1,x2)>1 and min(y1+h1,y2+h2)-max(y1,y2)>1)
       assert not overlap,(wh,zoom,page,a['name'],b['name'])
  # The easy-to-miss nested editors/dropdowns/help screens also need space.
  # They use different button counts and native editable fields.
  for wh in ((854.,480.),(1920.,1080.)):
   ns['viewport']=lambda wh=wh:wh
   for zoom in (.72,2.0):
    state.panel_scale=zoom
    for page,flag,value in (('SPAWN','spawn_view','SEARCH'),('SPAWN','spawn_view','LEVEL'),
                            ('SPAWN','spawn_view','TOOLS'),('STYLE','expand_theme',True),
                            ('STYLE','style_audio_open',True),('DEV','diag_open',True),
                            ('DEV','activity_open',True),('WAYPOINTS','waypoint_mode','SAVE')):
     state.page=page;state.opened=True;state.help_open=False
     state.expand_theme=False;state.style_audio_open=False;state.diag_open=False;state.activity_open=False
     setattr(state,flag,value)
     ns['redraw']()
     assert state.draw_ok,(wh,zoom,page,flag)
     x0,y0,pw,ph,*_=state.panel_rect
     for i,a in enumerate(state.buttons):
      x1,y1,w1,h1=a['rect']
      assert y1+h1<y0+ph,(wh,zoom,page,flag,a['name'])
      for b in state.buttons[i+1:]:
       x2,y2,w2,h2=b['rect']
       assert not (min(x1+w1,x2+w2)-max(x1,x2)>1 and
                   min(y1+h1,y2+h2)-max(y1,y2)>1),(wh,zoom,page,flag,a['name'],b['name'])
  state.expand_theme=False;state.style_audio_open=False;state.diag_open=False;state.activity_open=False
  state.spawn_view='BROWSE';state.waypoint_mode='TRAVEL'
  # Escape exits native overlay safely; no other actions.
  state.opened=False;state.panel_scale=1.
  state.controller_mode=False
  ns['viewport']=lambda:(1920.,1080.)
  ns['open_menu']()
  assert state.opened
  ns['key_down']=lambda pc,key:key=='Escape'
  state.last_poll=0;state.session_last_check=time.monotonic()
  ns['tick']()
  assert not state.opened and state.input_pc is None
  # A redraw should never retain an index pointing to a different action.
  ns['key_down']=lambda pc,key:False
  ns['open_menu']()
  assert state.opened
  state.controller_mode=True
  state.controller_focus=next(i for i,b in enumerate(state.buttons) if 'RESTORE TEMP' in b['name'])
  target_name=state.buttons[state.controller_focus]['name']
  ns['redraw']()
  assert state.buttons[state.controller_focus]['name']==target_name
  ns['close_menu']()
 # Already-bundled CC0 PNG/audio must remain verified; no new dependencies.
 for name,digest in ns['ART_SHA256'].items():
  path=root/'CROWN_CC0_ASSETS'/ns['ART_FILES'][name]
  assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,name
 assert 'SetAchievement(' not in (root/'SOURCE/__init__.py').read_text()
 print('PASS v3.4: settings directory, dropdown, comfort preset, dynamic captions, held D-pad, anti-accidental-A, ESC, focus identity, 248 geometry states with no button collisions, 12 verified art records')
finally:
 for name,value in old.items():
  if value is None:sys.modules.pop(name,None)
  else:sys.modules[name]=value
