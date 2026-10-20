import ast, json, sys, types, traceback
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

source_file=(Path(__file__).resolve().parent.parent/'SOURCE'/'__init__.py')
src=source_file.read_text();ast.parse(src)
class Widget:
 def __init__(self,cls='widget'):self.cls=cls;self.children=[];self.slot=None;self.Text='';self.WidgetTree=None;self.pressed=False
 def AddChild(self,c):self.children.append(c);c.slot=Widget('Slot')
 def SetText(self,value):self.Text=str(value)
 def IsPressed(self):return self.pressed
 def __getattr__(self,k):
  if k.startswith(('Set','Remove','Force','Add','Clear','Reset')):return lambda *args,**kwargs:None
  raise AttributeError(k)
class Pawn:
 def __init__(self,label):
  self.label=label;self.addr=id(self);self.loc=(120.,220.,320.);self.bCanBeDamaged=True;self.bActorEnableCollision=True;self.OakCharacterMovement=SimpleNamespace(MovementMode=1,SetMovementMode=self.move,MinAnalogWalkSpeed=600.,MaxWalkSpeed=600.,JumpZVelocity=840.,GravityScale=1.);self.mode=1
 def _get_address(self):return self.addr
 def HasAuthority(self):return True
 def move(self,a,b):self.mode=a
 def K2_GetActorLocation(self):return SimpleNamespace(X=self.loc[0],Y=self.loc[1],Z=self.loc[2])
 def K2_SetActorLocation(self,new,sweep,ignored,teleport):
  self.loc=(new.X,new.Y,new.Z)
  return True
class PS:
 def __init__(self,name,pawn):self.name=name;self.pawn=pawn;self.addr=id(self)
 def _get_address(self):return self.addr
 def GetPlayerName(self):return self.name
 def GetPawn(self):return self.pawn
class PC:
 def __init__(self,ps):
  self.PlayerState=ps;self.OakCharacter=ps.pawn;self.player=SimpleNamespace(BaseFOV=100,VehicleFOV=100)
  self.bShowMouseCursor=False;self.bEnableMouseOverEvents=False;self.bEnableClickEvents=False;self.bEnableTouchEvents=False;self.bBlockInput=False;self.prefs=[]
 def HasAuthority(self):return True
 def _get_address(self):return id(self)
 def ServerActivateDevPerk(self,num):self.prefs.append(num)
 def IsInputKeyDown(self,key):return False
hostpawn=Pawn('host');friendpawn=Pawn('guest');hostps=PS('CROWN',hostpawn);friendps=PS('Fil',friendpawn);pc=PC(hostps)
role=[2]
world=SimpleNamespace(GameState=SimpleNamespace(PlayerArray=[hostps,friendps]),GetNetMode=lambda:role[0],TimeDilation=1.0,GetName=lambda:'Providence')
world.PersistentLevel=SimpleNamespace(WorldSettings=world)
ENGINE=SimpleNamespace(GameViewport=SimpleNamespace(World=world))
mods=types.ModuleType('mods_base');mods.build_mod=lambda **kw:SimpleNamespace(**kw);mods.get_pc=lambda **kw:pc;mods.keybind=lambda *args,**kw:lambda fn:fn;mods.ENGINE=ENGINE
unreal=types.ModuleType('unrealsdk.unreal');unreal.IGNORE_STRUCT=object()
hooks=types.ModuleType('unrealsdk.hooks');hooks.Type=SimpleNamespace(POST='POST');hooks.add_hook=lambda *args:None;hooks.remove_hook=lambda *args:None
u=types.ModuleType('unrealsdk');u.logging=SimpleNamespace(info=lambda *a:None);u.make_struct=lambda name,**kw:SimpleNamespace(**kw);u.find_object=lambda name,path:SimpleNamespace(ClassDefaultObject=SimpleNamespace(GetViewportScale=lambda pc:1.0,GetViewportSize=lambda pc:SimpleNamespace(X=2560,Y=1440),SetInputMode_UIOnlyEx=lambda *args:None,SetInputMode_GameAndUIEx=lambda *args:None,SetInputMode_GameOnly=lambda *args:None,SetFocusToGameViewport=lambda *args:None));u.construct_object=lambda cls,outer:Widget(cls);u.hooks=hooks
u.find_class=lambda name:SimpleNamespace(ClassDefaultObject=SimpleNamespace(RefillCooldown=lambda *a:None,LockTargetableByAI=lambda *a:None))
old={k:sys.modules.get(k) for k in ('unrealsdk','unrealsdk.hooks','unrealsdk.unreal','mods_base')}
try:
 sys.modules.update({'unrealsdk':u,'unrealsdk.hooks':hooks,'unrealsdk.unreal':unreal,'mods_base':mods})
 ns={'__name__':'crown_test'};exec(compile(src,'crown.py','exec'),ns)
 assert ns['session_role']()=='HOST'
 rows=ns['party_entries']();assert len(rows)==2 and rows[0]['local'] and not rows[1]['local']
 assert ns['remote_target_god']() is None and friendpawn.bCanBeDamaged # blocked until consent
 ns['refresh_party']();ns['select_party'](1);ns['enable_party_changes']();ns['remote_target_god']()
 assert friendpawn.bCanBeDamaged is False and len(ns['State'].remote_originals)==1
 ns['remote_target_god']();assert friendpawn.bCanBeDamaged is True
 ns['remote_target_god']();ns['restore']();assert friendpawn.bCanBeDamaged is True
 ns['refresh_party']();ns['select_party'](1);ns['enable_party_changes']()
 ns['remote_target_god'](); assert friendpawn.bCanBeDamaged is False
 role[0]=3
 ns['remote_target_god']();assert friendpawn.bCanBeDamaged is False # guest cannot change remote
 ns['restore'](); assert friendpawn.bCanBeDamaged is True # host no longer authoritative but synthetic still write
 assert ns['session_role']()=='GUEST'
 ns['set_world_time'](3);assert world.TimeDilation==1.0 # blocked co-op as guest
 role[0]=2
 ns['refresh_party']();ns['enable_party_changes']();ns['set_world_time'](2.0);assert world.TimeDilation==2.0
 ns['select_party'](1);ns['refill_friend_skill']()
 ns['restore']();assert world.TimeDilation==1.0
 saved_local=pc.PlayerState
 pc.PlayerState=None
 ns['party_selected']=friendps._get_address();ns['party_approved']=True
 ns['remote_target_god']();assert friendpawn.bCanBeDamaged is True
 pc.PlayerState=saved_local
 # v1.0 movement writes actual reflected floats, not WrappedStructs.
 assert ns['tune_motion']('speed',1.5)
 assert hostpawn.OakCharacterMovement.MinAnalogWalkSpeed==900.0
 assert ns['tune_motion']('speed',2.)
 assert hostpawn.OakCharacterMovement.MinAnalogWalkSpeed==1200.0  # original not multiplied twice
 assert ns['tune_motion']('jump',1.5)
 assert hostpawn.OakCharacterMovement.JumpZVelocity==1260.
 assert ns['tune_motion']('gravity',.5)
 assert hostpawn.OakCharacterMovement.GravityScale==.5
 assert not ns['tune_motion']('gravity',float('nan'))
 assert hostpawn.OakCharacterMovement.GravityScale==.5
 ns['restore_motion']()
 assert hostpawn.OakCharacterMovement.MinAnalogWalkSpeed==600.
 assert hostpawn.OakCharacterMovement.JumpZVelocity==840.
 assert hostpawn.OakCharacterMovement.GravityScale==1.

 # Bookmarks are local and cannot cross maps.
 ns['bookmark_save'](1)
 hostpawn.loc=(800.,800.,900.)
 ns['bookmark_go'](1)
 assert hostpawn.loc==(120.,220.,320.)
 ns['bookmark_back']()
 assert hostpawn.loc==(800.,800.,900.)
 old_get_name=world.GetName
 world.GetName=lambda:'a_different_map'
 ns['bookmark_go'](1)
 assert hostpawn.loc==(800.,800.,900.)
 world.GetName=old_get_name

 ns['refresh_party']();ns['select_party'](1);ns['enable_party_changes']()
 ns['cycle_party_mode']();assert ns['State'].party_mode=='TRAVEL'
 friendpawn.loc=(500.,400.,300.)
 ns['jump_to_friend']();assert hostpawn.loc==friendpawn.loc
 hostpawn.loc=(700.,600.,500.)
 ns['bring_friend']();assert friendpawn.loc==(500.,400.,300.) # first press confirmation only
 ns['bring_friend']();assert friendpawn.loc==hostpawn.loc
 ns['enable_party_changes']()
 friendpawn.loc=(111.,222.,333.)
 ns['bring_friend']();assert friendpawn.loc==(111.,222.,333.) # consent disabled
 ns['State'].party_mode='BOOSTS'
 # Change in party roster automatically revokes host acknowledgement.
 ns['refresh_party']();ns['select_party'](1);ns['enable_party_changes']()
 assert ns['party_permission_ok']()
 third=Pawn('newfriend'); thirdps=PS('NewFriend',third)
 world.GameState.PlayerArray.append(thirdps)
 assert ns['party_permission_ok']() is False
 assert not ns['State'].party_approved
 world.GameState.PlayerArray.pop()
 ns['refresh_party']()

 # Wrong Unreal type must fail closed (no WrappedStruct-to-float crash).
 mov=hostpawn.OakCharacterMovement
 speed1,speed2=mov.MinAnalogWalkSpeed,mov.MaxWalkSpeed
 mov.MinAnalogWalkSpeed=object();mov.MaxWalkSpeed=object()
 assert ns['tune_motion']('speed',2) is False
 mov.MinAnalogWalkSpeed, mov.MaxWalkSpeed=speed1,speed2

 # Stale character wrappers should never be mutated during restore.
 ns['set_god'](True)
 replacement=Pawn('newpawn')
 oldp=pc.OakCharacter
 pc.OakCharacter=replacement
 ns['restore']()
 assert replacement.bCanBeDamaged is True
 pc.OakCharacter=oldp
 oldp.bCanBeDamaged=True  # simulate game reload

 # Native ribbon is optional and does not use a camera hook.
 ns['toggle_hud']();assert ns['State'].hud_visible
 ns['update_hud']();assert ns['State'].hud_label is not None
 ns['hide_hud']();assert not ns['State'].hud_visible

 for size in ((2560,1440),(1920,1080),(1280,720),(854,480)):
  ns['viewport']=lambda s=size:s
  ns['open_menu']();assert ns['State'].opened, ns['State'].message
  for page in ('PLAYER','MOTION','COMBAT','LOOT','WORLD','PARTY','SPAWN','EVENTS','CONTENT','PRESETS','STYLE','DEV'):
   ns['show_page'](page)
   assert ns['State'].draw_ok and len(ns['State'].buttons)>6,(size,page)
  # Geometry acceptance: actionable page widgets must not overlap footer.
  captured=[]
  native_btn=ns['btn']
  def observe_btn(parent,cap,x,y,w,h,fn,*args,**kwargs):
   captured.append((cap,float(x),float(y),float(w),float(h)))
   return native_btn(parent,cap,x,y,w,h,fn,*args,**kwargs)
  ns['btn']=observe_btn
  for expanded in (False,True):
   ns['State'].expand_theme=expanded
   captured.clear()
   ns['show_page']('STYLE')
   footer=[(cap,y) for cap,x,y,w,h in captured if cap=='RESTORE TEMP']
   assert footer, (size,'missing footer')
   foot_y=footer[-1][1]
   names=('THEME:','RESET POSITION','TEXT -','TEXT +','COMPACT','RESET UI','SANCTUARY SCRAP','DAHL TERMINAL',"EARL'S BACKROOM",'VAULT STEEL','CRIMSON DUST')
   for cap,x,y,w,h in captured:
    if cap.startswith('THEME:') or cap in names:
     assert y+h <= foot_y-2.0, (size,expanded,cap,y,h,foot_y)
  ns['btn']=native_btn
  ns['State'].expand_theme=False
  # UI: two native sliders should be present on STYLE, with live values.
  ns['show_page']('STYLE')
  assert len(ns['State'].sliders)==3,(size,len(ns['State'].sliders))
  slider=ns['State'].sliders[0]
  slider.widget.GetValue=lambda:.74
  ns['State'].last_poll=0
  ns['tick']()
  assert abs(ns['State'].appearance_draft['opacity']-.74)<.001
  ns['appearance_apply']()
  assert abs(ns['State'].panel_opacity-.74)<.001
  ns['show_page']('STYLE')
  original_theme=ns['State'].theme_idx
  ns['appearance_cycle']('theme')
  assert ns['State'].theme_idx==original_theme and len(ns['State'].sliders)==3
  ns['appearance_cancel']()
  # Move the panel using the cursor and commit via left-click.
  coords=[(400.,250.)]; click=[False]
  pc.GetMousePosition=lambda: coords[0]
  pc.IsInputKeyDown=lambda key: click[0] if getattr(key,'KeyName',key)=='LeftMouseButton' else False
  ns['move_panel']()
  assert ns['State'].drag_armed
  coords[0]=(480.,295.)
  ns['State'].last_poll=0
  ns['tick']()
  assert ns['State'].drag_last is not None
  ns['State'].drag_deadline=0
  click[0]=True
  ns['State'].last_poll=0
  ns['tick']()
  assert not ns['State'].drag_armed and ns['State'].window_x is not None
  ns['reset_placement']()
  assert ns['State'].window_x is None
  pc.IsInputKeyDown=lambda key:False
  ns['close_menu']();assert not ns['State'].opened and not pc.bShowMouseCursor
 # Each page should fit vertically above the QUICK ACTIONS bar at 4 resolutions.
 for size in ((2560,1440),(1920,1080),(1280,720),(854,480)):
  ns['viewport']=lambda size=size:size
  ns['open_menu']()
  original_btn=ns['btn']
  data=[]
  def trace_btn(parent,caption,x,y,w,h,fn,*a,**kw):
   data.append((str(caption),x,y,w,h))
   return original_btn(parent,caption,x,y,w,h,fn,*a,**kw)
  ns['btn']=trace_btn
  ns['State'].expand_theme=False
  for tab in ('PLAYER','MOTION','COMBAT','LOOT','WORLD','PARTY','SPAWN','EVENTS','CONTENT','PRESETS','STYLE','DEV'):
   data.clear()
   ns['show_page'](tab)
   footer=next(y for name,x,y,w,h in data if name=='RESTORE TEMP')
   # Only buttons anchored to the right of the navigation rail count.
   main_start=ns['State'].panel_rect[0]+180 if ns['State'].panel_rect else 300
   violations=[(label,round(y+h-footer,1)) for label,x,y,w,h in data if (
     tab!='PRESETS' or not label.startswith('RESTORE EVERYTHING'))
     and x>main_start and y<footer and y+h>footer-2]
   assert not violations,(size,tab,violations)
  ns['btn']=original_btn
  ns['close_menu']()
 # Wallet: no request before 2nd click; solo only; guards broken currency API.
 role[0]=0
 pc.PlayerState=hostps
 ns['State'].anti_spam_until=0
 rewards=[]
 def fake_ptr(token,struct):return (token,struct)
 unreal.FGbxDefPtr=fake_ptr
 realfind=u.find_class
 def modified_class(name):
  if name=='GbxCurrencyFunctionLibrary':
   return SimpleNamespace(ClassDefaultObject=SimpleNamespace(
     GiveCurrency=lambda receiver,ptr,amount:rewards.append((receiver,ptr[0],amount))))
  return realfind(name)
 u.find_class=modified_class
 assert not ns['wallet_request']('cash',1000)
 assert not rewards
 assert ns['wallet_request']('cash',1000)
 assert len(rewards)==1 and rewards[0][1:] == ('Cash',1000)
 assert not ns['wallet_request']('cash',-1000000)
 assert len(rewards)==1
 assert not ns['wallet_request']('eridium',100) # request, not grant
 assert len(rewards)==1
 role[0]=3
 assert not ns['wallet_request']('eridium',100) # guest blocked
 assert len(rewards)==1
 ns['wallet_clear']()
 assert ns['State'].wallet_pending is None
 assert ns['State'].wallet_requests==1
 u.find_class=realfind
 role[0]=2
 # Host-only friend wallet: two clicks and identity-safe authority.
 role[0]=2
 ns['State'].anti_spam_until=0
 pc.PlayerState=hostps
 friend_controller=PC(friendps)
 friendps.GetPlayerController=lambda:friend_controller
 u.find_class=modified_class
 ns['refresh_party']()
 ns['select_party'](1)
 ns['enable_party_changes']()
 assert ns['party_permission_ok']()
 before=len(rewards)
 assert not ns['friend_wallet_request']('eridium',100)
 assert len(rewards)==before
 assert ns['friend_wallet_request']('eridium',100)
 assert len(rewards)==before+1 and rewards[-1][0] is friend_controller
 assert rewards[-1][1:] == ('eridium',100)
 # Change target in between clicks; previous pending request must never apply.
 ns['State'].anti_spam_until=0
 assert not ns['friend_wallet_request']('cash',1000)
 friend_controller.HasAuthority=lambda:False
 assert not ns['friend_wallet_request']('cash',1000)
 assert len(rewards)==before+1
 friend_controller.HasAuthority=lambda:True
 role[0]=3
 assert not ns['friend_wallet_request']('cash',1000)
 assert len(rewards)==before+1
 u.find_class=realfind
 role[0]=2
 print('PASS: 10 tabs ×4 resolutions, movement primitive type guarding/restoration, map-safe teleport bookmarks, party roster invalidation/consent, host remote travel, stale-pawn guard, optional HUD, input cleanup.')
except Exception:
 traceback.print_exc();raise
finally:
 for k,v in old.items():
  if v is None:sys.modules.pop(k,None)
  else:sys.modules[k]=v
