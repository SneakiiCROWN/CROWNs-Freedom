"""CROWNs Freedom v5.26.0 — Controller-first editors, safe staged values and clear live status and reviewed mod library / Oak2 PythonSDK.

A lean native Unreal UMG menu; no BLImGui dependency or external windows.
Gameplay integration is based on documented community BL4 SDK API examples.
Only the player's game can confirm actual effects.
"""
from __future__ import annotations

from datetime import datetime, timezone
import time
import json
import hashlib
import math
import random
import zipfile
from pathlib import Path
import unrealsdk
from mods_base import build_mod, get_pc, keybind
from unrealsdk import logging
from unrealsdk.hooks import Type, add_hook, remove_hook
try:
    from mods_base.settings import SETTINGS_DIR
except Exception:
    SETTINGS_DIR = None

HOOK = "/Script/Engine.CameraModifier:BlueprintModifyCamera"
RELEASE_VERSION = "5.26.0"
BUILD_ID = "5.26.0-echo-fieldcraft-r23"
RELEASE_LABEL = "CROWN ECHO FIELDCRAFT R23 / v" + RELEASE_VERSION + " • COMMAND CENTRE"
HOOK_ID = "crowns_freedom_native_v54"
GAMEPAD_HOOK_ID = "crowns_freedom_native_gamepad_v54"
PURPLE = (0.12, 0.09, 0.22, 0.98)
PANEL = (0.045, 0.065, 0.105, 0.97)
HEADER = (0.10, 0.14, 0.22, 0.98)
ACCENT = (0.99, 0.72, 0.19, 1.0)
CYAN = (0.12, 0.77, 0.91, 1.0)
RED = (0.77, 0.19, 0.25, 1.0)
BUTTON = (0.13, 0.20, 0.31, 1.0)
MUTED = (0.10, 0.13, 0.18, 1.0)
WHITE = (0.95, 0.97, 0.99, 1.0)
DIM = (0.61, 0.71, 0.79, 1.0)


THEMES = [
    {"name":"CROWN BLACKGLASS","bg":"#07090C","panel":"#101821","header":"#15232B","border":"#345F69","accent":"#F0C787","highlight":"#5FD7D4","action":"#142129","muted":"#111C23","danger":"#D66D65","text":"#FFF8E8","dim":"#B3C2C5"},
    {"name":"DAHL TERMINAL","bg":"#0A181A","panel":"#1C3235","header":"#294A4D","border":"#8EA9A7","accent":"#E7CC72","highlight":"#7ED2CF","action":"#355A5E","muted":"#223B3F","danger":"#B56B53","text":"#F5F4E9","dim":"#C1D0CD"},
    {"name":"EARL'S BACKROOM","bg":"#0C1018","panel":"#202733","header":"#2E3443","border":"#A2A9AA","accent":"#FFD15D","highlight":"#42D7DD","action":"#394451","muted":"#252C38","danger":"#C74840","text":"#FFF7E9","dim":"#D5E0DF"},
    {"name":"VAULT STEEL","bg":"#09131D","panel":"#173049","header":"#23496B","border":"#6E9CBC","accent":"#FFD24A","highlight":"#3CC2E0","action":"#305D80","muted":"#20384E","danger":"#BA4758","text":"#F0FAFF","dim":"#B2D2E0"},
    {"name":"CRIMSON DUST","bg":"#170C0F","panel":"#3A2129","header":"#5A2F3A","border":"#A06E77","accent":"#F4C05B","highlight":"#E16A5A","action":"#7A4851","muted":"#462B31","danger":"#B93745","text":"#FFF1E3","dim":"#DAB8BC"},
    {"name":"CROWN NOIR","bg":"#0B0909","panel":"#1D1918","header":"#292320","border":"#8B7661","accent":"#FFD08A","highlight":"#D39D65","action":"#312B28","muted":"#1E1917","danger":"#BD6250","text":"#FFF6E8","dim":"#D4C6B6"},
    {"name":"NEON AFTERDARK","bg":"#06061A","panel":"#0B102C","header":"#090F2B","border":"#F737A5","accent":"#FCA5DC","highlight":"#49DFF2","action":"#101432","muted":"#090F24","danger":"#F55769","text":"#FDF5FF","dim":"#C4C3DF"}
]
FLAVOR = [
    "EARL // Watchu want... activate somethin' and get outta my face.",
    "MARCUS // If it changes your save, back it up before you get cute.",
    "EARL // Press the bright bits. The ugly bits are probably also buttons.",
    "MARCUS // No refunds on bad decisions, Vault Hunter.",
    "EARL // If it looks dangerous, it probably works.",
    "MARCUS // Two clicks means I already warned you once."
]
def _hex(code):
    value=code.lstrip("#")
    return tuple(int(value[i:i+2],16)/255.0 for i in (0,2,4))+(1.0,)

_THEME_RGBA=[{k:_hex(v) for k,v in theme.items() if k!="name"} for theme in THEMES]

def theme_color(key):
    result=_THEME_RGBA[State.theme_idx].get(key, (1.0,1.0,1.0,1.0))
    if key=="accent" and State.custom_accent is not None:return _hex(State.custom_accent)
    if key=="bg":return result[:3]+(State.background_opacity,)
    if key in ("panel","header","muted","action"):
        return result[:3]+(State.panel_opacity,)
    return result
def _finite_setting(value,minimum,maximum,default):
    try:
        result=float(value)
        if not math.isfinite(result):return float(default)
        return max(minimum,min(maximum,result))
    except (TypeError,ValueError,OverflowError):
        return float(default)

def _safe_theme_index(value):
    """A broken theme index must never prevent travel slots or favourites loading."""
    if type(value) is int and 0<=value<len(THEMES):return value
    if isinstance(value,str) and len(value)<=2 and value.isascii() and value.isdecimal():
        idx=int(value)
        if idx<len(THEMES):return idx
    return 0

def _finite_position(value):
    if not isinstance(value,(float,int)) or isinstance(value,bool):return None
    try:
        result=float(value)
        return result if math.isfinite(result) and -100000<=result<=100000 else None
    except (TypeError,ValueError,OverflowError):return None

def _prefs_file():
    return SETTINGS_DIR / "CROWNs_Freedom_UI.json" if SETTINGS_DIR is not None else None
def _menu_marker_path():
    return Path(SETTINGS_DIR)/'CROWNs_Freedom_Menu_Active.json' if SETTINGS_DIR is not None else None

_KNOWN_PAGES = frozenset(('PLAYER','MOTION','COMBAT','LOOT','WORLD','PARTY','SPAWN','EVENTS','WEEKLY','CONTENT','PRESETS','STYLE','DEV','TROPHIES','WAYPOINTS','PROFILES','GEAR','DISPLAY','GUIDE','FINDER','ARENA','CAPACITY','DASHBOARD','BOOSTS','COMMUNITY'))

_NATIVE_PHASES=frozenset(('START','REDRAW_BEGIN','FRAME_DETACH','FRAME_STAGE','FRAME_COMMIT','FRAME_ATTACH','ART_IMPORT','REDRAW_READY','INPUT_CAPTURE','UI_ONLY','MENU_CLOSE','FRAME_SIZE','FRAME_RETIRE','APPEARANCE_APPLY','UNKNOWN'))

def _set_native_phase(phase):
    """Bounded diagnostic breadcrumb, written on transitions, never every game tick.

    This cannot identify a native fault by itself; the matching BL4 minidump
    and UnrealSDK logs are necessary. No player names, coordinates or saves.
    """
    if phase not in _NATIVE_PHASES:return
    if getattr(State,'native_phase',None)==phase:return
    State.native_phase=phase
    State.native_history=(State.native_history+[{'phase':phase,'page':State.page if State.page in _KNOWN_PAGES else 'UNKNOWN','generation':State.frame_generation,'art':State.art_mode}])[-24:]
    if State.opened:_mark_menu_opened()

def _mark_menu_opened():
    """Store only the active UI surface for a future crash investigation.

    This is *not* a crash log and must never store character identifiers,
    save contents, world coordinates, file paths or exception messages.
    Updating only during page/dock changes avoids writes every game tick.
    """
    path=_menu_marker_path()
    if path is None or not State.opened:return
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        page=str(State.page)
        if page not in _KNOWN_PAGES:page='UNKNOWN'
        data={'schema':2,'version':RELEASE_VERSION,'state':'open',
              'page':page,'dock':'SIDE' if State.dock_mode=='SIDE' else 'FULL',
              'art':'SHAPES' if State.art_mode=='SHAPES' else 'AUTO',
              'safe_mode':bool(State.safe_mode),'phase':getattr(State,'native_phase','UNKNOWN')}
        path.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    except (OSError,ValueError,TypeError):pass

def _clear_menu_marker():
    path=_menu_marker_path()
    if path is None:return
    try:path.unlink(missing_ok=True)
    except OSError:pass

def _detect_unclean_menu_close():
    """Fail to safe rendering only after a known CROWN menu-open marker.

    May be a normal power-off rather than a CROWN crash; user can switch back.
    """
    path=_menu_marker_path()
    if path is None:return False
    try:
        if not path.is_file() or path.stat().st_size>2000:return False
        payload=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(payload,dict) or payload.get('version') not in ('5.2','5.2.0','5.3','5.3.0','5.3.1','5.4.0','5.4.1','5.5.0','5.6.0','5.7.0','5.7.1','5.8.0','5.8.1','5.9.0','5.9.1','5.9.2','5.9.3','5.9.4','5.9.5','5.10.0','5.11.0','5.12.0','5.13.0','5.14.0','5.15.0','5.16.0','5.16.1','5.16.2','5.17.0','5.18.0','5.19.0','5.20.0','5.21.0','5.22.0','5.23.0','5.24.0','5.25.0','5.26.0') or payload.get('state')!='open':return False
        page=payload.get('page','UNKNOWN')
        State.previous_unclean_page=page if page in _KNOWN_PAGES else 'UNKNOWN'
        phase=payload.get('phase','UNKNOWN')
        State.previous_native_phase=phase if phase in _NATIVE_PHASES else 'UNKNOWN'
        State.safe_mode=True
        State.previous_menu_unclean=True
        State.art_status='SAFE MODE / previous menu exit unclean'
        State.audio_status='SAFE MODE / previous menu exit unclean'
        return True
    except (OSError,UnicodeError,ValueError,TypeError):return False

def _read_preferences_with_backup(path):
    """Reject damaged/oversize JSON and recover the last valid local snapshot.

    This changes only CROWN's own UI file; never game saves or achievements.
    """
    for candidate in (path,path.with_name(path.name+'.bak')):
        try:
            if not candidate.is_file() or candidate.stat().st_size>262144:
                continue
            loaded=json.loads(candidate.read_text(encoding='utf-8'))
            if not isinstance(loaded,dict):continue
            is_legacy=(loaded.get('prefs_schema') is None and
                       (isinstance(loaded.get('forge_favorites'),list) or
                        isinstance(loaded.get('forge_search'),str)))
            if loaded.get('prefs_schema') not in (2,3,4) and not is_legacy:continue
            State.prefs_recovered=(candidate!=path)
            return loaded
        except (OSError,UnicodeError,ValueError,TypeError):
            continue
    State.prefs_recovered=False
    return None

def _backup_valid_preferences(path):
    """Keep one known-valid previous settings snapshot before replacement."""
    try:
        if not path.is_file() or path.stat().st_size>262144:return
        raw=path.read_bytes()
        data=json.loads(raw)
        if not isinstance(data,dict):return
        if data.get('prefs_schema') not in (2,3,4) and not (data.get('prefs_schema') is None and isinstance(data.get('forge_favorites'),list)):return
        backup=path.with_name(path.name+'.bak')
        stage=path.with_name(path.name+'.bak.tmp')
        stage.write_bytes(raw)
        stage.replace(backup)
    except (OSError,ValueError,TypeError):
        pass

def save_preferences():
    p=_prefs_file()
    if p is None:return
    try:
        # SDK installations can present a settings path before creating its
        # parent directory. A missing folder must not silently erase bookmarks.
        p.parent.mkdir(parents=True,exist_ok=True)
        data=json.dumps({"prefs_schema":4,
                         "echo_appearance":{'background':State.background_opacity,'accent':State.custom_accent,'duration':State.transition_duration},
                         "presentation_revision":526,
                         "maurice_slot_week":State.maurice_slot_week,
                         "travel_slots":[{"slot":index,"map":record[0],"xyz":[round(float(q),2) for q in record[1]]}
                             for index,record in sorted(State.checkpoints.items())
                             if _valid_travel_record(index,record)],
                         "controller_enabled":State.controller_enabled,
                         "gamepad_icons":State.gamepad_icons,
                         "reduced_motion":State.reduced_motion,
                         "theme_index":State.theme_idx,
                         "text_scale":State.font_scale,
                         "compact":State.compact,
                         "opacity":State.panel_opacity,
                         "scale":State.panel_scale,
                         "window_x":State.window_x,
                         "window_y":State.window_y,
                         "forge_favorites":sorted(State.spawn_favorites),
                         "forge_search":State.spawn_search,
                         "art_mode":State.art_mode,
                         "audio_mode":State.audio_mode,
                         "audio_hover":State.audio_hover,
                         "sfx_set":State.sfx_set,
                         "cursor_aid":State.cursor_aid,
                         "cursor_coordinates":State.cursor_coordinates,
                         "safe_mode":State.safe_mode,
                         "toasts_enabled":State.toasts_enabled,
                         "toast_duration":State.toast_duration,
                         "toast_position":State.toast_position,
                         "hud_anchor":State.hud_anchor,
                         "dock_mode":State.dock_mode,
                         "dock_right":State.dock_right,
                         "sandbox_presets":_sandbox_saved_validate(State.sandbox_saved),
                         "encounter_favorites":list(State.encounter_favorites)[:12],
                         "echo_personality":State.echo_personality,
                         "recipe_library":State.recipe_library,
                         "external_xp_draft":State.external_xp_draft,
                         "studio_dock":{"width":State.dock_width,"opacity":State.dock_opacity,"vertical":State.dock_vertical,"compact":State.dock_compact,"favorites":_dock_favorites_valid(State.dock_favorites)},
                         "trophy_marked":sorted(State.trophy_marked),
                         "ui_profiles":State.ui_profiles,
                         "forge_blueprints":_validated_forge_blueprints(State.forge_blueprints),
                         "arena_planned_batch":State.arena_planned_batch,
                         "reduced_motion":State.reduced_motion,
                         "profile_names":State.profile_names,
                         "tool_pins":list(State.tool_pins)},indent=2)
        pending=p.with_name(p.name+'.tmp')
        pending.write_text(data,encoding='utf-8')
        _backup_valid_preferences(p)
        pending.replace(p)
    except Exception as e: log("UI preferences not saved: "+str(e))
def load_preferences():
    p=_prefs_file()
    if p is None:return
    data=_read_preferences_with_backup(p)
    if data is None:return
    try:
        try:
            extra=_appearance_extra_validate(data.get('echo_appearance',{}))
            State.background_opacity=extra['background'];State.custom_accent=extra['accent'];State.transition_duration=extra['duration']
        except ValueError:pass
        if State.prefs_recovered:
            log('UI SETTINGS RECOVERED // Previous valid preferences snapshot loaded.')
        # Legacy preferences used render scaling that overflowed text boundaries.
        # Migrate to safe styling while retaining user favourites and search.
        if data.get('prefs_schema') in (2,3,4):
            State.maurice_slot_week=str(data.get('maurice_slot_week',''))[:20] if isinstance(data.get('maurice_slot_week',''),str) else ''
            State.theme_idx=_safe_theme_index(data.get("theme_index",0))
            if data.get('prefs_schema')==2 and State.theme_idx==2:
                # Legacy default was Earl's brown; refresh to higher-contrast industrial
                # blue unless the user chooses brown again in v2.4.
                State.theme_idx=0
            State.font_scale=_finite_setting(data.get("text_scale",1.0),.85,1.25,1.0)
            State.compact=bool(data.get("compact",False))
            State.panel_opacity=_finite_setting(data.get("opacity",.94),.65,1.0,.94)
            State.panel_scale=_finite_setting(data.get("scale",1.0),.72,2.00,1.0)
            xx,yy=data.get("window_x"),data.get("window_y")
            State.window_x=_finite_position(xx)
            State.window_y=_finite_position(yy)
        else:
            State.window_x=State.window_y=None
            State.font_scale=1.0
            State.panel_scale=1.0
            State.theme_idx=0
            State.panel_opacity=.94
        State.external_xp_draft=_finite_setting(data.get('external_xp_draft'),.1,10.,1.5)
        try:State.recipe_library=_recipe_library_validate(data.get('recipe_library',{}))
        except (ValueError,TypeError):State.recipe_library={}
        State.sandbox_saved=_sandbox_saved_validate(data.get('sandbox_presets',{}))
        fav=data.get('encounter_favorites',[])
        allowed={row[0] for row in ENCOUNTER_CATALOGUE}
        State.encounter_favorites=list(dict.fromkeys(v for v in fav[:48] if isinstance(v,str) and v in allowed))[:12] if isinstance(fav,list) else []
        State.echo_personality=data.get('echo_personality',True) is True
        dock=data.get('studio_dock',{})
        if isinstance(dock,dict):
            State.dock_width=_finite_setting(dock.get('width'),360,560,430)
            State.dock_opacity=_finite_setting(dock.get('opacity'),.3,.95,.78)
            State.dock_vertical=_finite_setting(dock.get('vertical'),0,1,.5)
            State.dock_compact=dock.get('compact') is True
            State.dock_favorites=_dock_favorites_valid(dock.get('favorites'))
        State.art_mode='SHAPES' if data.get('art_mode')=='SHAPES' else 'AUTO'
        State.audio_mode=data.get('audio_mode','NORMAL') if data.get('audio_mode') in ('OFF','LOW','NORMAL','HIGH') else 'NORMAL'
        State.audio_hover=bool(data.get('audio_hover',False))
        State.sfx_set='CLASSIC' if data.get('sfx_set')=='CLASSIC' else 'ECHO'
        State.cursor_aid=bool(data.get('cursor_aid',True))
        State.cursor_coordinates=data.get('cursor_coordinates','AUTO') if data.get('cursor_coordinates') in ('AUTO','NATIVE') else 'AUTO'
        State.safe_mode=bool(data.get('safe_mode',False))
        State.toasts_enabled=bool(data.get('toasts_enabled',True))
        State.toast_duration=_finite_setting(data.get('toast_duration',4.2),2.0,8.0,4.2)
        State.toast_position=data.get('toast_position') if data.get('toast_position') in ('TOP_CENTRE','TOP_LEFT','TOP_RIGHT') else 'TOP_CENTRE'
        try: planned=int(data.get('arena_planned_batch',1))
        except (ValueError,TypeError,OverflowError): planned=1
        State.arena_planned_batch=planned if planned in (1,2,3,5,10) else 1
        State.hud_anchor=data.get('hud_anchor') if data.get('hud_anchor') in HUD_ANCHORS else 'TOP_CENTRE'
        State.dock_mode='SIDE' if data.get('dock_mode','SIDE')=='SIDE' else 'FULL'
        if data.get('presentation_revision')!=526:State.dock_mode='FULL'
        State.dock_right=bool(data.get('dock_right',False))
        State.controller_enabled=bool(data.get('controller_enabled',True))
        State.gamepad_icons='PLAYSTATION' if data.get('gamepad_icons')=='PLAYSTATION' else 'XBOX'
        State.reduced_motion=bool(data.get('reduced_motion',True))
        names=data.get('profile_names',{})
        if isinstance(names,dict):
            State.profile_names={str(i):str(names.get(str(i),'Profile '+str(i)))[:24] for i in range(1,4)}
        State.tool_pins=_validate_tool_pins(data.get('tool_pins',[]))
        marks=data.get('trophy_marked',[])
        if isinstance(marks,list):
            State.trophy_marked={x for x in marks if type(x) is int and 0<=x<len(ACHIEVEMENT_NAMES)}
        # Blueprints are inert local metadata; reject malformed, obsolete or
        # forged pool references before any recipe can reach the Forge UI.
        State.forge_blueprints=_validated_forge_blueprints(data.get('forge_blueprints',{}))
        profiles=data.get('ui_profiles',{})
        if isinstance(profiles,dict):
            State.ui_profiles={str(k):v for k,v in profiles.items()
                               if str(k) in ('1','2','3') and isinstance(v,dict)}
        # Migration: earlier builds had session-only bookmarks; v3.3 stores
        # validated same-map coordinates, never inventory, Steam or saves.
        entries=data.get('travel_slots',[]) if data.get('prefs_schema')==4 else []
        State.checkpoints={}
        if isinstance(entries,list):
            for item in entries[:TRAVEL_SLOT_COUNT]:
                if not isinstance(item,dict):continue
                idx=item.get('slot')
                record=(item.get('map'),item.get('xyz'))
                if _valid_travel_record(idx,record):
                    State.checkpoints[idx]=(record[0],tuple(float(q) for q in record[1]))
        q=data.get('forge_search','')
        if isinstance(q,str):
            State.spawn_search=_clean_forge_query(q)
        # Favorites are safe UI metadata, never a request to the game.
        # Reject rogue/obsolete tokens instead of trusting arbitrary paths.
        allowed={token for _label,token,_cat in SPAWN_POOLS}
        incoming=data.get("forge_favorites",[])
        if isinstance(incoming,list):
            State.spawn_favorites={str(token) for token in incoming[:150]
                                   if isinstance(token,str) and token in allowed}
    except Exception as e:log("UI preferences ignored: "+str(e))
def set_theme(index):
    State.theme_idx=max(0,min(len(THEMES)-1,int(index)))
    # Choosing an entry closes the dropdown immediately; it must not obscure
    # the following controls or require a second tap to dismiss.
    State.expand_theme=False
    save_preferences()
    log("THEME // "+THEMES[State.theme_idx]["name"])
    _queue_toast('THEME_APPLIED')
    redraw()
def set_text_scale(value):
    State.font_scale=max(.85,min(1.25,float(value)))
    save_preferences()
    redraw()
def toggle_compact():
    State.compact=not State.compact
    save_preferences()
    redraw()
def set_opacity(v):
    State.panel_opacity=max(.65,min(1.0,float(v)))
    save_preferences()
    if State.opened:redraw()

def set_panel_scale(v):
    State.panel_scale=_finite_setting(v,.72,2.00,1.0)
    save_preferences()
    if State.opened:redraw()

def toggle_theme_dropdown():
    State.expand_theme=not State.expand_theme
    redraw()

def reset_placement():
    State.window_x=State.window_y=None
    State.drag_armed=False
    State.drag_origin=State.drag_start=None
    save_preferences()
    redraw()

def _mouse_xy(value):
    """Decode Unreal's FVec2, (x,y), or (success,x,y) without treating
    an unsuccessful native query's (False,0,0) as a real mouse coordinate.
    """
    try:
        if hasattr(value,'X') and hasattr(value,'Y'):
            xx,yy=float(value.X),float(value.Y)
        elif isinstance(value,(list,tuple)):
            if len(value)>=3 and (isinstance(value[0],bool) or (isinstance(value[0],int) and value[0] in (0,1))):
                if not value[0]:return None
                xx,yy=float(value[1]),float(value[2])
            elif len(value)>=2 and not isinstance(value[0],bool):
                xx,yy=float(value[0]),float(value[1])
            else:return None
        else:return None
        if not (math.isfinite(xx) and math.isfinite(yy)):return None
        if abs(xx)>200000 or abs(yy)>200000:return None
        return xx,yy
    except (ValueError,TypeError,OverflowError):return None

def _dpi_scale(pc):
    try:
        lib=cls('/Script/UMG.WidgetLayoutLibrary').ClassDefaultObject
        factor=float(lib.GetViewportScale(pc))
        return factor if math.isfinite(factor) and 0.2<factor<6.0 else 1.0
    except Exception:return 1.0

def _mouse_position(pc):
    """Return *viewport-local logical* coordinates, never mixed pixel units.

    UE PlayerController.GetMousePosition gives hardware viewport pixels; the
    UMG canvas and WidgetLayoutLibrary use viewport/DPI logical coordinates.
    AUTO first uses UE's DPI-aware mouse API if available, then raw / DPI.
    NATIVE is an explicit fallback for BL4/driver revisions whose PC already
    reports logical coordinates. Only cursor/drag mapping uses this choice.
    """
    if pc is None:return None
    layout=None
    try:layout=cls('/Script/UMG.WidgetLayoutLibrary').ClassDefaultObject
    except Exception:pass
    mode=getattr(State,'cursor_coordinates','AUTO')
    if mode=='AUTO' and layout is not None:
        try:
            method=getattr(layout,'GetMousePositionScaledByDPI',None)
            if callable(method):
                pos=_mouse_xy(method(pc))
                if pos is not None:
                    State.cursor_source='UMG DPI'
                    return pos
        except Exception:pass
    try:
        raw=_mouse_xy(pc.GetMousePosition())
        if raw is not None:
            if mode=='NATIVE':
                State.cursor_source='PC NATIVE'
                return raw
            dpi=_dpi_scale(pc)
            State.cursor_source='PC PIXELS / DPI %.2f'%dpi
            return (raw[0]/dpi,raw[1]/dpi)
    except Exception:pass
    if layout is not None:
        try:
            position=_mouse_xy(layout.GetMousePositionOnViewport(pc))
            if position is not None:
                State.cursor_source='UMG VIEWPORT'
                return position
        except Exception:pass
    State.cursor_source='UNAVAILABLE'
    return None

def cycle_gamepad_icons():
    """Select only visual button hints; never modify actual controller mappings."""
    State.gamepad_icons='PLAYSTATION' if State.gamepad_icons=='XBOX' else 'XBOX'
    save_preferences()
    log('GAMEPAD ART // '+State.gamepad_icons+' (labels only; game controls unchanged)')
    if State.opened:redraw()
    return State.gamepad_icons

def _gamepad_art(asset):
    if State.gamepad_icons=='PLAYSTATION':
        return {'PAD_A':'PS_CROSS','PAD_B':'PS_CIRCLE','PAD_L3':'PS_L3','PAD_R3':'PS_R3'}.get(asset,asset)
    return asset

def cycle_cursor_coordinates():
    """Manual driver compatibility switch; never alters desktop mouse state."""
    State.cursor_coordinates='NATIVE' if State.cursor_coordinates=='AUTO' else 'AUTO'
    State.cursor_last=State.mouse_last=None
    save_preferences()
    log('CURSOR ALIGN // '+State.cursor_coordinates+' / use AUTO normally; NATIVE for drivers that pre-scale the pointer')
    if State.opened:redraw()
    return State.cursor_coordinates

def move_panel():
    pc=get_pc(possibly_loading=True)
    m=_mouse_position(pc)
    if m is None:
        log('MOVE needs mouse-position support on this SDK; menu unchanged.')
        return
    State.drag_armed=True
    State.drag_origin=(State.window_x,State.window_y)
    State.drag_start=m
    State.drag_last=None
    State.mouse_was_down=key_down(pc,'LeftMouseButton')
    State.drag_deadline=time.monotonic()+.25
    log('MOVE MODE: place the menu and left-click; press ESC to cancel.')

def _poll_move(pc):
    if not State.drag_armed:return False
    # Keep the window under the pointer by translating the active native canvas.
    position=_mouse_position(pc)
    if position is None:
        State.drag_armed=False
        State.drag_origin=State.drag_start=None
        log('MOVE canceled: pointer unavailable.')
        return True
    if State.drag_start is None:
        State.drag_start=position
    dx,dy=position[0]-State.drag_start[0],position[1]-State.drag_start[1]
    factor=max(.2,State.render_scale)  # mouse is already DPI-normalised
    virtual_dx=dx/factor
    virtual_dy=dy/factor
    # Clamp within viewport; on 720p the panel always stays in reach.
    if State.panel_rect is None:
        State.drag_armed=False
        return True
    px,py,pw,ph,vw,vh=State.panel_rect
    desired_x=max(8.0,min(vw-pw-8.0,px+virtual_dx))
    desired_y=max(8.0,min(vh-ph-8.0,py+virtual_dy))
    moved_x,moved_y=desired_x-px,desired_y-py
    State.drag_last=(desired_x,desired_y)
    # Move layout without constructing new widgets per-frame.
    try:State.canvas.SetRenderTranslation(v2(moved_x,moved_y))
    except Exception:
        log('MOVE unsupported by this Unreal UI build.')
        State.drag_armed=False
        return True
    if key_down(pc,'Escape'):
        State.drag_armed=False
        State.drag_last=None
        State.drag_origin=None
        redraw()
        log('MOVE canceled.')
        return True
    down=key_down(pc,'LeftMouseButton')
    was=State.mouse_was_down
    State.mouse_was_down=down
    if down and not was and time.monotonic()>=State.drag_deadline:
        State.window_x,State.window_y=desired_x,desired_y
        State.drag_armed=False
        State.drag_origin=State.drag_start=State.drag_last=None
        save_preferences()
        redraw()
        log('MENU PLACEMENT saved.')
    return True

def rotate_flavor():
    State.flavor_idx=(State.flavor_idx+1)%len(FLAVOR)
    if State.opened:redraw()
def refresh_status():
    try:log("VAULT HUNTER // CONNECTED" if pawn() is not None else "VAULT HUNTER // NOT LOADED")
    except Exception as e:log("STATUS ERROR // "+str(e))
def reset_fov():
    """Undo only the FOV fields that still match CROWN's last adjustment."""
    obj=State.fov_saved;original=State.fov_original;expected=State.fov_last
    if obj is None or original is None:
        log('No CROWN FOV changes to restore.');return False
    try:
        pc=get_pc(possibly_loading=True)
        current=getattr(pc,'player',None) if pc is not None else None
        if current is None or not same_unreal_object(current,obj):
            log('FOV RESTORE SKIPPED // original controller replaced.');return False
        live=tuple(_read_number(obj,k) for k in ('BaseFOV','VehicleFOV'))
        if expected is None or any(v is None or (abs(v-e)>max(.05,abs(e)*.01) and abs(v-o)>max(.05,abs(o)*.01))
                                   for v,e,o in zip(live,expected,original)):
            log('FOV RESTORE SKIPPED // camera values changed outside CROWN.');return False
        for key,value in zip(('BaseFOV','VehicleFOV'),original):
            setattr(obj,key,value)
        after=tuple(_read_number(obj,k) for k in ('BaseFOV','VehicleFOV'))
        if any(v is None or abs(v-e)>max(.05,abs(e)*.01) for v,e in zip(after,original)):
            log('FOV RESTORE NOT CONFIRMED // recheck camera.');return False
        State.fov_saved=State.fov_original=State.fov_last=None
        State.fov_selected=None
        log('Original FOV restored (owned readback confirmed).')
        if State.opened and State.page=='PLAYER':redraw()
        return True
    except Exception as error:
        log('FOV RESTORE FAILED // '+type(error).__name__);return False

def preset_vacation():
    set_god(True)
    if not State.target_off:toggle_no_target()
    log("VAULT VACATION // TOGGLES REQUESTED")
    redraw()
def preset_mayhem():
    set_world_time(2.0)
    set_god(True)
    log("WALKING APOCALYPSE // TOGGLES REQUESTED")
    redraw()
def preset_normal():
    restore()
    log("NORMAL-ISH // RESTORE REQUESTED")
    redraw()


# --------------------- Movement & travel ---------------------------
def movement_obj():
    actor=ensure_pawn()
    if actor is None:return None,None
    for field in ("OakCharacterMovement","CharMoveComp","CharacterMovement"):
        try:
            move=getattr(actor,field,None)
            if move is not None:return actor,move
        except Exception:pass
    log("MOVEMENT // Character movement component not reflected in this build")
    return actor,None

def _read_number(obj,name):
    try:
        v=getattr(obj,name)
        if isinstance(v,(float,int)) and not isinstance(v,bool) and math.isfinite(float(v)):
            return float(v)
    except Exception:pass
    return None

def _motion_tune_r3(mode,mult):
    """Only write reflected primitive properties, preserving session originals.
    BL4 attribute wrappers may differ by game patch: never replace a WrappedStruct.
    """
    try:mult=float(mult)
    except Exception:log('Movement value not numeric');return False
    if not math.isfinite(mult) or not .3<=mult<=3.0:
        log('Movement value must be 0.3x to 3x.');return False
    if mode=='speed' and State.noclip_boost_active and not getattr(State,'noclip_boost_writing',False):
        log('MOTION // Release F5 flight boost before changing walking speed.')
        return False
    actor,move=movement_obj()
    if move is None:return False
    if State.motion_owner is not None and not same_unreal_object(actor,State.motion_owner):
        State.motion_owner=None
        State.motion_originals.clear()
        State.motion_last.clear()
    if State.motion_owner is None:
        State.motion_owner=actor
    fields={
        'speed':('MinAnalogWalkSpeed','MaxWalkSpeed'),
        'jump':('JumpZVelocity',),
        'gravity':('GravityScale',),
    }.get(mode)
    if not fields:
        log('Unsupported movement adjustment.');return False
    # Validate every relevant primitive before writing ANYTHING. On partially
    # supported game builds a speed tweak must not leave just one field changed.
    prior={}
    planned={}
    for name in fields:
        before=_read_number(move,name)
        if before is None:
            log('MOTION BLOCKED // '+name+' is not a reflected finite float.')
            return False
        if name in State.motion_originals:
            expected=State.motion_last.get(name)
            if expected is None or abs(before-expected)>max(.05,abs(expected)*.01):
                log('MOTION BLOCKED // '+name+' changed outside CROWN. No overwrite; try restoring after checking other mods.')
                return False
        original=State.motion_originals.get(name,before)
        proposed=original*mult
        if not math.isfinite(proposed) or abs(proposed)>25000:
            log('MOTION BLOCKED // '+name+' target outside safe range.')
            return False
        prior[name]=before
        planned[name]=float(proposed)
    changed=[]
    try:
        for name,proposed in planned.items():
            setattr(move,name,proposed)
            after=_read_number(move,name)
            if after is None or abs(after-proposed)>max(.05,abs(proposed)*.01):
                raise RuntimeError(name+' write/readback failed')
            changed.append(name)
    except Exception as error:
        for name in reversed(changed):
            try:setattr(move,name,prior[name])
            except Exception:pass
        # Include the failing field: assignment may have partially succeeded.
        for name in fields:
            try:
                if _read_number(move,name)!=prior[name]:setattr(move,name,prior[name])
            except Exception:pass
        log('MOTION FAILED // Attempted rollback after '+type(error).__name__)
        return False
    for name in fields:
        if name not in State.motion_originals:
            State.motion_originals[name]=prior[name]
        State.motion_last[name]=planned[name]
    if mode=='speed':State.motion_scale=mult
    elif mode=='jump':State.jump_selected=mult
    elif mode=='gravity':State.gravity_selected=mult
    log('MOTION // '+mode.upper()+' x%.2f applied to %d fields (session)'%(mult,len(changed)))
    if State.opened and State.page=='MOTION':redraw()
    return True

def restore_motion():
    if State.noclip_boost_active:release_noclip_flight_boost()
    actor=State.motion_owner;anchor=State.motion_anchor;component=State.motion_component
    if actor is None:return False
    if anchor!=_session_anchor() or not same_unreal_object(actor,pawn()):
        State.motion_originals={};State.motion_last={};State.motion_owner=None;State.motion_component=None
        State.motion_status='OLD CONTEXT / Skipped stale movement writes.';log(State.motion_status);return False
    _,current=movement_obj()
    if current is None or not same_unreal_object(current,component):return False
    restored=0
    for key,original in list(State.motion_originals.items()):
        if _read_number(component,key)!=State.motion_last.get(key):continue
        try:
            setattr(component,key,original)
            if _read_number(component,key)==original:
                State.motion_originals.pop(key);State.motion_last.pop(key,None);restored+=1
        except Exception as error:record_runtime_fault('MOTION_RESTORE',error)
    if not State.motion_originals:
        State.motion_owner=None;State.motion_component=None;State.motion_anchor=None
        State.motion_scale=State.jump_selected=State.gravity_selected=1.
        State.boost_preset='NONE';State.boost_status='OWNED MOVEMENT RESTORED'
    State.motion_draft={};State.motion_status='RESTORE / %d fields verified / %d retained or changed outside CROWN.'%(restored,len(State.motion_originals))
    log(State.motion_status)
    if State.opened and State.page=='MOTION':redraw()
    return restored>0


def map_tag():
    world,_=world_and_state()
    if world is None:return None
    try:return str(world.GetName())
    except Exception:return None

def _position(actor):
    try:
        raw=actor.K2_GetActorLocation()
        vals=(float(raw.X),float(raw.Y),float(raw.Z))
        if all(math.isfinite(v) and abs(v)<1e9 for v in vals):return vals
    except Exception:pass
    return None

def _travel_distance(a,b):
    if a is None or b is None:return None
    try:return math.sqrt(sum((float(x)-float(y))**2 for x,y in zip(a,b)))
    except (ValueError,TypeError,OverflowError):return None


def _teleport_actor(actor,coordinates):
    """Collision-swept same-world travel request, with checked arrival/rollback.

    This is NOT a guarantee the landing terrain is safe: dynamic hazards,
    moving objects, streamed levels, co-op authority, and world updates still
    require a live BL4 check. An engine refusing Sweep=True fails closed;
    never silently retry using an unsafe no-sweep teleport.
    """
    State.travel_last_state='INVALID_REQUEST'
    if actor is None or coordinates is None:return False
    if not isinstance(coordinates,(tuple,list)) or len(coordinates)!=3:return False
    if not all(type(v) in (int,float) and math.isfinite(v) and abs(v)<1e9 for v in coordinates):return False
    original=_position(actor)
    if original is None:
        State.travel_last_state='ORIGIN_READBACK_UNAVAILABLE'
        return False
    try:
        from unrealsdk.unreal import IGNORE_STRUCT
        vector=unrealsdk.make_struct('Vector',X=float(coordinates[0]),Y=float(coordinates[1]),Z=float(coordinates[2]))
        # Sweep=True asks the game to stop at obstructions; never auto-downgrade.
        result=actor.K2_SetActorLocation(vector,True,IGNORE_STRUCT,True)
        arrival=_position(actor)
        distance=_travel_distance(arrival,coordinates)
        # Tight ~85 cm tolerance for small engine adjustments to placement.
        if result is not False and distance is not None and distance<=85.0:
            State.travel_last_state='ARRIVAL_READBACK_CONFIRMED_SWEPT'
            return True
        State.travel_last_state=('ENGINE_REJECTED_SWEPT_MOVE' if result is False
                                 else 'DESTINATION_READBACK_UNCONFIRMED')
        if arrival is None:
            # The request may have moved the pawn even if location readback has
            # become temporarily unavailable. Preserve a way home; don't claim
            # arrival and don't attempt an unverified blind second movement.
            try:
                if same_unreal_object(actor,pawn()) and map_tag():
                    State.travel_recovery_anchor=(map_tag(),original)
            except Exception:pass
            State.travel_last_state='POSITION_READBACK_LOST_RETURN_AVAILABLE'
            return False
        # Sweeps may move the actor part-way even when they return False.
        # Attempt a collision-swept return to the original position.
        moved=_travel_distance(arrival,original)
        if moved is not None and moved>15.0:
            State.travel_rollback_attempts+=1
            back=unrealsdk.make_struct('Vector',X=original[0],Y=original[1],Z=original[2])
            try:
                actor.K2_SetActorLocation(back,True,IGNORE_STRUCT,True)
            except Exception:pass
            restored=_travel_distance(_position(actor),original)
            if restored is not None and restored<=35.0:
                State.travel_last_state='PARTIAL_MOVE_ROLLBACK_CONFIRMED'
            else:
                State.travel_last_state='PARTIAL_MOVE_RETURN_UNCONFIRMED'
                # Recovery is only local to the current player's pawn/session.
                try:
                    if same_unreal_object(actor,pawn()):
                        tag=map_tag()
                        if tag:State.travel_recovery_anchor=(tag,original)
                except Exception:pass
                log('TRAVEL WARNING // Partial movement; check location and use RETURN.')
        return False
    except Exception as error:
        # Some native calls can throw *after* mutating the actor. Never assume
        # an exception means the original position is intact.
        current=_position(actor)
        moved=_travel_distance(current,original)
        if moved is None or moved>15.0:
            try:
                if same_unreal_object(actor,pawn()) and map_tag():
                    State.travel_recovery_anchor=(map_tag(),original)
            except Exception:pass
            State.travel_last_state='EXCEPTION_AFTER_POSSIBLE_MOVE_RETURN_AVAILABLE'
            log('TRAVEL WARNING // API exception; position may have changed. RETURN remains available.')
        else:
            State.travel_last_state='SWEEP_API_EXCEPTION_NO_MOVE'
        log('TELEPORT sweep unavailable: '+type(error).__name__)
        return False

# User-defined map locations are NOT game-registered fast-travel stations.
# BL4 map-specific gravity, doors, hazards and co-op authority may reject a move.
TRAVEL_SLOT_COUNT=12
TRAVEL_SLOT_NAMES=(
    'HOME BASE','FARM RUN','BOSS ENTRANCE','VENDOR','QUEST START','SHORTCUT',
    'SAFE HOUSE','LOOT ROUTE','ARENA','GARAGE','EXPLORATION','SPARE'
)


# Official activity bulletin retrieved 2026-10-14; intentionally expires BEFORE
# the October 15 server rotation. The game/ECHO map is authoritative.
WEEKLY_SNAPSHOT = {
    'start_utc':'2026-10-08T00:00:00+00:00',
    'expires_utc':'2026-10-15T17:00:00+00:00',  # 1h before published ~18:00 UTC Thursday reset
    'week_key':'2026-10-08',
    'maurice_region':'Terminus Range',
    'encore_boss':'Mimicron',
    'wildcard':'Savage Salvage',
    'reward':"Aegon's Dream (Vladof Assault Rifle)",
    'source':'Borderlands 4 official weekly bulletin Oct 8-15; Mobalytics region guide'
}
# Public DLC release descriptions, not an ownership/installation or item-ID probe.
DLC_RELEASE_INDEX = (
    ('STORY 1 / MAD ELLIE','Mad Ellie and the Vault of the Damned: Whispering Glacier'),
    ('STORY 2 / FL4K','FL4K and the Last Resort: Providence'),
    ('BOUNTY / DEMON','The Demon\'s Domain: new boss and Pearlescent loot'),
    ('BOUNTY / AMARA','Amara and the Vile Shadows: new boss and Pearlescent loot'),
)

def _weekly_snapshot(now=None):
    """Return freshness without trusting local time to control gameplay.

    System clock is advisory, not server-signed; this never unlocks assets or
    teleports from unverified vendor coordinates. The conservative window also
    prevents cached announcements from masquerading as live after rotation.
    """
    try:
        stamp = now if now is not None else datetime.now(timezone.utc)
        if stamp.tzinfo is None:return None
        stamp=stamp.astimezone(timezone.utc)
        start=datetime.fromisoformat(WEEKLY_SNAPSHOT['start_utc'])
        end=datetime.fromisoformat(WEEKLY_SNAPSHOT['expires_utc'])
        return WEEKLY_SNAPSHOT if start<=stamp<end else None
    except (TypeError,ValueError,OverflowError,KeyError,AttributeError):return None

def _maurice_anchor_ready(now=None):
    weekly=_weekly_snapshot(now)
    return bool(weekly and State.maurice_slot_week==weekly['week_key'] and
                _valid_travel_record(4,State.checkpoints.get(4)) and
                map_tag()==State.checkpoints[4][0])

def weekly_summary():
    snap=_weekly_snapshot()
    if not snap:
        log('WEEKLY EXPIRED / Check latest ECHO map and official announcements. No vendor teleport allowed.')
        return False
    log('WEEKLY / MAURICE: '+snap['maurice_region']+' / BOSS: '+snap['encore_boss'])
    log('WILDCARD / '+snap['wildcard']+' / '+snap['reward'])
    return True

def weekly_save_vendor():
    """Explicit player-position bookmark only; never guess Maurice's coordinates."""
    snap=_weekly_snapshot()
    if snap is None:
        log('MAURICE SAVE BLOCKED / Weekly bulletin expired. Check official location.');return False
    # Slot 4 is the user's existing VENDOR bookmark. Its normal two-press
    # overwrite protection is retained. The button must be pressed AT vendor.
    success=bookmark_save(4)
    if success:
        State.maurice_slot_week=snap['week_key']
        save_preferences()
        log('MAURICE / Slot 04 tagged for this week only. No vendor detection is claimed.')
    return bool(success)

def weekly_go_vendor():
    if not _maurice_anchor_ready():
        log('MAURICE BLOCKED / No current-week same-map vendor bookmark. Save at the machine first.')
        return False
    return bookmark_go(4)  # validated, collision-swept and reversible by RETURN

def weekly_dlc_info(index):
    if type(index) is not int or not 0<=index<len(DLC_RELEASE_INDEX):return False
    label,details=DLC_RELEASE_INDEX[index]
    log('DLC INDEX / '+label+': '+details+' / Ownership and spawn IDs NOT verified.')
    return True

def _valid_travel_record(index,record):
    if type(index) is not int or index<1 or index>TRAVEL_SLOT_COUNT:return False
    if not isinstance(record,(tuple,list)) or len(record)!=2:return False
    tag,location=record
    if not isinstance(tag,str) or not tag or len(tag)>160 or any(ord(c)<32 for c in tag):return False
    if not isinstance(location,(list,tuple)) or len(location)!=3:return False
    return all(type(v) in (float,int) and math.isfinite(v) and abs(v)<=10_000_000 for v in location)

def bookmark_save(index):
    if type(index) is not int or index<1 or index>TRAVEL_SLOT_COUNT:
        log('TRAVEL // Invalid slot');return False
    actor=ensure_pawn()
    tag=map_tag()
    loc=_position(actor) if actor is not None else None
    record=(tag,loc)
    if not _valid_travel_record(index,record):
        log('TRAVEL // Cannot read safe current map and character location.');return False
    old=State.checkpoints.get(index)
    # Accidental overwrites are more likely with a controller than a mouse.
    # A first-time save needs one press; overwriting an existing spot needs two.
    now=time.monotonic()
    if old is not None and old!=(tag,loc):
        if State.travel_save_pending!=index or now>State.travel_save_expires:
            State.travel_save_pending=index
            State.travel_save_expires=now+5.0
            log('TRAVEL // Overwrite slot %02d? Press SAVE again within 5s.'%index)
            if State.opened and State.page=='WAYPOINTS':redraw()
            return False
    State.travel_save_pending=None
    State.travel_save_expires=0.0
    State.checkpoints[index]=(tag,tuple(loc))
    if index==4:State.maurice_slot_week=''  # ordinary saves must not impersonate weekly vendor
    save_preferences()
    if SETTINGS_DIR is None:
        log('TRAVEL // Slot %02d saved for session only (settings directory missing).'%index)
    else:
        log('TRAVEL // Slot %02d %s saved for %s'%(index,TRAVEL_SLOT_NAMES[index-1],tag[:42]))
    _queue_toast('BOOKMARK_SAVED')
    if State.opened and State.page=='WAYPOINTS':redraw()
    return True

def bookmark_go(index):
    if type(index) is not int or index<1 or index>TRAVEL_SLOT_COUNT:
        log('TRAVEL // Invalid slot');return False
    entry=State.checkpoints.get(index)
    if not _valid_travel_record(index,entry):
        log('TRAVEL // Slot %02d is empty or invalid.'%index);return False
    current=map_tag()
    if not current or current!=entry[0]:
        log('TRAVEL BLOCKED // Slot %02d belongs to %s; current map differs.'%(index,entry[0][:36]));return False
    now=time.monotonic()
    if now<State.travel_cooldown_until:
        log('TRAVEL // Wait a moment for the last movement to settle.');return False
    actor=ensure_pawn()
    old=_position(actor) if actor is not None else None
    if old is None:
        log('TRAVEL BLOCKED // Player location unavailable.');return False
    if all(abs(a-b)<20 for a,b in zip(old,entry[1])):
        log('TRAVEL // Already at slot %02d.'%index);return False
    if _teleport_actor(actor,entry[1]):
        State.travel_recovery_anchor=None
        State.checkpoint_return=(entry[0],old)
        State.travel_cooldown_until=now+1.3
        log('TRAVEL // Slot %02d swept arrival confirmed; RETURN goes back.'%index)
        # Drop directly back into gameplay after a confirmed travel.
        if State.opened:close_menu()
        return True
    log('TRAVEL // Slot %02d was not confirmed; player may be blocked by the game.'%index)
    return False

def bookmark_back():
    entry=State.travel_recovery_anchor or State.checkpoint_return
    if not _valid_travel_record(1,entry):
        log('TRAVEL // No valid return location in this session.');return False
    if map_tag()!=entry[0]:
        log('RETURN BLOCKED // The current map is different.');return False
    now=time.monotonic()
    # The emergency reverse path must never be throttled: if a position was
    # unsafe, the player must be able to return immediately.
    actor=ensure_pawn()
    old=_position(actor) if actor else None
    if old is None:
        log('RETURN BLOCKED // Player location unavailable.');return False
    if _teleport_actor(actor,entry[1]):
        State.travel_recovery_anchor=None
        State.checkpoint_return=(entry[0],old)
        State.travel_cooldown_until=now+1.3
        log('RETURN // Swept arrival confirmed; press again later to swap back.')
        if State.opened:close_menu()
        return True
    log('RETURN // Travel unconfirmed; return remains available.')
    return False

def travel_next_page():
    State.waypoint_page=1-State.waypoint_page
    State.travel_save_pending=None
    if State.opened:redraw()

def travel_hub():
    if State.opened:
        show_page('WAYPOINTS')
    else:
        State.page='WAYPOINTS'
        State.nav_group='VAULT'
        State.waypoint_mode='TRAVEL'
        open_menu()

def cycle_party_mode():
    State.party_mode={'BOOSTS':'TRAVEL','TRAVEL':'GIFTS','GIFTS':'SESSION','SESSION':'BOOSTS'}.get(State.party_mode,'SESSION')
    if State.opened:redraw()

def jump_to_friend():
    # Local player's position only; can be corrected by the game server.
    item=selected_friend()
    if item is None:log('Select a friend first.');return
    target=remote_pawn(item['ps'])
    if target is None or same_unreal_object(target,pawn()):
        log('Friend target not available.');return
    pos=_position(target)
    actor=ensure_pawn()
    if pos is None or actor is None:return
    original=_position(actor)
    if _teleport_actor(actor,pos):
        State.checkpoint_return=(map_tag(),original)
        log('ME TO FRIEND // '+item['name']+' (local request)')
    else:log('ME TO FRIEND // not confirmed')

def bring_friend():
    if not party_permission_ok():
        log('BLOCKED // Host + friend consent required.');return
    item=selected_friend()
    if item is None:log('Select a friend first.');return
    target=remote_pawn(item['ps'])
    if target is None or same_unreal_object(target,pawn()):
        log('Friend pawn not available.');return
    try:
        if not bool(target.HasAuthority()):
            log('BLOCKED // No authority over friend pawn.');return
    except Exception:
        log('BLOCKED // Cannot verify friend authority.');return
    now=time.monotonic()
    # Co-op confirmation binds player identity AND the current map/character.
    # An earlier click must never authorise a different friend after selection
    # changes, a party rejoin, or a map transition.
    session=_session_anchor()
    friend_key=item['key']
    if session is None or friend_key is None:
        State.friend_teleport_confirm=0.0
        State.friend_teleport_target=None
        State.friend_teleport_anchor=None
        log('TELEPORT BLOCKED // Stable session and friend identity required.')
        return
    same_request=(now<State.friend_teleport_confirm and
                  State.friend_teleport_target==friend_key and
                  State.friend_teleport_anchor==session)
    if not same_request:
        State.friend_teleport_confirm=now+5.0
        State.friend_teleport_target=friend_key
        State.friend_teleport_anchor=session
        log('CONFIRM TELEPORT // '+item['name']+' / press again within 5 seconds.')
        return
    State.friend_teleport_confirm=0.0
    State.friend_teleport_target=None
    State.friend_teleport_anchor=None
    if not party_permission_ok() or selected_friend() is None:
        log('TELEPORT BLOCKED // Roster or permission changed.');return
    destination=_position(ensure_pawn())
    if destination is None:
        log('TELEPORT BLOCKED // Host position unavailable.');return
    if _teleport_actor(target,destination):
        log('BRING FRIEND // '+item['name']+' (host request; ask friend to verify)')
    else:log('BRING FRIEND // teleport not confirmed')

# ------------------- Safe, independent companion field HUD ----------------
# This is NOT a replacement for BL4's health/ammo/minimap. It reports CROWN's
# own toggles and request stages; no game HUD widgets are touched or hidden.
HUD_ANCHORS = ('TOP_CENTRE', 'LEFT_MIDDLE', 'RIGHT_MIDDLE')

def _hud_rect(viewport_size=None, anchor=None):
    """Viewport-pixel placement away from the original health/ammo corners."""
    try:
        vw, vh = viewport() if viewport_size is None else viewport_size
        vw, vh = float(vw), float(vh)
        if not math.isfinite(vw) or not math.isfinite(vh) or vw < 240 or vh < 180:
            raise ValueError('Bad viewport')
    except (ValueError, TypeError, OverflowError):
        vw, vh = 1280.0, 720.0
    width = max(210.0, min(444.0, vw - 32.0))
    height = min(78.0, vh - 32.0)
    anchor = anchor if anchor in HUD_ANCHORS else 'TOP_CENTRE'
    if anchor == 'LEFT_MIDDLE':
        x, y = 16.0, max(18.0, (vh-height)*.46)
    elif anchor == 'RIGHT_MIDDLE':
        x, y = vw - width - 16.0, max(18.0, (vh-height)*.46)
    else:
        x, y = max(16.0, (vw-width)*.5), min(105.0, max(16.0, vh-height-16.0))
    return (max(16.0, min(x, vw-width-16.0)), max(16.0, min(y, vh-height-16.0)), width, height)

def hud_summary():
    """Read only CROWN-maintained state; never imply native game readback."""
    first=('GOD '+('ON' if State.god else 'OFF')+'  /  NOCLIP '+('ON' if State.noclip else 'OFF')+
           '  /  AI '+('IGNORE' if State.target_off else 'NORMAL')+
           ('  /  FLIGHT F5' if State.noclip_boost_active else ''))
    second=('TIME x%.1f'%State.speed+'  /  '+session_role()+'  /  EVENT '+str(State.active_event)[:15])
    if State.r10_bonus is not None:
        second=('BONUS %ds / '+State.r10_bonus.get('profile','DAMAGE')+' / EFFECT UNVERIFIED')%max(0,round(State.r10_bonus['until']-time.monotonic()))
    return first, second

def _place_hud(ui):
    x,y,width,height=_hud_rect(anchor=State.hud_anchor)
    call(ui,'SetAlignmentInViewport',v2(0,0))
    call(ui,'SetPositionInViewport',v2(x,y),False)
    call(ui,'SetDesiredSizeInViewport',v2(width,height))
    return x,y,width,height

def toggle_hud():
    if State.hud_visible:
        hide_hud()
        log('COMPANION HUD // OFF')
        return False
    pc=get_pc(possibly_loading=True)
    if pc is None:
        log('COMPANION HUD // No player controller; try in a loaded map.')
        return False
    ui=None
    try:
        x,y,width,height=_hud_rect(anchor=State.hud_anchor)
        ui=create('/Script/UMG.UserWidget',pc)
        tree=create('/Script/UMG.WidgetTree',ui)
        ui.WidgetTree=tree
        root=create('/Script/UMG.CanvasPanel',tree)
        tree.RootWidget=root
        old_tree=State.tree
        State.tree=tree
        try:
            box(root,0,0,width,height,theme_color('bg')[:3]+(.89,),1)
            box(root,0,0,5,height,theme_color('accent'),2)
            box(root,0,0,width,2,theme_color('border'),3)
            box(root,0,height-2,width,2,theme_color('border'),3)
            box(root,10,8,width-20,25,theme_color('header'),2)
            if 'R9_DOCK' in State.art_textures:optional_art_image(root,'R9_DOCK',width*.59,0,width*.41,height,z=2,opacity=.23)
            title=text(root,'CROWN  /  FIELD STATUS',18,9,width-36,23,theme_color('accent'),.72,4)
            details=text(root,'REQUESTED SETTINGS / not BL4 readback',18,36,width-34,19,theme_color('text'),.62,4)
            sub=text(root,'GAME HUD UNCHANGED',18,55,width-34,19,theme_color('dim'),.53,4)
        finally:
            State.tree=old_tree
        # ESlateVisibility 3=HitTestInvisible for ALL CHILDREN; 4 is only
        # SelfHitTestInvisible and may intercept firing through child text.
        if not attempt(root,'SetVisibility',3) or not attempt(ui,'SetVisibility',3):
            raise RuntimeError('Unreal refused noninteractive HUD visibility')
        _place_hud(ui)
        if not attempt(ui,'AddToViewport',999996):
            raise RuntimeError('UMG AddToViewport rejected companion HUD')
        State.hud_widget=ui
        State.hud_label=details
        State.hud_subtitle=sub
        State.hud_visible=True
        State.hud_last_summary=None
        update_hud()
        log('COMPANION HUD // ON; CROWN-only state, game HUD unchanged')
        return True
    except Exception as exc:
        record_runtime_fault('HUD_CREATE',exc)
        if ui is not None:
            try:call(ui,'RemoveFromParent')
            except Exception:pass
        State.hud_widget=State.hud_label=State.hud_subtitle=None
        State.hud_visible=False
        log('COMPANION HUD UNAVAILABLE // '+type(exc).__name__+'; menu still works')
        return False

def update_hud():
    if not State.hud_visible or State.hud_label is None:return False
    first, second=hud_summary()
    summary=(first,second)
    if summary==State.hud_last_summary:return True # no needless UMG text writes
    try:
        State.hud_label.SetText(first)
        if State.hud_subtitle is not None:State.hud_subtitle.SetText(second)
        State.hud_last_summary=summary
        return True
    except Exception as exc:
        record_runtime_fault('HUD_UPDATE',exc)
        hide_hud() # stale Unreal widget after loading/map transitions
        return False

def cycle_hud_position():
    State.hud_anchor=HUD_ANCHORS[(HUD_ANCHORS.index(State.hud_anchor)+1)%len(HUD_ANCHORS)] if State.hud_anchor in HUD_ANCHORS else HUD_ANCHORS[0]
    if State.hud_visible and State.hud_widget is not None:
        try:_place_hud(State.hud_widget)
        except Exception as exc:
            record_runtime_fault('HUD_REPOSITION',exc)
            hide_hud()
    save_preferences()
    log('COMPANION HUD POSITION // '+State.hud_anchor.replace('_',' '))
    if State.opened:redraw()
    return State.hud_anchor

def hide_hud():
    obj=State.hud_widget
    State.hud_widget=State.hud_label=State.hud_subtitle=None
    State.hud_visible=False
    State.hud_last_summary=None
    if obj is not None:
        try:call(obj,'RemoveFromParent')
        except Exception as exc:record_runtime_fault('HUD_REMOVE',exc)

# ------------------- Final build diagnostics -------------------------
def compatibility_report():
    try:
        import mods_base
        sdk=(getattr(unrealsdk,'__version__',None) or 'available')
        base=(getattr(mods_base,'__version__',None) or 'available')
        active=map_tag() or 'none'
        log('SDK '+str(sdk)+' / BASE '+str(base)+' / MAP '+active[:26]+' / ROLE '+session_role())
    except Exception as e:log('COMPAT CHECK // '+str(e))

def feature_probe():
    """Read-only probe: inspect currently loaded SDK classes, never mutate."""
    capabilities={}
    checks=(('PLAYER','OakCharacter'),('SKILL','GbxSkillComponentFunctions_ActionSkill'),
            ('CURRENCY','GbxCurrencyFunctionLibrary'))
    for label,klass in checks:
        try:
            klass_obj=unrealsdk.find_class(klass)
            capabilities[label]=klass_obj is not None
        except Exception:
            capabilities[label]=False
    try:
        capabilities['ITEM POOLS']=_spawn_api() is not None
    except Exception:
        capabilities['ITEM POOLS']=False
    State.capabilities=capabilities
    State.capabilities_checked_unix=int(time.time())
    msg=' | '.join(label+(' PRESENT' if present else ' ABSENT') for label,present in capabilities.items())
    log('PROBE / '+msg[:132]+' // Presence is not verified functionality')
    return capabilities

def advanced_feature_audit():
    """Read-only diagnostic. No object creation, grants, pointers or mutations."""
    actor=pawn()
    game_world,_=world_and_state()
    if actor is None or game_world is None:
        result={'character':'missing','vehicle_spawn':'not_verified',
                'boss_spawn':'not_verified','weapon_parts':'not_verified'}
        State.advanced_audit=result
        State.advanced_audit_matches={}
        State.advanced_audit_unix=int(time.time())
        log('ADVANCED AUDIT // Load a solo character first. No gameplay changes.')
        return result
    # Presence of a reflected method is NOT proof that the engine accepts its
    # arguments or that the operation is authorized on this build.
    probes={
        'weapon_parts':('GetEquippedInventory','GetInventoryComponent'),
        'vehicle_spawn':('GetVehicle','GetCurrentVehicle'),
        'boss_spawn':('GetTargetActor','GetCurrentTarget'),
    }
    found={}
    for name,names in probes.items():
        matches=[]
        for method in names:
            try:
                if callable(getattr(actor,method,None)):matches.append(method)
            except Exception:pass
        found[name]=matches
    state={name:'read_only_refs:'+str(len(matches)) for name,matches in found.items()}
    state['character']='loaded'
    State.advanced_audit=state
    # Export ONLY the predefined method names seen on this actor. No UObject
    # identity, memory addresses, positions, inventory, player data or paths.
    State.advanced_audit_matches={name:list(matches) for name,matches in found.items()}
    State.advanced_audit_unix=int(time.time())
    log('ADVANCED AUDIT // Read-only references: '+
        ' / '.join(name+'='+str(len(matches)) for name,matches in found.items()))
    log('ADVANCED AUDIT // No vehicle, boss or weapon editing API verified; no operation sent.')
    return state

def run_advanced_audit_and_export():
    """One button: read-only probes + privacy-conscious JSON export.

    This does NOT invoke Forge preflight because that can cancel a pending
    two-step item confirmation. It never calls spawning/grant methods.
    """
    feature_probe()
    advanced_feature_audit()
    exported=export_qa_report()
    if exported:
        log('ADVANCED AUDIT EXPORTED // Read-only results now included in QA JSON.')
    else:
        log('ADVANCED AUDIT // Report unavailable; open Activity Log for summaries.')
    return exported


def status_readback():
    c=ensure_pawn()
    if c is None:return
    move=getattr(c,'OakCharacterMovement',None)
    statuses=[]
    for name,attr in (('MOVE','MinAnalogWalkSpeed'),('JUMP','JumpZVelocity'),('GRAV','GravityScale')):
        val=_read_number(move,attr) if move is not None else None
        if val is not None:statuses.append(name+' %.2f'%val)
    statuses.append('HP IMMUNITY '+str(not bool(getattr(c,'bCanBeDamaged',True))))
    log(' | '.join(statuses)[:148] or 'No reflected stats found')


# ----------------------- Native wallet utilities -------------------------
# Based on BL4 SDK GbxCurrencyFunctionLibrary/GbxCurrencyDef usage. Avoid
# undocumented memory offsets and distinguish requests from verified delivery.
CURRENCY_CODES={'cash':'Cash','eridium':'eridium'}

def _native_wallet():
    try:
        struct=None
        for ref in ('/Script/GbxGame.GbxCurrencyDef',
                    '/Script/OakGame.GbxCurrencyDef'):
            try:struct=unrealsdk.find_object('ScriptStruct',ref)
            except Exception:struct=None
            if struct is not None:break
        if struct is None:raise RuntimeError('Currency definition missing on this build')
        from unrealsdk.unreal import FGbxDefPtr
        lib=unrealsdk.find_class('GbxCurrencyFunctionLibrary')
        if lib is None:raise RuntimeError('Currency function class unavailable')
        cdo=lib.ClassDefaultObject
        give=getattr(cdo,'GiveCurrency',None)
        if not callable(give):raise RuntimeError('GiveCurrency not callable')
        return struct,give,FGbxDefPtr
    except Exception as exc:
        log('WALLET API UNAVAILABLE / '+str(exc)[:95])
        return None

def _wallet_receiver():
    # Solo and host can modify themselves. Client mode is allowed to request
    # a local wallet write only if game SDK exposes the required function;
    # not a promise that the server will accept it.
    pc=get_pc(possibly_loading=True)
    if pc is None or getattr(pc,'PlayerState',None) is None:
        log('WALLET BLOCKED / Player state not initialised.')
        return None
    if not is_local_host_action():
        log('WALLET BLOCKED / Requires solo or verified local host for self wallet write.')
        return None
    return pc

def wallet_request(kind,amount):
    if kind not in CURRENCY_CODES or type(amount) is not int or not 1<=amount<=100000:return False
    pc=_wallet_receiver();anchor=_session_anchor()
    if pc is None or anchor is None:return False
    job=State.r10_wallet_job
    if job is not None and job['anchor']==anchor:
        log('WALLET BLOCKED // Prior native exception may have granted currency. Travel before another request.');return False
    before=wallet_balance(kind,pc);token=(kind,amount,anchor,_native_address(pc.PlayerState) or id(pc.PlayerState),before)
    now=time.monotonic()
    if State.wallet_pending!=token or now>=State.wallet_expires:
        State.wallet_pending=token;State.wallet_expires=now+6.
        log('CONFIRM WALLET // '+kind.upper()+' +'+str(amount)+' / permanent / press again');redraw();return False
    State.wallet_pending=None;State.wallet_expires=0
    if now<State.anti_spam_until:return False
    rpc=wallet_rpc(pc,kind)
    if rpc is None:
        resolved=_native_wallet()
        if resolved is None:return False
        struct,give,typed=resolved
        try:ptr=typed(CURRENCY_CODES[kind],struct)
        except Exception as error:record_runtime_fault('WALLET_DEFINITION',error);return False
    State.anti_spam_until=now+1.5
    State.r10_wallet_job=dict(anchor=anchor,kind=kind,amount=amount,before=before)
    try:
        # Exactly one receiver/call. TypeError can occur after a native effect;
        # never use exception-driven retries with another receiver.
        if rpc is not None:rpc[0](rpc[1],amount)
        else:give(pc,ptr,amount)
        after=wallet_balance(kind,pc)
        status='FIELD DELTA MATCHED' if before is not None and after==before+amount else 'REQUEST ONLY / PAYOUT UNCONFIRMED'
        State.r10_wallet_history=(State.r10_wallet_history+[dict(kind=kind,amount=amount,before=before,after=after,status=status)])[-8:]
        State.r10_wallet_job=None;State.wallet_requests+=1;State.wallet_last=kind.upper()+' +'+str(amount)
        log('WALLET // '+status+' / '+State.wallet_last+' / cannot undo');redraw();return True
    except Exception as error:
        record_runtime_fault('WALLET_REQUEST',error);log('WALLET UNCONFIRMED // No retry; partial grant possible.');return False

def friend_wallet_request(kind,amount):
    if kind not in CURRENCY_CODES or type(amount) is not int or not 1<=amount<=100000:
        log('FRIEND WALLET / invalid value.');return False
    if getattr(State,'r10_gift_uncertain',None)==_session_anchor():
        log('FRIEND GIFT BLOCKED / Previous grant uncertain; travel before retry.');return False
    if not party_permission_ok():
        log('FRIEND GIFT BLOCKED / You must host and have current party consent.')
        return False
    friend=selected_friend()
    if friend is None:return False
    ps=friend['ps']
    pc=get_pc(possibly_loading=True)
    try:
        ctrl=ps.GetPlayerController()
        if ctrl is None:raise RuntimeError('Remote controller not replicated to host')
        if same_unreal_object(ctrl,pc):raise RuntimeError('Refusing to edit the host as a friend')
        ctrl_ps=getattr(ctrl,'PlayerState',None)
        if ctrl_ps is None or not same_unreal_object(ctrl_ps,ps):
            raise RuntimeError('Remote controller has mismatched PlayerState')
        if not bool(ctrl.HasAuthority()):
            raise RuntimeError('Host does not control the selected receiver')
    except Exception as exc:
        log('FRIEND GIFT UNAVAILABLE / '+str(exc)[:105]);return False
    now=time.monotonic()
    request=('friend',friend['key'],kind,amount,_session_anchor(),_native_address(ctrl) or id(ctrl),_native_address(ps) or id(ps))
    if State.wallet_pending!=request or now>=State.wallet_expires:
        State.wallet_pending=request
        State.wallet_expires=now+6.0
        log('CONFIRM GIFT / '+str(friend['name'])+' +'+str(amount)+' '+kind+
            ' - press again within 6s')
        if State.opened:redraw()
        return False
    State.wallet_pending=None
    State.wallet_expires=0
    if now<State.anti_spam_until:
        log('GIFT WAIT / Please slow down.');return False
    if not party_permission_ok() or selected_friend() is None:
        log('GIFT BLOCKED / Party changed before confirmation.');return False
    resolved=_native_wallet()
    if resolved is None:return False
    struct,give,ptr_cls=resolved
    try:
        ptr=ptr_cls(CURRENCY_CODES[kind],struct)
        State.r10_gift_uncertain=_session_anchor()
        give(ctrl,ptr,int(amount))
        State.r10_gift_uncertain=None
        State.anti_spam_until=now+2
        State.wallet_requests+=1
        State.wallet_last=kind.upper()+' +'+str(amount)+' -> '+friend['name']
        log('FRIEND GIFT REQUEST SENT / '+State.wallet_last+
            ' - ask friend to check wallet')
        if State.opened:redraw()
        return True
    except Exception as exc:
        log('FRIEND GIFT FAILED / '+str(exc)[:96]);return False

def wallet_clear():
    State.wallet_pending=None
    State.wallet_expires=0.0
    log('Pending wallet confirmation cleared.')

def report_mod_status():
    role=session_role()
    try:
        count=len(party_entries())
    except Exception:count=0
    states=[]
    for field,title in (('god','GOD'),('noclip','FLY'),('target_off','UNTARGETABLE'),
                        ('hud_visible','HUD')):
        if getattr(State,field):states.append(title)
    msg='CROWN v1.2 / '+role+' / '+str(count)+' players / '+(
        ', '.join(states) if states else 'DEFAULT SETTINGS')
    log(msg)

def backup_notice():
    log('REMINDER / Copy your BL4 save folder before cash/XP/items testing.')


# ------------------- Black Market Forge extension -------------------
# Explicitly selected, bounded item-pool spawn requests. Public BL4 SDK
# references: NexusConfigStoreItemPool.SpawnInventoryFromItemPool.
# Curated catalogue from the MIT-licensed community item_pools.json database.
# Availability depends on BL4 build, DLC, runtime definitions and ownership.
# Name, Unreal item-pool token, menu category. Entries are DATA, not promised drops.
SPAWN_POOLS=(
    ('Convergence','itempool_bor_sg_05_legendary_convergence_shiny','SHOTGUN'),
    ('Hellfire','itempool_bor_sm_05_legendary_hellfire_shiny','SMG'),
    ('Star Helix','itempool_dad_ar_05_legendary_star_helix_shiny','RIFLE'),
    ('Rangefinder','itempool_dad_ps_05_legendary_Rangefinder_shiny','PISTOL'),
    ('Golden God','itempool_bor_sg_05_legendary_GoldenGod_shiny','SHOTGUN'),
    ('Gore Master','itempool_bor_sg_05_legendary_GoreMaster_shiny','SHOTGUN'),
    ('Heart Gun','itempool_dad_sg_05_legendary_HeartGun_shiny','SHOTGUN'),
    ('Cannon Brawl','itempool_dad_sg_05_legendary_cannonbrawl_shiny','SHOTGUN'),
    ('Hellwalker','itempool_jak_sg_05_legendary_Hellwalker_shiny','SHOTGUN'),
    ('Rainbow Vomit','itempool_jak_sg_05_legendary_RainbowVomit_shiny','SHOTGUN'),
    ('Slugger','itempool_jak_sg_05_legendary_Slugger_shiny','SHOTGUN'),
    ('Bod','itempool_dad_sg_05_legendary_Bod_shiny','SHOTGUN'),
    ('Miss Laser','itempool_dad_sg_05_legendary_misslaser_shiny','SHOTGUN'),
    ('Falke','itempool_bor_sm_05_legendary_falke_shiny','SMG'),
    ('Prince','itempool_bor_sm_05_legendary_Prince_shiny','SMG'),
    ('Brickhouse','itempool_vla_sm_05_legendary_brickhouse_shiny','SMG'),
    ('Bloodstarved','itempool_dad_sm_05_legendary_bloodstarved_shiny','SMG'),
    ('Follower','itempool_dad_sm_05_legendary_follower_shiny','SMG'),
    ('Luty','itempool_dad_sm_05_legendary_Luty_shiny','SMG'),
    ('Loarmaster','itempool_dad_sm_05_legendary_loarmaster_shiny','SMG'),
    ('Plasma Coil','itempool_mal_sm_05_legendary_PlasmaCoil_shiny','SMG'),
    ('Ohm I Got','itempool_mal_sm_05_legendary_OhmIGot_shiny','SMG'),
    ('Mercury','itempool_mal_sm_05_legendary_mercury_shiny','SMG'),
    ('Lumberjack','itempool_dad_ar_05_legendary_Lumberjack_shiny','RIFLE'),
    ('Mercredi','itempool_dad_ar_05_legendary_mercredi_shiny','RIFLE'),
    ('Bonnie & Clyde','itempool_jak_ar_05_legendary_BonnieClyde_shiny','RIFLE'),
    ('Rowan','itempool_jak_ar_05_legendary_Rowan_shiny','RIFLE'),
    ('Rowdy','itempool_jak_ar_05_legendary_rowdy_shiny','RIFLE'),
    ('GMR','itempool_ord_ar_05_legendary_GMR_shiny','RIFLE'),
    ('Goalkeeper','itempool_ord_ar_05_legendary_Goalkeeper_shiny','RIFLE'),
    ('Chuck','itempool_ted_ar_05_legendary_Chuck_shiny','RIFLE'),
    ('Divided Focus','itempool_ted_ar_05_legendary_DividedFocus_shiny','RIFLE'),
    ('Laserdisc','itempool_ted_ar_05_legendary_laserdisc_shiny','RIFLE'),
    ('Soul Survivor','itempool_dad_ps_05_legendary_soulsurvivor_shiny','PISTOL'),
    ('Zipgun','itempool_dad_ps_05_legendary_Zipgun_shiny','PISTOL'),
    ('Kings Gambit','itempool_jak_ps_05_legendary_KingsGambit_shiny','PISTOL'),
    ('Phantom Flame','itempool_jak_ps_05_legendary_Phantom_Flame_shiny','PISTOL'),
    ('Quickdraw','itempool_jak_ps_05_legendary_QuickDraw_shiny','PISTOL'),
    ('Seventh Sense','itempool_jak_ps_05_legendary_seventh_sense_shiny','PISTOL'),
    ('Shalashaska','itempool_jak_ps_05_legendary_Shalashaska_shiny','PISTOL'),
    ('Noisy Cricket','itempool_ord_ps_05_legendary_NoisyCricket_shiny','PISTOL'),
    ('Roulette','itempool_ord_ps_05_legendary_Roulette_shiny','PISTOL'),
    ('Stray','itempool_bor_sr_05_legendary_Stray_shiny','SNIPER'),
    ('Tankbuster','itempool_bor_sr_05_legendary_tankbuster_shiny','SNIPER'),
    ('Vamoose','itempool_bor_sr_05_legendary_Vamoose_shiny','SNIPER'),
    ('Ballista','itempool_jak_sr_05_legendary_Ballista_shiny','SNIPER'),
    ('Boomslang','itempool_jak_sr_05_legendary_Boomslang_shiny','SNIPER'),
    ('Truck','itempool_jak_sr_05_legendary_Truck_shiny','SNIPER'),
    ('Complex Root','itempool_mal_sr_05_legendary_complex_root_shiny','SNIPER'),
    ('Katagawa','itempool_mal_sr_05_legendary_katagawa_shiny','SNIPER'),
    ('Manifest','itempool_mal_sr_05_legendary_manifest_shiny','SNIPER'),
    ('Fisheye','itempool_ord_sr_05_legendary_Fisheye_shiny','SNIPER'),
    ('Om', 'itempool_dad_ar_05_legendary_om_shiny', 'RIFLE'),
    ('Fishward', 'itempool_jak_ar_05_legendary_fishward_shiny', 'RIFLE'),
    ('Lucian', 'itempool_vla_ar_05_legendary_Lucian_shiny', 'RIFLE'),
    ('Wombo Combo', 'itempool_vla_ar_05_legendary_WomboCombo_shiny', 'RIFLE'),
    ('Lockjaw', 'itempool_tor_ar_05_legendary_lockjaw_shiny', 'RIFLE'),
    ('Potato Thrower', 'itempool_tor_ar_05_legendary_PotatoThrower_shiny', 'RIFLE'),
    ('Cold Shoulder', 'itempool_tor_ar_05_legendary_ColdShoulder_shiny', 'RIFLE'),
    ('Bugbear', 'itempool_tor_ar_05_legendary_Bugbear_shiny', 'RIFLE'),
    ('Fleabag', 'itempool_tor_ar_05_legendary_Fleabag_shiny', 'RIFLE'),
    ('Dual Damage', 'itempool_vla_ar_05_legendary_DualDamage_shiny', 'RIFLE'),
    ('Bubbles', 'itempool_vla_ar_05_legendary_bubbles_shiny', 'RIFLE'),
    ('Flash Cyclone', 'itempool_mal_sm_05_legendary_flashcyclone_shiny', 'SMG'),
    ('Bully', 'itempool_ord_ps_05_legendary_Bully_shiny', 'PISTOL'),
    ('Rocket Reload', 'itempool_ord_ps_05_legendary_RocketReload_shiny', 'PISTOL'),
    ('Ishmael', 'itempool_ord_sr_05_legendary_ishmael_shiny', 'SNIPER'),
    ('Asher', 'itempool_mal_sr_05_legendary_Asher_shiny', 'SNIPER'),
)
SPAWN_CATEGORIES=('ALL','SHOTGUN','SMG','RIFLE','PISTOL','SNIPER','FAVORITES','RECENT')

# Display names verified against Steam's public BL4 achievement catalogue.
# Deliberately excludes SetAchievement/StoreStats and any Steam DLL hooks.
ACHIEVEMENT_NAMES = tuple("Crimson Rising|Pop Out|False Idolator|Good Hunter|Long Live the Queen|As If Moved by an Occult Hand|The Lookbook is the Cookbook|Howling on the Moon|Everything Breaks|Master of Death and Dance|Glucose Guardian|Nothing Left to Guard|Reverse Abduction|Arena Grande|Unfaded|Mole Money, Mole Problems|Shoot the Moon|Pale Blueberry Dot|I Earned This|Who's the Boss?|Catch-A-Ride|Widely Beloved Mascot|Gear Five!|The Mountain Provides|Useful Citizen|Churn the Burn|Ruler of Everything|Hearthwarming|Sugar Wrath|Legally Unspecified Tincture|Hull Frozen Over|He Loved You|Freelance, but Not for Free|All Things Vend|The Demon's Domain|Find Me in the Rift|Cut That Out|Grassroots Campaigner|Brand Equity|Fist of the Mountain|Rift Incompatible|Does The Skag Die?|Bane of Zane|Area of Expertise|Guac is Extra|Gimme a Hand(s)|Murdered + Acquired|Dahl Cleanup Crew|Pay to Win|Harmony Awaits|Wild at Heart|Ordon't You Glad I Didn't Say Eridium|Reach Exceeded|Rift and Tear|Looking for Work at the Top of the World|AI Psychosis|Detoxed and Ready to Rock|Substation Satisfaction|Came Back Wrong|Vacation From My Vacation|The Full Flock|Thief in the Night|Tourism of Duty".split('|'))

def trophy_change_page(delta):
    max_page=max(0,(len(ACHIEVEMENT_NAMES)-1)//6)
    State.trophy_page=max(0,min(max_page,State.trophy_page+int(delta)))
    if State.opened:redraw()

def trophy_mark(index):
    # This sets only a LOCAL PERSONAL NOTE; does not grant achievements.
    if not (0<=index<len(ACHIEVEMENT_NAMES)):return False
    if index in State.trophy_marked:State.trophy_marked.remove(index)
    else:State.trophy_marked.add(index)
    save_preferences()
    log('JOURNAL ONLY // '+ACHIEVEMENT_NAMES[index][:35]+(' marked' if index in State.trophy_marked else ' unmarked'))
    if State.opened:redraw()
    return True

def waypoint_cycle_mode():
    State.waypoint_mode='SAVE' if State.waypoint_mode=='TRAVEL' else 'TRAVEL'
    State.travel_save_pending=None
    if State.opened:redraw()

def _profile_snapshot_r3():
    # Interface-only preferences: never copy game saves, money or actor data.
    return {'theme_index':State.theme_idx,'text_scale':State.font_scale,
            'opacity':State.panel_opacity,'scale':State.panel_scale,
            'art_mode':State.art_mode,'audio_mode':State.audio_mode,
            'audio_hover':State.audio_hover,'forge_search':State.spawn_search,
            'sfx_set':State.sfx_set,'hud_anchor':State.hud_anchor,
            'gamepad_icons':State.gamepad_icons,
            'toasts_enabled':State.toasts_enabled,'toast_duration':State.toast_duration,'toast_position':State.toast_position,'cursor_aid':State.cursor_aid,'cursor_coordinates':State.cursor_coordinates,
            'echo_appearance':{'background':State.background_opacity,'accent':State.custom_accent,'duration':State.transition_duration},
            'reduced_motion':State.reduced_motion,
            'tool_pins':list(State.tool_pins)}

FORGE_BLUEPRINT_SLOTS = (1,2,3)

def _validated_forge_blueprints(raw):
    """Keep only complete, safe, owned catalogue recipes. No raw serials/paths."""
    if not isinstance(raw,dict):return {}
    index={token:i for i,(_name,token,_cat) in enumerate(SPAWN_POOLS)}
    result={}
    for slot in FORGE_BLUEPRINT_SLOTS:
        item=raw.get(str(slot))
        if not isinstance(item,dict):continue
        token=item.get('pool')
        level=item.get('level')
        count=item.get('count')
        if (not isinstance(token,str) or token not in index
                or type(level) is not int or not 1<=level<=100
                or type(count) is not int or not 1<=count<=3):continue
        result[str(slot)]={'pool':token,'level':level,'count':count}
    return result

def forge_open_blueprints():
    """Open local preset controls; never arm or dispatch a game spawn."""
    State.spawn_pending=None
    State.spawn_expires=0.0
    State.spawn_view='BLUEPRINTS'
    State.forge_blueprint_pending=None
    State.forge_blueprint_pending_until=0.0
    if State.opened:redraw()
    return True

def forge_blueprints_browse():
    State.spawn_view='BROWSE'
    State.spawn_pending=None
    State.spawn_expires=0.0
    if State.opened:redraw()
    return True

def forge_close_blueprints():
    State.spawn_view='TOOLS' if _forge_selection() else 'BROWSE'
    State.forge_blueprint_pending=None
    State.forge_blueprint_pending_until=0.0
    State.spawn_pending=None
    State.spawn_expires=0.0
    if State.opened:redraw()
    return True

def forge_save_blueprint(slot):
    if type(slot) is not int or slot not in FORGE_BLUEPRINT_SLOTS:return False
    item=_forge_selection()
    if item is None:
        log('FORGE BLUEPRINT // Select a visible pool before saving.')
        return False
    recipe={'pool':item[1], 'level':int(State.spawn_level),
            'count':int(State.spawn_count)}
    # Overwriting a saved loadout requires a second press within six seconds.
    # Store only the exact pending recipe: changing levels or items resets it.
    current=_validated_forge_blueprints(State.forge_blueprints).get(str(slot))
    pending=(slot,recipe['pool'],recipe['level'],recipe['count'])
    now=time.monotonic()
    if (current is not None and current!=recipe and
            (State.forge_blueprint_pending!=pending or
             now>=State.forge_blueprint_pending_until)):
        State.forge_blueprint_pending=pending
        State.forge_blueprint_pending_until=now+6.0
        log('CONFIRM BLUEPRINT %d OVERWRITE // Press SAVE again within 6 seconds.'%slot)
        if State.opened:redraw()
        return False
    State.forge_blueprint_pending=None
    State.forge_blueprint_pending_until=0.0
    State.forge_blueprints[str(slot)]=recipe
    State.forge_blueprints=_validated_forge_blueprints(State.forge_blueprints)
    if str(slot) not in State.forge_blueprints:return False
    State.spawn_pending=None
    State.spawn_expires=0.0
    save_preferences()
    log('BLUEPRINT '+str(slot)+' SAVED // Local Forge settings only; no item spawned.')
    if State.opened:redraw()
    return True

def forge_load_blueprint(slot):
    if type(slot) is not int or slot not in FORGE_BLUEPRINT_SLOTS:return False
    saved=_validated_forge_blueprints(State.forge_blueprints).get(str(slot))
    if saved is None:
        log('FORGE BLUEPRINT // Slot unavailable or invalid; nothing changed.')
        return False
    # Commit only after every field is checked; a failed preset must be atomic.
    choice=next((i for i,(_,token,_) in enumerate(SPAWN_POOLS)
                 if token==saved['pool']),None)
    if choice is None:return False
    State.spawn_pending=None
    State.spawn_expires=0.0
    State.forge_blueprint_pending=None
    State.forge_blueprint_pending_until=0.0
    State.spawn_pool_idx=choice
    State.spawn_level=saved['level']
    State.spawn_count=saved['count']
    State.spawn_category_idx=SPAWN_CATEGORIES.index('ALL')
    State.spawn_search=''  # Always reveal the loaded pool, even from stale filters.
    State.spawn_page=_spawn_visible_indices().index(choice)//max(1,forge_page_capacity())
    State.spawn_view='TOOLS'
    log('BLUEPRINT '+str(slot)+' LOADED // '+SPAWN_POOLS[choice][0]+
        ', LV'+str(State.spawn_level)+', x'+str(State.spawn_count)+' STAGED ONLY.')
    if State.opened:redraw()
    return True

def save_ui_profile(slot):
    # Named UI profiles are NOT save editor profiles and never touch character files.
    if slot not in (1,2,3):return False
    State.ui_profiles[str(slot)]=profile_snapshot()
    State.current_ui_profile=slot
    save_preferences()
    log('UI PROFILE '+str(slot)+' SAVED // No character data changed.')
    _queue_toast('PROFILE_SAVED')
    if State.opened:redraw()
    return True

def _load_ui_profile_r3(slot):
    if slot not in (1,2,3):return False
    data=State.ui_profiles.get(str(slot))
    if not isinstance(data,dict):
        log('UI PROFILE '+str(slot)+' is empty; save one first.')
        return False
    try:
        # Every field must validate before *any* of the active UI is changed.
        # A malformed or old profile cannot leave theme/scale half-updated.
        extra=_appearance_extra_validate(data.get('echo_appearance',{}))
        theme=int(data['theme_index'])
        if not 0<=theme<len(THEMES):raise ValueError('theme outside known palette')
        scale=_finite_setting(data['scale'],.72,2.00,1.0)
        font=_finite_setting(data['text_scale'],.85,1.25,1.0)
        opacity=_finite_setting(data['opacity'],.65,1.0,.94)
        search=_clean_forge_query(data.get('forge_search',''))
        if not isinstance(data.get('forge_search',''),str):raise ValueError('search is not text')
        mode='SHAPES' if data.get('art_mode')=='SHAPES' else 'AUTO'
        audio=data.get('audio_mode')
        if audio not in ('OFF','LOW','NORMAL','HIGH'):audio='LOW'
        hover=bool(data.get('audio_hover',False))
        pad_icons=data.get('gamepad_icons','XBOX')
        if pad_icons not in ('XBOX','PLAYSTATION'):raise ValueError('invalid gamepad icon family')
        sound_set=data.get('sfx_set','CLASSIC')
        if sound_set not in ('CLASSIC','ECHO'):raise ValueError('unknown sound pack')
        hud_anchor=data.get('hud_anchor','TOP_CENTRE')
        if hud_anchor not in ('TOP_CENTRE','LEFT_MIDDLE','RIGHT_MIDDLE'):
            raise ValueError('unknown status ribbon position')
        if any(type(data.get(k,True)) is not bool for k in ('toasts_enabled','cursor_aid')):
            raise ValueError('invalid interface toggle')
        toast_pref=data.get('toasts_enabled',True)
        cursor_pref=data.get('cursor_aid',True)
        cursor_coordinates=data.get('cursor_coordinates','AUTO')
        if cursor_coordinates not in ('AUTO','NATIVE'):raise ValueError('invalid cursor coordinate mode')
        toast_duration=_finite_setting(data.get('toast_duration',4.2),2.0,8.0,4.2)
        toast_position=data.get('toast_position','TOP_CENTRE')
        if toast_position not in ('TOP_CENTRE','TOP_LEFT','TOP_RIGHT'):raise ValueError('invalid popup position')
        pins=_validate_tool_pins(data.get('tool_pins',[]))
    except (ValueError,TypeError,KeyError,OverflowError):
        log('UI PROFILE '+str(slot)+' invalid; existing appearance preserved.')
        return False
    State.background_opacity=extra['background'];State.custom_accent=extra['accent'];State.transition_duration=extra['duration']
    State.reduced_motion=bool(data.get('reduced_motion',True))
    State.theme_idx=theme
    State.panel_scale=scale
    State.font_scale=font
    State.panel_opacity=opacity
    State.spawn_search=search
    State.art_mode=mode
    State.audio_mode=audio
    State.audio_hover=hover
    State.sfx_set=sound_set
    State.gamepad_icons=pad_icons
    State.hud_anchor=hud_anchor
    State.toasts_enabled=toast_pref
    State.toast_duration=toast_duration
    State.toast_position=toast_position
    State.cursor_aid=cursor_pref
    State.cursor_coordinates=cursor_coordinates
    State.tool_pins=pins
    State.cursor_last=State.mouse_last=None
    if not State.toasts_enabled:_dismiss_toast(clear_queue=True)
    State.current_ui_profile=slot
    save_preferences()
    log('UI PROFILE '+str(slot)+' LOADED // Display preferences only.')
    if State.hud_visible and State.hud_widget is not None:
        try:_place_hud(State.hud_widget)  # existing HUD only; never create another widget
        except Exception as error:
            record_runtime_fault('PROFILE_HUD_POSITION',error)
            hide_hud()
    if State.opened:redraw()
    return True

def gear_jump(category):
    if category not in SPAWN_CATEGORIES:return False
    State.spawn_category_idx=SPAWN_CATEGORIES.index(category)
    State.spawn_search=''
    State.spawn_page=0
    State.spawn_pending=None
    State.spawn_view='BROWSE'
    show_page('SPAWN') if State.opened else None
    log('FORGE FILTER // '+category)
    return True

def set_scale_preset(value):
    set_panel_scale(value)
    log('WINDOW SCALE // '+str(round(State.panel_scale*100))+'% (viewport-clamped)')

def toggle_controller_enabled():
    State.controller_enabled=not State.controller_enabled
    State.controller_mode=False
    State.controller_focus=-1
    State.controller_hold_start=0.0
    State.controller_last_keys={}
    State.controller_repeat_key=None
    State.controller_repeat_due=0.0
    save_preferences()
    log('GAMEPAD // '+('ENABLED' if State.controller_enabled else 'DISABLED')+
        ' / Keyboard F7 always works')
    if State.opened:redraw()

def apply_noir_preset():
    State.theme_idx=5
    State.panel_opacity=.89
    State.font_scale=1.12
    State.cursor_aid=True
    State.compact=False
    State.dock_right=False
    State.window_x=State.window_y=None
    save_preferences()
    log('CROWN NOIR // Translucent panels, readable text, cursor aid enabled.')
    if State.opened:redraw()

def apply_comfort_preset():
    """Balanced, readable setup that keeps space for every navigation row."""
    State.panel_scale=1.12
    State.font_scale=1.08
    State.compact=False
    State.dock_right=False
    State.window_x=State.window_y=None
    State.panel_opacity=.98
    save_preferences()
    log('DISPLAY // COMFORT applied: readable text, centered, high contrast')
    if State.opened:redraw()

def apply_couch_preset():
    # No gameplay data changed. The 200% limit is always viewport-clamped.
    State.panel_scale=1.82
    State.font_scale=1.20
    State.compact=False
    save_preferences()
    log('DISPLAY // Couch preset applied (screen-clamped)')
    if State.opened:redraw()

# New primary categories are a presentation layer over all 18 original
# handlers: no abilities, saves or gameplay actions are replaced by this map.
UI_CATEGORY_PAGES={
    'PLAYER':('PLAYER','MOTION','BOOSTS','COMBAT','PRESETS'),
    'WORLD':('WORLD','WEEKLY','EVENTS','PARTY','ARENA','COMMUNITY'),
    'FORGE':('SPAWN','GEAR','CONTENT'),
    'TRAVEL':('WAYPOINTS',),
    'FREEDOM':('LOOT','CAPACITY','TROPHIES'),
    'SETTINGS':('STYLE','DISPLAY','PROFILES','DEV','GUIDE','FINDER'),
}

STUDIO_SECTIONS={
    'Dashboard':('DASHBOARD',), 'Player':('PLAYER','MOTION','PRESETS'),
    'Combat':('COMBAT',), 'Weapons':('GEAR',), 'Forge':('SPAWN',),
    'Inventory':('CAPACITY',), 'Loot':('LOOT','WEEKLY','TROPHIES'),
    'Spawner':('ARENA',), 'Travel':('WAYPOINTS',), 'World':('WORLD','EVENTS','PARTY'),
    'HUD':('DISPLAY',), 'Profiles':('PROFILES',), 'Appearance':('STYLE',),
    'Settings':('GUIDE','FINDER','COMMUNITY'), 'Diagnostics':('DEV','CONTENT'),
}

def profile_rename_open():
    State.profile_name_draft=State.profile_names.get(str(State.current_ui_profile),'PROFILE '+str(State.current_ui_profile))
    State.profile_name_edit=True
    redraw()

def profile_rename_apply():
    field=State.profile_name_widget
    if field is None:return False
    try:value=str(field.GetText()).strip()
    except Exception:return False
    if not 1<=len(value)<=24 or not value.isprintable():
        log('PROFILE NAME // Use 1-24 printable characters.');return False
    State.profile_names[str(State.current_ui_profile)]=value
    State.profile_name_edit=False
    save_preferences();redraw()
    return True

def studio_section_for(page):
    return next((name for name,pages in STUDIO_SECTIONS.items() if page in pages),'Dashboard')

def studio_open_section(name):
    pages=STUDIO_SECTIONS.get(name)
    if not pages:return False
    return show_page(State.page if State.page in pages else pages[0])

def studio_rail_geometry(y,height):
    top=y+145;bottom=y+height-176
    pitch=min(65.,(bottom-top)/len(STUDIO_SECTIONS))
    return top,pitch,max(30.,pitch-7.)


def _studio_navigation_geometry(panel_x,panel_y,panel_width,panel_height,sidebar,category,steps=None):
    """Visible 2x3 department selector + dedicated one-column tool list.

    These coordinates are shared by actual UMG buttons and QA. Six tools must
    fit before the quickbar even at the minimum 680-unit panel height.
    """
    category_width=(sidebar-34.0)/2.0
    category_gap=5.0
    category_y=panel_y+159.0
    category_pitch=44.0 if panel_height>=790.0 else 41.0
    subpages=UI_CATEGORY_PAGES.get(category,())
    tool_y=category_y+category_pitch*3.0+34.0
    usable_bottom=panel_y+panel_height-164.0
    count=max(1,len(subpages))
    tool_pitch=max(28.0,min(43.0,(usable_bottom-tool_y-4.0)/count))
    # At 680 units: SETTINGS has six rows, each >=28 high with no overlap.
    return {'category_width':category_width,'category_gap':category_gap,
            'category_y':category_y,'category_pitch':category_pitch,
            'tool_y':tool_y,'tool_pitch':tool_pitch,'tool_bottom':usable_bottom,
            'list_count':len(subpages)}

# Evidence-level capability ledger: no entry here claims in-game verification.
# A reflected method or successful mock is *not* a confirmed BL4 gameplay effect.
# Keep this shared with the status screen and distribution audit; no game calls
# or expensive native introspection happen on a per-frame redraw.
PAGE_CAPABILITY_LEDGER={
    'PLAYER':('GAME REQUEST','Reflected player property and movement requests','Game-side readback + restore through deaths/travel'),
    'MOTION':('GAME REQUEST','Speed, jump and gravity adjustment attempts','Confirm actual movement and restore per BL4 build'),
    'BOOSTS':('SESSION GAME REQUEST','Hold F5 noclip speed boost and four staged movement presets','Verify native movement readback, key-release and restoration in BL4; level/perk edits not connected'),
    'COMMUNITY':('OPTIONAL MOD BRIDGE','Verified installed-mod names, direct developer-perk attempts and Bonk console requests','External modules must be separately installed/enabled; received commands and resulting game effects are unverified'),
    'COMBAT':('OWNED FIELD EDITOR','Combat/resource field drafts, temporary timed outgoing bonus and existing refill requests','Owned restoration, outside-change conflicts retained; native effects unverified'),
    'PRESETS':('REQUEST PRESETS','Local buttons applying existing gameplay requests','Verify resulting effects and undo in game'),
    'WORLD':('GAME REQUEST','World speed/time tuning and related tools','Verify world ownership and live change'),
    'WEEKLY':('TIME-LIMITED INFO','Stored weekly/vendor information and bookmark helper','Recheck rotation in game; dated information expires'),
    'EVENTS':('GAME REQUEST','Local training/challenge modifier presets','Verify game effects; not official BL4 events'),
    'PARTY':('RESTRICTED','Private-party tools with consent/session gates','Live host/target authority testing; do not assume safe'),
    'ARENA':('OPTIONAL MANAGED SPAWNER','Reviewed Arena lifecycle observer or CROWN BMS ownership ledger','Requires exact compatible loaded backend; Arena owns its cleanup; native acceptance pending'),
    'SPAWN':('REQUEST / NOT VERIFIED','Forge catalogue, inspector, staged two-click pool call','Native item creation, ground pickup and ownership readback'),
    'GEAR':('OWNED FIELD EDITOR','Six reflected weapon fields, staged presets and owned restoration','Selected actor may not be equipped; no parts/item-image backend; native acceptance pending'),
    'CONTENT':('READ ONLY','Local compatibility and game-content inspection','Actual DLC presence depends on active game data'),
    'WAYPOINTS':('LOCAL + GAME REQUEST','Saved travel slots and swept teleport requests','Live landing checks, map/actor validity and restoration'),
    'LOOT':('EXPERIMENTAL PROGRESSION','Confirmed wallet requests, total point allowances, optional reviewed level backend, XP comparisons','Persistent effects need native acceptance; no save rollback; level decreases blocked'),
    'CAPACITY':('OPTIONAL BRIDGE','BL4Live solo-only reads, guarded staged writes','Separate BL4Live; live capacity/persistence readback'),
    'TROPHIES':('LOCAL JOURNAL','CROWN-only achievement tracking checklist','Not connected to Steam achievements'),
    'STYLE':('LOCAL SETTINGS','Local visual preferences and art fallback','Actual imported artwork and rendering not certified'),
    'DISPLAY':('LOCAL SETTINGS','Viewport/menu size and accessibility controls','Real display scales and controller ergonomics'),
    'PROFILES':('LOCAL SETTINGS','Saved CROWN presets and staged Forge recipes','No edits to character save/profile entitlements'),
    'DEV':('LOCAL DIAGNOSTICS','Safe UI recovery, logs, feature ledger and export','Crash dump still needed for native crash attribution'),
    'GUIDE':('LOCAL GUIDE','Safety guidance and feature limitations','Reference only; does not mutate game state'),
    'FINDER':('LOCAL SEARCH','Search/index access to registered tool pages','Search does not prove underlying tools work'),
}
assert set(PAGE_CAPABILITY_LEDGER)==_KNOWN_PAGES-{'DASHBOARD'}

def toggle_feature_ledger():
    State.feature_ledger_open=not State.feature_ledger_open
    State.feature_ledger_index=max(0,min(len(PAGE_CAPABILITY_LEDGER)-1,State.feature_ledger_index))
    State.diag_open=False
    State.activity_open=False
    if State.opened:redraw()

def feature_ledger_step(direction):
    State.feature_ledger_index=(State.feature_ledger_index+int(direction))%len(PAGE_CAPABILITY_LEDGER)
    if State.opened:redraw()

def feature_ledger_selected_page():
    return tuple(p for pages in UI_CATEGORY_PAGES.values() for p in pages)[State.feature_ledger_index]

def open_feature_ledger_page():
    target=feature_ledger_selected_page()
    State.feature_ledger_open=False
    return show_page(target)

def _ui_category_for(page):
    for category,pages in UI_CATEGORY_PAGES.items():
        if page in pages:
            return category
    return 'PLAYER'

def show_category(category):
    pages=UI_CATEGORY_PAGES.get(category)
    if not pages:return
    # Keep the current page when clicking an already-active category.
    if State.page not in pages:
        show_page(pages[0])
    elif State.opened:
        redraw()

def toggle_nav_group():
    # Legacy hotkey compatibility for callers; new full UI uses six categories.
    State.nav_group={'CORE':'MORE','MORE':'VAULT','VAULT':'CORE'}.get(State.nav_group,'CORE')
    State.side_action_page=0
    State.page={'CORE':'PLAYER','MORE':'SPAWN','VAULT':'TROPHIES'}[State.nav_group]
    State.help_open=False
    redraw()

def _spawn_category():
    return SPAWN_CATEGORIES[State.spawn_category_idx]

def _clean_forge_query(raw):
    value=str(raw or '').lower().strip()[:40]
    return ''.join(ch for ch in value if ch.isalnum() or ch in " -_")

def _spawn_visible_indices():
    category=_spawn_category()
    if category=='ALL':
        indices=list(range(len(SPAWN_POOLS)))
    elif category=='FAVORITES':
        indices=[i for i,p in enumerate(SPAWN_POOLS) if p[1] in State.spawn_favorites]
    elif category=='RECENT':
        by_token={pool[1]:i for i,pool in enumerate(SPAWN_POOLS)}
        indices=[by_token[token] for token in State.spawn_recent if token in by_token]
    else:
        indices=[i for i,pool in enumerate(SPAWN_POOLS) if pool[2]==category]
    term=State.spawn_search
    if not term:
        return r16_sorted_pools(indices)
    return r16_sorted_pools([i for i in indices if all(word in (SPAWN_POOLS[i][0]+' '+SPAWN_POOLS[i][1]+' '+SPAWN_POOLS[i][2]).casefold() for word in term.split())])

def forge_open_search():
    State.spawn_view='SEARCH'
    State.spawn_search_draft=State.spawn_search
    State.spawn_pending=None
    State.spawn_expires=0.0
    State.search_widget=None
    if State.opened:redraw()

def forge_apply_search():
    widget_ref=State.search_widget
    if widget_ref is None:
        log('SEARCH UNAVAILABLE // Native input field did not load.')
        return False
    try:
        query=_clean_forge_query(widget_ref.GetText())
    except Exception as error:
        log('SEARCH FAILED // '+str(error)[:80])
        return False
    State.spawn_search=query
    State.spawn_search_draft=query
    State.spawn_page=0
    State.spawn_pending=None
    State.spawn_expires=0.0
    visible=_spawn_visible_indices()
    State.spawn_pool_idx=visible[0] if visible else -1
    State.spawn_view='BROWSE'
    State.search_widget=None
    save_preferences()
    log('FORGE SEARCH // '+(query or '(all)')+' / '+str(len(visible))+' matches')
    if State.opened:redraw()
    return True

def forge_search_preset(term):
    """Controller-friendly search: only filters the published curated catalogue.

    No typed object paths or unverified names can be spawned by this action.
    """
    # Quick choices are catalogue *categories*, not text terms; pool IDs
    # use short names such as _ps/_sg, so a literal 'pistol' query misses them.
    category=str(term).upper().strip()
    if category in SPAWN_CATEGORIES:
        State.spawn_category_idx=SPAWN_CATEGORIES.index(category)
        query=''
    else:
        query=_clean_forge_query(term)
    State.spawn_search=query
    State.spawn_search_draft=query
    State.spawn_page=0
    State.spawn_pending=None
    State.spawn_expires=0.0
    visible=_spawn_visible_indices()
    State.spawn_pool_idx=visible[0] if visible else -1
    State.spawn_view='BROWSE'
    State.search_widget=None
    save_preferences()
    log('FORGE QUICK FILTER // '+(category if category in SPAWN_CATEGORIES else (query or 'ALL'))+' / '+str(len(visible))+' candidates')
    if State.opened:redraw()
    return True

def forge_clear_search():
    State.spawn_search=''
    State.spawn_search_draft=''
    State.search_widget=None
    State.spawn_page=0
    State.spawn_pending=None
    State.spawn_expires=0.0
    visible=_spawn_visible_indices()
    State.spawn_pool_idx=visible[0] if visible else -1
    State.spawn_view='BROWSE'
    save_preferences()
    log('FORGE SEARCH // Cleared')
    if State.opened:redraw()

def forge_cancel_search():
    State.spawn_view='BROWSE'
    State.search_widget=None
    State.spawn_pending=None
    if State.opened:redraw()

def forge_lucky_pick():
    # Only pick from the currently filtered catalogue. Does NOT spawn anything.
    visible=_spawn_visible_indices()
    if not visible:
        log('LUCKY PICK // No matches. Clear search or change category.')
        return False
    State.lucky_counter+=1
    slot=random.randrange(len(visible))
    if len(visible)>1 and visible[slot]==State.spawn_pool_idx:
        slot=(slot+1)%len(visible)
    State.spawn_pool_idx=visible[slot]
    State.spawn_pending=None
    State.spawn_expires=0.0
    State.spawn_view='TOOLS'
    log('LUCKY PICK // '+SPAWN_POOLS[State.spawn_pool_idx][0]+' (not spawned)')
    if State.opened:redraw()
    return True

def forge_open_level():
    if _forge_selection() is None:
        log('LEVEL // Select a Forge item first.')
        return False
    State.spawn_view='LEVEL'
    State.level_draft=str(State.spawn_level)
    State.level_widget=None
    State.spawn_pending=None
    State.spawn_expires=0.0
    if State.opened:redraw()
    return True

def forge_cancel_level():
    State.spawn_view='TOOLS'
    State.level_widget=None
    if State.opened:redraw()

def forge_apply_level():
    field=State.level_widget
    if field is None:
        log('LEVEL // Numeric input unavailable on this SDK.')
        return False
    try:
        raw=str(field.GetText()).strip()
        if not raw.isascii() or not raw.isdigit() or len(raw)>3:
            raise ValueError('Use digits only, 1 to 100')
        requested=int(raw)
        if not 1<=requested<=100:
            raise ValueError('Level must be between 1 and 100')
    except Exception as error:
        log('LEVEL REJECTED // '+str(error)[:88])
        return False
    State.spawn_level=requested
    State.spawn_view='TOOLS'
    State.level_widget=None
    State.spawn_pending=None
    State.spawn_expires=0.0
    log('FORGE LEVEL // '+str(requested)+' / next spawn requires confirmation')
    if State.opened:redraw()
    return True

def forge_controller_step(delta):
    """Stepper and typed editor share ONE draft; never apply item creation."""
    if State.spawn_view!='LEVEL' or type(delta) is not int:return False
    # A user may type 42 then press + without applying text first. Respect it
    # when valid; never allow redraw's old GetText to undo the new step.
    if State.level_widget is not None:
        try:
            incoming=str(State.level_widget.GetText()).strip()
            if incoming.isascii() and incoming.isdigit() and 1<=int(incoming)<=100:
                State.level_draft=incoming
        except Exception:pass
    try:value=int(State.level_draft)
    except (TypeError,ValueError,OverflowError):value=State.spawn_level
    State.level_draft=str(max(1,min(100,value+delta)))
    State.level_widget=None  # old widget no longer owns the next draft
    State.spawn_pending=None
    State.spawn_expires=0.0
    if State.opened:redraw()
    return True

def forge_controller_commit():
    if State.spawn_view!='LEVEL':return False
    try:value=int(State.level_draft)
    except (TypeError,ValueError):return False
    if not 1<=value<=100:return False
    State.spawn_level=value
    State.spawn_view='TOOLS'
    State.level_widget=None
    State.spawn_pending=None
    State.spawn_expires=0.0
    log('FORGE LEVEL // '+str(value)+' staged, no item spawned')
    if State.opened:redraw()
    return True

def forge_set_level_preset(value):
    if int(value) not in (40,60,70,100):
        return False
    State.spawn_level=int(value)
    State.spawn_view='TOOLS'
    State.level_widget=None
    State.spawn_pending=None
    State.spawn_expires=0.0
    log('FORGE LEVEL // '+str(value)+' (preset)')
    if State.opened:redraw()
    return True

def toggle_activity():
    State.activity_open=not State.activity_open
    if State.opened:redraw()

def clear_activity():
    State.activity_history=[]
    log('ACTIVITY // Log cleared.')
    if State.opened:redraw()


FORGE_PAGE_SIZE=4

def forge_page_capacity():
    """Viewport-conditional density: more visible items in XXL, never footer overlap.

    The classic four-per-page Forge remains on compact views. All related
    pagination uses the same capacity per redraw, including selection return.
    """
    rect=State.panel_rect
    height=float(rect[3]) if rect is not None else 0.0
    if State.compact or height<760:return 4
    if height<870:return 6
    return 8

def forge_pages():
    visible=_spawn_visible_indices()
    return max(1,(len(visible)+forge_page_capacity()-1)//forge_page_capacity())

def forge_page_indices():
    visible=_spawn_visible_indices()
    State.spawn_page=max(0,min(State.spawn_page,forge_pages()-1))
    begin=State.spawn_page*forge_page_capacity()
    return visible[begin:begin+forge_page_capacity()]

def forge_change_page(direction):
    total=forge_pages()
    State.spawn_page=(State.spawn_page+int(direction))%total
    State.spawn_pending=None
    State.spawn_expires=0.0
    log('FORGE BROWSER // PAGE '+str(State.spawn_page+1)+'/'+str(total))
    if State.opened:redraw()

def forge_choose(slot):
    page=forge_page_indices()
    if int(slot)<0 or int(slot)>=len(page):
        log('FORGE // This item slot is empty.')
        return False
    State.spawn_pool_idx=page[int(slot)]
    State.spawn_view='TOOLS'
    State.spawn_pending=None
    State.spawn_expires=0.0
    name=SPAWN_POOLS[State.spawn_pool_idx][0]
    log('FORGE SELECTED // '+name+' / open workbench')
    if State.opened:redraw()
    return True

def forge_open_inspector():
    """Display a source-backed item card; does not contact or mutate BL4."""
    if _forge_selection() is None:
        log('INSPECTOR // Pick an item first.')
        return False
    State.spawn_view='INSPECT'
    State.spawn_pending=None
    State.spawn_expires=0.0
    if State.opened:redraw()
    return True

def forge_close_inspector():
    if State.spawn_view!='INSPECT':return False
    State.spawn_view='TOOLS'
    State.spawn_pending=None
    State.spawn_expires=0.0
    if State.opened:redraw()
    return True

def forge_inspector_values():
    """Published catalogue details ONLY; no fictional DPS/rarity/readback."""
    item=_forge_selection()
    if item is None:return None
    name,token,category=item
    return {'name':name,'pool':token,'category':category,
            'level':State.spawn_level,'quantity':State.spawn_count,
            'favourite':token in State.spawn_favorites,
            'backend':State.forge_stage,
            'verified':False}

def forge_toggle_view():
    if State.spawn_view=='TOOLS':
        # Return to the page containing the selected item if possible.
        visible=_spawn_visible_indices()
        if State.spawn_pool_idx in visible:
            State.spawn_page=visible.index(State.spawn_pool_idx)//forge_page_capacity()
        State.spawn_view='BROWSE'
    else:
        State.spawn_view='TOOLS'
    State.spawn_pending=None
    State.spawn_expires=0.0
    if State.opened:redraw()

def forge_cycle_category_reverse():
    cycle_spawn_category(-1)

def forge_readback():
    current=_forge_selection()
    if current is None:
        log('FORGE // No item selected in this filter.')
        return
    starred='YES' if current[1] in State.spawn_favorites else 'NO'
    log('FORGE // '+current[0]+', '+current[2]+', level '+str(State.spawn_level)
        +', x'+str(State.spawn_count)+', starred '+starred)

def toggle_spawn_favorite():
    visible=_spawn_visible_indices()
    idx=State.spawn_pool_idx
    if idx<0 or idx>=len(SPAWN_POOLS) or idx not in visible:
        log('FORGE FAVORITES // Choose a visible item first.');return False
    name,token,_category=SPAWN_POOLS[idx]
    if token in State.spawn_favorites:
        State.spawn_favorites.remove(token)
        is_favorite=False
    else:
        State.spawn_favorites.add(token)
        is_favorite=True
    # Old two-click confirmation must never survive a change of selection.
    State.spawn_pending=None
    State.spawn_expires=0.0
    save_preferences()
    current=_spawn_visible_indices()
    if current and idx not in current:
        State.spawn_pool_idx=current[0]
    log('FORGE // '+('FAVORITE SAVED: ' if is_favorite else 'FAVORITE REMOVED: ')+name)
    if State.opened:redraw()
    return True

def _forge_selection():
    visible=_spawn_visible_indices()
    if not visible or State.spawn_pool_idx not in visible:return None
    return SPAWN_POOLS[State.spawn_pool_idx]

def clear_spawn_recent():
    State.spawn_recent=[]
    State.spawn_pending=None
    log('FORGE // Recent requests cleared.')
    if State.opened:redraw()

def cycle_spawn_category(step=1):
    State.spawn_category_idx=(State.spawn_category_idx+int(step))%len(SPAWN_CATEGORIES)
    visible=_spawn_visible_indices()
    State.spawn_page=0
    if visible:State.spawn_pool_idx=visible[0]
    State.spawn_pending=None
    State.spawn_expires=0.0
    log('FORGE CATEGORY // '+_spawn_category()+' / '+str(len(visible))+' choices')
    if State.opened:redraw()

def cycle_spawn_pool(step=1):
    visible=_spawn_visible_indices()
    if not visible:
        log('FORGE // No items in selected category')
        return
    previous=visible.index(State.spawn_pool_idx) if State.spawn_pool_idx in visible else -1
    State.spawn_pool_idx=visible[(previous+int(step))%len(visible)]
    State.spawn_pending=None
    State.spawn_expires=0.0
    log('FORGE ITEM // '+SPAWN_POOLS[State.spawn_pool_idx][0]+' / '+
        str(visible.index(State.spawn_pool_idx)+1)+' of '+str(len(visible)))
    if State.opened:redraw()

def adjust_spawn_level(delta):
    State.spawn_level=max(1,min(100,int(State.spawn_level)+int(delta)))
    State.spawn_pending=None
    log('ITEM LEVEL // '+str(State.spawn_level))
    if State.opened:redraw()

def adjust_spawn_count(delta):
    """Bounded Forge batch stepper; never writes to the game."""
    previous=State.spawn_count
    try:
        shift=int(delta)
        if type(delta) is bool: return False
    except (ValueError,TypeError,OverflowError): return False
    State.spawn_count=max(1,min(3,int(previous)+shift))
    State.spawn_pending=None
    State.spawn_expires=0.0
    State.forge_stage='STAGED_NOT_SPAWNED'
    log('FORGE QUANTITY STAGED // '+str(State.spawn_count)+' / max 3 / no item created')
    if State.opened:redraw()
    return State.spawn_count!=previous

def toggle_spawn_count():
    return adjust_spawn_count(1 if State.spawn_count<3 else -2)

def reset_spawn_settings():
    State.spawn_level=40
    State.spawn_category_idx=0
    State.spawn_page=0
    State.spawn_view="BROWSE"
    State.spawn_pool_idx=0
    State.spawn_count=1
    spawn_clear()
    if State.opened:redraw()
def cycle_spawn_placement():
    """Cycle spawn placement: FRONT -> FEET -> CROSSHAIR -> FRONT."""
    options = ('FRONT', 'FEET', 'CROSSHAIR')
    current = getattr(State, 'spawn_placement', 'FRONT')
    try:
        idx = options.index(current)
    except ValueError:
        idx = 0
    State.spawn_placement = options[(idx + 1) % len(options)]
    log('SPAWN PLACEMENT // ' + State.spawn_placement)
    if State.opened: redraw()
def spawn_placement_label():
    """Human-readable spawn placement description."""
    labels = {'FRONT': 'In front of player', 'FEET': 'At player feet', 'CROSSHAIR': 'At crosshair/aim'}
    return labels.get(getattr(State, 'spawn_placement', 'FRONT'), 'In front of player')



def spawn_clear():
    State.spawn_pending=None
    State.spawn_expires=0.0
    log('SPAWN // Confirmation cleared')

def _spawn_api():
    # Never dereference hard-coded pointers/offsets or scan on a tick.
    try:
        objs=unrealsdk.find_all('NexusConfigStoreItemPool',False)
        if not objs:
            log('SPAWN API // No item-pool config found. DLC/build may differ.')
            return None
        for ob in reversed(list(objs)[-30:]):
            fn=getattr(ob,'SpawnInventoryFromItemPool',None)
            if callable(fn):return ob
        log('SPAWN API // Native item-pool method unavailable')
        return None
    except Exception as exc:
        log('SPAWN API FAILED // '+str(exc)[:100])
        return None

def spawn_probe():
    if session_role()!='SOLO':
        log('SPAWN CHECK // Solo only until multiplayer is validated.')
        return False
    if pawn() is None:
        log('SPAWN CHECK // Player not loaded.')
        return False
    ok=_spawn_api() is not None
    if ok:log('SPAWN CHECK // Native item-pool method exists. No item spawned.')
    return ok

def forge_preflight():
    """Read-only Forge readiness; never grants items or arms a drop.

    A positive API check is not proof of an actual delivered item. This
    command guards every step required for the two-click item-pool request.
    """
    State.spawn_pending=None
    State.spawn_expires=0.0
    if (getattr(State,'forge_uncertain_anchor',None) is not None
            and State.forge_uncertain_anchor==_session_anchor()):
        State.forge_stage='UNCERTAIN_REQUEST_QUARANTINED'
        log('FORGE PRECHECK BLOCKED // An earlier native request may have delivered items; no repeat in this session.')
        return False
    if not is_local_host_action():
        State.forge_stage='BLOCKED_NOT_LOCAL_HOST'
        log('FORGE PRECHECK // Solo or verified local host required. Nothing spawned.')
        return False
    actor=pawn()
    world,_=world_and_state()
    if actor is None or world is None:
        State.forge_stage='WORLD_OR_PLAYER_UNAVAILABLE'
        log('FORGE PRECHECK // No loaded player or world. Nothing spawned.')
        return False
    if _forge_selection() is None:
        State.forge_stage='NO_ITEM_SELECTED'
        log('FORGE PRECHECK // Pick a catalogue item. Nothing spawned.')
        return False
    position=_actor_world_position(actor)
    if position is None:
        State.forge_stage='POSITION_API_UNAVAILABLE'
        log('FORGE PRECHECK // Actor world-location API unavailable. Nothing spawned.')
        return False
    try:
        direction=_actor_forward_xy(actor)
        location=unrealsdk.make_struct('Vector',
            X=float(position.X)+direction[0]*220.,
            Y=float(position.Y)+direction[1]*220.,
            Z=float(position.Z)+65.)
        transform=_spawn_transform(actor,location)
        if transform is None:
            State.forge_stage='TRANSFORM_API_UNAVAILABLE'
            log('FORGE PRECHECK // Transform struct unavailable. Nothing spawned.')
            return False
    except Exception as error:
        State.forge_stage='TRANSFORM_API_UNAVAILABLE'
        log('FORGE PRECHECK // '+type(error).__name__+' while preparing transform; no spawn.')
        return False
    if _spawn_api() is None:
        State.forge_stage='POOL_API_UNAVAILABLE'
        log('FORGE PRECHECK // Item-pool API unavailable. Nothing spawned.')
        return False
    State.forge_stage='READY_NOT_SPAWNED'
    log('FORGE PRECHECK READY // Position + transform + pool API exist. No item spawned.')
    return True

def _actor_world_position(actor):
    """UE reflected K2 API differs across BL4 builds. Never assume a method."""
    for method_name in ('K2_GetActorLocation','GetActorLocation'):
        try:
            method=getattr(actor,method_name,None)
            if callable(method):
                value=method()
                if all(math.isfinite(float(getattr(value,k))) for k in ('X','Y','Z')):
                    return value
        except Exception:
            continue
    return None

def _actor_forward_yaw(actor):
    for method_name in ('K2_GetActorRotation','GetActorRotation'):
        try:
            method=getattr(actor,method_name,None)
            if callable(method):
                angle=float(method().Yaw)
                if math.isfinite(angle):return angle
        except Exception:continue
    return 0.0

def _actor_aim_location(actor):
    """Determine a valid world placement location from the crosshair/aim.

    Uses a forward collision trace from the camera/player viewpoint to find
    a valid surface, rather than merely returning the camera position.
    Falls back to a forward offset from the player if tracing is unavailable.
    Returns a Vector-like object or None.
    """
    # 1. Try player controller line trace to a surface
    try:
        pc = get_pc(possibly_loading=True)
        if pc is not None:
            # Try to get camera location and rotation
            cam_loc = None
            cam_rot = None
            for loc_method in ('GetPlayerViewPoint', 'GetCameraLocation', 'GetPawnViewLocation'):
                m = getattr(pc, loc_method, None)
                if callable(m):
                    try:
                        result = m()
                        if result is not None:
                            if hasattr(result, 'Location'):
                                cam_loc = result.Location
                                if hasattr(result, 'Rotation'):
                                    cam_rot = result.Rotation
                            elif hasattr(result, 'X') and hasattr(result, 'Y') and hasattr(result, 'Z'):
                                cam_loc = result
                            break
                    except Exception:
                        pass
            # Try actor eyes view point
            if cam_loc is None:
                m = getattr(actor, 'GetActorEyesViewPoint', None)
                if callable(m):
                    try:
                        result = m()
                        if result is not None and hasattr(result, 'Location'):
                            cam_loc = result.Location
                            if hasattr(result, 'Rotation'):
                                cam_rot = result.Rotation
                    except Exception:
                        pass
            # If we have a camera location, do a forward trace
            if cam_loc is not None:
                # Calculate forward direction from rotation or actor forward
                fwd = None
                if cam_rot is not None:
                    try:
                        # Convert rotation to forward vector
                        import math
                        yaw = math.radians(getattr(cam_rot, 'Yaw', 0.0))
                        pitch = math.radians(getattr(cam_rot, 'Pitch', 0.0))
                        fwd = (math.cos(pitch) * math.cos(yaw),
                               math.cos(pitch) * math.sin(yaw),
                               math.sin(pitch))
                    except Exception:
                        pass
                if fwd is None:
                    fwd = _actor_forward_xy(actor)
                    fwd = (fwd[0], fwd[1], 0.3)  # slight upward bias
                # Trace forward up to 5000 units
                try:
                    trace_end = unrealsdk.make_struct('Vector',
                        X=float(cam_loc.X if hasattr(cam_loc, 'X') else cam_loc[0]) + fwd[0] * 5000.0,
                        Y=float(cam_loc.Y if hasattr(cam_loc, 'Y') else cam_loc[1]) + fwd[1] * 5000.0,
                        Z=float(cam_loc.Z if hasattr(cam_loc, 'Z') else cam_loc[2]) + fwd[2] * 5000.0)
                    # Try LineTraceSingle or similar
                    for trace_method in ('LineTraceSingle', 'LineTraceSingleByChannel', 'K2_LineTraceSingle'):
                        m = getattr(pc, trace_method, None)
                        if callable(m):
                            try:
                                hit = m(cam_loc, trace_end)
                                if hit is not None and hasattr(hit, 'Location'):
                                    return hit.Location
                                if hit is not None and hasattr(hit, 'X'):
                                    return hit
                            except Exception:
                                pass
                except Exception:
                    pass
                # If trace failed, use a forward offset from camera
                try:
                    fwd_xy = _actor_forward_xy(actor)
                    return unrealsdk.make_struct('Vector',
                        X=float(cam_loc.X if hasattr(cam_loc, 'X') else cam_loc[0]) + fwd_xy[0] * 500.0,
                        Y=float(cam_loc.Y if hasattr(cam_loc, 'Y') else cam_loc[1]) + fwd_xy[1] * 500.0,
                        Z=float(cam_loc.Z if hasattr(cam_loc, 'Z') else cam_loc[2]))
                except Exception:
                    pass
    except Exception:
        pass
    # 2. Fallback: use actor position + forward offset
    try:
        origin = _actor_world_position(actor)
        if origin is not None:
            fwd = _actor_forward_xy(actor)
            return unrealsdk.make_struct('Vector',
                X=float(origin.X) + fwd[0] * 500.0,
                Y=float(origin.Y) + fwd[1] * 500.0,
                Z=float(origin.Z) + 65.0)
    except Exception:
        pass
    return None
def _actor_forward_xy(actor):
    """Try the actor's reflected world-forward vector before yaw fallback.

    No direct pointer casts. Return identity direction only if every known
    reflected approach fails; the drop remains in a known safe local offset.
    """
    for method_name in ('GetActorForwardVector','K2_GetActorForwardVector'):
        try:
            fn=getattr(actor,method_name,None)
            if not callable(fn):continue
            value=fn()
            x,y=float(value.X),float(value.Y)
            length=math.hypot(x,y)
            if math.isfinite(length) and length>0.01 and length<10000:
                return (x/length,y/length)
        except Exception:continue
    yaw=math.radians(_actor_forward_yaw(actor))
    return (math.cos(yaw),math.sin(yaw))

def _spawn_transform(actor,location):
    """Construct a fresh FTransform; BL4 OakCharacter lacks K2_GetActorTransform.

    On a build that does expose an actor transform, clone its scale/rotation.
    Otherwise produce the identity quaternion and unit scale. No ctypes or
    hardcoded pointers; SDK struct construction fails closed on unsupported APIs.
    """
    original=None
    for method_name in ('GetActorTransform','K2_GetActorTransform'):
        try:
            method=getattr(actor,method_name,None)
            if callable(method):
                candidate=method()
                if candidate is not None:
                    original=candidate
                    break
        except Exception:pass
    try:
        rotation=getattr(original,'Rotation',None) if original is not None else None
        if rotation is None:
            rotation=unrealsdk.make_struct('Quat',X=0.,Y=0.,Z=0.,W=1.)
        scale=getattr(original,'Scale3D',None) if original is not None else None
        if scale is None:
            scale=unrealsdk.make_struct('Vector',X=1.,Y=1.,Z=1.)
        result=unrealsdk.make_struct('Transform',Rotation=rotation,Translation=location,Scale3D=scale)
        if getattr(result,'Translation',None) is None:
            raise ValueError('Unreal FTransform Translation unavailable')
        return result
    except Exception as error:
        log('SPAWN TRANSFORM UNSUPPORTED // '+type(error).__name__+'; use current Oak2 SDK')
        return None

def spawn_request():
    # Two-click, SOLO or verified local host, fixed catalogue, capped batch count; no save rollback.
    if (type(State.spawn_level) is not int or not 1<=State.spawn_level<=100
            or type(State.spawn_count) is not int or not 1<=State.spawn_count<=3):
        State.forge_stage='INVALID_DRAFT';State.spawn_pending=None
        log('FORGE BLOCKED // Level 1–100 and quantity 1–3 must be whole numbers.');return False
    if not is_local_host_action():
        State.forge_stage='BLOCKED_NOT_LOCAL_HOST'
        log('SPAWN BLOCKED // Requires solo or verified local host session.');return False
    if getattr(State,'forge_uncertain_anchor',None)==_session_anchor():
        State.forge_stage='UNCERTAIN_REQUEST_QUARANTINED'
        log('FORGE BLOCKED // Previous call may have dropped items. Check ground; travel before another request.');return False
    actor=pawn()
    if actor is None:
        State.forge_stage='NO_PLAYER'
        log('SPAWN BLOCKED // No playable character.');return False
    world,_gs=world_and_state()
    if world is None:
        State.forge_stage='NO_WORLD'
        log('SPAWN BLOCKED // No active game world.');return False
    selected=_forge_selection()
    if selected is None:
        State.forge_stage='NO_SELECTION'
        log('SPAWN BLOCKED // Pick a weapon in the current filter.');return False
    current=(selected[1],State.spawn_level,State.spawn_count,
             map_tag(),_native_address(world) or id(world),_native_address(actor) or id(actor))
    now=time.monotonic()
    if State.spawn_pending!=current or now>=State.spawn_expires:
        State.spawn_pending=current
        State.forge_stage='ARMED_AWAITING_CONFIRM'
        State.spawn_expires=now+8.0
        log('CONFIRM SPAWN // '+selected[0]+' x'+str(State.spawn_count)+
            ' LV'+str(State.spawn_level)+' / click again')
        if State.opened:redraw()
        return False
    State.spawn_pending=None
    State.spawn_expires=0.0
    if now<State.anti_spam_until:
        State.forge_stage='COOLDOWN'
        log('SPAWN COOLDOWN // Wait before trying another batch.');return False
    origin=_actor_world_position(actor)
    if origin is None:
        State.forge_stage='POSITION_API_UNAVAILABLE'
        log('SPAWN BLOCKED // Player position API unavailable.');return False
    placement=getattr(State,'spawn_placement','FRONT')
    if placement=='FEET':
        pass  # origin already at feet
    elif placement=='CROSSHAIR':
        try:
            aim=_actor_aim_location(actor)
            if aim is not None:
                origin=aim
        except Exception:
            pass  # Fall back to front placement
    placement=getattr(State,'spawn_placement','FRONT')
    if placement=='FEET':
        # Spawn at player feet (no forward offset)
        pass  # origin already at feet
    elif placement=='CROSSHAIR':
        # Attempt crosshair/aim location; fall back to front if unavailable
        try:
            aim=_actor_aim_location(actor)
            if aim is not None:
                origin=aim
        except Exception:
            pass  # Fall back to front placement
    # Avoid consuming the cooldown until the prerequisites are ready.
    config=_spawn_api()
    if config is None:
        State.forge_stage='POOL_API_UNAVAILABLE'
        return False
    forward=_actor_forward_xy(actor)
    side=(-forward[1],forward[0])
    prepared=[]
    try:
        for i in range(min(3,State.spawn_count)):
            off=(i-(State.spawn_count-1)/2.0)*115.0
            loc=unrealsdk.make_struct('Vector',
                X=float(origin.X)+forward[0]*220.0+side[0]*off,
                Y=float(origin.Y)+forward[1]*220.0+side[1]*off,
                Z=float(origin.Z)+65.0)
            transform=_spawn_transform(actor,loc)
            if transform is None:
                State.forge_stage='TRANSFORM_API_UNAVAILABLE'
                log('SPAWN BLOCKED // Could not prepare a valid FTransform.');return False
            prepared.append(transform)
    except Exception as exc:
        State.forge_stage='POSITION_PREP_FAILED'
        log('SPAWN POSITION FAILED // '+type(exc).__name__)
        return False
    State.anti_spam_until=now+2.0
    complete=0;dispatch_anchor=_session_anchor()
    try:
        for transform in prepared:
            if dispatch_anchor is None or _session_anchor()!=dispatch_anchor or not is_local_host_action():raise RuntimeError('Forge context changed during batch')
            config.SpawnInventoryFromItemPool(world,transform,int(State.spawn_level),current[0])
            complete+=1
        State.forge_request_history=(State.forge_request_history+[{'pool':current[0],'level':int(State.spawn_level),'quantity':complete,'status':'REQUEST_ONLY'}])[-8:]
        State.spawn_requests+=complete
        State.forge_stage='REQUEST_SENT_NOT_VERIFIED'
        token=current[0]
        State.spawn_recent=[token]+[t for t in State.spawn_recent if t!=token][:9]
        State.spawn_last=selected[0]+' x'+str(complete)+' LV'+str(State.spawn_level)
        log('SPAWN REQUEST ACCEPTED // '+str(complete)+' '+selected[0]+'; check the ground')
        if State.opened:redraw()
        return complete>0
    except Exception as exc:
        # Native methods may have already created items before raising.
        State.forge_uncertain_anchor=dispatch_anchor
        State.forge_request_history=(State.forge_request_history+[{'pool':current[0],'level':int(State.spawn_level),'quantity':complete,'status':'UNCERTAIN_PARTIAL_POSSIBLE'}])[-8:]
        record_runtime_fault('FORGE_NATIVE_CALL',exc)
        State.forge_stage='SDK_EXCEPTION_PARTIAL_POSSIBLE'
        State.spawn_last='LAST REQUEST FAILED / partial drop possible'
        log('SPAWN FAILED // '+type(exc).__name__+': '+str(exc)[:78])
        return False

def start_event(event):
    if session_role()!='SOLO':
        log('EVENT BLOCKED // Solo sandbox only.');return False
    # CROWN-only training experiments; never mislabel them as official game events.
    choices={
        'BULLET BALLET':(.5,None,False,None),
        'HYPERDRIVE':(2.0,None,False,None),
        'MOON BOOTS':(1.0,.5,False,None),
        'LAST STAND':(1.0,None,True,None),
        'COSMIC SLO-MO':(.5,.5,False,None),
        'LOW GRAV DASH':(1.0,.5,False,2.0),
        'BULLET TIME RUN':(.5,None,False,2.0),
    }
    if event not in choices:return False
    if pawn() is None or world_and_state()[0] is None:
        log('EVENT BLOCKED // Load a playable solo map first.');return False
    stop_event(quiet=True)
    factor,gravity,god,run_speed=choices[event]
    if set_world_time(factor) is not True:
        log('EVENT NOT ACTIVATED // Time API rejected settings.');return False
    if gravity is not None and not tune_motion('gravity',gravity):
        restore()
        log('EVENT NOT ACTIVATED // Gravity unsupported; previous settings restored.')
        return False
    if run_speed is not None and not tune_motion('speed',run_speed):
        restore()
        log('EVENT NOT ACTIVATED // Movement unsupported; previous settings restored.')
        return False
    if god:
        set_god(True)
        if not State.god:
            restore()
            log('EVENT NOT ACTIVATED // Survival control unsupported.')
            return False
    State.active_event=event
    log('CROWN EVENT // '+event+' (solo session modifiers)')
    if State.opened:redraw()
    return True

def stop_event(quiet=False):
    # Restore all CROWN local session properties without tampering with saves.
    State.active_event='NONE'
    State.toast_suppress_restore=bool(quiet)
    try:restore()
    finally:State.toast_suppress_restore=False
    if not quiet:log('CROWN EVENT // Normal settings requested.')
    if State.opened:redraw()

def event_status():
    log('EVENT STATUS // '+State.active_event)

def reset_ui_defaults():
    # Restore the readable stable-release palette, not the old brown UI.
    State.theme_idx=0
    State.panel_opacity=.91
    State.panel_scale=1.06
    State.font_scale=1.06
    State.controller_enabled=True
    State.gamepad_icons='XBOX'
    State.compact=False
    State.dock_right=False
    State.window_x=State.window_y=None
    State.expand_theme=False
    State.art_mode='AUTO'
    State.art_failed.clear()
    State.art_fail_reasons.clear()
    save_preferences()
    log('UI // Stable high-contrast defaults restored')
    if State.opened:redraw()

# -----------------------------------------------------------------------------
# OPTIONAL CAPACITY STUDIO // BL4Live v0.10.30 local protocol, separate install.
# No native pointer/memory APIs copied into CROWN. No network on the game thread.
# -----------------------------------------------------------------------------
_CAPACITY_PORT=28777
_CAPACITY_MAX_REPLY=131072

def _capacity_read_exact(sock, amount):
    buf=bytearray()
    while len(buf)<amount:
        part=sock.recv(amount-len(buf))
        if not part:raise ConnectionError('bridge closed connection')
        buf.extend(part)
    return bytes(buf)

def _capacity_bridge_exchange(payload, connect_timeout=1.25):
    import socket as _socket, struct as _struct
    # The only permissible endpoint is local loopback; never user-controllable.
    body=json.dumps(payload,separators=(',',':')).encode('utf-8')
    if len(body)>2048:raise ValueError('request too long')
    with _socket.create_connection(('127.0.0.1',_CAPACITY_PORT),connect_timeout) as conn:
        conn.settimeout(4.5)
        conn.sendall(_struct.pack('>I',len(body))+body)
        size=_struct.unpack('>I',_capacity_read_exact(conn,4))[0]
        if not 0<size<=_CAPACITY_MAX_REPLY:raise ValueError('invalid bridge response length')
        result=json.loads(_capacity_read_exact(conn,size).decode('utf-8'))
        if not isinstance(result,dict):raise ValueError('non-object bridge reply')
        return result

def capacity_queue_request(kind, value=None):
    import threading as _threading
    # BL4Live's host can select remote players; avoid modifying someone else.
    if session_role()!='SOLO':
        log('CAPACITY // SOLO ONLY. A private co-op character target cannot be verified.')
        return False
    if kind not in ('PREFLIGHT','READ','APPLY'):return False
    if State.capacity_bridge_job is not None:
        log('CAPACITY // Waiting for previous backend reply.');return False
    anchor=_session_anchor()
    if anchor is None:
        log('CAPACITY // Load your solo character before using the bridge.');return False
    if kind=='APPLY':
        if type(value) is not int or not (value==0 or 20<=value<=5000):return False
        if State.capacity_mode=='BANK' and value==0:return False
        # This checks the public queue entry as well as the UI button: direct
        # callers must not bypass a current-session, recent inventory read.
        if (State.capacity_readback_anchor!=anchor or State.capacity_readback_at<=0
                or time.monotonic()-State.capacity_readback_at>30):
            log('CAPACITY // Fresh READ BAG / BANK SIZE required before a write.')
            return False
        container='BackpackItems' if State.capacity_mode=='BACKPACK' else 'BankItems'
        slots=State.capacity_occupied.get(container)
        if type(slots) is not int or slots<0 or (value and value<slots):
            log('CAPACITY // No valid slot count, or requested size below existing slots.')
            return False
        # Enforce the reset safety rule at the *backend boundary* too. A
        # scripted call to capacity_queue_request must not bypass the menu.
        if value==0:
            original=State.capacity_bag_original
            if (State.capacity_mode!='BACKPACK' or type(original) is not int
                    or not 20<=original<=5000 or original<slots):
                log('CAPACITY RESET BLOCKED // Verified original size is unknown or below existing slots.')
                return False
        # A backend write needs a complete trustworthy current size as well
        # as a slot count. A malformed container row cannot authorize it.
        live_size=State.capacity_readback.get(container)
        if type(live_size) is not int or not 0<=slots<=live_size<=5000:
            log('CAPACITY // Live container size missing or inconsistent; READ again.')
            return False
    req={'id':int(time.monotonic()*1000)%1000000000,'op':'info' if kind=='PREFLIGHT' else 'list' if kind=='READ' else 'runtime'}
    if kind=='APPLY':
        req['action']='set_backpack_size' if State.capacity_mode=='BACKPACK' else 'set_bank_size'
        req['value']=value
    State.capacity_bridge_generation+=1
    token=State.capacity_bridge_generation
    job={'kind':kind,'value':value,'mode':State.capacity_mode,'anchor':anchor,'token':token,'finished':False,'result':None}
    State.capacity_bridge_job=job
    State.capacity_status='REQUEST PENDING // '+kind
    def worker():
        try:
            answer=_capacity_bridge_exchange(req)
            # Sanitise; never store raw inventories, player IDs or other saves.
            if kind=='PREFLIGHT':
                result={'ok':answer.get('ok') is True,'write_enabled':answer.get('write_enabled') is True,'error':str(answer.get('error',''))[:110]}
            elif kind=='READ':
                rows=[]
                for item in answer.get('containers',[])[:12] if isinstance(answer.get('containers'),list) else []:
                    if isinstance(item,dict) and item.get('container') in ('BackpackItems','BankItems'):
                        rows.append({'container':item['container'],'max_size':item.get('max_size') if type(item.get('max_size')) is int else None,'slots':item.get('slots') if type(item.get('slots')) is int else None})
                result={'ok':answer.get('ok') is True,'containers':rows,'error':str(answer.get('error',''))[:110]}
            else:
                actual=answer.get('actual') if kind=='APPLY' and job['mode']=='BACKPACK' else answer.get('after')
                if type(actual) is not int:actual=None
                result={'ok':answer.get('ok') is True,'actual':actual,'error':str(answer.get('error',''))[:110]}
        except (OSError,ValueError,UnicodeError,OverflowError) as exc:
            result={'ok':False,'error':type(exc).__name__+': '+str(exc)[:100]}
        except Exception as exc:
            result={'ok':False,'error':type(exc).__name__+' / backend unavailable'}
        job['result']=result
        job['finished']=True
    _threading.Thread(target=worker,daemon=True,name='CROWN-LiveCapacity').start()
    log('CAPACITY // '+kind+' requested. Waiting for local bridge readback.')
    return True

def capacity_consume_result():
    job=State.capacity_bridge_job
    if not isinstance(job,dict) or not job.get('finished'):return False
    State.capacity_bridge_job=None
    if (job['token']!=State.capacity_bridge_generation or _session_anchor()!=job['anchor']
            or session_role()!='SOLO'):
        State.capacity_status='SESSION CHANGED / stale reply discarded'
        return False
    res=job.get('result') or {}
    if not res.get('ok'):
        if job['kind'] in ('READ','APPLY'):
            # A timed-out/failed read is NOT permission to reuse yesterday's
            # inventory count. It could be a changed character or container.
            State.capacity_readback.clear()
            State.capacity_occupied.clear()
            State.capacity_readback_anchor=None
            State.capacity_readback_at=0.0
            State.capacity_confirm=None
        State.capacity_status='BACKEND REFUSED // '+str(res.get('error','no response'))[:90]
        if job['kind'] in ('READ','APPLY'):
            State.capacity_status+=' // READ AGAIN before editing'
    elif job['kind']=='PREFLIGHT':
        State.capacity_status=('BRIDGE READY // runtime write available' if res.get('write_enabled') else 'BRIDGE READ ONLY // writes not confirmed')
    elif job['kind']=='READ':
        # Never combine partial/malformed bridge replies with stale values.
        State.capacity_readback.clear()
        State.capacity_occupied.clear()
        State.capacity_readback_anchor=None
        State.capacity_readback_at=0.0
        duplicates=set()
        for row in res.get('containers',[]):
            container=row.get('container')
            if container not in ('BackpackItems','BankItems'):continue
            if container in State.capacity_readback:
                duplicates.add(container)
                continue
            size,slots=row.get('max_size'),row.get('slots')
            if type(size) is int and type(slots) is int and 0<=slots<=size<=5000:
                State.capacity_readback[container]=size
                State.capacity_occupied[container]=slots
        for container in duplicates:
            State.capacity_readback.pop(container,None)
            State.capacity_occupied.pop(container,None)
        if State.capacity_occupied:
            State.capacity_readback_anchor=job['anchor']
            State.capacity_readback_at=time.monotonic()
            State.capacity_status='LIVE // BAG '+str(State.capacity_readback.get('BackpackItems','?'))+' / BANK '+str(State.capacity_readback.get('BankItems','?'))
            if State.capacity_bag_original is None and type(State.capacity_readback.get('BackpackItems')) is int:
                State.capacity_bag_original=State.capacity_readback['BackpackItems']
            if State.capacity_bank_original is None and type(State.capacity_readback.get('BankItems')) is int:
                State.capacity_bank_original=State.capacity_readback['BankItems']
        else:
            # Fixed cooked capacity overrides (e.g., 9999-slot PAKs) cannot be
            # safely combined with the bounded dynamic capacity editor.
            oversized=any(type(r.get('max_size')) is int and r['max_size']>5000
                          for r in res.get('containers',[]))
            State.capacity_status=('STATIC CAPACITY CONFLICT / remove fixed-size PAK, close BL4, restart and READ again'
                if oversized else 'READ INCOMPLETE // No valid live item counts. Apply disabled.')
    else:
        expected=job['value']
        actual=res.get('actual')
        if actual is None:
            State.capacity_status='BACKEND ACKNOWLEDGED / UNVERIFIED SIZE // '+job['mode']
        elif expected!=0 and actual!=expected:
            State.capacity_status='MISMATCH // requested '+str(expected)+', backend reports '+str(actual)
        else:
            State.capacity_status='BACKEND ACCEPTED // '+job['mode']+' '+str(actual)
        # A successful write makes the pre-write inventory snapshot obsolete.
        # Require fresh readback before ANY further modification.
        State.capacity_readback_anchor=None
        State.capacity_readback_at=0.0
        State.capacity_occupied.clear()
        State.capacity_status+=' // READ AGAIN to verify'
    log('CAPACITY // '+State.capacity_status)
    if State.opened and State.page=='CAPACITY' and State.capacity_view!='EDIT':redraw()
    return True

def capacity_mode_toggle():
    # A staged bank value must never overwrite the staged backpack value.
    # Switching containers does NOT send a runtime write.
    State.capacity_drafts[State.capacity_mode]=State.capacity_draft
    State.capacity_mode='BANK' if State.capacity_mode=='BACKPACK' else 'BACKPACK'
    State.capacity_confirm=None
    State.capacity_draft=State.capacity_drafts.get(State.capacity_mode,40)
    if State.opened:redraw()

def capacity_set_draft(value, refresh=True):
    if type(value) is not int or not 20<=value<=5000:return False
    State.capacity_draft=value
    State.capacity_drafts[State.capacity_mode]=value
    State.capacity_confirm=None
    if refresh and State.opened:redraw()
    return True

def capacity_edit_open():
    State.capacity_edit_original=State.capacity_draft
    State.capacity_text_draft=str(State.capacity_draft)
    State.capacity_view='EDIT'
    State.capacity_input=None
    State.capacity_confirm=None
    if State.opened:redraw()

def capacity_edit_cancel():
    # Keyboard entry never modifies the stored draft until Apply. A controller
    # stepper does; CANCEL must therefore roll back its pending changes.
    if type(State.capacity_edit_original) is int:
        State.capacity_draft=State.capacity_edit_original
        State.capacity_drafts[State.capacity_mode]=State.capacity_draft
    State.capacity_edit_original=None
    State.capacity_confirm=None
    State.capacity_view='BROWSE'
    State.capacity_input=None
    if State.opened:redraw()

def capacity_step(delta):
    """Stepper stays synchronised with the visible text field; NO SDK write."""
    if State.capacity_view!='EDIT' or type(delta) is not int:return False
    base=State.capacity_draft
    if State.capacity_input is not None:
        try:
            incoming=str(State.capacity_input.GetText()).strip()
            if incoming.isascii() and incoming.isdigit() and 20<=int(incoming)<=5000:
                base=int(incoming)
        except Exception:pass
    target=max(20,min(5000,base+delta))
    State.capacity_text_draft=str(target)
    State.capacity_input=None  # prevent a stale native field undoing our step
    return capacity_set_draft(target)

def capacity_step_commit():
    if State.capacity_view!='EDIT':return False
    State.capacity_edit_original=None
    State.capacity_view='BROWSE'
    State.capacity_input=None
    State.capacity_confirm=None
    log('CAPACITY // Staged '+State.capacity_mode+' '+str(State.capacity_draft)+' slots. Apply still requires live READ and two presses.')
    if State.opened:redraw()
    return True

def capacity_apply_text():
    field=State.capacity_input
    if field is None:
        log('CAPACITY // Numeric input unavailable in current SDK.');return False
    try:
        raw=str(field.GetText()).strip()
        if not raw.isascii() or not raw.isdigit() or len(raw)>4:raise ValueError('digits only')
        value=int(raw)
    except (ValueError,TypeError):
        log('CAPACITY // Enter digits from 20 to 5000.');return False
    if not 20<=value<=5000:
        log('CAPACITY // Capacity must be 20-5000.');return False
    State.capacity_draft=value
    State.capacity_drafts[State.capacity_mode]=value
    State.capacity_edit_original=None
    State.capacity_view='BROWSE'
    State.capacity_input=None
    if State.opened:redraw()
    return True

def capacity_numeric_input(parent,x,y,width,height):
    try:
        field=widget('EditableTextBox')
        put(parent,field)
        size_position(field,x,y,width,height,19)
        if not attempt(field,'SetText',State.capacity_text_draft):raise RuntimeError('EditableTextBox unavailable')
        call(field,'SetHintText','20 to 5000 slots')
        call(field,'SetIsReadOnly',False)
        call(field,'SetIsEnabled',True)
        call(field,'SetVisibility',0)
        try:field.ForegroundColor=linear(theme_color('text'))
        except Exception:pass
        try:field.BackgroundColor=linear(theme_color('muted'))
        except Exception:pass
        if not State.controller_mode:attempt(field,'SetKeyboardFocus')
        State.capacity_input=field
    except Exception:
        State.capacity_input=None
        log('CAPACITY // Use preset buttons if numeric input unavailable.')

def capacity_apply_request(reset=False):
    value=(0 if reset else State.capacity_draft)
    if State.capacity_mode=='BANK' and reset:
        value=State.capacity_bank_original
        if type(value) is not int or not 20<=value<=5000:
            log('CAPACITY // No verified original bank size. Read live status first.');return False
    if session_role()!='SOLO':
        log('CAPACITY // Solo only. Co-op selection could affect friends.');return False
    anchor=_session_anchor()
    if (anchor is None or State.capacity_readback_anchor!=anchor
            or State.capacity_readback_at<=0 or time.monotonic()-State.capacity_readback_at>30):
        State.capacity_confirm=None
        log('CAPACITY // READ BAG / BANK SIZE again (live values expire after 30 seconds).');return False
    source='BackpackItems' if State.capacity_mode=='BACKPACK' else 'BankItems'
    used=State.capacity_occupied.get(source)
    if type(used) is not int or used<0:
        log('CAPACITY // Could not verify existing inventory count; refusing the edit.');return False
    if value and value<used:
        log('CAPACITY BLOCKED // '+str(used)+' existing array slots > requested '+str(value)+'. Clear your inventory first.');return False
    if value==0 and State.capacity_mode=='BACKPACK':
        original=State.capacity_bag_original
        if type(original) is not int or not 20<=original<=5000 or original<used:
            log('CAPACITY // Original backpack capacity is unknown or below occupied slots; reset blocked.');return False
    now=time.monotonic()
    anchor=_session_anchor()
    key=(State.capacity_mode,value,anchor)
    if State.capacity_confirm!=key or now>=State.capacity_confirm_until:
        State.capacity_confirm=key
        State.capacity_confirm_until=now+8.0
        log('CONFIRM CAPACITY // Press again within 8 sec for '+State.capacity_mode+' '+str(value)+'; live only.')
        if State.opened:redraw()
        return False
    State.capacity_confirm=None
    return capacity_queue_request('APPLY',value)

class State:
    xp_external_view = False
    xp_external_confirm = None
    xp_external_status = 'NOT TESTED / Check optional XP mod first.'
    community_confirm = None
    community_status = 'Not checked / other mods must be installed separately.'
    opened = False
    root = None
    tree = None
    canvas = None
    page = "DASHBOARD"
    buttons = []
    frame_generation = 0
    native_history = []
    polling_ui = False
    combat_owner = None
    combat_originals = {}
    combat_last = {}
    combat_view = 'QUICK'
    numeric_editor = None
    numeric_widget = None
    appearance_draft = None
    appearance_preview = {}
    reduced_motion = True
    transition_started = 0.0
    transition_canvas = None
    palette_bindings = []
    studio_section = 'Dashboard'
    profile_name_widget = None
    profile_name_edit = False
    profile_names = {'1':'Desktop','2':'Controller','3':'Minimal'}
    last_poll = 0.0
    hook_active = False
    message = "READY // Back up your save before anything persistent."
    status_widget = None
    status_marker = None
    status_label = None
    status_kind = "IDLE"
    fov_selected = None
    jump_selected = 1.0
    gravity_selected = 1.0
    input_pc = None
    input_saved = None
    saved_char = None
    damage_original = None
    collision_original = None
    movement_original = 1
    god = False
    noclip = False
    noclip_boost_active = False
    noclip_boost_base = None
    noclip_boost_owner = None
    noclip_boost_anchor = None
    boost_preset = 'NONE'
    boost_status = 'READY / Choose a temporary local boost.'
    target_off = False
    infinite_ammo = False
    world_saved = None
    world_original = None
    world_last = None
    speed = 1.0
    fov_saved = None
    fov_original = None
    fov_last = None
    total_actions = 0
    theme_idx = 0  # Neon Vault on new installs; numeric saved themes still respected.
    nav_group = "CORE"
    trophy_page = 0
    maurice_slot_week = '' # Explicitly player-tagged slot 04; NEVER inferred from the weekly article.
    tool_pins = []  # Max 3 saved UI shortcuts; never actions or game writes.
    recent_tools = []  # Session-only navigation history (no save data).
    trophy_marked = set()  # User-maintained journal, NOT actual Steam achievement states.
    waypoint_mode = "TRAVEL"
    ui_profiles = {}
    current_ui_profile = 1
    spawn_pool_idx = 0
    spawn_category_idx = 0
    spawn_page = 0
    spawn_view = "BROWSE"
    spawn_placement = "FRONT"  # FRONT, FEET, CROSSHAIR
    spawn_search = ""
    spawn_search_draft = ""
    search_widget = None
    level_widget = None
    level_draft = "40"
    lucky_counter = 0
    activity_history = []
    toasts_enabled = True
    toast_queue = []
    toast_widget = None
    toast_expires = 0.0
    toast_last_code = ''
    toast_last_time = -10.0
    toast_render_failed = False
    toast_shown = 0
    toast_suppress_restore = False
    activity_open = False
    f10_down = False
    f9_down = False
    f9_last_action = 0.0
    f8_down = False
    controller_enabled = True
    gamepad_icons = 'XBOX'
    dock_mode = "FULL"
    dock_right = False
    side_action_page = 0  # Visible subset of quick actions; never silently hide choices.
    strict_input = True
    input_mode_used = "UNKNOWN"
    controller_mode = False
    controller_focus = -1
    controller_focus_outline = []
    controller_watcher_installed = False
    controller_hold_start = 0.0
    controller_open_latched = False
    controller_open_block_until = 0.0
    controller_poll_last = 0.0
    controller_last_keys = {}
    controller_repeat_key = None
    controller_repeat_due = 0.0
    esc_down = False
    f11_down = False
    arrow_keys_down = {}
    hover_poll_last = 0.0
    editor_enter_down = False

    capacity_mode = 'BACKPACK'
    capacity_draft = 40
    capacity_drafts = {'BACKPACK':40,'BANK':40}  # Separate per-mode staged values, never game writes.
    capacity_edit_original = None  # Cancel restores the stepper's old staged value.
    capacity_view = 'BROWSE'
    capacity_text_draft = '40'
    capacity_input = None
    capacity_bridge_job = None
    capacity_bridge_generation = 0
    capacity_status = 'NOT CONNECTED / install BL4Live separately'
    capacity_readback = {}
    capacity_occupied = {}
    capacity_readback_anchor = None
    capacity_readback_at = 0.0  # Monotonic freshness check; readbacks expire.
    capacity_confirm = None
    capacity_confirm_until = 0.0
    capacity_bank_original = None
    capacity_bag_original = None
    capacity_session_anchor = None
    spawn_last = "No item pool requests yet"
    forge_stage = "NOT_CHECKED"
    spawn_favorites = set()
    spawn_recent = []
    forge_blueprints = {}  # Three saved, inert catalogue recipes; never auto-spawn.
    forge_blueprint_pending = None
    forge_blueprint_pending_until = 0.0
    spawn_level = 40
    spawn_count = 1
    spawn_pending = None
    spawn_expires = 0.0
    spawn_requests = 0
    active_event = "NONE"
    ux_mode = "READABLE"
    capabilities = {}
    advanced_audit = {}
    advanced_audit_matches = {}
    advanced_audit_unix = None
    capabilities_checked_unix = None
    font_scale = 1.06
    compact = False
    flavor_idx = 0
    f7_down = False
    f6_down = False
    ui_warnings = []
    art_textures = {}
    art_failed = set()
    art_fail_reasons = {}
    art_mode = 'AUTO'  # AUTO attempts decorative images, SHAPES is lightweight.
    safe_mode = False  # Persistent one-switch native art/audio recovery.
    previous_menu_unclean = False
    previous_unclean_page = "UNKNOWN"
    previous_native_phase = "UNKNOWN"
    native_phase = 'START'
    art_status = "SHAPES / unchecked"
    art_archive_status = 'NOT CHECKED'
    art_drawn_count = 0
    # A redraw may import only a bounded number of never-before-seen textures.
    # Keep existing cached images and native shape fallback; no extra UMG tick.
    art_imports_this_frame = 0
    art_ambient_imports_this_frame = 0
    art_deferred = set()
    art_warmup_steps = 0
    art_warmup_due = 0.0
    status_chars = 74
    diag_open = False
    diag_page = 0
    feature_ledger_open = False
    feature_ledger_index = 0
    guide_status_open = False
    capability_page = 0
    capability_status_rows = []
    hovered_control = None
    # A/B and Enter can be seen by both raw polling and native UMG widgets.
    # Suppress the duplicate native release of THAT same button only.
    native_activation_widget = None
    native_activation_ignore_until = 0.0
    # A full raw/native press-release handshake, not a 350 ms debounce.
    native_activation_source = None
    native_activation_released_at = None
    native_activation_saw_native_press = False
    duplicate_native_releases_blocked = 0
    audio_mode = 'NORMAL'
    audio_hover = False
    sfx_set = 'ECHO'
    audio_status = 'UNCHECKED'
    audio_last = 0.0
    style_audio_open = False
    ammo_requests = 0
    confirm_kill_until = 0.0
    render_scale = 1.0
    background_opacity = .75
    custom_accent = None
    transition_duration = .16
    appearance_view = "MAIN"
    profile_name_draft = ""
    profile_manage = False
    profile_pending = None
    profile_pending_until = 0.
    resource_view = False
    resource_index = 0
    panel_opacity = .91
    cursor_aid = True
    cursor_shapes = []
    cursor_last = None
    mouse_last = None
    cursor_coordinates = 'AUTO'
    cursor_source = 'UNCHECKED'
    mouse_refresh_at = 0.0
    focus_refresh_at = 0.0
    input_move_ignored_original = None
    input_look_ignored_original = None
    input_last_status = "UNCHECKED"
    input_guard_confirmed = False
    input_mode_owned = False  # Sticky until close, even if recovery fails.
    focus_watch_at = 0.0
    focus_loss_count = 0
    focus_repair_count = 0
    # Foreground guard prevents stale UMG mouse/controller release activation
    # after an Alt+Tab, desktop notification, or a long game-frame pause.
    foreground_suspended = False
    foreground_resume_after = 0.0
    foreground_guard_count = 0
    panel_scale = 1.14
    window_x = None
    window_y = None
    drag_armed = False
    drag_origin = None
    drag_start = None
    drag_last = None
    drag_deadline = 0.0
    mouse_was_down = False
    sliders = []
    expand_theme = False
    help_open = False
    active_preview = False
    panel_rect = None
    _layout_dpi = 1.0
    draw_ok = False
    redraw_busy = False
    redraw_pending = False
    party = []
    party_selected = None
    party_approved = False   # Host asserts each currently connected friend has agreed.
    party_approved_roster = None
    remote_originals = {}   # Never persisted to disk.
    content_line = "Game content is queried live; no DLC unlock assumptions."
    motion_owner = None
    motion_originals = {}
    motion_last = {} # Last native values written by CROWN, never overwrite outside changes.
    motion_scale = 1.0
    checkpoints = {}  # Validated and persisted across game launches since v3.3.
    checkpoint_return = None  # Deliberately session-only.
    travel_recovery_anchor = None  # Last partial-movement safety origin; session-only.
    travel_last_state = 'NOT_CHECKED'
    travel_rollback_attempts = 0
    waypoint_page = 0
    travel_save_pending = None
    travel_save_expires = 0.0
    travel_cooldown_until = 0.0
    party_mode = "BOOSTS"
    friend_teleport_confirm = 0.0
    friend_teleport_target = None   # A confirmation belongs to one remote pawn, not just a timer.
    friend_teleport_anchor = None   # A loading/map transition invalidates every pending request.
    coop_last_status = "NOT CHECKED"
    hud_widget = None
    hud_label = None
    hud_subtitle = None
    hud_visible = False
    hud_anchor = 'TOP_CENTRE'
    hud_refresh_at = 0.0
    hud_last_summary = None
    finder_query = ''
    finder_draft = ''
    finder_input = None
    finder_mode = 'BROWSE'
    finder_page = 0
    toast_duration = 4.2
    toast_position = 'TOP_CENTRE'
    arena_planned_batch = 1  # Advice only; NEVER represented as an enforced BMS spawn limit.
    bms_last_open = -20.0
    bms_open_confirm_until = 0.0
    runtime_failures = []
    last_confirm_action = ""
    last_confirm_expires = 0.0
    wallet_pending = None
    wallet_expires = 0.0
    wallet_requests = 0
    wallet_last = "No reward requests yet"
    anti_spam_until = 0.0
    session_anchor = None
    session_last_check = 0.0
    session_resets = 0
    party_grant_armed = False
    prefs_recovered = False
    viewport_signature = None
    viewport_last_check = 0.0
    ui_error_count = 0
    ui_rebuild_count = 0
    ui_last_ms = 0.0
    ui_peak_ms = 0.0

def record_runtime_fault(stage,exc):
    """Opt-in QA export may include only the exception TYPE, never user data."""
    label=str(stage).upper().replace(' ','_')[:30]
    try:kind=type(exc).__name__[:50]
    except Exception:kind='UnknownError'
    State.runtime_failures.append({'stage':label,'kind':kind})
    State.runtime_fault_sites=({'stage':label,'kind':kind,'sites':r9_fault_sites(exc)})
    if len(State.runtime_failures)>12:del State.runtime_failures[:-12]

def log(message):
    State.message = str(message)[:150]
    upper=State.message.upper()
    if any(key in upper for key in ('FAILED','FAILURE','BLOCKED','ERROR','UNAVAILABLE','UNSUPPORTED','MISSING','REJECTED')):
        State.status_kind='ERROR'
    elif any(key in upper for key in ('CONFIRM','WAIT','COOLDOWN','WARNING','BACKUP','REQUIRES')):
        State.status_kind='CAUTION'
    elif 'REQUEST' in upper or 'UNVERIFIED' in upper or 'UNCONFIRMED' in upper:
        State.status_kind='INFO'
    elif any(key in upper for key in ('READBACK OK','READY','SAVED','REQUEST SENT','RESTORED','APPLIED',' ON ',' OFF ',' ON (',' OFF (')):
        State.status_kind='OK'
    else:
        State.status_kind='INFO'
    # In-memory only: no log file containing potentially personal player names.
    State.activity_history.append(State.message)
    if len(State.activity_history)>16:
        del State.activity_history[:-16]
    logging.info("[CROWNs Freedom] " + State.message)
    toast_code=_toast_from_result(State.message)
    if toast_code is not None:_queue_toast(toast_code)
    if State.status_widget is not None:
        try:
            width=getattr(State,'status_chars',75)
            State.status_widget.SetText(_status_brief(State.message,max(25,width-16)))
        except Exception:pass
    if State.status_marker is not None:
        try:State.status_marker.SetBrushColor(linear(_status_tint()))
        except Exception:pass
    if State.status_label is not None:
        try:State.status_label.SetText(_status_caption())
        except Exception:pass
    if State.hud_visible:
        update_hud()

# -------------------- Diegetic, noninteractive in-game notifications --------------------
# Toasts contain only CROWN action results, never arbitrary save contents,
# character/player names, or persistent gameplay changes. In particular, an
# accepted currency/item API REQUEST must never be called a verified grant.
TOAST_COPY = {
    'GOD_ON': ('GOD MODE // ACTIVE', 'Good luck dying. You might need it.', 'success'),
    'GOD_OFF': ('GOD MODE // OFF', 'Mortality has entered the chat.', 'info'),
    'NOCLIP_ON': ('NOCLIP // ACTIVE', 'Walls are more of a suggestion now.', 'success'),
    'NOCLIP_OFF': ('NOCLIP // OFF', 'Physics called. It wants its rules back.', 'info'),
    'MONEY_REQUEST': ('MONEY // REQUEST SENT', 'Ooo, a piece of money! Check your wallet.', 'caution'),
    'ERIDIUM_REQUEST': ('ERIDIUM // REQUEST SENT', 'Shiny purple rocks! Check your wallet.', 'caution'),
    'CONFIRM': ('ONE MORE CLICK', 'Press again before the confirmation expires.', 'caution'),
    'SPAWN_REQUEST': ('FORGE // REQUEST SENT', 'Check the ground, loot goblin. Drop not verified.', 'caution'),
    'TRAVEL': ('ROADRUNNER // ARRIVED', 'Fast travel, questionable driving. RETURN is ready.', 'success'),
    'EVENT': ('CHAOS // SESSION EVENT', 'Temporary chaos, responsibly irresponsible.', 'success'),
    'EVENT_STOP': ('CHAOS // STOP REQUESTED', 'Normal-ish service has resumed.', 'info'),
    'RESTORE': ('CROWN // RESTORE REQUESTED', 'Put the toys away. Verify the game state.', 'info'),
    'BLOCKED': ('CROWN // ACTION BLOCKED', 'No dice. Check the status bar for the reason.', 'error'),
    'TEST': ('CROWN // POPUP TEST', 'It works! Your regularly scheduled nonsense returns.', 'success'),
    'BOOKMARK_SAVED': ('ROADRUNNER // BOOKMARK SAVED', 'Marked. Future you owes present you a drink.', 'success'),
    'PROFILE_SAVED': ('UI PROFILE // SAVED', 'Pocketed your layout and style for later.', 'success'),
    'THEME_APPLIED': ('STYLE // APPLIED', 'Fresh paint, same bad decisions.', 'info'),
    'SAFE_ON': ('SAFE MODE // ON', 'Native-only fallback engaged. Pretty can wait.', 'caution'),
    'SAFE_OFF': ('SAFE MODE // OFF', 'Optional art and audio may strut again.', 'success'),
    'CURSOR_ON': ('CURSOR AID // ON', 'Lost cursor? Not on my watch.', 'info'),
    'CURSOR_OFF': ('CURSOR AID // OFF', "Raw doggin' the pointer now.", 'info'),
}

def cycle_toast_position():
    choices=('TOP_CENTRE','TOP_LEFT','TOP_RIGHT')
    State.toast_position=choices[(choices.index(State.toast_position)+1)%len(choices)]
    save_preferences()
    log('POPUP POSITION // '+State.toast_position.replace('_',' '))
    if State.opened:redraw()

def set_toast_duration(value):
    State.toast_duration=_finite_setting(value,2.0,8.0,4.2)
    save_preferences()
    log('POPUP DURATION // %.1fs'%State.toast_duration)
    if State.opened:redraw()

def _queue_toast(code, now=None):
    if code not in TOAST_COPY or not State.toasts_enabled:
        return False
    now=time.monotonic() if now is None else float(now)
    # Guard against duplicate native/raw button activations, and never queue
    # an endless flood of the same action on a long press.
    if code==State.toast_last_code and now-State.toast_last_time<1.0:
        return False
    State.toast_last_code=code
    State.toast_last_time=now
    State.toast_queue.append(code)
    if len(State.toast_queue)>3:
        State.toast_queue=State.toast_queue[-3:]
    return True

def _toast_from_result(message):
    """Recognize only precise status confirmations, not generic SDK success."""
    m=str(message).upper()
    if m.startswith('GOD MODE ON (READBACK OK)'):return 'GOD_ON'
    if m.startswith('GOD MODE OFF (READBACK OK)'):return 'GOD_OFF'
    if m.startswith('NOCLIP ON (COLLISION/DAMAGE READBACK OK'):return 'NOCLIP_ON'
    if m.startswith('NOCLIP OFF (COLLISION/DAMAGE READBACK OK'):return 'NOCLIP_OFF'
    if m.startswith('WALLET REQUEST ACCEPTED / ERIDIUM +'):return 'ERIDIUM_REQUEST'
    if m.startswith('WALLET REQUEST ACCEPTED / CASH +'):return 'MONEY_REQUEST'
    if m.startswith('CONFIRM /') or m.startswith('CONFIRM SPAWN //'):return 'CONFIRM'
    if m.startswith('SPAWN REQUEST ACCEPTED //'):return 'SPAWN_REQUEST'
    if m.startswith('TRAVEL // SLOT ') and 'SWEPT ARRIVAL CONFIRMED' in m:return 'TRAVEL'
    if m.startswith('TRAVEL // SLOT ') and ' SAVED FOR ' in m:return 'BOOKMARK_SAVED'
    if m.startswith('RETURN // SWEPT ARRIVAL CONFIRMED'):return 'TRAVEL'
    if m.startswith('UI PROFILE ') and ' SAVED //' in m:return 'PROFILE_SAVED'
    if m.startswith('CROWN EVENT //') and 'SOLO SESSION MODIFIERS' in m:return 'EVENT'
    if m.startswith('CROWN EVENT // NORMAL SETTINGS REQUESTED'):return 'EVENT_STOP'
    if m.startswith('RESTORE LOCAL SETTINGS REQUESTED'):
        return None if State.toast_suppress_restore else 'RESTORE'
    if (m.startswith('MAURICE BLOCKED /') or m.startswith('SPAWN BLOCKED //')
        or m.startswith('TRAVEL BLOCKED //') or m.startswith('WALLET REQUEST FAILED /')
        or m.startswith('SPAWN FAILED //')):
        return 'BLOCKED'
    return None

def _dismiss_toast(clear_queue=False):
    ui=State.toast_widget
    State.toast_widget=None
    State.toast_expires=0.0
    if clear_queue: State.toast_queue.clear()
    if ui is not None:
        try:ui.RemoveFromParent()
        except Exception:pass

def _toast_screen_rect():
    """Return native viewport-pixel geometry for a noninteractive toast.

    Menu panel_rect uses VIRTUAL layout coordinates that are scaled during
    _redraw_impl. Toasts live in their own native viewport widget and must NOT
    compare virtual panel coordinates to physical viewport pixels. On 1080p
    the full menu may leave only ~400px on the right: shrink to that gap,
    rather than drawing the default 528px notification over the controls.
    """
    try:
        screen_w,screen_h=(float(v) for v in viewport())
        if not all(math.isfinite(v) and v>0 for v in (screen_w,screen_h)):
            raise ValueError('Invalid viewport')
    except (ValueError,TypeError,OverflowError):
        screen_w,screen_h=1280.0,720.0
    margin=18.0
    w=min(528.0,max(1.0,screen_w-2*margin))
    h=min(83.0,max(1.0,screen_h-2*margin))
    x=(screen_w-w)/2.0 if State.toast_position=='TOP_CENTRE' else (screen_w-w-margin if State.toast_position=='TOP_RIGHT' else margin)
    y=min(max(margin,min(96.0,screen_h*.11)),max(margin,screen_h-h-margin))
    if State.opened and State.panel_rect is not None:
        try:
            # menu coordinates are virtual: _redraw_impl multiplies by
            # render_scale before Unreal's viewport positioning is applied.
            scale=float(State.render_scale)
            if not math.isfinite(scale) or scale<=0:scale=1.0
            px,py,pw,ph,_,_=State.panel_rect
            px,py,pw,ph=(float(v)*scale for v in (px,py,pw,ph))
            if not all(math.isfinite(v) for v in (px,py,pw,ph)):
                raise ValueError('Invalid panel')
            # Each gap includes margin to the window and between the widgets.
            free_right=screen_w-(px+pw)-2*margin
            free_left=px-2*margin
            if max(free_right,free_left)>=250.0:
                if free_right>=free_left:
                    w=min(w,free_right)
                    x=px+pw+margin
                else:
                    w=min(w,free_left)
                    x=px-margin-w
            else:
                # No side gap is large enough for readable content. An
                # on-screen fallback is better than running off the edge.
                x=max(margin,min(screen_w-w-margin,(screen_w-w)/2))
            y=min(max(margin,py+84),max(margin,screen_h-h-margin))
        except (TypeError,ValueError,OverflowError):pass
    return x,y,w,h

def _toast_has_safe_space():
    """A floating popup must not obscure the active menu's click targets.

    On compact screens, the full menu may span nearly the whole viewport.
    Queue its popup until the user closes the menu instead of presenting it
    across confirmation buttons. The status line already gives feedback.
    """
    if not State.opened or State.panel_rect is None:return True
    try:
        px,py,pw,ph,*_=State.panel_rect
        scale=float(State.render_scale)
        if not math.isfinite(scale) or scale<=0:return False
        px,py,pw,ph=[float(v)*scale for v in (px,py,pw,ph)]
        x,y,w,h=_toast_screen_rect()
        if not all(math.isfinite(v) for v in (x,y,w,h,px,py,pw,ph)):
            return False
        return (x+w<=px-8 or x>=px+pw+8 or y+h<=py-8 or y>=py+ph+8)
    except (TypeError,ValueError,OverflowError):return False

def _create_toast(code,now):
    """An independent UMG canvas; no focus, input capture, or game HUD edits."""
    pc=get_pc(possibly_loading=True)
    if pc is None:return False
    root_ui=None
    old_tree=State.tree
    try:
        root_ui=create('/Script/UMG.UserWidget',pc)
        tree=create('/Script/UMG.WidgetTree',root_ui)
        root_ui.WidgetTree=tree
        canvas=create('/Script/UMG.CanvasPanel',tree)
        tree.RootWidget=canvas
        State.tree=tree
        # Top-left avoids minimap, reticle, inventory and bottom status HUD.
        px,py,w,h=_toast_screen_rect()
        box(canvas,0,0,w,h,theme_color('border')[:3]+(.98,),1)
        box(canvas,2,2,w-4,h-4,theme_color('bg')[:3]+(1.0,),2)
        box(canvas,3,3,5,h-6,theme_color('danger') if TOAST_COPY[code][2]=='error'
            else theme_color('accent'),3)
        box(canvas,14,35,w-30,1,theme_color('border')[:3]+(.65,),3)
        if State.theme_idx==0:
            box(canvas,10,3,w-21,2,theme_color('highlight')[:3]+(.55,),3)
            box(canvas,w-11,6,3,h-12,theme_color('accent')[:3]+(.70,),3)
            optional_art_image(canvas,'NEON_STRIP',16,36,w-32,7,z=3,opacity=.45)
        if 'R9_EXPEDITION' in State.art_textures:optional_art_image(canvas,'R9_EXPEDITION',w*.55,2,w*.45,h-4,z=3,opacity=.20)
        title,detail,_=TOAST_COPY[code]
        color=theme_color('danger') if TOAST_COPY[code][2]=='error' else theme_color('accent')
        text(canvas,title,19,10,w-40,24,color,.82,4)
        text(canvas,detail,19,44,w-39,30,theme_color('text'),.67,4)
        # Unreal visibility 3 means HitTestInvisible *self AND descendants*.
        # 4 (SelfHitTestInvisible) is NOT sufficient: child text/borders can
        # still intercept clicks over gameplay or a menu. Refuse the toast if
        # a particular game/SDK revision cannot make both layers inert.
        if not (attempt(canvas,'SetVisibility',3) and
                attempt(root_ui,'SetVisibility',3)):
            raise RuntimeError('Noninteractive toast visibility refused')
        call(root_ui,'SetAlignmentInViewport',v2(0,0))
        call(root_ui,'SetPositionInViewport',v2(px,py),False)
        call(root_ui,'SetDesiredSizeInViewport',v2(w,h))
        if not attempt(root_ui,'AddToViewport',999996):
            raise RuntimeError('Toast viewport refused')
        State.toast_widget=root_ui
        State.toast_expires=now+State.toast_duration
        State.toast_shown+=1
        return True
    except Exception as error:
        record_runtime_fault('TOAST_WIDGET',error)
        State.toast_render_failed=True # Do not hammer a missing Unreal method.
        if root_ui is not None:
            try:root_ui.RemoveFromParent()
            except Exception:pass
        return False
    finally:
        State.tree=old_tree

def _toast_tick(now=None):
    now=time.monotonic() if now is None else float(now)
    if State.toast_widget is not None and now>=State.toast_expires:
        _dismiss_toast()
    elif State.toast_widget is not None and State.toast_expires-now<.40:
        # Only the last 0.4s animates: no page redraws or persistent tick work.
        call(State.toast_widget,'SetRenderOpacity',max(0.0,(State.toast_expires-now)/.40))
    if (State.toasts_enabled and not State.toast_render_failed and
            State.toast_widget is None and State.toast_queue and
            _toast_has_safe_space()):
        code=State.toast_queue.pop(0)
        _create_toast(code,now)

def toggle_toasts():
    State.toasts_enabled=not State.toasts_enabled
    if not State.toasts_enabled:_dismiss_toast(clear_queue=True)
    else:State.toast_render_failed=False # user explicitly retried optional UMG
    save_preferences()
    log('ACTION POPUPS // '+('ON' if State.toasts_enabled else 'OFF'))
    if State.opened:redraw()
    return State.toasts_enabled

def test_toast():
    # Testing a cosmetic notification must never issue a gameplay command.
    if not State.toasts_enabled:
        log('Enable ACTION POPUPS before testing.');return False
    return _queue_toast('TEST')

def attempt(obj, name, *args):
    """A void Unreal call can succeed; explicit False is an API refusal.

    Especially important for UI-only input capture: a callable method which
    returns False must NOT be logged as having accepted gameplay isolation.
    """
    try:
        result=getattr(obj, name)(*args)
        return result is not False
    except Exception:
        return False

def call(obj, name, *args):
    """Best-effort cosmetic call only, never used to validate critical input."""
    try:
        method = getattr(obj, name, None)
        return method(*args) if callable(method) else None
    except Exception:
        return None


def _safe_native_call(obj, method_name, *args, default=None):
    """Call a native method on any object with crash protection.

    Validates the object is not None, the method exists and is callable,
    and catches all exceptions (including access violations wrapped as
    Python exceptions by pyunrealsdk).
    """
    if obj is None:
        return default
    try:
        method = getattr(obj, method_name, None)
        if not callable(method):
            return default
        return method(*args)
    except Exception:
        return default


def _safe_pc_call(pc, method_name, *args, default=None):
    """Call a method on a PlayerController only if the wrapper is still valid.

    A UObject wrapper can become stale after map travel, character replacement,
    or crash recovery. Calling a method on a stale wrapper raises or, worse,
    accesses freed memory (the historical 0xC0000005 access violations).
    This helper validates the wrapper is the current live PC before any call.
    """
    if pc is None:
        return default
    try:
        current = get_pc(possibly_loading=True)
        if current is None or not same_unreal_object(current, pc):
            return default
        method = getattr(pc, method_name, None)
        if not callable(method):
            return default
        return method(*args)
    except Exception:
        return default


def _pc_wrapper_valid(pc):
    """True if the given PC wrapper is still the live PlayerController."""
    if pc is None:
        return False
    try:
        current = get_pc(possibly_loading=True)
        return current is not None and same_unreal_object(current, pc)
    except Exception:
        return False


def _safe_attr_set(pc, attr, value):
    """Set an attribute on a PC only if the wrapper is still valid.

    Prevents access violations when setting properties on stale UObject
    wrappers after map travel or controller replacement.
    """
    if not _pc_wrapper_valid(pc):
        return False
    try:
        setattr(pc, attr, value)
        return True
    except Exception:
        return False


def _safe_create_widget(path, outer):
    """Create a UMG widget with None-checks and crash protection.

    Returns the widget or None on failure. Never raises.
    """
    try:
        obj_class = cls(path)
        if obj_class is None:
            return None
        obj = unrealsdk.construct_object(obj_class, outer)
        if obj is None:
            return None
        return obj
    except Exception:
        return None

def cls(path):
    return unrealsdk.find_object("Class", path)

def create(path, outer):
    obj_class = cls(path)
    if obj_class is None:
        raise RuntimeError("Missing widget class: " + path)
    return unrealsdk.construct_object(obj_class, outer)

def v2(x, y):
    return unrealsdk.make_struct("Vector2D", X=float(x), Y=float(y))

def linear(col):
    return unrealsdk.make_struct("LinearColor", R=col[0], G=col[1], B=col[2], A=col[3])

def slate(col):
    try:
        return unrealsdk.make_struct("SlateColor",
                                    SpecifiedColor=linear(col), ColorUseRule=0)
    except Exception:
        return linear(col)

def size_position(w, x, y, width, height, z=0):
    slot = getattr(w, "slot", None)
    if slot is None: return
    call(slot, "SetPosition", v2(x, y))
    call(slot, "SetSize", v2(width, height))
    call(slot, "SetAutoSize", False)
    call(slot, "SetZOrder", z)

def put(parent, child):
    if hasattr(parent, "AddChild"): parent.AddChild(child)
    else: parent.SetContent(child)


# --------------- Optional CC0 art import: strictly fail open to native shapes ----
# Kenney CC0 UI elements plus original generated shopkeeper art; no ripped BL4 assets.
# Unreal UTexture2D support is patch-specific, so missing APIs must never fail UI.
ART_MOD_FILENAME="CROWNs_Freedom_v5_26_ECHO_Fieldcraft_R23.sdkmod"
ART_FILES={
    'RIVET_PANEL':'RIVET_PANEL.png',
    'BLADE_PLATE':'BLADE_PLATE.png',
    'AMBER_PLATE':'AMBER_PLATE.png',
    'GLASS_BADGE':'GLASS_BADGE.png',
    'BORDER_BTN':'BORDER_BTN.png',
    'CHECK':'CHECK.png',
    'DROP_ARROW':'DROP_ARROW.png',
    'TRADER_LEFT':'TRADER_LEFT.png',
    'TRADER_RIGHT':'TRADER_RIGHT.png',
    'TITLE_WORDMARK':'TITLE_WORDMARK.png',
    'HAZARD_STRIP':'HAZARD_STRIP.png',
    'ROUTE_STRIP':'ROUTE_STRIP.png',
    'PAD_R3':'PAD_R3.png',
    'PAD_L3':'PAD_L3.png',
    'INK_RAIL':'INK_RAIL.png',
    'SIDE_SIGIL':'SIDE_SIGIL.png',
    'WENREXA_SIDE':'WENREXA_SIDE.png',
    'BLACK_MARKET_SKIN':'BLACK_MARKET_SKIN.png',
    'NEON_HEADER':'NEON_HEADER.png',
    'NEON_SIDEPANEL':'NEON_SIDEPANEL.png',
    'NEON_CIRCUITS':'NEON_CIRCUITS.png',
    'NEON_STRIP':'NEON_STRIP.png',
    'NEON_WORDMARK_COMPACT':'NEON_WORDMARK_COMPACT.png',
    'ECHO_TOP_FRAME':'ECHO_TOP_FRAME.png',
    'ECHO_NAV_FRAME':'ECHO_NAV_FRAME.png',
    'ECHO_CONTENT_GLASS':'ECHO_CONTENT_GLASS.png',
    'ECHO_DOCK_PLATE':'ECHO_DOCK_PLATE.png',
    'PAD_A':'PAD_A.png',
    'PAD_B':'PAD_B.png',
    'ECHO_BTN_IDLE':'ECHO_BTN_IDLE.png',
    'ECHO_BTN_ACTIVE':'ECHO_BTN_ACTIVE.png',
    'ECHO_BTN_DANGER':'ECHO_BTN_DANGER.png',
    'PS_CROSS':'PS_CROSS.png',
    'PS_CIRCLE':'PS_CIRCLE.png',
    'PS_L3':'PS_L3.png',
    'PS_R3':'PS_R3.png',
    'AFTERDARK_BTN_IDLE':'AFTERDARK_BTN_IDLE.png',
    'AFTERDARK_BTN_ACTIVE':'AFTERDARK_BTN_ACTIVE.png',
    'AFTERDARK_BTN_DANGER':'AFTERDARK_BTN_DANGER.png',
    'AFTERDARK_TOP_FRAME':'AFTERDARK_TOP_FRAME.png',
    'AFTERDARK_DOCK_FRAME':'AFTERDARK_DOCK_FRAME.png',

}
ART_SHA256={'RIVET_PANEL': '37e09d770b74109779c64073e5f16f631172a96cf4583f808ba681f9d332f8f2', 'BLADE_PLATE': '34e2a065ea6c4e6efefba508b96c029e1db5f4af4e4d3899dada06308199aeea', 'AMBER_PLATE': '54ac8737524516f6caad65d788034a5de6ec27ea9bb6ff87a820f50fb6b7cdc1', 'GLASS_BADGE': '6059efb0bbff5597104ecaef460d120eb30e31b174a7556e6122cec70419cc94', 'BORDER_BTN': '19dd881d5c38d58e93db451152356a8ecb1375b247615d4e340b678233398b01', 'CHECK': '82a5c1c3dfe9a704e9f5f220c9510b622c77c2207c226b41728978c2335b1f3b', 'DROP_ARROW': 'd6d01360096a720828f3311e60e757466b8d0a8fece247a04637e91081a50c6c', 'TRADER_LEFT': 'f5ea1e50ea231999b0cf5aa1984cae4cbf402d30e3e37218e34429e5c5cee376', 'TRADER_RIGHT': '119435157cc1ddb34faa736025aae3f347c1257760e93e77ecc142a606ee3592'}

ART_SHA256['TITLE_WORDMARK']='109dde22f772a90e60f85b36dd5ddd4f0d8e263baeaf8c2fbdc5f76ec0248bff'

ART_SHA256['HAZARD_STRIP']='ccb1efcd473527e4edd86114358d48a4b3969d1194a7f197c457ea0058585fbe'
ART_SHA256['PAD_L3']='6ce290d2cd7c38768e7c16b114c702da31d994d541bd4e0464bfeb13d697710e'
ART_SHA256['PAD_R3']='c9b9bdd53fd412240328df8e81a20673a774af9ba395bccb7923d584f2fad0a1'
ART_SHA256['ROUTE_STRIP']='8f94bcd27268c18c54ba4e637c0098cc02f089f652f6e9c14a449d1f3ef8b034'

ART_SHA256['INK_RAIL']='c9f920c78a57b3c55a7a5c22571dfdf31ad2977df919f74b62f1d473078a3f74'

ART_SHA256['SIDE_SIGIL']='df409a531463b7b6ea856f9c9965935d2f8ac90c39fcb6e4cd6944615d9fafbd'

ART_SHA256['WENREXA_SIDE']='8643cf4a34a524bf3a97c726c0c8a19ec0faf5f554e24c2d58e91a6e0cb6544c'
ART_SHA256['BLACK_MARKET_SKIN']='c98f3fedc7623e209da847d6439f88d1394ad246c302039804defeeb4647b60a'

ART_SHA256['NEON_HEADER']='f1bf51c03f477136d5732dfdfa1c253d02443943c28302c8c89b39ba6c92904e'
ART_SHA256['NEON_SIDEPANEL']='7e4402746fa4334d2e284953049d11ed0ebb285620a1def8dc7f80b2f5c3cd18'
ART_SHA256['NEON_CIRCUITS']='25ee05c63835934c187f82c84c897f6d0d910898189e1b9b0e5cb55d6332d40c'
ART_SHA256['NEON_WORDMARK_COMPACT']='b9e2ab158200dd1a6aafeab94763116476cb6c9dba2586eda8ef30273191fac4'
ART_SHA256['NEON_STRIP']='7e6f55714b912472df3b43769f734f5cc45f329a084f1c37034f64e1ddc0fbe9'

ART_SHA256['ECHO_TOP_FRAME']='d77ac251a0f1a3cac465a41d06d9de9974a64c366e139f33f497ce6f41159038'
ART_SHA256['ECHO_NAV_FRAME']='aa5e6c8622253eaba8e498626df3ac2c5ca0e7956a114062ca8a45acfc52b5ac'
ART_SHA256['ECHO_CONTENT_GLASS']='78554a027abcb38ad22b06e5da0b8f2a60b838393e85a875df97165a9a2ae668'
ART_SHA256['ECHO_DOCK_PLATE']='7562a948a07beb7b79a0e1a1964aa5b4f2c8f0cbba1a2a61b340962bb9eda706'
ART_SHA256['PAD_A']='3ce5ca7c877d41e9c52022d86e3bd2f3548dd4b7096fa94fb2c0651677721a57'
ART_SHA256['PAD_B']='aa4dffc0f618ee6e25c9886c911c935162954c4b00aac3c46bc16efbacdc7768'
ART_SHA256['ECHO_BTN_IDLE']='3991c0878c5b8e7126eb25a7874aae79683cd1af1af0c8b7b68fe3b1055b642a'
ART_SHA256['ECHO_BTN_ACTIVE']='b7be59747eeb8eb2c40c697d2f7daa86b081657c2d8ded119b4d5a56d499aded'
ART_SHA256['ECHO_BTN_DANGER']='f9b08e8c998223c593c3518eecf0090905fcd2653c8f727cac4ba8dbc83fa0ce'


ART_SHA256['PS_CROSS']='b198de5487c139410b005b75d1600a4cc1cab6db839bdba89add97d28df3d998'
ART_SHA256['PS_CIRCLE']='9cab93e97e6a4cd0c04b1fe2baf4d3a8c36d410ec372e108adfa3f435868d8b0'
ART_SHA256['PS_L3']='01a40871c9926f3097c96e92b587a1991acd60967213846bfe1508e8fc78691d'
ART_SHA256['PS_R3']='0c151dbee12e9d0ac9bb5b49d459fb73bc1e1edc4afd2b3b053311f24c6c0d97'
ART_SHA256['AFTERDARK_BTN_IDLE']='90b156286635862517d2531bcf245bd5407fffe935205bc8be477e54cd13c482'
ART_SHA256['AFTERDARK_BTN_ACTIVE']='adf15d942ba2bd5333c7b679ddef527d3aefe6e20142be023b15d5268892d147'
ART_SHA256['AFTERDARK_BTN_DANGER']='220b9b4f9178d052b8866637213fdcfdd2a085bf35ce4a89aa7582421f7ea3cd'
ART_SHA256['AFTERDARK_TOP_FRAME']='a19f28dc23f83a5d93cd09fa51f24a2ce65a5332c5cd9936b80477dcc230af7c'
ART_SHA256['AFTERDARK_DOCK_FRAME']='0a638e059a7ebe629398ca996ab40e21fb41455c79e5ae58860ed9e101ca56ec'

def _verify_png_bytes(asset_id, raw):
    return (asset_id in ART_SHA256 and isinstance(raw, bytes)
            and raw.startswith(b'\x89PNG\r\n\x1a\n')
            and hashlib.sha256(raw).hexdigest()==ART_SHA256[asset_id])


def _art_mod_archive():
    """Resolve this exact running build's art archive, not a same-named older build.

    The historical file name is shared by multiple releases, so never trust
    filename alone. Confirm the embedded BUILD_ID and hash-verified identity
    PNG before loading any artwork or WAVs. Prefer the active zipimport loader.
    Fail closed on ambiguous fallbacks rather than mixing versions of assets.
    No player data, game settings, or external mods are modified.
    """
    base=Path(SETTINGS_DIR).parent if SETTINGS_DIR is not None else None
    if base is None:
        State.art_archive_status='SETTINGS PATH UNAVAILABLE'
        return None
    loader_path=None
    try:
        origin=getattr(globals().get('__loader__'),'archive',None)
        if origin:loader_path=Path(origin)
    except (TypeError,ValueError,OSError):pass

    def same_running_build(path):
        try:
            if not path.is_file() or path.suffix.lower()!='.sdkmod':return False
            with zipfile.ZipFile(path) as z:
                names=z.namelist()
                source=[n for n in names if n.endswith('/__init__.py')]
                marks=[n for n in names if n.endswith('/CROWN_CC0_ASSETS/NEON_WORDMARK_COMPACT.png')]
                if len(source)!=1 or len(marks)!=1:return False
                if z.getinfo(source[0]).file_size>900000 or z.getinfo(marks[0]).file_size>250000:return False
                raw_source=z.read(source[0])
                # The BUILD_ID is deliberately unique for this patch. Even an
                # older R3/R2 with the same installer name cannot be selected.
                marker=('BUILD_ID = "'+BUILD_ID+'"').encode('ascii')
                if marker not in raw_source or ("RELEASE_VERSION = "+chr(34)+RELEASE_VERSION+chr(34)).encode("ascii") not in raw_source:return False
                return _verify_png_bytes('NEON_WORDMARK_COMPACT',z.read(marks[0]))
        except (OSError,ValueError,zipfile.BadZipFile,RuntimeError,KeyError):return False

    if loader_path is not None and same_running_build(loader_path):
        State.art_archive_status='ACTIVE LOADER / BUILD VERIFIED'
        return loader_path
    exact=base/ART_MOD_FILENAME
    if same_running_build(exact):
        State.art_archive_status='EXACT FILE / BUILD VERIFIED'
        return exact
    try:
        paths=sorted(base.glob('CROWNs_Freedom*.sdkmod'))
        if len(paths)>16:
            State.art_archive_status='TOO MANY CROWN INSTALLERS / REMOVE OLD VERSIONS'
            return None
        matches=[p for p in paths if p!=exact and same_running_build(p)]
        if len(matches)==1:
            State.art_archive_status='RENAMED FILE / BUILD VERIFIED'
            return matches[0]
        State.art_archive_status=('MULTIPLE MATCHING INSTALLERS / KEEP ONE' if matches
                                  else 'ACTIVE R13 ART ARCHIVE NOT FOUND')
        return None
    except (OSError,ValueError,TypeError):
        State.art_archive_status='MOD FOLDER SCAN UNAVAILABLE'
        return None

def _art_png_path(asset_id):
    if asset_id not in ART_FILES or SETTINGS_DIR is None:
        return None
    filename=ART_FILES[asset_id]
    cache_dir=Path(SETTINGS_DIR)/'CROWNs_Freedom_ArtCache'
    dst=cache_dir/filename
    try:
        if dst.is_file() and 0<dst.stat().st_size<250000:
            if _verify_png_bytes(asset_id,dst.read_bytes()):
                return dst
            # An old or corrupted cached file must never be imported.
            # Re-extract only from the authenticated resource in this .sdkmod.
        archive=_art_mod_archive()
        if archive is None:return None
        with zipfile.ZipFile(archive) as z:
            matches=[n for n in z.namelist() if n.endswith('/CROWN_CC0_ASSETS/'+filename)]
            if len(matches)!=1:return None
            info=z.getinfo(matches[0])
            if info.file_size<=0 or info.file_size>250000:return None
            raw=z.read(matches[0])
        if not _verify_png_bytes(asset_id,raw):
            return None
        cache_dir.mkdir(parents=True,exist_ok=True)
        # Small assets are checked before replacement, so a failed extraction
        # never overwrites a known-good original image with untrusted bytes.
        dst.write_bytes(raw)
        return dst
    except Exception:
        return None

def _art_texture(asset_id):
    if asset_id not in ART_FILES:return None
    if State.safe_mode:
        State.art_status='SAFE MODE / native shapes only'
        return None
    if State.art_mode=='SHAPES':
        State.art_status='SHAPES / lightweight mode'
        return None
    if asset_id in State.art_textures:return State.art_textures[asset_id]
    if asset_id in State.art_failed:return None
    # ImportFileAsTexture2D is a synchronous native call. Bound cold imports
    # during a single redraw instead of creating an unbounded hitch while
    # CROWN also constructs the UMG tree. Unloaded art remains native shapes.
    ambient={'NEON_STRIP','ECHO_CONTENT_GLASS','TRADER_LEFT','TRADER_RIGHT',
             'NEON_SIDEPANEL','ECHO_NAV_FRAME','WENREXA_SIDE','INK_RAIL',
             'BLACK_MARKET_SKIN','NEON_CIRCUITS','HAZARD_STRIP'}
    # Reserve cold-import budget for readable title art and BUTTON skins. An
    # ornamental background must not use all eight slots before buttons draw.
    if (getattr(State,'art_imports_this_frame',0)>=8 or
            (asset_id in ambient and getattr(State,'art_ambient_imports_this_frame',0)>=3)):
        State.art_deferred.add(asset_id)
        State.art_status='ART DEFERRED / next page draw'
        return None
    # A missing WORLD is a transient loading state, not proof of a broken API.
    # Do not poison the failed-assets cache until we're actually in a map.
    world,_=world_and_state()
    if world is None:
        State.art_status='SHAPES / waiting for playable map'
        return None
    def failed(reason):
        State.art_failed.add(asset_id)
        State.art_fail_reasons[asset_id]=reason
        if not State.art_drawn_count:
            State.art_status='SHAPES / '+reason
        return None
    try:
        kr=cls('/Script/Engine.KismetRenderingLibrary')
        library=getattr(kr,'ClassDefaultObject',None)
        method=getattr(library,'ImportFileAsTexture2D',None)
        if not callable(method):return failed('texture importer unavailable')
        path=_art_png_path(asset_id)
        if path is None:return failed('asset archive/cache unavailable')
        _set_native_phase('ART_IMPORT')
        State.art_imports_this_frame+=1
        if asset_id in ambient:State.art_ambient_imports_this_frame+=1
        texture=method(world,str(path))
        if texture is None:return failed('texture importer returned no image')
        State.art_textures[asset_id]=texture
        State.art_deferred.discard(asset_id)
        State.art_failed.discard(asset_id)
        State.art_fail_reasons.pop(asset_id,None)
        State.art_status='PACKED ART / texture ready'
        return texture
    except Exception as exc:
        return failed('import rejected: '+type(exc).__name__)

def _art_widget_failed(asset_id,reason):
    # Native fallbacks remain operational; do not rebuild a rejected image
    # on every menu redraw. RETRY ART deliberately clears this cache.
    State.art_failed.add(asset_id)
    State.art_fail_reasons[asset_id]=reason
    if not State.art_drawn_count:
        State.art_status='SHAPES / '+reason
    return False

def optional_art_image(parent,asset_id,x,y,w,h,z=6,opacity=.42):
    """Optional UMG art; MUST be invisible to hit tests before mounting."""
    texture=_art_texture(asset_id)
    if texture is None:return False
    try:
        picture=widget('Image')
        if not attempt(picture,'SetBrushFromTexture',texture,False):
            return _art_widget_failed(asset_id,'UMG texture brush unavailable')
        if not attempt(picture,'SetColorAndOpacity',linear((1.0,1.0,1.0,max(.05,min(1.0,opacity))))):
            return _art_widget_failed(asset_id,'UMG image tint unavailable')
        # ESlateVisibility=3 ignores both the image and ALL its descendants.
        # Never add an untrusted click-catching art layer above native actions.
        if not attempt(picture,'SetVisibility',3):
            return _art_widget_failed(asset_id,'UMG art hit-test bypass unavailable')
        put(parent,picture)
        size_position(picture,x,y,w,h,z)
        State.art_drawn_count+=1
        State.art_status='PACKED ART / drawn'
        return True
    except Exception as exc:
        return _art_widget_failed(asset_id,'image widget '+type(exc).__name__)

# Non-invasive hover help: no rebuild or game mutation during mouse motion.
CONTROL_HELP=(
    ('PLAYER LAB','Guarded permanent progression, XP observations and owned timed bonuses.'),
    ('TARGET LEVEL','Stage a raise-only level request. Permanent; exact reviewed BL4Live required.'),
    ('TOTAL POINT ALLOWANCE','Total acquired points, not unspent points. Raise by 1–25; no skill reset or lowering.'),
    ('START OWNED TIMER','Temporary outgoing damage factor; background callback and uncontested ownership required.'),
    ('BEGIN REWARD','Sample both XP tracks before one comparable reward; Finish records the delta.'),
    ('READ RESULT','Observe the previous request. Never repeats a native write.'),
    ('ENABLE GOD MODE','Request damage immunity for your character.'),
    ('DISABLE GOD MODE','Restore damage from enemies, best effort.'),
    ('ENABLE NOCLIP','Disable collision and switch movement mode. Use Restore to undo.'),
    ('DISABLE NOCLIP','Try to restore normal collision and movement.'),
    ('ENABLE NO TARGET','Request that enemy AI stop targeting your character.'),
    ('DISABLE NO TARGET','Allow enemy AI to target your character again.'),
    ('SET FOV','Change your field of view. F10 can try to restore it.'),
    ('SPEED','Adjust movement speed temporarily.'),
    ('JUMP','Adjust jump strength temporarily.'),
    ('GRAVITY','Change gravity temporarily. Can affect fall behaviour.'),
    ('CASH','Currency request. May permanently affect your save. Two clicks.'),
    ('ERIDIUM','Eridium request. May permanently affect your save. Two clicks.'),
    ('CLEAR ENEMIES','Destructive enemy-clear request. Two-click confirmation.'),
    ('TOGGLE AMMO','Experimental dev perk. State cannot be reliably read back.'),
    ('BOOKMARK','Save or travel to a known safe position on this same map.'),
    ('TRAVEL HUB','Open the 12-slot same-map Roadrunner travel panel. Keyboard F8.'),
    ('RETURN TO LAST','Reverse the previous confirmed teleport.'),
    ('TRAVEL SPRINT','Request a temporary three-times movement speed. Restore in Movement.'),
    ('OVERWRITE','Double press within five seconds to replace a saved travel slot.'),
    ('WORLD SPEED','Changes world-time multiplier; may affect more than you.'),
    ('FRIEND','Co-op experiment. Requires host authority and friend consent.'),
    ('CONSENT','Acknowledges you asked each friend. It is not real remote permission.'),
    ('REQUEST SPAWN','Arms a solo item-pool request; second click sends, not proof of a drop.'),
    ('FORGE PRE-FLIGHT','Checks location, transform and pool APIs without spawning anything.'),
    ('RUN API AUDIT + EXPORT','Read-only method presence checks; writes a diagnostic JSON, never spawns or edits gear.'),
    ('CONFIRM SPAWN','Sends the prepared drop request once. Confirm actual item in game.'),
    ('CATEGORY','Switches the current Forge browse filter.'),
    ('FIND BY NAME','Open a native text field to search known Forge items.'),
    ('? HELP','Open explanations and safety details for this page.'),
    ('ART MODE','AUTO attempts holographic textures; SHAPES is a safety fallback without artwork.'),
    ('INFINITE AMMO','Requests the game developer-perk ammo toggle. Actual state cannot be read back; do not assume it worked.'),
    ('AMMO TOGGLE','Requests infinite ammo toggle; no confirmed on/off state. Test ammo count.'),
    ('EXTERNAL XP','Requires separately installed and enabled XP mod. Only sends a console request; verify earned reward.'),
    ('SAFE MODE','Disable optional image imports and UI audio without losing preferences. Safe mode can be switched off anytime.'),
    ('RETRY ART','Retry optional packaged holographic textures on a supported native build.'),
    ('AUDIO','Open adjustable UI sound effects settings; uses Windows audio if supported.'),
    ('TEST SOUND','Play a short Kenney CC0 sample through Windows audio.'),
    ('UI DIAGNOSTICS','Read why optional art and runtime APIs are available or unavailable.'),
    ('EXPORT QA REPORT','Save a privacy-conscious JSON report to sdk_mods/settings.'),
    ('NEXT DIAGNOSTICS','Turn to the next diagnostics page; every error line is available.'),
    ('RESTORE','Best-effort recovery of temporary CROWN changes; saved rewards remain.'),
    ('CLOSE','Closes the native menu, returning controls to gameplay.'),
)
def _control_description(caption):
    text_label=str(caption).upper()
    for needle,desc in CONTROL_HELP:
        if needle in text_label:return desc
    return 'Select this control to perform the named action. See ? HELP for details.'

# Windows-native UI audio bridge. This is NOT Unreal/Borderlands sound importing.
# Only call winsound from intentional user UI interaction. No worker, thread,
# web request, executable subprocess or whole-game sound-mixer changes.
SOUND_HASHES = {'low_open.wav': '34e377192a48050addb124d5b91952e93dbe3729000bcfbe1bf3646da42ff812', 'normal_open.wav': '400f2cbcee921aa94819054c6770df5ae9948f2a9775577c2ae777f1ecbd00ea', 'high_open.wav': '7e17c2be963693de05b3412fedc54ef38543a738d43e875cce8a1e55c34fd58d', 'low_close.wav': '25ecd8a67406fd1f1a7cc12e090da91df749109edbd3ad2857b49c4a05b81dfc', 'normal_close.wav': '3646d1a9895948aa7d6efcb30c864d1a53306b857edb48a0493c4b76f9e38f52', 'high_close.wav': 'a42f8ccc910262ec8c16636a65548f258f4396ef7e5f71a1f7d58b203afff8b4', 'low_select.wav': 'cfeab283feb8de46b4836260832a76244fc4df52614e0bae6d17541bcddc9001', 'normal_select.wav': '4c4dd28995915cb7457ac2a78eb5292496943f44925625d855277665dfc43bd5', 'high_select.wav': 'e3b015ee0b697914cbae22b63b0c105d11bfa9211d893b8cdbfe624266ef71dc', 'low_confirm.wav': '2871ebee7fd828ad8875fa2d96a61f8223da485289d853e138416c199ea1d103', 'normal_confirm.wav': '4e33ec9ef950eb5a902b5916fbc161c3a1a884bbfa9cf112576de79bf2eddb0c', 'high_confirm.wav': '160d868b130620ef8a03465de9fb81bc75b9c766d9c3ef099d1c64693ab950e8', 'low_warn.wav': 'e1e1509226df2619c39134da4f22b034adb6a1d94ba7a4e99dc2ea029e22cb21', 'normal_warn.wav': '56e8b2842b6f7b9c458514ac71c4c9e2701fb641a42591b31efdeb2904fd2c6e', 'high_warn.wav': 'eda6c04d8a870c553ca5c69037fa76e38bf6b7a0299d6c4a20ae7e8d95d09aad', 'low_hover.wav': '88638af29fe2a21c3602dc25c14fa89765d5d34a1bd38f70a989c05a046da7d8', 'normal_hover.wav': 'db4168bc52ae9b034390ef500a691d17f74f817f81d3c5b25d6c77283b934bcf', 'high_hover.wav': '1c9c87e32b40c409f80d576cb9d8cec8891b81ec176f70b83c90e8e68c3d3aed'}
SOUND_HASHES['echo_low_hover.wav']='3b7b7a04b6917747b7a4542f6f6340144b36410fc00944f0db2a3c88427a7e39'
SOUND_HASHES['echo_normal_hover.wav']='653351d225ba3fbf5fffd24bd31d0db6a535acf0493c696a51c6005e3e9618c7'
SOUND_HASHES['echo_high_hover.wav']='d17f2f9390812d56f154827e9a0d3f976bbd5a592f44c9d4ee434c42ebb7888a'
SOUND_HASHES['echo_low_select.wav']='a22a855ed090e25bee3538904d46b66ea4eefafd9fd0de3acca15a8029335aa0'
SOUND_HASHES['echo_normal_select.wav']='321d80cb0da5a82a22b3ed9d540e2a23189e3863a59ad37c8d232b7b08adbacb'
SOUND_HASHES['echo_high_select.wav']='1d422b3f8e4e7be8deb0becadbcb6e8831a3b7365900c352b1f8b4636cd78457'
SOUND_HASHES['echo_low_confirm.wav']='da3aca8fddfa9eba2fb2b018778cb4b486c26f0b25d167500d28a7198e44d163'
SOUND_HASHES['echo_normal_confirm.wav']='e559aec3776d99e7241257b56a0df0c8eff5fa58625e4ffaa41f779789b9d3fa'
SOUND_HASHES['echo_high_confirm.wav']='b185459bbf93ec6a061e09a5c311073a41cadd821bfb45fba8603a78e9936651'
SOUND_HASHES['echo_low_warn.wav']='4279c9d2ce99547ef62ed6a904d3a3619ecddb2ef416edd34747f75304228f0c'
SOUND_HASHES['echo_normal_warn.wav']='03dd9b12578b3c8a74c3c2fc36904f8951eb36f5d0f9eb1f4ff6d1ecbbd3c1d9'
SOUND_HASHES['echo_high_warn.wav']='65704e18e748ee6a68fb1365c62a5f095b05ca1dbfaabaf8c7bddf770cbb27aa'
SOUND_HASHES['echo_low_open.wav']='ea33ddd9023d83fed5aef262cf8bd0d3143685985042c98518f635271f56eb9a'
SOUND_HASHES['echo_normal_open.wav']='8f053fb322887188e998a073fc40047dadc4ea3feb865858678ec6c935e02155'
SOUND_HASHES['echo_high_open.wav']='304afd0a022e46731fa63b3d4e0b468c59205c22599d7fd09d30c82a5715412d'
SOUND_HASHES['echo_low_close.wav']='94b550b95ff3dfc74a2a15f353621d2b52cd496111fa0fe95eea51a9d5f838a3'
SOUND_HASHES['echo_normal_close.wav']='aae35f8ee7a78052f0daf04231b1448153ffee85c6f1410eba22f2e11db8b8b7'
SOUND_HASHES['echo_high_close.wav']='103ab2499c1f06f3cb90d36f9d970de952dfdf6e2542c53437236ba9ed5ba378'
SOUND_CUES = ('hover','select','confirm','warn','open','close')
SOUND_LEVELS = ('OFF','LOW','NORMAL','HIGH')

def _sound_bytes_valid(name,data):
    return (name in SOUND_HASHES and isinstance(data,bytes) and
            44<=len(data)<50000 and data[:4]==b'RIFF' and data[8:12]==b'WAVE' and
            hashlib.sha256(data).hexdigest()==SOUND_HASHES[name])

def _sound_file(cue,level):
    if cue not in SOUND_CUES or level not in SOUND_LEVELS or level=='OFF' or SETTINGS_DIR is None:
        return None
    name=('echo_'+level.lower()+'_'+cue+'.wav') if State.sfx_set=='ECHO' else (level.lower()+'_'+cue+'.wav')
    if State.sfx_set=='ECHO' and cue in ('open','close'):name='r3_'+level.lower()+'_'+cue+'.wav'
    cache=Path(SETTINGS_DIR)/'CROWNs_Freedom_AudioCache'
    dst=cache/name
    try:
        if dst.is_file() and dst.stat().st_size<50000 and _sound_bytes_valid(name,dst.read_bytes()):
            return dst
        archive=_art_mod_archive()
        if archive is None:return None
        with zipfile.ZipFile(archive) as z:
            matches=[n for n in z.namelist() if n.endswith('/CROWN_CC0_ASSETS/UI_WAV/'+name)]
            if len(matches)!=1:return None
            info=z.getinfo(matches[0])
            if info.file_size<44 or info.file_size>=50000:return None
            data=z.read(matches[0])
        if not _sound_bytes_valid(name,data):return None
        cache.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(data)
        return dst
    except Exception:return None

def _windows_play_wav(path):
    """Nonblocking Windows UI sound; standard library only, no custom DLL."""
    try:
        import winsound
        winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
        return 'winsound'
    except ImportError:
        pass
    except Exception as err:
        State.audio_status='winsound failed // '+str(err)[:45]
    # Some embedded Python distributions omit winsound but include ctypes.
    # WinMM is part of Windows itself, not a downloaded/custom executable.
    try:
        import ctypes
        fn=ctypes.windll.winmm.PlaySoundW
        fn.argtypes=[ctypes.c_wchar_p,ctypes.c_void_p,ctypes.c_uint]
        fn.restype=ctypes.c_int
        if fn(str(path),None,0x00020000|0x0001|0x0002):
            return 'Windows WinMM'
    except Exception as err:
        State.audio_status='WinMM unavailable // '+str(err)[:45]
    return None

def play_ui_sound(cue, force=False):
    if State.safe_mode or cue not in SOUND_CUES or State.audio_mode=='OFF':return False
    if cue=='hover' and not (State.audio_hover or force):return False
    now=time.monotonic()
    if not force and now-State.audio_last<(0.11 if cue=='hover' else 0.06):return False
    if cue=='hover' and not force and now<getattr(State,'r13_audio_priority_until',0.):return False
    path=_sound_file(cue,State.audio_mode)
    if path is None:
        State.audio_status='UNAVAILABLE // WAV asset path/verification failed'
        return False
    backend=_windows_play_wav(path)
    if backend is None:
        State.audio_status='UNAVAILABLE // embedded Windows audio interface not exposed'
        return False
    State.audio_last=now
    if cue in ('confirm','warn','open','close'):State.r13_audio_priority_until=now+.30
    State.audio_status='REQUESTED // '+backend+' (not BL4 mixer)'
    return True

def cycle_sfx_set():
    State.sfx_set='ECHO' if State.sfx_set=='CLASSIC' else 'CLASSIC'
    save_preferences()
    play_ui_sound('confirm',force=True)
    log('UI AUDIO SET // '+State.sfx_set+' / no BL4 mixer changes')
    if State.opened:redraw()
    return State.sfx_set

def set_audio_mode(mode):
    if mode not in SOUND_LEVELS:return False
    State.audio_mode=mode
    save_preferences()
    if mode!='OFF':play_ui_sound('confirm',force=True)
    else:State.audio_status='MUTED'
    log('UI AUDIO // '+mode+' (Windows-side; not native BL4 audio)')
    if State.opened:redraw()
    return True

def toggle_audio_hover():
    State.audio_hover=not State.audio_hover
    save_preferences()
    log('HOVER AUDIO // '+('ON' if State.audio_hover else 'OFF'))
    if State.opened:redraw()

def toggle_safe_mode():
    """One-click fallback for suspect image imports/audio; game settings untouched.

    Store only the switch, preserving a user's chosen theme, art and audio
    preferences for a later return to full visuals.
    """
    State.safe_mode=not State.safe_mode
    if State.safe_mode:
        State.art_textures.clear()
        State.art_status='SAFE MODE / no PNG imports'
        State.audio_status='SAFE MODE / muted'
    else:
        State.art_failed.clear()
        State.art_fail_reasons.clear()
        State.art_status='AUTO / ready to retry' if State.art_mode=='AUTO' else 'SHAPES / native-only'
    save_preferences()
    log('UI SAFE MODE // '+('ON / graphics and UI audio disabled' if State.safe_mode else 'OFF / chosen visual/audio settings restored'))
    _queue_toast('SAFE_ON' if State.safe_mode else 'SAFE_OFF')
    if State.opened:redraw()
    return State.safe_mode

def resume_custom_art():
    """Explicit user opt-in: Safe Mode OFF *and* AUTO artwork enabled.

    Previously the resume label switched only Safe Mode, while a saved SHAPES
    preference silently kept all PNGs disabled. Keep a native fallback if the
    local BL4 SDK cannot import images; never touch game settings or saves.
    """
    State.safe_mode=False
    State.art_mode='AUTO'
    State.art_textures.clear()
    State.art_failed.clear()
    State.art_fail_reasons.clear()
    State.art_status='AUTO / import retry requested'
    save_preferences()
    log('ART READY // Safe Mode OFF, AUTO art selected. Run CHECK ART if it stays flat.')
    _queue_toast('SAFE_OFF')
    if State.opened:redraw()
    return True

def toggle_style_audio():
    State.style_audio_open=not State.style_audio_open
    if State.opened:redraw()

def toggle_art_mode():
    State.art_mode='SHAPES' if State.art_mode=='AUTO' else 'AUTO'
    if State.art_mode=='SHAPES':
        State.art_status='SHAPES / lightweight mode'
    else:
        State.art_status='SHAPES / ready to attempt import'
    save_preferences()
    log('ART MODE // '+State.art_mode+' (reopens the menu artwork)')
    if State.opened:redraw()

def retry_art():
    if State.safe_mode:
        log('ART BLOCKED // Safe Mode is ON. Choose RESUME CUSTOM ART first.')
        return False
    # Explicit retry never manipulates game objects. Prior texture handles are
    # dropped and re-imported only on the next menu draw, if AUTO is selected.
    State.art_mode='AUTO'
    State.art_textures.clear()
    State.art_failed.clear()
    State.art_fail_reasons.clear()
    State.art_status='SHAPES / retry requested'
    save_preferences()
    log('ART // Rechecking Kenney images; unsupported APIs fall back to shapes')
    if State.opened:redraw()

def art_preflight():
    """Opt-in read of the packaged wordmark + Unreal texture import status.

    Performs no gameplay action or network operation. Import is best-effort
    and uses the same hash-checked cache that the actual menu uses.
    """
    if State.safe_mode:
        log('ART CHECK // SAFE MODE ON. Select RESUME CUSTOM ART first.')
        return False
    if State.art_mode!='AUTO':
        log('ART CHECK // SHAPES selected. Switch to AUTO first.')
        return False
    archive=_art_mod_archive()
    if archive is None:
        log('ART CHECK // '+State.art_archive_status+'. Keep only one CROWN build in sdk_mods.')
        return False
    path=_art_png_path('NEON_WORDMARK_COMPACT')
    if path is None:
        log('ART CHECK // wordmark file missing or SHA256 mismatch. Check sdk_mods/settings permissions.')
        return False
    tex=_art_texture('NEON_WORDMARK_COMPACT')
    if tex is None:
        reason=State.art_fail_reasons.get('NEON_WORDMARK_COMPACT',State.art_status)
        log('ART CHECK // Import unavailable: '+str(reason)[:85])
        return False
    log('ART CHECK // VERIFIED: PNG hash and Unreal texture import; UI brush still requires live draw.')
    if State.opened:redraw()
    return True

def ui_diagnostic_lines():
    # Snapshot only when user opens the diagnostics page, not per camera tick.
    archive=_art_mod_archive()
    try:
        kl=cls('/Script/Engine.KismetRenderingLibrary')
        importer=callable(getattr(getattr(kl,'ClassDefaultObject',None),'ImportFileAsTexture2D',None))
    except Exception:importer=False
    w,h=viewport()
    failures=', '.join(k+':'+v for k,v in list(State.art_fail_reasons.items())[:2]) or 'none'
    return [
        'ART MODE: '+State.art_mode+'  /  DRAWN: '+str(State.art_drawn_count),
        'SAFE MODE: '+('ON / no imported PNG or WAV' if State.safe_mode else 'OFF / normal UI')+' / INPUT: '+State.input_last_status[:30],
        'PREVIOUS MENU EXIT: '+('UNCLEAN / review logs' if State.previous_menu_unclean else 'CLEAN / no marker detected'),
        'CURSOR AID: '+('ON' if State.cursor_aid else 'OFF')+' / ALIGN: '+State.cursor_coordinates+' / '+State.cursor_source+' / INPUT: '+State.input_last_status[:28],
        'ART ARCHIVE: '+('FOUND' if archive is not None else 'NOT FOUND')+' / '+State.art_archive_status[:65],
        'UNREAL PNG IMPORTER: '+('AVAILABLE' if importer else 'NOT EXPOSED'),
        'TEXTURES IN CACHE: '+str(len(State.art_textures))+'  /  FAILED: '+str(len(State.art_failed))+'  /  DEFERRED: '+str(len(State.art_deferred)),
        'COMMAND CENTRE: '+str(State.frame_generation)+' frames / '+str(len(State.native_history))+' bounded phase events',
        'LAST NATIVE PHASE: '+getattr(State,'native_phase','UNKNOWN')+' / UNCLEAN: '+getattr(State,'previous_native_phase','UNKNOWN'),
        'BUILD: '+BUILD_ID+' / texture draw still requires live BL4',
        'BUNDLED PNG HASHES: '+str(len(ART_FILES))+' LISTED; RUNTIME IMPORT CHECKS REQUIRED',
        'DISPLAY: %d x %d  /  UI SCALE: %.2f'%(w,h,State.panel_scale),
        'LAST ART ISSUE: '+failures[:95],
        'INK ART: optional panels, wordmark, icons and decorations',
        'INPUT: '+('MENU ACTIVE' if State.opened else 'CLOSED')+'  /  ROLE: '+session_role(),
        'CO-OP: '+str(coop_snapshot()['visible_players'])+' player(s) / '+State.coop_last_status[:70],
        'HOST AUTHORITY PROBE: '+_probe_summary(),
        'HINT: SHAPES MODE AVOIDS PNG IMPORT FOR FPS TESTS',
        'FORGE STAGE: '+State.forge_stage,
        'TRAVEL: '+State.travel_last_state+' // ROLLBACK ATTEMPTS '+str(State.travel_rollback_attempts),
        'UI AUDIO: '+State.sfx_set+' / '+State.audio_mode+' // '+State.audio_status[:65],
        'ACTION POPUPS: '+('ON' if State.toasts_enabled else 'OFF')+' / SHOWN '+str(State.toast_shown)+
            (' / UMG FALLBACK' if State.toast_render_failed else ''),
        'GAMEPAD: '+('ENABLED' if State.controller_enabled else 'DISABLED')+' // HOOK: '+('INSTALLED' if State.controller_watcher_installed else 'UNAVAILABLE'),
        'GAMEPAD FOCUS: '+str(State.controller_focus)+' / '+str(len(State.buttons))+' visible buttons',
        'HOVER CUES: '+('ON' if State.audio_hover else 'OFF')+' // Windows-side playback only',
        'UI REDRAWS: '+str(State.ui_rebuild_count)+' // LAST %.1fms // PEAK %.1fms'%(State.ui_last_ms,State.ui_peak_ms),
        'PRESS SAFETY: '+str(State.duplicate_native_releases_blocked)+' redundant native releases blocked',
        'FOREGROUND GUARD: '+str(State.foreground_guard_count)+' focus losses / '+('RESUMING' if State.foreground_suspended or State.foreground_resume_after>0 else 'CLEAR'),
        'ADVANCED API AUDIT: '+('RUN AT '+str(State.advanced_audit_unix) if State.advanced_audit_unix is not None else 'NOT RUN / FORGE > API/DLC'),
        'NOT IMPLEMENTED: boss/vehicle spawn, arbitrary weapon parts, Steam achievement grants',
        'RUNTIME FAULTS: '+str(len(State.runtime_failures))+' / last stage: '+(State.runtime_failures[-1]['stage'] if State.runtime_failures else 'none'),
    ]

def export_qa_report():
    """Write a local, opt-in report without names, save contents or coordinates."""
    if SETTINGS_DIR is None:
        log('QA EXPORT UNAVAILABLE // SDK settings directory not exposed.')
        return False
    try:
        w,h=viewport()
        report={
            'project':'CROWNs Freedom', 'version':RELEASE_VERSION, 'build_id':BUILD_ID,
            'notice':'No character names, friend names, save data or position included.',
            'captured_unix_time':int(time.time()),
            'display':{'width':int(w),'height':int(h)},
            'session':{'role':session_role()},
            'co_op':coop_snapshot(),
            'ui':{'page':State.page,'theme':THEMES[State.theme_idx]['name'],
                  'menu_open':bool(State.opened),
                  'panel_opacity':State.panel_opacity,
                  'safe_mode':bool(State.safe_mode),
                  'toasts_enabled':bool(State.toasts_enabled),
                  'toasts_displayed':State.toast_shown,
                  'toast_render_fallback':bool(State.toast_render_failed),
                  'previous_menu_exit_unclean':bool(State.previous_menu_unclean),
                  'previous_unclean_menu_page':State.previous_unclean_page,
                  'previous_unclean_native_phase':State.previous_native_phase,
                  'current_native_phase':State.native_phase,
                  'native_history':list(State.native_history),
                  'frame_generation':State.frame_generation,
                  'numeric_editor_active':State.numeric_editor is not None,
                  'panel_scale':State.panel_scale,
                  'controller_enabled':bool(State.controller_enabled),
                  'gamepad_icons':State.gamepad_icons,
                  'controller_hook_installed':bool(State.controller_watcher_installed),
                  'builds':State.ui_rebuild_count,
                  'last_rebuild_ms':round(State.ui_last_ms,2),
                  'peak_rebuild_ms':round(State.ui_peak_ms,2),
                  'errors':State.ui_error_count,
                  'prefs_backup_recovered':bool(State.prefs_recovered),
                  'message_kind':State.status_kind,
                  'runtime_fault_types':list(State.runtime_failures[-12:]),
                  'last_fault_sites':getattr(State,'runtime_fault_sites',None)},
            'art':{'mode':State.art_mode,'loaded_count':len(State.art_textures),
                   'drawn_count':State.art_drawn_count,
                   'failed_ids':sorted(State.art_failed),
                   'deferred_ids':sorted(State.art_deferred),
                   'status_tag':State.art_status.split(' / ')[0]},
            'r12_audit':{'restore_remaining':r12_restore_summary(),'community_grant_uncertain':State.r12_grant_uncertain is not None,'xp_attempt_uncertain':State.r12_xp_attempt is not None},
            'player_lab':{'view':State.r10_view,'track':State.r10_track,'pending_progression':State.r10_progress_job is not None,
                'reward_samples':[{'group':r['group'],'delta':r['delta'],'levels':r['levels']} for r in State.r10_rewards],
                'bonus_active':State.r10_bonus is not None,'wallet_history':list(State.r10_wallet_history)},
            'audio':{'mode':State.audio_mode,'hover_enabled':State.audio_hover,
                     'status_tag':State.audio_status.split(' // ')[0]},
            'input':{'requested_mode':State.input_mode_used,
                     'ui_only_api_accepted':bool(State.input_guard_confirmed),
                     'native_duplicate_releases_blocked':State.duplicate_native_releases_blocked,
                     'foreground_focus_guards':State.foreground_guard_count,
                     'foreground_guard_active':bool(State.foreground_suspended or State.foreground_resume_after>0),
                  'controller_replacement_policy':'never write flags/input mode to a new PC',
                     'note':'Accepted API call is not proof BL4 consumes all game events'},
            'echo_sandbox':{'available_field_definitions':len(TUNING_FIELDS),'draft_values':len(State.sandbox_stage),
                            'owned_pairs':len(State.combat_last),'xp_owned':State.xp_owner is not None,
                            'live_game_verified':False,'native_crash_resolved':False,
                            'weapon_owned_fields':len(State.weapon_owned),'xp_source':'REWARD' if State.xp_external_view else State.xp_route,
                            'native_xp_state':('QUARANTINED' if State.native_xp_adapter and State.native_xp_adapter.unknown_handle else 'UNRESOLVED' if State.native_xp_adapter and State.native_xp_adapter.unresolved else 'OWNED' if State.native_xp_adapter and State.native_xp_adapter.handle is not None else 'IDLE'),
                            'input_guard_readback':State.input_guard_readback,'dock_view':State.dock_view},
            'effects':{'god':bool(State.god),'noclip':bool(State.noclip),
                       'world_time_multiplier':round(State.speed,2),
                       'walk_multiplier':round(State.motion_scale,2),
                       'jump_multiplier':round(State.jump_selected,2),
                       'gravity_multiplier':round(State.gravity_selected,2),
                       'flight_boost_held':bool(State.noclip_boost_active),
                       'flight_preboost_multiplier':State.noclip_boost_base,
                       'session_booster':State.boost_preset,
                       'booster_status_tag':str(State.boost_status).split(' / ')[0][:35],
                       'fov_selected':State.fov_selected},
            'travel':{'stage':State.travel_last_state,'sweep_requested':True,
                      'rollback_attempts':State.travel_rollback_attempts,
                      'emergency_return_available':State.travel_recovery_anchor is not None,
                      'notice':'Sweep and position readback do not establish safe terrain or host authority'},
            'external_arena':{'recommended_batch_only':State.arena_planned_batch,
                              'installed_files_not_enabled':_arena_local_mod_files(),
                              'director_candidates':len(ENCOUNTER_CATALOGUE),
                              'owned_tracked_count':len(State.encounter_owned),
                              'request_budget_used':State.encounter_budget,
                              'pending_request':State.encounter_job is not None,
                              'note':'Optional reviewed BMS integration; queued requests are not proof of spawned actors; native verification still required'},
            'forge':{'catalogue_size':len(SPAWN_POOLS),
                     'stage':State.forge_stage,
                     'last_request_state':'FAILED' if 'FAILED' in State.spawn_last else 'NOT CONFIRMED'},
            'read_only_api_audit':{
                'status':'RUN' if State.advanced_audit_unix is not None else 'NOT_RUN',
                'captured_unix_time':State.advanced_audit_unix,
                'character_and_categories':dict(State.advanced_audit),
                'allowlisted_actor_methods_present':{
                    key:list(value) for key,value in State.advanced_audit_matches.items()},
                'class_presence_checked_unix':State.capabilities_checked_unix,
                'class_presence':{str(k):bool(v) for k,v in State.capabilities.items()},
                'meaning':'These are READ-ONLY names/presence checks. NOT validated spawn or edit functions.',
                'no_gameplay_write_intended':True},
            'limitations':[
                'Game actions and networking are not certified by this report.',
                'A present rendering/audio API does not establish visible or audible output.',
                'Run your own save backups before persistent gameplay modifications.'
            ]
        }
        path=Path(SETTINGS_DIR)/'CROWNs_Freedom_QA_Report.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        stage=path.with_name(path.name+'.tmp')
        stage.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
        stage.replace(path)
        log('QA REPORT SAVED // sdk_mods/settings/CROWNs_Freedom_QA_Report.json')
        return True
    except Exception as exc:
        log('QA EXPORT FAILED // '+type(exc).__name__)
        return False

def toggle_ui_diagnostics():
    State.diag_open=not State.diag_open
    State.diag_page=0
    if State.diag_open:State.activity_open=False
    if State.opened:redraw()

def next_ui_diagnostics():
    # Exactly the same conservative number of lines on small displays.
    _,_,_,height,_,_=State.panel_rect or (0,0,0,600,0,0)
    per_page=4 if height>=700 else 3
    page_count=max(1,math.ceil(len(ui_diagnostic_lines())/per_page))
    State.diag_page=(State.diag_page+1)%page_count
    if State.opened:redraw()

def poll_hover_help():
    if not State.opened:return
    hovered=None
    hovered_entry=None
    for entry in State.buttons:
        try:
            if not entry.get('disabled') and bool(entry['widget'].IsHovered()):
                hovered=entry['name']
                hovered_entry=entry
                break
        except Exception:continue
    # Duplicate captions are common (CLOSE, HELP, NEXT). Track the actual
    # hovered widget, not just its text, or the border lands on the wrong row.
    hover_identity=id(hovered_entry['widget']) if hovered_entry is not None else None
    if hover_identity==State.hovered_control:return
    State.hovered_control=hover_identity
    highlights=getattr(State,'mouse_hover_frame',[])
    if len(highlights)==4:
        if hovered_entry is None or State.controller_mode:
            for bar in highlights:size_position(bar,-60,-60,1,1,15)
        else:
            x,y,w,h=hovered_entry['rect']
            for bar,frame in zip(highlights,((x-3,y-3,w+6,3),(x-3,y+h,w+6,3),
                        (x-3,y-3,3,h+6),(x+w,y-3,3,h+6))):size_position(bar,*frame,15)
    if hovered is not None:
        play_ui_sound('hover')
        call(State.status_widget,'SetText',_status_brief('TIP // '+_control_description(hovered),State.status_chars))
    else:
        call(State.status_widget,'SetText',_status_brief('STATUS // '+State.message,State.status_chars))


def widget(path):
    return create("/Script/UMG." + path, State.tree)

def box(parent, x,y,w,h,col,z=1):
    b=widget("Border")
    call(b, "SetBrushColor", linear(col))
    _palette_binding(b,'box',col)
    call(b,"SetVisibility",4) # HitTestInvisible
    put(parent,b)
    size_position(b,x,y,w,h,z)
    return b

def _clip_text(value,max_chars):
    """TextBlocks have no responsive font metric via PythonSDK; bound our labels."""
    string=str(value).replace('\n',' ')
    limit=max(8,int(max_chars))
    return string if len(string)<=limit else string[:limit-3].rstrip()+'...'

def _fit_block_text(value, columns, lines):
    """Hard-wrap explanatory text inside its real card allocation.

    Unreal TextBlock automatic wrapping is version dependent. Hard limits
    prevent instructions painting over the next control when it is ignored.
    """
    columns=max(12,int(columns))
    lines=max(1,int(lines))
    words=str(value).replace('\r',' ').replace('\n',' ').split()
    output=[];current=''
    for word in words:
        if len(word)>columns:word=word[:columns-3]+'...'
        candidate=(current+' '+word).strip() if current else word
        if len(candidate)<=columns:
            current=candidate
            continue
        if current:output.append(current)
        current=word
    if current:output.append(current)
    if len(output)<=lines:return '\n'.join(output)
    kept=output[:lines]
    last=kept[-1]
    kept[-1]=last[:max(0,columns-3)].rstrip()+'...'
    return '\n'.join(kept)

def _status_caption():
    return {'ERROR':'! CHECK','CAUTION':'! CONFIRM','OK':'OK',
            'INFO':'INFO','IDLE':'READY'}.get(State.status_kind,'STATUS')

def _status_tint():
    if State.status_kind=='ERROR':return theme_color('danger')
    if State.status_kind=='CAUTION':return theme_color('accent')
    if State.status_kind=='OK':return theme_color('highlight')
    return theme_color('border')

def _status_brief(value,max_chars):
    value=' '.join(str(value).split())
    length=max(32,int(max_chars))
    if len(value)<=length:return value
    # Keep both the action and the actionable end of native error messages.
    front=max(16,int(length*.55))
    return value[:front].rstrip()+' ... '+value[-(length-front-5):]

def text(parent,label,x,y,w,h,col=WHITE,scale=.72,z=5):
    t=widget('TextBlock')
    # Use a readable minimum on ordinary screens; source text still clips
    # to physical control bounds, and extremely narrow controls keep fallback.
    scaled=max(.60 if float(h)>=19 else .52,
               min(1.50,float(scale)*State.font_scale))
    # All single-line text gets strict char bounds and native clipping. This
    # prevents the long Unreal error lines and chips seen outside v2.3 cards.
    single_line=float(h)<43.0
    content=str(label)
    if single_line:
        chars=max(7,int(float(w)/(13.0*scaled)))
        content=_clip_text(content,chars)
    else:
        # This is defensive against Oak2 builds that ignore SetWrapTextAt.
        # Explicit newlines and an allocated-height limit always remain.
        columns=max(10,int(float(w)/(13.2*scaled)))
        rows=max(1,int(float(h)/(27.0*scaled)))
        content=_fit_block_text(content,columns,rows)
    call(t,'SetText',content)
    call(t,'SetColorAndOpacity',slate(col))
    _palette_binding(t,'text',col)
    call(t,'SetRenderTransformPivot',v2(0,0))
    call(t,'SetRenderScale',v2(scaled,scaled))
    call(t,'SetVisibility',4)
    call(t,'SetClipping',1) # EWidgetClipping::ClipToBounds, ignored on old builds
    call(t,'SetAutoWrapText',False)
    virtual_w=max(20.0,float(w)/scaled)
    virtual_h=max(6.0,float(h)/scaled)
    call(t,'SetWrapTextAt',virtual_w)
    put(parent,t)
    size_position(t,x,y,virtual_w,virtual_h,z)
    return t

def create_mouse_cursor_aid(layout):
    """Optional hit-test-invisible software pointer when BL4 hides OS cursor.

    Draw only five small native shapes once per redraw. They never intercept
    mouse clicks and their position is updated cheaply without widget rebuild.
    """
    State.cursor_shapes=[]
    State.cursor_last=None
    State.mouse_last=None
    if not State.cursor_aid:return
    for col in (theme_color('bg'),theme_color('highlight'),theme_color('accent'),
                theme_color('bg'),theme_color('highlight')):
        State.cursor_shapes.append(box(layout,-80,-80,1,1,col,60))

def update_mouse_cursor_aid(pc,now):
    if not State.opened:return
    if now-State.mouse_refresh_at<1/30:return
    State.mouse_refresh_at=now
    if pc is None:return
    # Re-assert only when the engine hides the pointer, not every game frame.
    try:
        if not bool(pc.bShowMouseCursor):pc.bShowMouseCursor=True
    except Exception:pass
    position=_mouse_position(pc)
    if position is None:
        State.cursor_last=None
        for piece in State.cursor_shapes:size_position(piece,-80,-80,1,1,60)
        return
    if State.mouse_last is not None and (abs(position[0]-State.mouse_last[0])>11 or
                                        abs(position[1]-State.mouse_last[1])>11):
        if State.controller_mode and not State.drag_armed:
            State.controller_mode=False;State.r10_device='MOUSE'
            State.hovered_control=None  # force hover/focus visual update
            _controller_update_focus_outline()
    State.mouse_last=position
    if not State.cursor_shapes:return
    factor=max(.2,State.render_scale)  # do not apply Unreal viewport DPI twice
    px,py=position[0]/factor,position[1]/factor
    # Avoid a second cursor outside CROWN: show only inside the menu itself.
    bounds=State.panel_rect
    if bounds is None or not(bounds[0]<=px<=bounds[0]+bounds[2] and
                              bounds[1]<=py<=bounds[1]+bounds[3]):
        State.cursor_last=None  # re-paint when returning to identical point
        for piece in State.cursor_shapes:size_position(piece,-80,-80,1,1,60)
        return
    # Cyan crosshair with a dark outline and amber centre: visible on both
    # light/bright and dark textures; no asset importer or custom shader.
    pieces=((px-12,py-3,25,7),(px-3,py-12,7,25),
            (px-10,py-2,21,4),(px-2,py-10,4,21),(px-3,py-3,7,7))
    if State.cursor_last is not None and abs(px-State.cursor_last[0])<.5 and abs(py-State.cursor_last[1])<.5:return
    for part,r in zip(State.cursor_shapes,pieces):size_position(part,*r,60)
    State.cursor_last=(px,py)

def toggle_cursor_aid():
    State.cursor_aid=not State.cursor_aid
    save_preferences()
    log('MOUSE VISIBILITY AID // '+('ON' if State.cursor_aid else 'OFF'))
    _queue_toast('CURSOR_ON' if State.cursor_aid else 'CURSOR_OFF')
    if State.opened:redraw()

def note_panel(parent,title,body,x,y,w,h,warning=False):
    if h<58 or w<160:return
    edge=theme_color('danger') if warning else theme_color('accent')
    panel=theme_color('panel')
    box(parent,x,y,w,h,panel[:3]+(.72*State.panel_opacity,),8)
    box(parent,x,y,3,h,edge,9)
    text(parent,title,x+18,y+7,w-36,24,edge,.84,10)
    text(parent,body,x+18,y+34,w-36,max(18,h-39),theme_color('text'),.76,10)

def chip(parent,label,x,y,w,h,active=False,danger=False):
    fill = theme_color("danger") if danger else (theme_color("accent") if active else theme_color("muted"))
    ink = (0.08,0.08,0.08,1.0) if active else theme_color("text")
    box(parent,x,y,w,h,theme_color("border"),9)
    box(parent,x+1.5,y+1.5,w-3,h-3,fill,10)
    text(parent,label,x+8,y+3,w-16,h-6,ink,.52,12)

def _button_caption_scale(caption,width,small=False,height=43):
    """Fit long action labels in their physical button, preserving hit targets.

    The real name remains stored on the button for full hover explanation and
    controller action. The rendered name is clipped only as a last resort.
    """
    normal=.64 if height<30 else (.82 if small else .90)
    available=max(34.0,float(width)-32.0)
    # text() defensively clips based on 13 px per source character at 1.0
    # render scale; choose a scale that agrees with that EXACT bound.
    need=(available / (13.0*max(1,len(str(caption)))*State.font_scale))
    return max(.58,min(normal,need))

def btn(parent, caption, x,y,w,h,action, active=False,danger=False,small=False,disabled=False,icon=None):
    fill = theme_color("muted") if disabled else (theme_color("danger") if danger else (theme_color("header") if active else theme_color("action")))
    edge = theme_color("border") if disabled else (theme_color("danger") if danger else (theme_color("accent") if active else theme_color("border")))
    ink = theme_color('accent') if active and not danger else theme_color("text")
    # Neon Vault: dark glass hit targets, cyan tech seams and yellow active state.
    # UMG-native fallback stays readable if Unreal texture imports fail.
    transparent_fill=fill[:3]+(((.98 if active else .64) if State.theme_idx==0 else (.96 if active else .64))*State.panel_opacity,)
    nav=(State.panel_rect is not None and x<State.panel_rect[0]+min(290.,max(224.,State.panel_rect[2]*.18)) and y>State.panel_rect[1]+130 and y+h<State.panel_rect[1]+State.panel_rect[3]-165 and State.dock_mode=='FULL')
    if not nav and (active or danger):box(parent,x-1,y-1,w+2,h+2,edge[:3]+(.62,),9)
    elif not nav:box(parent,x+8,y+h-1,w-16,1,edge[:3]+(.30,),9)
    box(parent,x,y,w,h,transparent_fill,10)
    # One surface, one edge; avoid a bevel around every text label.
    # Native clickable Button remains authoritative: this optional imported
    # skin is purely decorative, ignores all clicks and shares cached textures.
    # Existing native background is ALWAYS available if the importer declines.
    skin_drawn=False
    nav=(State.panel_rect is not None and x<State.panel_rect[0]+min(290.,max(224.,State.panel_rect[2]*.18)) and y>State.panel_rect[1]+130 and y+h<State.panel_rect[1]+State.panel_rect[3]-165 and State.dock_mode=='FULL')
    if not nav and (active or danger) and State.theme_idx in (0,6) and not State.safe_mode and State.art_mode!="SHAPES" and w>=112 and h>=27 and not disabled:
        prefix='AFTERDARK_' if State.theme_idx==6 else 'ECHO_'
        plate='R3_CARD' if active and not danger and State.theme_idx==0 else prefix+('BTN_DANGER' if danger else ('BTN_ACTIVE' if active else 'BTN_IDLE'))
        skin_drawn=optional_art_image(parent,plate,x,y,w,h,z=10,opacity=.80 if active or danger else .38)
    if active or danger:
        box(parent,x+1,y+3,3,h-6,theme_color('accent') if active else theme_color('danger'),11)
    # Controller focus has a distinct cyan frame; amber remains the ACTIVE value.
    focused=(State.controller_mode and (State.controller_enabled or State.r10_device=='KEYBOARD')
             and State.controller_focus==len(State.buttons) and not disabled)
    if focused:
        box(parent,x-3,y-3,w+6,2.4,theme_color('highlight'),11)
        box(parent,x-3,y+h+.6,w+6,2.4,theme_color('highlight'),11)
        box(parent,x-3,y-3,2.4,h+6,theme_color('highlight'),11)
        box(parent,x+w+.6,y-3,2.4,h+6,theme_color('highlight'),11)
    if active:
        box(parent,x+w-11,y+5,6,h-10,theme_color('highlight'),11)
        box(parent,x+w-20,y+6,4,4,theme_color('bg'),11)
    elif danger:
        box(parent,x+w-11,y+5,5,h-10,theme_color('accent'),11)
    b=widget("Button")
    put(parent,b)
    size_position(b,x,y,w,h,12)
    call(b,"SetVisibility",0)
    attempt(b,'SetIsFocusable',False)
    call(b,"SetIsEnabled",not disabled)
    call(b,"SetRenderOpacity",.03)
    # Stock OS/UMG tooltip balloons were enormous white overlays in BL4.
    # CROWN's own bottom status line already supplies help on hover.
    # Clear native tooltips and keep the hover/status help path.
    call(b,'SetToolTipText','')
    pad=2 if h<30 else (7 if small else 10)
    badge=None
    label_caption=caption
    upper=str(caption).upper()
    if w>=190 and h>=32:
        if upper in ('ENABLE GOD MODE','DISABLE GOD MODE','GOD MODE: ON','GOD MODE: OFF'):
            badge='ON' if State.god else 'OFF'
            label_caption='GOD MODE'
        elif upper in ('ENABLE NOCLIP','DISABLE NOCLIP','NOCLIP: ON','NOCLIP: OFF'):
            badge='ON' if State.noclip else 'OFF'
            label_caption='NOCLIP'
        elif upper in ('ENABLE NO TARGET','DISABLE NO TARGET','NO TARGET: ON','NO TARGET: OFF'):
            badge='REQ' if State.target_off else 'OFF'
            label_caption='NO TARGET'
    # Existing Button remains the ONLY clickable control; badge shapes and
    # text cannot intercept mouse, touch or controller selection. Reserve
    # visual space for right-side glyphs so button captions cannot overlap.
    has_dropdown=upper.startswith('THEME:') and w>=155 and h>=30
    has_check=active and not badge and not has_dropdown and w>=125 and h>=30
    glyph_pad=20 if has_dropdown or has_check else 0
    icon_pad=28 if icon is not None and w>=150 and h>=32 else 0
    if icon_pad:optional_art_image(parent,icon,x+9,y+(h-20)/2,20,20,z=13,opacity=.7 if disabled else .95)
    label_width=w-22-icon_pad-(66 if badge else 0)-glyph_pad
    label_scale=_button_caption_scale(label_caption,label_width,small,h)
    pad=max(2.,(h-30.*label_scale*State.font_scale)/2.)
    text(parent,label_caption,x+11+icon_pad,y+pad,label_width,max(7,h-2*pad),
         theme_color("dim") if disabled else ink,label_scale,13)
    if has_check:
        optional_art_image(parent,'CHECK',x+w-29,y+(h-17)/2,16,16,z=13,opacity=.82)
    if has_dropdown:
        optional_art_image(parent,'DROP_ARROW',x+w-25,y+(h-12)/2,14,12,z=13,opacity=.81)
    if badge:
        bw=49.0;bx=x+w-bw-9;by=y+(h-24)/2
        box(parent,bx,by,bw,24,theme_color('highlight') if badge in ('REQ','ON') else theme_color('bg'),13)
        text(parent,badge,bx+5,by+4,bw-10,17,
             (0.08,0.12,0.16,1.0) if badge in ('REQ','ON') else theme_color('dim'),.63,14)
    State.buttons.append({"widget":b,"run":action,"pressed":False,"name":caption,
                          "rect":(float(x),float(y),float(w),float(h)),
                          "disabled":bool(disabled)})
    return b

def forge_search_input(parent, x, y, width, height):
    """Construct one native UMG search box; Apply Search reads only on click."""
    try:
        field=widget('EditableTextBox')
        put(parent,field)
        size_position(field,x,y,width,height,19)
        if not attempt(field,'SetText',State.spawn_search_draft):
            raise RuntimeError('Native EditableTextBox.SetText unavailable')
        call(field,'SetHintText','Find a weapon by name...')
        try:field.ForegroundColor=linear(theme_color('text'))
        except Exception:pass
        try:field.BackgroundColor=linear(theme_color('muted'))
        except Exception:pass
        call(field,'SetIsReadOnly',False)
        call(field,'SetVisibility',0)
        call(field,'SetIsEnabled',True)
        State.search_widget=field
        # This is optional: some SDK builds don't expose UWidget.SetKeyboardFocus.
        # Leave mouse-editing usable when it is unavailable.
        if not State.controller_mode:attempt(field,'SetKeyboardFocus')
        return True
    except Exception as error:
        State.search_widget=None
        log('SEARCH FIELD // '+str(error)[:84])
        return False

def forge_level_input(parent,x,y,width,height):
    try:
        field=widget('EditableTextBox')
        put(parent,field)
        size_position(field,x,y,width,height,19)
        if not attempt(field,'SetText',State.level_draft):
            raise RuntimeError('Numeric Edit Box unavailable')
        call(field,'SetHintText','Type level (1-100)')
        call(field,'SetIsReadOnly',False)
        call(field,'SetVisibility',0)
        call(field,'SetIsEnabled',True)
        if not State.controller_mode:attempt(field,'SetKeyboardFocus')
        try:field.ForegroundColor=linear(theme_color('text'))
        except Exception:pass
        try:field.BackgroundColor=linear(theme_color('muted'))
        except Exception:pass
        State.level_widget=field
    except Exception as error:
        State.level_widget=None
        log('LEVEL INPUT // '+str(error)[:84])

def crown_emblem(parent,x,y,size):
    """Original layered insignia, no game artwork, no image loads."""
    box(parent,x,y,size,size,theme_color('border'),4)
    box(parent,x+4,y+4,size-8,size-8,theme_color('bg'),5)
    box(parent,x+size*.19,y+size*.27,size*.18,size*.40,theme_color('accent'),6)
    box(parent,x+size*.43,y+size*.19,size*.18,size*.48,theme_color('accent'),6)
    box(parent,x+size*.67,y+size*.27,size*.13,size*.40,theme_color('accent'),6)
    box(parent,x+size*.17,y+size*.68,size*.68,size*.08,theme_color('highlight'),7)

def _slider_display(value, percentage):
    if percentage=='SLOTS':return str(int(round(value)))
    if percentage=='SECONDS':return '%.2fs'%value
    return ('%d%%' % round(value*100)) if percentage else ('x%.2f' % value)

class UISlider:
    """One bounded native slider, visual fill and shared precise editor.

    No native delegates are attached. Poll once per UI tick, commit after
    release, then let tick's boundary perform any requested redraw.
    """
    def __init__(self,widget,label,value,apply,percentage=False,minimum=0,maximum=1,step=.01,name='',fill=None,track=None):
        self.widget,self.label,self.apply=widget,label,apply
        self.value=float(value);self.percentage=percentage;self.dragged=False
        self.minimum,self.maximum,self.step=float(minimum),float(maximum),float(step)
        self.name=name;self.fill=fill;self.track=track
        self.generation=State.frame_generation
        self.committed=self.value
    def validate(self,value):
        try:value=float(value)
        except (ValueError,TypeError,OverflowError):return None
        if not math.isfinite(value):return None
        return round(max(self.minimum,min(self.maximum,value))/self.step)*self.step
    def display(self,value):
        if self.percentage=='NUMBER':return '%g'%value
        return _slider_display(value,self.percentage)
    def update_fill(self,value):
        if self.fill is None or self.track is None:return
        x,y,w=self.track
        proportion=max(0,min(1,(value-self.minimum)/(self.maximum-self.minimum)))
        size_position(self.fill,x,y,max(1,w*proportion),3,18)
    def adjust(self,direction,coarse=False):
        return _slider_apply_checked(self,self.value+direction*self.step*(10 if coarse else 1))


def slider(parent,label,current,minimum,maximum,x,y,width,callback):
    minimum,maximum=float(minimum),float(maximum)
    current=_finite_setting(current,minimum,maximum,minimum)
    percentage=('SECONDS' if any(unit in str(label).upper() for unit in ('COOLDOWN','DURATION','FADE SECONDS')) else
                'SLOTS' if 'SLOTS' in str(label).upper() else
                True if 'OPACITY' in str(label).upper() or 'TEXT SIZE' in str(label).upper() else
                'NUMBER' if any(q in str(label).upper() for q in ('LEVEL','POINT ALLOWANCE','QUANTITY','FOV','CHARGES','ACCENT RED','ACCENT GREEN','ACCENT BLUE','GAME UNITS','DOCK WIDTH')) else False)
    step=1 if percentage in ('SLOTS','NUMBER') else .01
    box(parent,x,y,width,72,theme_color('panel'),9)
    box(parent,x,y,3,72,theme_color('border'),10)
    text(parent,label,x+13,y+7,max(55,width-195),25,theme_color('text'),.76,13)
    value_label=text(parent,('%g'%current if percentage=='NUMBER' else _slider_display(current,percentage)),x+width-176,y+7,90,25,theme_color('accent'),.77,13)
    w=widget('Slider')
    for name,value in (('SetMinValue',minimum),('SetMaxValue',maximum),('SetStepSize',step),('SetValue',current)):
        call(w,name,value)
    call(w,'SetSliderBarColor',linear(theme_color('border')))
    call(w,'SetSliderHandleColor',linear(theme_color('highlight')))
    try:w.IsFocusable=False
    except Exception:pass
    call(w,'SetIsEnabled',True);call(w,'SetVisibility',0)
    put(parent,w);size_position(w,x+13,y+36,width-26,28,20)
    box(parent,x+15,y+63,width-30,3,theme_color('muted'),17)
    fill=box(parent,x+15,y+63,1,3,theme_color('highlight'),18)
    ref=UISlider(w,value_label,current,callback,percentage,minimum,maximum,step,label,fill,(x+15,y+63,width-30))
    ref.update_fill(current)
    State.sliders.append(ref)
    # Slider is a real controller target. Left/Right requests one step; A
    # opens exact/stepper editing. Disabled native IsPressed is never required.
    State.buttons.append({'widget':w,'run':lambda r=ref:numeric_open(r),
        'pressed':False,'name':label,'rect':(x+13,y+36,width-26,28),'disabled':False,'slider':ref})
    btn(parent,'EDIT',x+width-77,y+5,65,27,lambda r=ref:numeric_open(r),small=True)
    return w

def numeric_open(ref):
    if ref.generation!=State.frame_generation or ref not in State.sliders:return False
    State.numeric_editor={'page':State.page,'anchor':_session_anchor(),'name':ref.name,'value':ref.value,'original':ref.value,
        'minimum':ref.minimum,'maximum':ref.maximum,'step':ref.step,'apply':ref.apply,
        'text':'%g'%ref.value,'error':'','generation':State.frame_generation}
    State.numeric_widget=None
    redraw()

def _numeric_read():
    item=State.numeric_editor
    if item is None:return None
    raw=item['text']
    if State.numeric_widget is not None:
        try:raw=str(State.numeric_widget.GetText())
        except Exception:pass
    item['text']=raw[:40]
    if len(raw)>40:
        item['error']='Number is too long.'
        return None
    try:value=float(raw)
    except (ValueError,TypeError,OverflowError):value=float('nan')
    if not math.isfinite(value) or not item['minimum']<=value<=item['maximum']:
        item['error']='Enter a finite value from %g to %g.'%(item['minimum'],item['maximum'])
        return None
    if item['step']==1 and value!=int(value):
        item['error']='Whole numbers only.'
        return None
    item['error']=''
    return value

def numeric_step(direction,coarse=False):
    item=State.numeric_editor
    if item is None:return False
    value=_numeric_read()
    if value is None:value=item['value']
    item['value']=max(item['minimum'],min(item['maximum'],round(value+direction*item['step']*(10 if coarse else 1),5)))
    item['text']='%g'%item['value'];item['error']=''
    if State.numeric_widget is not None:call(State.numeric_widget,'SetText',item['text'])
    # Update exact entry in place. The stepped value survives later redraws.
    return True

def numeric_apply():
    def commit():
        item=State.numeric_editor
        value=_numeric_read()
        if item is None:return False
        if item.get('page',State.page)!=State.page or item.get('anchor',_session_anchor())!=_session_anchor():
            numeric_cancel();log('VALUE REJECTED // Editor session changed.');return False
        if value is None:redraw();return False
        if abs(value-item['original'])<.0000001:
            State.numeric_editor=State.numeric_widget=None;redraw();return True
        # Release the old native field before a backend can request a new frame.
        State.numeric_widget=None
        try:result=item['apply'](value)
        except Exception as error:
            record_runtime_fault('NUMERIC_APPLY',error);result=False
        if result is False:
            item['error']='Backend declined value. '+State.message[:90]
            State.numeric_editor=item
            log('VALUE REJECTED // '+item['error'])
        else:State.numeric_editor=None
        redraw()
        return result is not False
    return _ui_batch(commit)

def numeric_cancel():
    State.numeric_editor=State.numeric_widget=None
    if State.opened:redraw()

def numeric_reset():
    item=State.numeric_editor
    if item is None:return
    item['value']=item['original'];item['text']='%g'%item['original'];item['error']=''
    if State.numeric_widget is not None:call(State.numeric_widget,'SetText',item['text'])

def draw_numeric_editor(layout,left,y,width,step,action,info):
    item=State.numeric_editor
    text(layout,'PRECISE EDIT / '+item['name'],left,y,width,33,theme_color('highlight'),.96)
    text(layout,item['error'] or 'STAGED VALUE / %g - %g'%(item['minimum'],item['maximum']),left,y+36,width,26,theme_color('danger' if item['error'] else 'dim'),.68)
    try:
        field=widget('EditableTextBox');put(layout,field);size_position(field,left,y+71,width,45,20)
        if not attempt(field,'SetText',item['text']):raise RuntimeError('Text input unavailable')
        call(field,'SetHintText','Type a number, then Apply')
        call(field,'SetVisibility',0);call(field,'SetIsEnabled',True);call(field,'SetIsReadOnly',False)
        State.numeric_widget=field
        if not State.controller_mode:attempt(field,'SetKeyboardFocus')
    except Exception:
        State.numeric_widget=None
        text(layout,'TEXT INPUT UNAVAILABLE / use Fine or Coarse below, or Cancel',left,y+74,width,40,theme_color('danger'),.65)
    for i,(label,fn) in enumerate((('- FINE',lambda:numeric_step(-1)),('+ FINE',lambda:numeric_step(1)),('- COARSE',lambda:numeric_step(-1,True)),('+ COARSE',lambda:numeric_step(1,True)),('APPLY VALUE',numeric_apply),('CANCEL',numeric_cancel),('RESET DRAFT',numeric_reset))):
        xx=left+(i%2)*(width/2+6);yy=y+130+(i//2)*43
        btn(layout,label,xx,yy,width/2-6,36,fn,active=(label=='APPLY VALUE'),small=True)
    # Errors occupy the reserved range/status line above the field, including 720p.

def _appearance_snapshot():
    return {'theme':State.theme_idx,'opacity':State.panel_opacity,'scale':State.panel_scale,
        'text':State.font_scale,'art':State.art_mode,'compact':State.compact,'reduced':State.reduced_motion,
        'accent':State.custom_accent,'background':State.background_opacity,'duration':State.transition_duration}

def appearance_begin():
    if State.appearance_draft is None:State.appearance_draft=_appearance_snapshot()
    return State.appearance_draft

def appearance_stage(key,value):
    draft=appearance_begin()
    bounds={'opacity':(.65,1,.94),'scale':(.72,2,1),'text':(.85,1.25,1),'background':(.2,1,.75),'duration':(.08,.4,.16)}
    if key in bounds:value=_finite_setting(value,*bounds[key])
    elif key=='accent':
        try:value=_valid_accent(value)
        except ValueError:return False
    elif key=='theme':value=_safe_theme_index(value)
    elif key=='art':value='SHAPES' if value=='SHAPES' else 'AUTO'
    elif key in ('compact','reduced'):value=bool(value)
    else:return False
    draft[key]=value
    preview=State.appearance_preview
    if key=='opacity' and preview.get('panel') is not None:
        call(preview['panel'],'SetBrushColor',linear(_THEME_RGBA[draft['theme']]['panel'][:3]+(value,)))
    if key=='text' and preview.get('title') is not None:
        call(preview['title'],'SetRenderScale',v2(value,value))
    return True

def appearance_cycle(key):
    draft=appearance_begin()
    if key=='theme':appearance_stage(key,(draft[key]+1)%len(THEMES))
    elif key=='art':appearance_stage(key,'SHAPES' if draft[key]=='AUTO' else 'AUTO')
    else:appearance_stage(key,not draft[key])
    redraw()

def appearance_apply():
    draft=appearance_begin()
    try:_appearance_extra_validate(draft)
    except ValueError as error:
        log('APPEARANCE REJECTED // '+str(error));return False
    # Sanitize again at the mutation boundary; all fields must be validated
    # BEFORE any widget/theme or persistent preference is changed.
    for key,value in tuple(draft.items()):appearance_stage(key,value)
    old=_appearance_snapshot()
    if old==draft:
        log('APPEARANCE // No changes to apply.');return True
    State.custom_accent=draft['accent'];State.background_opacity=draft['background'];State.transition_duration=draft['duration']
    State.theme_idx=draft['theme'];State.panel_opacity=draft['opacity']
    State.panel_scale=draft['scale'];State.font_scale=draft['text']
    State.art_mode=draft['art'];State.compact=draft['compact'];State.reduced_motion=draft['reduced']
    State.appearance_draft=None
    _set_native_phase('APPEARANCE_APPLY')
    save_preferences()
    # Pure palette changes update existing native properties. Geometry, art
    # transitions and captions require just one queued, atomic frame swap.
    geometry=any(old[k]!=draft[k] for k in ('scale','text','art','compact','reduced'))
    if geometry:redraw()
    else:
        refresh_palette()
        log('APPEARANCE APPLIED // Palette updated in place; no canvas rebuild.')
    return True

def appearance_cancel():
    State.appearance_draft=None
    redraw()

def appearance_reset():
    State.appearance_draft={'theme':0,'opacity':.94,'scale':1.,'text':1.,'art':'AUTO','compact':False,'reduced':True,'accent':None,'background':.75,'duration':.16}
    redraw()

def draw_appearance_studio(layout,left,y,width,half,step,bh,info):
    if State.appearance_view!='MAIN':
        draw_appearance_extras(layout,left,y,width,half,info);return
    draft=appearance_begin()
    for i,(label,key,lo,hi) in enumerate((('PANEL OPACITY','opacity',.65,1),('WINDOW SCALE','scale',.72,2),('TEXT SIZE','text',.85,1.25))):
        slider(layout,label,draft[key],lo,hi,left,y+i*83,half,lambda v,k=key:appearance_stage(k,v))
    xx=left+half+12
    choices=(('THEME / '+THEMES[draft['theme']]['name'],'theme'),('ART / '+draft['art'],'art'),('LAYOUT / '+('COMPACT' if draft['compact'] else 'EXPANDED'),'compact'),('MOTION / '+('REDUCED' if draft['reduced'] else 'FADE'),'reduced'))
    for i,(label,key) in enumerate(choices):
        btn(layout,label,xx,y+i*45,half,37,lambda k=key:appearance_cycle(k),small=True)
    btn(layout,'DIRECT THEMES',xx,y+188,(half-8)/2,37,lambda:appearance_view('THEMES'),small=True)
    btn(layout,'COLOURS / FADE',xx+(half+8)/2,y+188,(half-8)/2,37,lambda:appearance_view('COLOURS'),small=True)
    palette=dict(_THEME_RGBA[draft['theme']])
    if draft.get('accent'):palette['accent']=_hex(draft['accent'])
    controls=(('APPLY',appearance_apply),('CANCEL',appearance_cancel),('RESET DRAFT',appearance_reset))
    cw=(width-16)/3
    for i,(label,fn) in enumerate(controls):btn(layout,label,left+i*(cw+8),y+252,cw,39,fn,active=i==0,small=True)
    info('Draft changes stay local until Apply. Cancel keeps the applied appearance. Theme/opacity update native properties in place; scale/art swap one staged frame. Reduced motion is on by default.',step*4.7)
    if State.panel_rect[3]>=850:
        py=y+388;ph=min(170,State.panel_rect[1]+State.panel_rect[3]-177-py)
        if ph>=125:
            sample=box(layout,left,py,width,ph,palette['panel'][:3]+(draft['opacity'],),8)
            box(layout,left,py,4,ph,palette['highlight'],9)
            box(layout,left+14,py+ph-14,width-28,2,palette['accent'],9)
            title=text(layout,'ECHO / '+THEMES[draft['theme']]['name'],left+24,py+17,width-48,38,palette['text'],draft['text'],13)
            text(layout,'COLOUR & TYPE PREVIEW / READ ONLY',left+24,py+65,width-48,25,palette['highlight'],.70,13)
            text(layout,'Drag opacity or text size to preview. Apply commits the menu appearance.',left+24,py+99,width-48,27,palette['dim'],.68,13)
            State.appearance_preview={'panel':sample,'title':title}


def _palette_binding(obj,kind,color):
    """Cache semantic swatches and avoid a generator per colour per widget."""
    signature=(State.theme_idx,State.custom_accent,State.background_opacity,State.panel_opacity)
    if getattr(State,'palette_match_signature',None)!=signature:
        State.palette_match_signature=signature
        State.palette_match_rows=tuple((key,theme_color(key)) for key in _THEME_RGBA[State.theme_idx])
    for key,reference in State.palette_match_rows:
        if (abs(color[0]-reference[0])<.0001 and abs(color[1]-reference[1])<.0001
                and abs(color[2]-reference[2])<.0001):
            factor=color[3]/reference[3] if reference[3] else 1.
            State.palette_bindings.append((obj,kind,key,factor));return

def refresh_palette():
    for binding in tuple(State.palette_bindings):
        obj,kind,key=binding[:3];factor=binding[3] if len(binding)>3 else 1.
        col=theme_color(key);col=col[:3]+(max(0.,min(1.,col[3]*factor)),)
        call(obj,'SetBrushColor' if kind=='box' else 'SetColorAndOpacity',linear(col) if kind=='box' else slate(col))

R11_RETURN_LABELS={
    'LOOT':'PROGRESSION','SPAWN':'FORGE','ARENA':'ENCOUNTERS',
    'GEAR':'WEAPON LAB','MOTION':'MOVEMENT','BOOSTS':'FLIGHT',
    'WAYPOINTS':'TRAVEL','PROFILES':'RECIPES','CAPACITY':'CAPACITY',
    'COMBAT':'COMBAT','COMMUNITY':'COMMUNITY','WORLD':'WORLD',
    'PLAYER':'PLAYER','STYLE':'STYLE','DEV':'DIAGNOSTICS',
    'FINDER':'FIND TOOLS','PARTY':'PARTY','DISPLAY':'DISPLAY',
}

def r11_last_workspace(recent,known):
    """Safe, read-only recent navigation, never auto-execute a gameplay action.

    Session history may contain stale, invalid or saved values. Restrict to
    a public label whitelist and the installed page registry. No game API.
    """
    if not isinstance(recent,(tuple,list)):return None
    for page in recent[:6]:
        if type(page) is str and page in R11_RETURN_LABELS and page in known:
            return (page,R11_RETURN_LABELS[page])
    return None


def draw_dashboard(layout,left,y,width,step,action,info):
    """An illustrated destination board with a compact play strip, not a wall of text."""
    available=State.panel_rect[1]+State.panel_rect[3]-177-y
    gap=12.;cw=(width-gap)/2
    short=available<430
    hero_h=72 if short else min(154,max(104,available*.25))
    optional_art_image(layout,'R9_EXPEDITION',left,y,width,hero_h,z=7,opacity=.96)
    text(layout,'YOUR NEXT EXPEDITION',left+18,y+12,width*.76,30,theme_color('text'),1.05,9)
    if not short:text(layout,'Build. Explore. Experiment.',left+18,y+49,width*.62,28,theme_color('accent'),.80,9)
    text(layout,session_role()+'  /  SESSION TOOLS',left+18,y+hero_h-23,width-36,20,theme_color('dim'),.58,9)
    yy=y+hero_h+gap
    # Fit the actual available body at 480p virtual scale through 1440p.
    card_h=max(74,min(150,(available-hero_h-120)/2))
    cards=(('ITEM FORGE','Browse pools and stage a drop.','R9_FORGE','SPAWN',None),
           ('ENCOUNTER DIRECTOR','Arena or BMS, with live lifecycle checks.','R9_ARENA','ARENA',None),
           ('PROGRESSION LAB','Track earned XP and choose one backend.','FIELD_CARD_XP','LOOT','XP'),
           ('MOVEMENT & FLIGHT','Owned restoration, boost and travel.','R9_FLIGHT','MOTION',None))
    for i,(caption,detail,asset,page,mode) in enumerate(cards):
        r9_art_card(layout,caption,detail,asset,left+(i%2)*(cw+gap),yy+(i//2)*(card_h+gap),cw,card_h,
                    lambda p=page,m=mode:r3_open_tool(p,m),'0'+str(i+1))
    qy=yy+2*(card_h+gap)
    choices=(('GOD MODE: '+('ON' if State.god else 'OFF'),lambda:(set_god(),redraw()),State.god),
             ('NOCLIP: '+('ON' if State.noclip else 'OFF'),lambda:(set_noclip(),redraw()),State.noclip),
             ('REFILL ACTION SKILL',refill_skills,False),('FARM RUN',farm_open,False))
    bw=(width-3*8)/4
    for i,(caption,fn,active) in enumerate(choices):btn(layout,caption,left+i*(bw+8),qy,bw,35,fn,active=active,small=True)
    if qy+80<y+available:
        last=r11_last_workspace(State.recent_tools,_KNOWN_PAGES)
        last_choice=(('BACK TO '+last[1]),(lambda p=last[0]:show_page(p))) if last else ('COMMUNITY MODS',lambda:show_page('COMMUNITY'))
        for i,(caption,fn) in enumerate((('MY RECIPES',recipe_open),('BOOST LAB',lambda:show_page('BOOSTS')),
                                        ('TRAVEL BOOKMARKS',lambda:show_page('WAYPOINTS')),last_choice)):
            btn(layout,caption,left+i*(bw+8),qy+44,bw,31,fn,small=True)


# Field names/Value+BaseValue pattern reviewed from Squ1ggs Damage & More
# (MIT, 2026). Original guarded adapter; no third-party hooks are installed.
COMBAT_FIELDS={
    'OUTGOING':('DamageCauserData','DamageDealtMultiplier',.1,100.,'OUTGOING DAMAGE'),
    'INCOMING':('DamageState','DamageTakenMultiplier',0.,10.,'INCOMING DAMAGE'),
    'CRITICAL':('DamageCauserData','DefaultCriticalHitMultiplier',.1,20.,'CRITICAL MULTIPLIER'),
}

def combat_pair(key,actor=None):
    if key not in TUNING_FIELDS:return None
    actor=pawn() if actor is None else actor
    container,field,*_=TUNING_FIELDS[key]
    try:
        target=actor
        for segment in container.split('.') if container else ():target=getattr(target,segment)
        pair=getattr(target,field)
        values=tuple(_read_number(pair,k) for k in ('Value','BaseValue'))
        if any(v is None for v in values):return None
        # Primitive float fields only; never replace a wrapped struct.
        if any(type(getattr(pair,k)) is not float for k in ('Value','BaseValue')):return None
        return pair,values
    except Exception:return None

def combat_tune(key,value):
    import sys
    if key not in TUNING_FIELDS or type(value) not in (int,float) or not math.isfinite(value):return False
    lo,hi=TUNING_FIELDS[key][2:4]
    if not lo<=value<=hi or not is_local_host_action():return False
    if State.r10_bonus is not None and not State.r10_bonus_internal:
        log('TUNING BLOCKED // Stop the owned timed bonus first.');return False
    if any(n.split('.')[-1] in ('damage_and_more','bl4_damage_and_more','resources_and_cooldowns','bl4_resources_and_cooldowns') for n in sys.modules):return False
    actor=pawn()
    if actor is None or actor.HasAuthority() is not True:return False
    if State.combat_owner is not None:
        if not same_unreal_object(actor,State.combat_owner):
            State.combat_originals={};State.combat_last={};State.combat_owner=None
        else:
            for owned,expected in State.combat_last.items():
                live=combat_pair(owned,actor)
                if live is None or live[1]!=expected:
                    log('TUNING BLOCKED // Outside change; ownership retained, no overwrite.');return False
    resolved=combat_pair(key,actor)
    if resolved is None:return False
    pair,before=resolved;value=float(value);was_owned=key in State.combat_originals
    previous_last=State.combat_last.get(key)
    State.combat_owner=actor;State.combat_originals.setdefault(key,before)
    State.combat_last[key]=(value,value)
    try:
        pair.Value=value;pair.BaseValue=value
        after=combat_pair(key,actor)
        if after is None or after[1]!=(value,value):raise RuntimeError('pair readback differs')
    except Exception as error:
        # Only undo fields still equal to this attempt, never an outside value.
        for field,old in zip(('Value','BaseValue'),before):
            try:
                if _read_number(pair,field)==value:setattr(pair,field,old)
            except Exception:pass
        current=combat_pair(key,actor)
        if current is not None and current[1]==before:
            if was_owned:State.combat_last[key]=previous_last
            else:State.combat_originals.pop(key,None);State.combat_last.pop(key,None)
            if not State.combat_originals:State.combat_owner=None
        record_runtime_fault('COMBAT_PAIR',error);log('TUNING FAILED // Owned rollback attempted; unresolved fields retained.');return False
    log(TUNING_FIELDS[key][4]+' // %g / field readback matched; gameplay unverified.'%value)
    if State.opened:redraw()
    return True

def restore_combat_tuning():
    actor=pawn();restored=0
    if actor is None or not same_unreal_object(actor,State.combat_owner):
        State.combat_owner=None;State.combat_originals={};State.combat_last={};State.r10_bonus=None;return 0
    State.r10_bonus=None
    if actor.HasAuthority() is not True:return 0
    for key,original in tuple(State.combat_originals.items()):
        resolved=combat_pair(key,actor)
        if resolved is None or resolved[1]!=State.combat_last.get(key):continue
        pair,current=resolved
        try:
            pair.Value,pair.BaseValue=original
            verified=combat_pair(key,actor)
            if verified is not None and verified[1]==original:
                State.combat_originals.pop(key,None);State.combat_last.pop(key,None);restored+=1
        except Exception as error:record_runtime_fault('COMBAT_RESTORE',error)
    if not State.combat_originals:State.combat_owner=None
    return restored

def combat_toggle_view():
    State.combat_view='TUNING' if State.combat_view=='QUICK' else 'QUICK'
    redraw()

def draw_combat_tuning(layout,left,y,width,bh,info):
    yy=y+47
    btn(layout,'QUICK COMBAT TOOLS',left,y,width,36,combat_toggle_view,small=True)
    for key,spec in COMBAT_FIELDS.items():
        found=combat_pair(key)
        if found is not None:
            slider(layout,spec[4],found[1][0],spec[2],spec[3],left,yy,width,lambda v,k=key:combat_tune(k,v))
        else:
            text(layout,spec[4]+' / NOT EXPOSED BY THIS GAME BUILD',left+10,yy+18,width-20,40,theme_color('dim'),.73)
        yy+=77
    btn(layout,'RESTORE COMBAT VALUES',left,yy,width,36,lambda:(restore_combat_tuning(),redraw()),small=True)
    info('Experimental local float-pair edits from reviewed BL4 source. Authoritative solo only; no sticky hooks. Missing fields stay read-only. Values restore only on the same pawn while still owned.',340)



def same_unreal_object(first, second):
    """Fail closed on unknown UObject identity when restoring owned input.

    SDK versions can return None/0 for an invalid or unexposed address. Two
    unknown addresses must NEVER compare equal: that could restore CROWN's
    cursor/UIOnly state onto a newly spawned game-owned PlayerController.
    Python identity remains enough when the same original wrapper is passed.
    """
    if first is second:
        return first is not None
    if first is None or second is None:
        return False
    a,b=_native_address(first),_native_address(second)
    return a is not None and b is not None and a==b

def _native_address(obj):
    if obj is None: return None
    try:
        value=int(obj._get_address())
        return value if value>0 else None
    except Exception:
        return None

def world_and_state():
    try:
        from mods_base import ENGINE
        world=ENGINE.GameViewport.World
        return world,getattr(world,"GameState",None)
    except Exception:
        return None,None

def coop_snapshot():
    """Sanitised, read-only session data; never imply network replication works.

    No player names, account IDs, Unreal pointers or positions are included.
    This helper does not perform gameplay writes or toggle remote consent.
    """
    role=session_role()
    players=party_entries()
    count=len(players)
    local=sum(1 for x in players if x['local'])
    remote=sum(1 for x in players if not x['local'])
    stable=bool(count and local==1 and all(x['key'] is not None for x in players))
    selected=bool(State.party_selected is not None and any(
        x['key']==State.party_selected and not x['local'] for x in players))
    acknowledged=bool(role=='HOST' and State.party_approved and stable and
                      State.party_approved_roster==tuple(sorted(x['key'] for x in players)))
    # A host acknowledgement is NOT automatic opt-in by individual friends.
    return {'role':role,'visible_players':count,'remote_players':remote,
            'local_player_identified':local==1,'roster_stable':stable,
            'selected_friend_valid':selected,
            'host_consent_acknowledged':acknowledged,
            'remote_controls_eligible':bool(acknowledged and remote),
            'solo_only_tools':'item pools, event modifiers, wallet writes, enemy arena',
            'warning':'Remote features require consent, host authority, and in-game validation.'}

def show_coop_status():
    """Read-only party snapshot for friends in an active BL4 lobby."""
    report=coop_snapshot()
    State.coop_last_status=(str(report['role'])+' / '+str(report['visible_players'])+
        ' players / '+str(report['remote_players'])+' friends / '+
        ('HOST ACKNOWLEDGED' if report['host_consent_acknowledged'] else 'REMOTE EDITS LOCKED'))
    log('CO-OP CHECK // '+State.coop_last_status)
    if State.opened:redraw()
    return report

_NETMODE_NAMES={0:'NM_Standalone',1:'NM_DedicatedServer',2:'NM_ListenServer',3:'NM_Client'}

def _netmode_name(raw):
    """Canonical ENetMode name from int, str, enum wrapper, or None.

    pyunrealsdk may reflect the enum as its int, a python enum, or a wrapper
    whose str() is like 'ENetMode.NM_ListenServer'. Never raises.
    """
    if raw is None:return None
    if isinstance(raw,str):
        s=raw
    else:
        name=getattr(raw,'name',None)
        if isinstance(name,str) and name in _NETMODE_NAMES.values():return name
        val=getattr(raw,'value',None)
        for candidate in (val,raw):
            try:
                iv=int(candidate)
                if iv in _NETMODE_NAMES:return _NETMODE_NAMES[iv]
            except Exception:pass
        try:s=str(raw)
        except Exception:return None
    up=s.upper()
    for iv,nm in _NETMODE_NAMES.items():
        if nm.upper() in up:return nm
    if 'STANDALONE' in up or 'SOLO' in up:return 'NM_Standalone'
    if 'LISTEN' in up:return 'NM_ListenServer'
    if 'DEDICATED' in up or 'SERVER' in up:return 'NM_DedicatedServer'
    if 'CLIENT' in up:return 'NM_Client'
    return None

def _pc_has_authority(pc):
    """Safe positive-authority read; any failure is False (fail closed)."""
    if pc is None:return False
    try:return bool(pc.HasAuthority()) is True
    except Exception:return False

def host_authority_probe():
    """Bounded, read-only HOST AUTHORITY PROBE for diagnostics.

    Captures presence/absence of the signals session_role relies on, without
    raw addresses or personal identifiers. Safe to call from diagnostics.
    """
    world,gs=world_and_state()
    pc=get_pc(possibly_loading=True)
    entry={'world_present':world is not None,'pc_present':pc is not None}
    if world is not None:
        try:
            raw=world.GetNetMode()
            entry['netmode_raw_type']=type(raw).__name__
            entry['netmode_name']=_netmode_name(raw)
        except Exception as exc:
            entry['netmode_error']=type(exc).__name__
    if pc is not None:
        try:entry['has_authority']=bool(pc.HasAuthority())
        except Exception as exc:entry['has_authority_error']=type(exc).__name__
        try:entry['role']=str(getattr(pc,'Role',None))
        except Exception as exc:entry['role_error']=type(exc).__name__
        try:entry['remote_role']=str(getattr(pc,'RemoteRole',None))
        except Exception as exc:entry['remote_role_error']=type(exc).__name__
    if gs is not None:
        try:
            arr=getattr(gs,'PlayerArray',None)
            entry['roster_len']=len(arr) if arr is not None else None
        except Exception as exc:entry['roster_error']=type(exc).__name__
    try:entry['derived_role']=session_role()
    except Exception as exc:entry['derived_error']=type(exc).__name__
    return entry

def _probe_summary():
    """One-line, bounded HOST AUTHORITY PROBE summary for the diagnostics page."""
    try:
        p=host_authority_probe()
    except Exception as exc:
        return 'UNAVAILABLE / '+type(exc).__name__
    nm=p.get('netmode_name') or p.get('netmode_error') or 'NONE'
    auth=p.get('has_authority')
    auth_s='YES' if auth is True else ('NO' if auth is False else (p.get('has_authority_error') or 'UNKNOWN'))
    role=p.get('derived_role','UNKNOWN')
    roster=p.get('roster_len')
    roster_s=('players='+str(roster)) if roster is not None else 'roster=UNKNOWN'
    return 'role=%s / netmode=%s / authority=%s / %s'%(role,nm,auth_s,roster_s)

def session_role():
    """Fail closed: unknown clients are never accepted as host.

    Derive SOLO, VERIFIED LISTEN HOST, CLIENT, DEDICATED SERVER or UNKNOWN
    from positive read-only evidence. HOST is ONLY returned when the world
    reports NM_ListenServer AND the local controller positively holds
    authority. A two-player roster never implies host.
    """
    world,gs=world_and_state()
    pc=get_pc(possibly_loading=True)
    if world is None or pc is None:
        return 'UNKNOWN'
    # Probe 1: authoritative net mode.
    try:raw=world.GetNetMode()
    except Exception:raw=None
    nm=_netmode_name(raw)
    if nm=='NM_Standalone':return 'SOLO'
    if nm=='NM_Client':return 'GUEST'
    if nm=='NM_DedicatedServer':return 'DEDICATED'
    if nm=='NM_ListenServer':
        # Positive host evidence required: listen server AND local authority.
        if _pc_has_authority(pc):return 'HOST'
        # Authority unavailable/ambiguous — record and fail closed.
        try:
            probe=host_authority_probe()
            log('HOST AUTHORITY PROBE // listen-server but authority unverified: '+str(probe))
        except Exception:pass
        return 'UNKNOWN'
    # Probe 2 fallback: only SOLO or UNKNOWN, never HOST.
    try:
        if gs is None or pc is None or not _pc_has_authority(pc):
            return 'UNKNOWN'
        players=getattr(gs,'PlayerArray',None)
        local=getattr(pc,'PlayerState',None)
        if players is None or local is None or len(players)!=1:
            return 'UNKNOWN'
        if not same_unreal_object(players[0],local):
            return 'UNKNOWN'
        driver=getattr(world,'NetDriver',None)
        if driver is not None:
            connections=getattr(driver,'ClientConnections',None)
            if connections is None or len(connections)>0:
                return 'UNKNOWN'
            if getattr(driver,'ServerConnection',None) is not None:
                return 'UNKNOWN'
        return 'SOLO'
    except Exception:
        return 'UNKNOWN'

def is_local_host_action():
    """True for verified solo or listen-host running an action on their OWN
    character/world. Remote/shared actions must still pass can_run_shared and
    party_permission_ok; this gate only unblocks host-local gameplay."""
    return session_role() in ('SOLO','HOST')

def party_entries():
    """Snapshot on-demand only, never during per-frame camera ticks."""
    world,gs=world_and_state()
    arr=getattr(gs,'PlayerArray',None) if gs is not None else None
    if arr is None:return []
    pc=get_pc(possibly_loading=True)
    local_ps=getattr(pc,'PlayerState',None) if pc else None
    result=[]
    try:n=min(len(arr),4)
    except Exception:return []
    for i in range(n):
        try:
            ps=arr[i]
            if ps is None:continue
            fn=getattr(ps,'GetPlayerName',None)
            raw=fn() if callable(fn) else getattr(ps,'PlayerName',None)
            name=str(raw or 'Player '+str(i+1)).strip()[:22]
            local=same_unreal_object(ps,local_ps)
            result.append({'index':i,'name':name,'local':local,
                           'ps':ps,'key':_native_address(ps)})
        except Exception:pass
    return result

def refresh_party():
    State.party=party_entries()
    if State.party_approved and _roster_signature()!=State.party_approved_roster:
        State.party_approved=False
        State.party_approved_roster=None
        log('CONSENT RESET // Party changed.')
    matches=[p for p in State.party if p['key'] is not None and p['key']==State.party_selected and not p['local']]
    if not matches:
        State.party_selected=None
        State.friend_teleport_confirm=0.0
        State.friend_teleport_target=None
        State.friend_teleport_anchor=None
    log('PARTY // '+str(len(State.party))+' players, role '+session_role())
    if State.opened:redraw()

def select_party(index):
    # A confirmation must never follow a changed selection to a new friend.
    State.friend_teleport_confirm=0.0
    State.friend_teleport_target=None
    State.friend_teleport_anchor=None
    State.party=party_entries()
    eligible=[p for p in State.party if p['index']==index and not p['local'] and p['key'] is not None]
    if not eligible:
        State.party_selected=None
        log('No stable remote player found in that slot.')
    else:
        State.party_selected=eligible[0]['key']
        log('TARGET // '+eligible[0]['name']+' (no action taken)')
    if State.opened:redraw()

def _roster_signature():
    rows=party_entries()
    if not rows or any(entry['key'] is None for entry in rows):
        return None
    return tuple(sorted(entry['key'] for entry in rows))

def party_permission_ok():
    if session_role()!='HOST' or not State.party_approved:
        return False
    current=_roster_signature()
    if current is None or current!=State.party_approved_roster:
        State.party_approved=False
        State.party_approved_roster=None
        log('CONSENT RESET // Someone joined/left or roster identity changed.')
        return False
    return True

def enable_party_changes():
    State.friend_teleport_confirm=0.0
    State.friend_teleport_target=None
    State.friend_teleport_anchor=None
    if session_role()!='HOST':
        State.party_approved=False
        State.party_approved_roster=None
        log('FRIEND MODS BLOCKED // You must be verified listen host.')
    elif State.party_approved:
        State.party_approved=False
        State.party_approved_roster=None
        log('FRIEND CONSENT disabled.')
    else:
        signature=_roster_signature()
        if signature is None or len(signature)<=1:
            log('FRIEND CONSENT unavailable; refresh a stable party first.')
        else:
            State.party_approved=True
            State.party_approved_roster=signature
            log('FRIEND CONSENT acknowledged for CURRENT PARTY only. Confirm each player agreed.')
    if State.opened:redraw()

def selected_friend():
    if State.party_selected is None: return None
    pc=get_pc(possibly_loading=True)
    if pc is None or getattr(pc,'PlayerState',None) is None:
        log('Cannot identify your own PlayerState; friend actions blocked.')
        return None
    for item in party_entries():
        if item['key']==State.party_selected and not item['local'] and item['key'] is not None:
            return item
    State.party_selected=None
    return None

def remote_pawn(ps):
    """Strict targeted resolution; no find-all/name guessing or blind remote changes."""
    for method in ('GetPawn','GetPlayerPawn'):
        try:
            fn=getattr(ps,method,None)
            p=fn() if callable(fn) else None
            if p is not None and hasattr(p,'bCanBeDamaged'):return p
        except Exception: pass
    try:
        ctrl=ps.GetPlayerController()
        p=getattr(ctrl,'OakCharacter',None) if ctrl is not None else None
        if p is not None and hasattr(p,'bCanBeDamaged'):return p
    except Exception: pass
    return None

def remote_target_god():
    if not party_permission_ok():
        log('BLOCKED // Host mode + friend consent acknowledgement required.');return
    item=selected_friend()
    if item is None:
        log('Select a connected friend first.');return
    ps=item['ps']; addr=item['key']
    if addr is None:
        log('Cannot validate friend identity, refusing to modify.');return
    target=remote_pawn(ps)
    if target is not None and same_unreal_object(target,pawn()):
        log('Selected player resolves to your own pawn; blocked.')
        return
    if target is None:
        log('Friend pawn unavailable on this game build.');return
    try:
        if not bool(target.HasAuthority()):
            log('Friend pawn is not locally authoritative; action blocked.');return
    except Exception:
        log('Cannot verify authority for friend; action blocked.');return
    try:
        existing=State.remote_originals.get(addr)
        if existing is not None:
            original,old_target=existing
            if not same_unreal_object(target,old_target):
                log('Friend respawned/rejoined; use new session after restore.');return
            target.bCanBeDamaged=bool(original)
            if bool(target.bCanBeDamaged)!=bool(original):
                log('Restore write was not accepted.');return
            del State.remote_originals[addr]
            log('FRIEND SHIELD OFF // '+item['name'])
        else:
            original=target.bCanBeDamaged
            if type(original) is not bool:raise ValueError('damage original unavailable')
            State.remote_originals[addr]=(original,target)
            target.bCanBeDamaged=False
            if bool(target.bCanBeDamaged):
                log('Friend God Mode write was not accepted.');return
            State.remote_originals[addr]=(original,target)
            log('FRIEND SHIELD ON // '+item['name']+' (host-local test)')
    except Exception as exc:
        log('Friend action unavailable: '+str(exc))
    if State.opened:redraw()

def refill_friend_skill():
    if not party_permission_ok():
        log('BLOCKED // Host + friend consent acknowledgement required.');return
    item=selected_friend()
    if item is None:
        log('Select a friend first.');return
    target=remote_pawn(item['ps'])
    if target is not None and same_unreal_object(target,pawn()):
        log('Selected player resolves to your own pawn; blocked.');return
    if target is None:
        log('Friend pawn unavailable.');return
    try:
        if not bool(target.HasAuthority()):
            log('Friend pawn is not locally authoritative.');return
    except Exception:
        log('Cannot verify friend pawn authority.');return
    try:
        lib=unrealsdk.find_class('GbxSkillComponentFunctions_ActionSkill').ClassDefaultObject
        lib.RefillCooldown(target,1.0,0)
        log('FRIEND SKILL REFILL requested // '+item['name'])
    except Exception as exc:
        log('Friend skill refill unavailable: '+str(exc))

def restore_friends():
    errors=0
    restored=0
    latest={item['key']:item for item in party_entries() if item['key'] is not None}
    for addr,(original,old_target) in list(State.remote_originals.items()):
        item=latest.get(addr)
        target=remote_pawn(item['ps']) if item and not item['local'] else None
        if target is None or not same_unreal_object(old_target,target):
            errors+=1
            continue
        try:
            if not bool(target.HasAuthority()):raise RuntimeError('friend authority changed')
            current=target.bCanBeDamaged
            if type(current) is not bool:raise ValueError('friend damage field unavailable')
            if current!=bool(original):target.bCanBeDamaged=bool(original)
            if bool(target.bCanBeDamaged)!=bool(original):errors+=1
            else:restored+=1;State.remote_originals.pop(addr,None)
        except Exception:errors+=1
    # Failed/stale entries remain until restoration or session retirement.
    State.party_approved=False
    State.party_approved_roster=None
    State.party_selected=None
    State.wallet_pending=None
    State.wallet_expires=0.0
    State.friend_teleport_confirm=0.0
    State.friend_teleport_target=None
    State.friend_teleport_anchor=None
    if errors:log('FRIEND RESTORE // %d unconfirmed. Ask affected players to reload if needed.'%errors)
    elif restored:log('FRIEND RESTORE // %d current pawns restored.'%restored)
    return errors==0

def has_other_players():
    # If roster is inaccessible, fail CLOSED for irreversible/world-wide actions.
    rows=party_entries()
    if not rows:
        return session_role()!='SOLO'
    return len(rows)>1

def can_run_shared(action):
    role=session_role()
    if role=='SOLO':return True
    if role not in ('HOST',):
        log('BLOCKED '+action+' // Game session authority not verified.')
        return False
    if not has_other_players():return True
    if party_permission_ok():return True
    log('BLOCKED '+action+' // Need host status + everyone agrees first.')
    return False

def current_content():
    world,gs=world_and_state()
    try:
        level=str(world.GetName())[:48] if world is not None else 'Not in world'
    except Exception:
        level='Unresolved level'
    State.content_line='MAP: '+level+' | SESSION: '+session_role()
    log(State.content_line)
    if State.opened:redraw()

def pawn():
    pc=get_pc(possibly_loading=True)
    return getattr(pc,"OakCharacter",None) if pc is not None else None

def ensure_pawn():
    target=pawn()
    if target is None:
        log("Load into a playable map first.")
        return None
    if State.saved_char is not None and not same_unreal_object(target, State.saved_char):
        # A previous actor became invalid; never write into it on transition.
        State.saved_char=None
        State.damage_original=None
        State.collision_original=None
        State.god=State.noclip=State.target_off=False
        _reset_noclip_flight_state()
        State.infinite_ammo=False
    return target

def protect_character(target):
    if _session_anchor() is None:return False
    if State.saved_char is None or not same_unreal_object(target,State.saved_char) or State.r12_player_anchor!=_session_anchor():
        State.r12_player_fields={};State.r12_player_anchor=_session_anchor();State.saved_char=target
        # Never invent defaults when the engine does not expose originals.
        State.damage_original=r12_player_read(target,'bCanBeDamaged')
        State.collision_original=r12_player_read(target,'bActorEnableCollision')
        State.movement_original=r12_player_read(target,'MODE')
        State.r12_player_component=getattr(target,'OakCharacterMovement',None)

def set_god(turn_on=None):
    actor=ensure_pawn()
    if actor is None:return False
    desired=not State.god if turn_on is None else bool(turn_on)
    protect_character(actor)
    if State.damage_original is None:return False
    value=False if desired or State.noclip else State.damage_original
    if not r12_player_change(actor,{'bCanBeDamaged':value}):return False
    State.god=desired;log('GOD MODE '+('ON' if desired else 'OFF')+' / damage field readback; gameplay unverified.');return True

def set_noclip(turn_on=None):
    actor=ensure_pawn()
    if actor is None:return False
    desired=not State.noclip if turn_on is None else bool(turn_on)
    protect_character(actor)
    if any(v is None for v in (State.damage_original,State.collision_original,State.movement_original)):return False
    if not desired and State.noclip_boost_active:release_noclip_flight_boost()
    plan=({'bCanBeDamaged':False,'MODE':5,'bActorEnableCollision':False} if desired else
          {'bActorEnableCollision':State.collision_original,'MODE':State.movement_original,
           'bCanBeDamaged':False if State.god else State.damage_original})
    if not r12_player_change(actor,plan):return False
    State.noclip=desired
    log('NOCLIP '+('ON' if desired else 'OFF')+' / collision/damage readback; movement request unverified.');return True

def toggle_no_target():
    c=ensure_pawn()
    if c is None:return
    pc=get_pc()
    try:
        lib=unrealsdk.find_class("GbxTargetingFunctionLibrary").ClassDefaultObject
        if State.target_off and (State.r12_target_pc is None or not same_unreal_object(pc,State.r12_target_pc)):
            State.target_off=False;State.r12_target_pc=None
        desired=not State.target_off
        if desired:State.r12_target_pc=pc;State.target_off=True
        lib.LockTargetableByAI(pc,"crown_native",desired,desired)
        State.target_off=desired;State.r12_target_pc=pc if desired else None
        log("AI TARGET "+("OFF" if desired else "NORMAL")+" requested (unverified)")
    except Exception as e: log("AI targeting unsupported: "+str(e))

def get_worldsettings():
    from mods_base import ENGINE
    return ENGINE.GameViewport.World.PersistentLevel.WorldSettings

def set_world_time(value):
    try:value=float(value)
    except (ValueError,TypeError,OverflowError):return False
    if not math.isfinite(value) or not .1<=value<=4.:return False
    if not can_run_shared('WORLD TIME'):return False
    world=None;before=None;after=None;dispatch_returned=False
    try:
        world=get_worldsettings();before=_read_number(world,'TimeDilation')
        if before is None:raise ValueError('World speed unavailable')
        if State.world_saved is not None and not same_unreal_object(State.world_saved,world):
            State.world_saved=State.world_original=State.world_last=None
        if State.world_saved is not None and (State.world_last is None or
                abs(before-State.world_last)>max(.02,abs(State.world_last)*.01)):
            log('WORLD SPEED BLOCKED // changed outside CROWN; no overwrite.');return False
        if State.world_saved is None:State.world_saved=world;State.world_original=before
        State.world_last=float(value)
        world.TimeDilation=value
        dispatch_returned=True
        after=_read_number(world,'TimeDilation')
        if after is not None:State.world_last=after
        if after is None or abs(after-value)>.02:raise RuntimeError('World speed readback failed')
        if State.world_saved is None:State.world_saved=world;State.world_original=before
        State.world_last=float(value)
        State.speed=value
        log('WORLD TIME x%.2f (readback OK; may affect simulation)'%value)
        if State.opened and State.page=='WORLD':redraw()
        return True
    except Exception as error:
        restored=False
        if world is not None and before is not None:
            try:
                if same_unreal_object(get_worldsettings(),world):
                    current=_read_number(world,'TimeDilation')
                    if current==value or (dispatch_returned and after is not None and current==after):world.TimeDilation=before
                restored=_read_number(world,'TimeDilation')==before
                if restored:State.world_last=before
            except Exception:pass
        log('WORLD TIME REJECTED // '+type(error).__name__+' / '+('previous value restored' if restored else 'RESTORATION UNCONFIRMED'))
        return False

def change_fov(value):
    try:value=float(value)
    except (ValueError,TypeError,OverflowError):return False
    if not math.isfinite(value) or not 60<=value<=140:return False
    obj=None;before=None
    try:
        obj=get_pc().player
        before=tuple(_read_number(obj,k) for k in ('BaseFOV','VehicleFOV'))
        if any(v is None for v in before):raise ValueError('FOV fields unavailable')
        if State.fov_saved is not None and not same_unreal_object(State.fov_saved,obj):
            State.fov_saved=State.fov_original=State.fov_last=None;State.fov_selected=None
        if State.fov_saved is not None:
            expected=State.fov_last
            if expected is None or any(abs(v-e)>max(.05,abs(e)*.01)
                                       for v,e in zip(before,expected)):
                log('FOV BLOCKED // Another system changed the camera; no overwrite.');return False
        desired=int(round(value))
        if State.fov_saved is None:State.fov_saved=obj;State.fov_original=before
        State.fov_last=(float(desired),float(desired))
        for name in ('BaseFOV','VehicleFOV'):setattr(obj,name,desired)
        if any(_read_number(obj,k)!=desired for k in ('BaseFOV','VehicleFOV')):raise RuntimeError('FOV readback failed')
        if State.fov_saved is None:State.fov_saved=obj;State.fov_original=before
        State.fov_last=(float(desired),float(desired))
        State.fov_selected=desired
        log('FOV %d (player-value readback OK; camera may override)'%desired)
        if State.opened and State.page=='PLAYER':redraw()
        return True
    except Exception as error:
        restored=True
        if obj is not None and before is not None and all(v is not None for v in before):
            for name,old in zip(('BaseFOV','VehicleFOV'),before):
                try:
                    if same_unreal_object(getattr(get_pc(),'player',None),obj) and _read_number(obj,name)==desired:setattr(obj,name,old)
                    restored=restored and _read_number(obj,name)==old
                except Exception:restored=False
        if restored and obj is not None:State.fov_last=before
        log('FOV REJECTED // '+type(error).__name__+' / '+('previous fields restored' if restored else 'RESTORATION UNCONFIRMED'))
        return False

def confirm_kill():
    if not can_run_shared("KILL ENEMIES"):return
    now=time.monotonic()
    context=studio_context()
    if context is None:return False
    if State.confirm_kill_until > now and State.r12_kill_confirm==context:
        State.confirm_kill_until = 0.0
        if dev_perk(3,"Kill enemies"):
            log("Kill Enemies requested. This action cannot be undone.")
    else:
        State.r12_kill_confirm=context
        State.confirm_kill_until=now+5.0
        log("WARNING: Kill Enemies may disrupt missions. Press again within 5s.")
    if State.opened: redraw()

def dev_perk(number,name):
    if type(number) is not int or number not in (3,5) or not can_run_shared(name):return False
    context=r12_grant_context()
    if context is None or State.r12_grant_uncertain==context:
        log('PERK BLOCKED // Context unavailable or previous native result uncertain.');return False
    try:
        pc=get_pc(possibly_loading=True)
        if studio_context()!=context:raise RuntimeError('player changed')
        State.r12_grant_uncertain=context
        pc.ServerActivateDevPerk(number)
        State.r12_grant_uncertain=None
        log(name+' requested; gameplay effect unverified.');return True
    except Exception as error:
        record_runtime_fault('DEV_PERK',error);log(name+' unconfirmed; no retry in this context.');return False

def toggle_infinite_ammo():
    if dev_perk(5,"Infinite ammo toggle"):
        State.ammo_requests += 1
        log("INFINITE AMMO / TOGGLE REQUEST SENT; actual state unknown. Check ammo in-game.")

def refill_skills():
    c=ensure_pawn()
    if c is None:return
    try:
        lib=unrealsdk.find_class("GbxSkillComponentFunctions_ActionSkill").ClassDefaultObject
        lib.RefillCooldown(c,1.0,0)
        log("Action skill cooldown refill requested.")
    except Exception as e:log("Cooldown refill unavailable: "+str(e))

def restore():
    State.active_event="NONE"
    State.spawn_pending=None
    State.wallet_pending=None
    State.wallet_expires=0.0
    restore_friends()
    restore_combat_tuning()
    _cleanup_safely('RESTORE_WEAPONS',weapon_restore)
    _cleanup_safely('RESTORE_XP',xp_restore_owned)
    State.sandbox_stage={}
    State.encounter_epoch+=1;State.encounter_job=None;State.encounter_confirm=None
    r12_restore_player()
    r12_restore_target()
    # Never automatically toggle a server-side perk. Without state readback,
    # calling toggle again could ENABLE ammo instead of restoring it.
    r12_restore_world()
    if State.fov_saved is not None and State.fov_original is not None:
        reset_fov()
    restore_motion()
    State.r12_restore_status=r12_restore_summary()
    log('RESTORE TEMP / Remaining ownership: '+State.r12_restore_status+' / Server perks and permanent grants not reversed.')
    if State.opened: redraw()

def preset_easy():
    set_god(True)
    if State.opened:redraw()

def preset_hard():
    set_god(False)
    if State.noclip: set_noclip(False)
    set_world_time(1.0)
    if State.opened:redraw()

def crown_capability_rows():
    # Read-only capability snapshot; disk presence != activated mod.
    import sys
    role=session_role()
    art=('SAFE MODE / IMPORTS OFF' if State.safe_mode else
         'SHAPES / ART OFF' if State.art_mode=='SHAPES' else
         'AUTO / '+str(State.art_status)[:32])
    files=_arena_local_mod_files()
    if files is None:
        dep='FILES NOT ACCESSIBLE / CHECK MODS MENU'
    else:
        dep=' / '.join(label+(' FILE' if files.get(key) else ' MISSING')
            for label,key in (('BMS','bms_file'),('OAK SPAWNER','oak_spawner_file'),('BLIMGUI','blimgui_file')))
    loaded=any(name in sys.modules for name in ('mob_spawner','bl4_mob_spawner'))
    xpmod=xp_external_backend()
    direct=('NATIVE / EXPERIMENTAL' if State.xp_route=='NATIVE' else
            'BL4LIVE / '+('MODULE FOUND' if 'bl4_live' in sys.modules else 'NOT LOADED'))
    return [
        'SESSION: '+role+' / host-only and solo-only permissions enforced',
        'GRAPHICS: '+art+' / '+str(getattr(State,'art_archive_status','NOT CHECKED'))[:25],
        'XP / INTERNAL: '+direct+' / earned XP still unproven',
        'XP / OPTIONAL: '+(xpmod[0]+' LOADED / UNVERIFIED' if xpmod else 'COMMUNITY XP MOD NOT LOADED'),
        'SPAWNER DEPENDENCIES: '+dep,
        'SPAWNER RUNTIME: '+('BMS MODULE PRESENT, CHECK API' if loaded else 'MISSING / EXTERNAL MOD')+' / no guarantee of live actors',
        'FORGE: game item pool requests / delivered item not proven',
        'CONTROLLER: focus navigation / character input isolation unverified',
        'OPTIONAL MODS: '+community_modules_brief(),
        'SOUND: '+str(State.audio_status)[:39]+' / Windows audio only',
    ]

def refresh_crown_capabilities():
    State.capability_status_rows=crown_capability_rows()
    log('CAPABILITY STATUS // Read-only overview refreshed; no game calls made.')
    if State.opened:redraw()
    return True

def toggle_capability_guide():
    State.guide_status_open=not State.guide_status_open
    State.capability_page=0
    if State.guide_status_open:
        State.capability_status_rows=crown_capability_rows()
    if State.opened:redraw()
    return State.guide_status_open

def show_page(tab):
    State.r10_view=None;State.r10_confirm=None
    if tab not in _KNOWN_PAGES:return False
    if tab!='PROFILES':State.recipe_open=False;State.farm_view=False
    if tab!='COMMUNITY':State.community_confirm=None
    if tab!='FINDER':
        State.recent_tools=[tab]+[t for t in State.recent_tools if t!=tab and t in _KNOWN_PAGES][:5]
    if tab!=State.page:
        State.help_open=False
        State.sandbox_view=False;State.xp_view=False
        State.encounter_confirm=None;State.encounter_input=None
        State.resource_view=False
        State.profile_pending=None
        State.profile_manage=False
        State.numeric_editor=State.numeric_widget=None
        State.appearance_draft=None
        State.profile_name_edit=False
    State.studio_section=studio_section_for(tab)
    State.page=tab
    State.side_action_page=0
    State.forge_compare_view=False;State.weapon_confirm=None
    if State.opened:play_ui_sound('select')
    if tab!='STYLE':State.style_audio_open=False
    if tab!='GUIDE':State.guide_status_open=False
    if tab!='DEV':
        State.diag_open=False
        State.feature_ledger_open=False
    if tab in ('PLAYER','MOTION','BOOSTS','COMBAT','LOOT','WORLD','WEEKLY','PARTY'):
        State.nav_group='CORE'
    elif tab in ('TROPHIES','WAYPOINTS','PROFILES','GEAR','DISPLAY','GUIDE'):
        State.nav_group='VAULT'
    else:
        State.nav_group='MORE'
    if State.opened:_mark_menu_opened()
    redraw()
    return True

def viewport():
    pc=get_pc()
    try:
        lib=cls("/Script/UMG.WidgetLayoutLibrary").ClassDefaultObject
        scale=float(lib.GetViewportScale(pc) or 1)
        sz=lib.GetViewportSize(pc)
        w=float(sz.X)/scale;h=float(sz.Y)/scale
        if w>=700 and h>=450:return w,h
    except Exception:pass
    return 1920.0,1080.0

PAGE_HELP={
    'PLAYER':("God Mode requests damage immunity; Noclip disables collision and changes movement; No Target asks AI not to choose you. FOV widens or narrows your camera.",
              "Temporary local effects only. They may reset on travel. God and Noclip should show amber when active; RESTORE TEMP or F10 attempts owned restoration, not server perks."),
    'COMMUNITY':("Find independently installed BL4 Arena, XP Gain Multiplier and Bonk Utilities. Optionally request +5 levels, a developer loot drop or small currency awards through Bonk.",
                 "These are third-party game commands, not CROWN grants. An enabled module or accepted ConsoleCommand does NOT prove the game updated. SOLO only, two presses, character save backup required. Changes may persist and cannot be undone with F10. BL4 Arena uses its own F6 window after closing CROWN."),
    'BOOSTS':("Real local movement presets: Sprint, Rocket, High Jump and Balanced write guarded reflected speed and jump properties. While NOCLIP is enabled, hold F5 to fly faster and release to return. F5 can be rebound in SDK Mods.",
              "Temporary session-only boosts; not Borderlands 3 Science consumables. Changes may be refused if another mod owns the properties. Player Lab has experimental raise-only progression controls; any such change may persist, and F10 cannot undo it."),
    'MOTION':("Speed changes walking rates; Jump changes jump strength; Low Gravity reduces your fall. The walk-speed slider offers finer control than presets.",
              "These values are session-only and can be overwritten by the game. Restore Movement Defaults before quitting if you get stuck."),
    'COMBAT':("Refill Action Skill requests cooldown recovery. Clear Enemies requests a destructive developer action. Ammo uses an experimental game perk.",
              "Enemy clearing requires two presses and cannot be undone. Ammo state cannot be reliably read back; never assume RESTORE will reverse that perk."),
    'CAPACITY':("Optional local BL4Live bridge for reversible per-session backpack capacity and bank size. Presets and numeric input stage values; Apply requires a second confirmation.",
                "Only enabled in SOLO; BL4Live is a separately installed AGPL project. Do not combine with fixed 9999-slot pak overrides; no disk save is edited. Readback and game restart remain necessary."),
    'LOOT':("Cash and Eridium controls ask the game to add the specified currency amount. First press arms; second press confirms the selected request.",
              "Changes may be saved permanently. Back up the character first. RESTORE TEMP does not remove awarded currency, XP or levels. Solo test first."),
    'WORLD':("World Speed changes time. F8 opens 12 saved travel locations; RETURN swaps between recent positions; TRAVEL SPRINT temporarily increases walk speed.",
              "Same-map bookmarks persist but only work if the map ID is identical. A content patch, moved level geometry or server can still reject the teleport."),
    'PARTY':("Refresh Party discovers teammates. Choose one friend, then choose Boosts, Travel or Gifts. Consent Lock is a host acknowledgement, not actual permission from others.",
              "Remote changes are experimental. Ask each friend first. Client, unstable roster and unknown host identity block requests. Do not use in public lobbies."),
    'SPAWN':("Browse or search 68 item-pool candidates, edit search or level and press Enter to apply, then request an item drop with two clicks. Run BUILD/DLC -> FORGE PRE-FLIGHT first.",
              "The catalogue is not a DLC ownership check. A successful native request does not prove an item spawned. Start with one item in solo after backing up."),
    'WEEKLY':("Maurice's Black Market, Mimicron and the Wildcard are date-limited official weekly notices. The ECHO Map and server are authoritative. Save a vendor bookmark only while standing safely beside the machine.",
              "Rotations expire; old vendor coordinates are blocked. No automatic live location lookup, item unlock, DLC entitlement or blind teleport. Only user-saved same-map collision-swept travel is offered."),
    'EVENTS':("CROWN Events are custom presets such as Bullet Ballet and Moon Boots. They combine previously available temporary gameplay modifiers.",
              "They are not official seasonal Borderlands events. Stop Active Event requests temporary restoration, which can fail after maps change."),
    'CONTENT':("Map, session and API probes check information and reflected functions exposed by the currently running game build.",
              "A present API does not guarantee DLC ownership or a successful gameplay action. DLC remains separately purchased and installed."),
    'PRESETS':("Vault Vacation applies defensive settings. Walking Apocalypse applies world-speed and defence changes. Normal-ish requests local restoration.",
              "Preset effects may be partial if one game API fails. None of these are character save backups. Use F10 for emergency temporary restore."),
    'STYLE':("Themes adjust the panel look. Text, opacity and window scale control readability. MOVE repositions the panel. AUDIO opens optional Windows sound effects.",
              "Choose OFF to mute cues, or LOW/NORMAL/HIGH. Sounds are Windows-side, not integrated with the Borderlands game mixer. UI settings never grant game items."),
    'DEV':("The activity log records recent status messages. Export QA Report creates a privacy-conscious file under sdk_mods/settings. The status ribbon is optional.",
              "F7 opens, F8 travels, F9 recovers input, F6 closes urgently, F10 attempts temporary restoration. Neither F10 nor a restart can undo saved currency/items."),
    'TROPHIES':("Review all 63 public Steam Borderlands 4 achievement titles. Mark your own notes about what you have earned using the page controls.",
                "The journal cannot read your actual Steam status. It NEVER grants, blocks, resets, or changes real achievements. Verify earned status in Steam."),
    'WAYPOINTS':("F8 opens the Roadrunner hub. Save 12 named locations for farm loops, vendors and bosses; visit them across sessions on the identical map. F8 and controller work independently.",
                "Bookmark slots persist in CROWNs_Freedom_UI.json. RETURN is session-only. No blind cross-map travel or game fast-travel registry modification. Game authority and geometry can still block the move."),
    'PROFILES':("Save and load three named sets of display and Forge search preferences. Great for switching between characters manually.",
                "These profiles contain no character stats, inventory or save data, and they do not load actual character saves."),
    'GEAR':("Jump into the verified 68-item Forge filter by weapon family; never constructs a new untrusted item-pool token.",
            "This is not a universal equipment/unlock editor. Missing DLC pools can still reject a request."),
    'DISPLAY':("Choose CROWN NOIR for a translucent high-contrast UI, then edit opacity and cursor visibility in STYLE. The menu supports sizes up to 200%.",
               "The window always clamps to screen bounds. Large interface sizes may cover more gameplay; use MOVE or RESET POSITION."),
    'GUIDE':("Safe F6 emergency close and F10 temporary-value restore. Back up your save before persistent currency or item experiments.",
             "Achievements never automatically turn off due to this journal. Some save/challenge edits may trigger platform achievements; no guarantees."),
}
def toggle_page_help():
    State.help_open=not State.help_open
    if State.opened:redraw()

def _capture_editor_drafts():
    """Retain user typing across an unrelated UMG redraw, without applying it.

    Only unsubmitted draft text is captured; no game changes or item spawn.
    Native SDK text widgets may fail on a patch: preserve existing draft then.
    """
    if State.profile_name_edit and State.profile_name_widget is not None:
        try:State.profile_name_draft=str(State.profile_name_widget.GetText())[:64]
        except Exception:pass
    if State.page=='CAPACITY' and State.capacity_view=='EDIT' and State.capacity_input is not None:
        try:
            value=State.capacity_input.GetText()
            if value is not None:State.capacity_text_draft=str(value)[:6]
        except Exception:pass
    if State.page=='ARENA' and State.encounter_view=='SEARCH' and State.encounter_input is not None:
        try:State.encounter_query_draft=str(State.encounter_input.GetText())[:64]
        except Exception:pass
    if State.page!='SPAWN':return
    if State.spawn_view=='SEARCH' and State.search_widget is not None:
        try:
            value=State.search_widget.GetText()
            if value is not None:State.spawn_search_draft=str(value)[:80]
        except Exception:pass
    if State.spawn_view=='LEVEL' and State.level_widget is not None:
        try:
            value=State.level_widget.GetText()
            if value is not None:State.level_draft=str(value)[:12]
        except Exception:pass

def toggle_dock_mode():
    """Switch between full-featured black market and compact one-column Side Dock."""
    State.dock_mode='SIDE' if State.dock_mode!='SIDE' else 'FULL'
    State.side_action_page=0
    # The drawer anchors itself; preserve the original full-window placement.
    if State.opened:_mark_menu_opened()
    save_preferences()
    if State.opened:redraw()


def toggle_dock_side():
    """Dock to the opposite screen edge without touching gameplay or saves."""
    State.dock_right=not State.dock_right
    save_preferences()
    log('SIDE DOCK // '+('RIGHT' if State.dock_right else 'LEFT')+' edge')
    if State.opened and State.dock_mode=='SIDE':redraw()

def _side_action(parent,label,fn,x,y,w,active=False,danger=False,disabled=False):
    def run_and_refresh():
        # Some older game actions update state but do not redraw unless the
        # full-size page is active. Keep compact badges truthful immediately.
        previous=State.ui_rebuild_count
        fn()
        if State.opened and State.dock_mode=='SIDE' and State.ui_rebuild_count==previous:
            redraw()
    btn(parent,label,x,y,w,42,run_and_refresh,active=active,danger=danger,disabled=disabled,small=True)

def side_next_tool():
    pages=UI_CATEGORY_PAGES[_ui_category_for(State.page)]
    i=pages.index(State.page) if State.page in pages else 0
    show_page(pages[(i+1)%len(pages)])

def side_previous_tool():
    pages=UI_CATEGORY_PAGES[_ui_category_for(State.page)]
    i=pages.index(State.page) if State.page in pages else 0
    show_page(pages[(i-1)%len(pages)])

def side_action_previous():
    State.side_action_page=max(0,State.side_action_page-1)
    if State.opened:redraw()

def side_action_next():
    State.side_action_page+=1  # renderer clamps the maximum on every view
    if State.opened:redraw()


def _reset_noclip_flight_state():
    State.noclip_boost_active=False
    State.noclip_boost_base=None
    State.noclip_boost_owner=None
    State.noclip_boost_anchor=None


def start_noclip_flight_boost():
    """Hold F5 for a 2.45x flight speed, locally and only in noclip.

    Uses the pre-existing motion backend with its property readback/ownership
    guards; no UE console cheats, timers, raw key interception or save edits.
    """
    if State.opened or not State.noclip or State.noclip_boost_active:
        return False
    actor=ensure_pawn()
    anchor=_session_anchor()
    if actor is None or anchor is None:
        return False
    previous=float(State.motion_scale)
    if previous>=2.45:
        log('NOCLIP BOOST // Existing speed is already at least 2.45x. No boost needed.')
        return False
    State.noclip_boost_writing=True
    try:
        if not tune_speed(2.45):return False
    finally:
        State.noclip_boost_writing=False
    State.noclip_boost_active=True
    State.noclip_boost_base=previous
    State.noclip_boost_owner=actor
    State.noclip_boost_anchor=anchor
    log('NOCLIP BOOST // F5 held / 2.45x; release F5 to restore x%.2f.'%previous)
    return True


def release_noclip_flight_boost():
    """Restore the exact prior multiplier, refusing stale owner/session writes."""
    if not State.noclip_boost_active:return False
    saved=State.noclip_boost_base
    actor=State.noclip_boost_owner
    anchor=State.noclip_boost_anchor
    _reset_noclip_flight_state()  # Allows tune_motion ownership-checked release.
    current=pawn()
    if (actor is None or current is None or not same_unreal_object(actor,current)
            or anchor is None or anchor!=_session_anchor()):
        log('NOCLIP BOOST // Character/map changed; stale restoration refused.')
        return False
    if saved is None or not .3<=saved<=3.:return False
    result=tune_speed(saved)
    log('NOCLIP BOOST // '+('Prior movement restored.' if result else
                            'Game value changed; safe restore refused.'))
    return bool(result)


BOOST_PRESETS={
    'SPRINT':(1.55,1.0),
    'ROCKET':(2.25,1.35),
    'HIGH JUMP':(1.1,2.25),
    'BALANCED':(1.35,1.4),
}


def apply_movement_boost(name):
    """Local session-only two-field preset, with best-effort rollback.

    No fake timed booster, persistent perk grant or co-op propagation.
    """
    preset=BOOST_PRESETS.get(name)
    if preset is None:return False
    if State.noclip_boost_active:
        log('BOOST // Release F5 flight boost before applying a preset.')
        return False
    if ensure_pawn() is None:return False
    old_speed=float(State.motion_scale)
    old_jump=float(State.jump_selected)
    if not tune_speed(preset[0]):
        State.boost_status='BLOCKED / Speed field unavailable or externally changed.'
        return False
    if not tune_jump(preset[1]):
        tune_speed(old_speed)  # Still ownership guarded; does not force restore.
        State.boost_status='BLOCKED / Jump field unavailable; speed rollback attempted.'
        return False
    State.boost_preset=name
    State.boost_status=name+' / ACTIVE REQUEST / speed %.2fx / jump %.2fx'%(preset[0],preset[1])
    log('BOOST // '+State.boost_status+'; restore with BOOST RESET or F10.')
    if State.opened:redraw()
    return True


def reset_movement_boost():
    if State.noclip_boost_active:release_noclip_flight_boost()
    # Preserve user-selected gravity; restore the speed+jump this studio owns.
    speed=tune_speed(1.)
    jump=tune_jump(1.)
    if speed and jump:State.boost_preset='NONE'
    State.boost_status=('BOOST RESTORED' if speed and jump else
                        'RESTORE PARTIAL / Check motion ownership and other mods.')
    log('BOOST // '+State.boost_status)
    if State.opened:redraw()
    return bool(speed and jump)


def stage_combat_booster(name):
    """Show real combat tuning with a source-defined draft; user must Apply.

    The existing sandbox backend performs solo-authority checks and
    readback before attempting writes. This function never grants a buff.
    """
    if name not in ('GENTLE FARM','GLASS CANNON'):
        return False
    if not sandbox_solo_ready():
        State.boost_status='BLOCKED / Combat presets require an authoritative solo pawn.'
        log('COMBAT BOOST // '+State.boost_status)
        if State.opened:redraw()
        return False
    r3_open_tool('COMBAT','SANDBOX')
    result=sandbox_preset(name)
    State.boost_status=(name+' / DRAFT STAGED / Check fields then press Apply in Combat Sandbox.'
                        if result else 'STAGING FAILED / Required reflected combat fields unavailable.')
    log('COMBAT BOOST // '+State.boost_status)
    return bool(result)


def progression_bridge_status():
    """Honest compatibility discovery. Never modifies character levels/saves."""
    import sys
    found=any(name=='save_editor' or name.startswith('save_editor.') for name in sys.modules)
    message=('SAVE EDITOR MODULE PRESENT / Open its own verified LEVEL screen from the SDK mods menu.'
             if found else
             'LEVEL/PERK EDIT NOT CONNECTED / optional Save Editor provides level, skill and specialization-point editing; not bundled.')
    State.boost_status=message
    log('PROGRESSION // '+message+' Back up saves and test solo.')
    if State.opened:redraw()
    return found


def boost_hotkey_event(event):
    # mods_base exposes event_filter=None, receiving EInputEvent on each
    # press/release. Rebindable F5; no guesswork from OS key polling.
    name=getattr(event,'name',str(event))
    if str(name).endswith('IE_Pressed'):
        return start_noclip_flight_boost()
    if str(name).endswith('IE_Released'):
        return release_noclip_flight_boost()
    return False


def tune_speed(mult):
    return tune_motion('speed',mult)

def tune_jump(mult):
    return tune_motion('jump',mult)

# Search includes EVERY visible page and intentionally never triggers its action.
FINDER_TERMS={
 'BOOSTS':'boost flight sprint jump f5 noclip movement',
 'COMMUNITY':'community arena xp bonk optional levels loot integration',
 'PLAYER':'god mode noclip invincibility no target fov',
 'MOTION':'speed jump gravity sprint movement',
 'BOOSTS':'boost booster caffeine sprint speed noclip flight fly perk levels skill points XP effects',
 'COMBAT':'combat damage ammo refill clear enemies',
 'PRESETS':'presets easy challenge vacation mayhem',
 'WORLD':'world speed time dilation',
 'WEEKLY':'maurice black market weekly boss wildcard',
 'EVENTS':'events challenge chaos bullet time',
 'PARTY':'coop party friends',
 'SPAWN':'forge item weapons spawn gun search catalogue',
 'GEAR':'gear filters rifles pistol shotgun smg',
 'CONTENT':'dlc audit compatibility api forge preflight',
 'WAYPOINTS':'teleport travel roadrunner waypoint bookmarks',
 'LOOT':'currency money eridium wallet',
 'CAPACITY':'capacity backpack bank sdu slots size editable adjustable bridge mod library inventory',
 'TROPHIES':'trophies journal achievements',
 'STYLE':'theme audio colour color art opacity popup sound',
 'DISPLAY':'display scaling hud position text size',
 'PROFILES':'ui save profile',
 'DEV':'restore recovery diagnostics qa safe mode input',
 'GUIDE':'help safety backups instructions',
 'FINDER':'search find locate tools',
 'ARENA':'enemy monster boss arena npc object mob spawner battle hordes safe batch scout preflight',
}

ARENA_ADVISORY_BATCHES = (1, 2, 3, 5, 10)

def arena_set_planned_batch(count):
    """User-facing safety recommendation only; does not call any spawn API."""
    if type(count) is not int or count not in ARENA_ADVISORY_BATCHES:
        return False
    State.arena_planned_batch=count
    save_preferences()
    log('ARENA PLAN // Suggested next BMS batch: %d. Set the actual count INSIDE BMS; CROWN cannot enforce it.'%count)
    if State.opened:redraw()
    return True

def _arena_local_mod_files():
    """Bounded, read-only presence check. A file present is NOT a running mod."""
    base=Path(SETTINGS_DIR).parent if SETTINGS_DIR is not None else None
    if base is None or not base.is_dir():return None
    try:
        names=set()
        for index,entry in enumerate(base.iterdir()):
            if index>=500:break
            names.add(entry.name.lower())
    except (OSError,PermissionError):return None
    def has(stems):
        return any(name==stem or name==stem+'.sdkmod' or (name.startswith(stem+' (') and name.endswith('.sdkmod'))
                   for name in names for stem in stems)
    return {'bms_file':has(('mob_spawner',)),
            'blimgui_file':has(('blimgui',)),
            'oak_spawner_file':has(('oak_spawner','oakspawner'))}

def arena_backend_check():
    """Reports only disk presence. Never probes or invokes unknown spawning methods."""
    if session_role()!='SOLO':
        log('ARENA PREFLIGHT // Solo recommended; no bridge action performed.')
        return False
    result=_arena_local_mod_files()
    if result is None:
        log('ARENA PREFLIGHT // Cannot inspect sdk_mods; check BMS and Oak Spawner manually in the mods menu.')
        return False
    lines=['%s %s'%('BMS' if k=='bms_file' else 'BLImGui' if k=='blimgui_file' else 'Oak Spawner',
                     'FILE FOUND' if result[k] else 'NOT FOUND') for k in ('bms_file','oak_spawner_file','blimgui_file')]
    log('ARENA PREFLIGHT // '+' / '.join(lines)+' // File presence does NOT prove enabled or compatible.')
    return bool(result['bms_file'] and result['oak_spawner_file'])

def _request_bms_console(command):
    """Read-only/open-UI bridge for the separately installed BMS mod.

    Never send bms_spawn or any actor-creating command here. Our tests do not
    assert that console acceptance means a third-party mod is installed.
    """
    if command not in ('bms_gui','bms_help'):return False
    if session_role()!='SOLO':
        log('ARENA BLOCKED // Use solo only; no cooperative spawning bridge.')
        return False
    pc=get_pc(possibly_loading=True)
    if pc is None or not callable(getattr(pc,'ConsoleCommand',None)):
        log('ARENA UNAVAILABLE // No player controller console command API.')
        return False
    if time.monotonic()-State.bms_last_open<2.0:
        log('ARENA WAIT // Avoid repeated console commands.')
        return False
    try:
        pc.ConsoleCommand(command)
    except Exception as error:
        record_runtime_fault('ARENA_BRIDGE',error)
        log('ARENA BRIDGE // '+type(error).__name__)
        return False
    State.bms_last_open=time.monotonic()
    log('ARENA UI REQUESTED // '+command+' / Check if BMS is installed and opens; no enemy spawn was requested.')
    return True

def open_bms_interface():
    # BMS UI is owned by BMS. We do not claim installed/backend detection.
    return _request_bms_console('bms_gui')

def show_bms_help():
    return _request_bms_console('bms_help')

def arena_safety_info():
    log('ARENA // Plan %d enemies, set the COUNT INSIDE BMS. Start with 1, stay solo, and let enemies despawn before increasing. CROWN cannot enforce BMS limits or cleanup.'%State.arena_planned_batch)
    return True

def _validate_tool_pins(values):
    """Only known tool-page IDs; never trust arbitrary persisted labels/commands.

    Duplicate, obsolete, malformed and oversized entries are discarded.
    """
    if not isinstance(values,list):return []
    good=[]
    for value in values[:24]:
        if isinstance(value,str) and value in _KNOWN_PAGES and value!='FINDER' and value not in good:
            good.append(value)
            if len(good)>=3:break
    return good

def toggle_tool_pin(page=None):
    """Pinned tools are UI navigation only; no gameplay action may run here."""
    page=page if page is not None else State.page
    if page not in _KNOWN_PAGES or page=='FINDER':
        log('QUICK PIN // Open a tool page first; Find remains permanently in the quick bar.')
        return False
    pins=_validate_tool_pins(State.tool_pins)
    if page in pins:
        pins.remove(page)
        message='REMOVED'
    else:
        pins=[page]+pins[:2]
        message='PINNED'
    State.tool_pins=pins
    save_preferences()
    log('COMMAND DECK // '+page+' '+message+' / '+str(len(pins))+' of 3 shortcut slots')
    if State.opened:redraw()
    return True

def open_quick_pin():
    pins=_validate_tool_pins(State.tool_pins)
    if not pins:
        # Default behaviour stays available until a user chooses a shortcut.
        return refill_skills()
    return show_page(pins[0])

def _quick_pin_caption():
    pins=_validate_tool_pins(State.tool_pins)
    if not pins:return 'REFILL ACTION SKILL'
    return 'PIN  /  '+DOCK_TOOL_LABELS.get(pins[0],pins[0])

def finder_results():
    phrase=' '.join(State.finder_query.lower().strip().split())
    choices=[]
    for cat, pages in UI_CATEGORY_PAGES.items():
        for page in pages:
            display=DOCK_TOOL_LABELS.get(page,page)
            indexed=' '.join((cat,page,display,FINDER_TERMS.get(page,''))).lower()
            if not phrase or all(term in indexed for term in phrase.split()):
                choices.append((page,cat,display))
    # Favourites rise to the top; visited pages follow, then all others.
    # Keep the same complete, searchable 21-page index.
    order=State.tool_pins+State.recent_tools
    rank={}
    for i,p in enumerate(order):
        if p in _KNOWN_PAGES and p not in rank:rank[p]=i
    choices.sort(key=lambda item:(rank.get(item[0],1000),item[1],item[2]))
    return choices

FINDER_PAGE_SIZE=6  # Six direct tool choices: four result pages rather than six.

def open_finder():
    State.finder_mode='BROWSE'
    State.finder_page=0
    show_page('FINDER')

def edit_finder_search():
    State.finder_draft=State.finder_query
    State.finder_input=None
    State.finder_mode='EDIT'
    if State.opened:redraw()

def finder_search_input(parent,x,y,w,h):
    try:
        field=widget('EditableTextBox')
        put(parent,field)
        size_position(field,x,y,w,h,19)
        if not attempt(field,'SetText',State.finder_draft):raise RuntimeError('Text field unavailable')
        call(field,'SetHintText','Find God Mode, Maurice, teleport, money...')
        call(field,'SetIsReadOnly',False)
        call(field,'SetVisibility',0)
        call(field,'SetIsEnabled',True)
        State.finder_input=field
        if not State.controller_mode:attempt(field,'SetKeyboardFocus')
        return True
    except Exception as exc:
        State.finder_input=None
        log('FINDER // Search input unavailable: '+type(exc).__name__)
        return False

def apply_finder_search():
    if State.finder_input is None:
        log('FINDER // Text input unavailable; browse all tools instead.')
        return False
    try:
        raw=str(State.finder_input.GetText())
    except Exception:
        log('FINDER // Cannot read the text field')
        return False
    State.finder_query=' '.join(raw.strip().lower().split())[:48]
    State.finder_page=0
    State.finder_mode='BROWSE'
    State.finder_input=None
    log('FINDER // '+str(len(finder_results()))+' tools match')
    if State.opened:redraw()
    return True

def cancel_finder_search():
    State.finder_mode='BROWSE'
    State.finder_input=None
    if State.opened:redraw()

def clear_finder_search():
    State.finder_query=''
    State.finder_draft=''
    State.finder_page=0
    State.finder_mode='BROWSE'
    State.finder_input=None
    if State.opened:redraw()

def finder_change_page(delta):
    pages=max(1,math.ceil(len(finder_results())/FINDER_PAGE_SIZE))
    State.finder_page=max(0,min(pages-1,State.finder_page+int(delta)))
    if State.opened:redraw()

def open_finder_result(page):
    if page not in _KNOWN_PAGES:return False
    State.finder_mode='BROWSE'
    show_page(page)
    return True

DOCK_TOOL_LABELS = {
    'COMMUNITY':'COMMUNITY MODS',
    'WEEKLY':'WEEKLY / MAURICE', 'PLAYER':'OVERVIEW', 'MOTION':'MOVEMENT','BOOSTS':'BOOST LAB', 'COMBAT':'COMBAT', 'PRESETS':'PRESETS',
    'WORLD':'WORLD SPEED', 'EVENTS':'EVENTS', 'PARTY':'CO-OP', 'ARENA':'ENEMY ARENA',
    'SPAWN':'ITEM FORGE', 'GEAR':'GEAR FILTERS', 'CONTENT':'API / DLC',
    'WAYPOINTS':'ROADRUNNER', 'LOOT':'CURRENCY', 'CAPACITY':'CAPACITY STUDIO', 'TROPHIES':'TROPHY JOURNAL',
    'STYLE':'APPEARANCE', 'DISPLAY':'DISPLAY', 'PROFILES':'PROFILES',
    'DEV':'RECOVERY', 'GUIDE':'SAFETY', 'FINDER':'FIND TOOLS'
}

def _visual_mode_label():
    """Truthful UI mode; importing files does not prove they rendered."""
    if State.safe_mode:
        return 'SAFE MODE / ART OFF'
    if State.art_mode=='SHAPES':
        return 'SHAPES / ART OFF'
    if State.art_drawn_count:
        return 'ART / WIDGETS '+str(State.art_drawn_count)
    return 'ART / AUTO'

def _dock_status_message():
    """Short useful status rather than a clipped, endlessly repeated welcome."""
    message=' '.join(str(State.message).split())
    if 'welcome' in message.lower() or message.startswith('READY //'):
        return 'READY / Choose a tool'
    for prefix in ('CROWNs Freedom // ', 'CROWN // ', 'STATUS // '):
        if message.startswith(prefix):message=message[len(prefix):]
    return _status_brief(message,31)

def _dock_quick_choices(page):
    """Existing tested handlers only; no speculative spawns, achievements or save edits."""
    if page=='PLAYER':
        return [('GOD MODE: '+('ON' if State.god else 'OFF'),lambda:set_god(),State.god),
                ('NOCLIP: '+('ON' if State.noclip else 'OFF'),lambda:set_noclip(),State.noclip),
                ('NO TARGET: '+('ON' if State.target_off else 'OFF'),toggle_no_target,State.target_off),
                ('FOV 100',lambda:change_fov(100),State.fov_selected==100),
                ('FOV 115',lambda:change_fov(115),State.fov_selected==115),
                ('FOV 130',lambda:change_fov(130),State.fov_selected==130),
                ('RESET FOV',reset_fov,False)]
    if page=='BOOSTS':
        return [('SPRINT x1.55',lambda:apply_movement_boost('SPRINT'),State.boost_preset=='SPRINT'),
                ('ROCKET x2.25',lambda:apply_movement_boost('ROCKET'),State.boost_preset=='ROCKET'),
                ('HIGH JUMP',lambda:apply_movement_boost('HIGH JUMP'),State.boost_preset=='HIGH JUMP'),
                ('RESET BOOSTS',reset_movement_boost,False),
                ('XP LAB',lambda:r3_open_tool('LOOT','XP'),False),
                ('FARM BUFF / DRAFT',lambda:stage_combat_booster('GENTLE FARM'),False)]
    if page=='MOTION':
        return [('SPEED x1.5',lambda:tune_speed(1.5),abs(State.motion_scale-1.5)<.01),
                ('SPEED x2.0',lambda:tune_speed(2.0),abs(State.motion_scale-2)<.01),
                ('SPRINT x3.0',lambda:tune_speed(3.0),abs(State.motion_scale-3)<.01),
                ('JUMP x1.5',lambda:tune_jump(1.5),State.jump_selected==1.5),
                ('JUMP x2.0',lambda:tune_jump(2.0),State.jump_selected==2),
                ('RESTORE MOVEMENT',restore_motion,False)]
    if page=='COMBAT':
        # Keep destructive, unverified requests behind full-size explanations.
        return [('REFILL ACTION SKILL',refill_skills,False),
                ('RESTORE TEMP CHANGES',restore,False),
                ('CLEAR ENEMIES / FULL',toggle_dock_mode,False),
                ('AMMO TOOLS / FULL',toggle_dock_mode,False)]
    if page=='PRESETS':
        return [('VAULT VACATION',preset_vacation,False),
                ('WALKING APOCALYPSE',preset_mayhem,False),
                ('RESTORE NORMAL',preset_normal,False)]
    if page=='WEEKLY':
        snap=_weekly_snapshot()
        if snap is None:return [('ROTATION EXPIRED / ECHO',weekly_summary,False),('OPEN ROADRUNNER',lambda:show_page('WAYPOINTS'),False)]
        return [('MAURICE / '+snap['maurice_region'][:16],weekly_summary,False),
                ('SAVE VENDOR HERE / SLOT04',weekly_save_vendor,False),
                ('GO SAVED VENDOR / SLOT04',weekly_go_vendor,False),
                ('WILDCARD & BOSS',weekly_summary,False),
                ('OPEN ROADRUNNER',lambda:show_page('WAYPOINTS'),False)]
    if page=='WORLD':
        return [('TIME x0.5',lambda:set_world_time(.5),abs(State.speed-.5)<.01),
                ('TIME x1.0',lambda:set_world_time(1),abs(State.speed-1)<.01),
                ('TIME x2.0',lambda:set_world_time(2),abs(State.speed-2)<.01),
                ('TIME x4.0',lambda:set_world_time(4),abs(State.speed-4)<.01),
                ('TRAVEL HUB',lambda:show_page('WAYPOINTS'),False),
                ('RETURN / SWAP',bookmark_back,False)]
    if page=='WAYPOINTS':
        choices=[('SLOT %02d / %s'%(i, 'SAVED' if i in State.checkpoints else 'EMPTY'),
                  lambda n=i:bookmark_go(n),False) for i in range(1,5)]
        return choices+[('ALL 12 SLOTS',toggle_dock_mode,False)]
    if page=='ARENA':
        return [('OPEN BMS SPAWNER',open_bms_interface,False),
                ('CHECK BACKEND FILES',arena_backend_check,False),
                ('SCOUT / PLAN 1',lambda:arena_set_planned_batch(1),State.arena_planned_batch==1),
                ('SMALL FIGHT / PLAN 3',lambda:arena_set_planned_batch(3),State.arena_planned_batch==3),
                ('FULL ARENA / LIMITS',toggle_dock_mode,False)]
    if page=='FINDER':
        return [('SEARCH BY NAME',edit_finder_search,False),('SHOW ALL TOOLS',clear_finder_search,False)]
    if page=='CONTENT':
        return [('DLC / API INDEX',toggle_dock_mode,False),('FORGE PREFLIGHT',forge_preflight,False)]
    if page=='SPAWN':
        return [('PISTOLS',lambda:forge_search_preset('PISTOL'),_spawn_category()=='PISTOL'),
                ('SHOTGUNS',lambda:forge_search_preset('SHOTGUN'),_spawn_category()=='SHOTGUN'),
                ('FULL ITEM FORGE',toggle_dock_mode,False)]
    if page=='GEAR':
        return [('PISTOLS',lambda:gear_jump('PISTOL'),False),
                ('SHOTGUNS',lambda:gear_jump('SHOTGUN'),False),
                ('RIFLES',lambda:gear_jump('RIFLE'),False),
                ('SMGS',lambda:gear_jump('SMG'),False),
                ('FULL GEAR FILTERS',toggle_dock_mode,False)]
    if page=='STYLE':
        return [('ECHO NEON',lambda:set_theme(0),State.theme_idx==0),
                ('CURSOR AID: '+('ON' if State.cursor_aid else 'OFF'),toggle_cursor_aid,State.cursor_aid),
                ('RESUME CUSTOM ART' if State.safe_mode else 'SAFE MODE: OFF',resume_custom_art if State.safe_mode else toggle_safe_mode,State.safe_mode),
                ('COMFORT PRESET',apply_comfort_preset,False),
                ('POPUPS: '+('ON' if State.toasts_enabled else 'OFF'),toggle_toasts,State.toasts_enabled),
                ('TEST POPUP',test_toast,False),
                ('CHECK ART',art_preflight,False),
                ('STYLE / AUDIO',toggle_dock_mode,False)]
    if page=='DISPLAY':
        return [('SIZE 100%',lambda:set_scale_preset(1),False),
                ('SIZE 125%',lambda:set_scale_preset(1.25),False),
                ('SIZE 150%',lambda:set_scale_preset(1.5),False),
                ('HUD POSITION: '+State.hud_anchor.replace('_',' '),cycle_hud_position,False),
                ('ALL DISPLAY SETTINGS',toggle_dock_mode,False)]
    if page=='TROPHIES':
        return [('JOURNAL %d/63 CHECKED'%len(State.trophy_marked),toggle_dock_mode,False),
                ('READ / MARK IN FULL',toggle_dock_mode,False)]
    if page=='DEV':
        return [('RECOVER INPUT',recover_ui_focus,False),
                ('EXPORT DIAGNOSTICS',export_qa_report,False),
                ('RESUME CUSTOM ART' if State.safe_mode else 'SAFE MODE: OFF',resume_custom_art if State.safe_mode else toggle_safe_mode,State.safe_mode),
                ('HUD POSITION: '+State.hud_anchor.replace('_',' '),cycle_hud_position,False),
                ('FULL RECOVERY',toggle_dock_mode,False)]
    if page=='EVENTS':
        return [('STOP CURRENT EVENT',lambda:stop_event(),False),
                ('EVENTS / FULL',toggle_dock_mode,False)]
    if page=='LOOT':
        return [('BACKUP SAVE REMINDER',backup_notice,False),
                ('CURRENCY MENU',toggle_dock_mode,False)]
    return [('OPEN '+DOCK_TOOL_LABELS.get(page,page)+' / FULL',toggle_dock_mode,False)]

def _draw_side_dock(layout,vw,vh,actual_w,actual_h,build_start):
    width=min(vw-20.,max(360.,State.dock_width))
    height=min(vh-20.,420. if State.dock_compact and State.dock_view=='QUICK' else 610.)
    x=max(10.,vw-width-12.) if State.dock_right else 12.
    y=10.+max(0.,vh-height-20.)*State.dock_vertical
    State.panel_rect=(x,y,width,height,vw,vh)
    State._layout_dpi=_dpi_scale(get_pc(possibly_loading=True))
    State.r3_context_rect=None
    box(layout,x+5,y+7,width,height,(0.,0.,0.,.24),1)
    box(layout,x,y,width,height,theme_color('bg')[:3]+(State.dock_opacity,),2)
    optional_art_image(layout,'R9_DOCK',x,y,width,height,z=3,opacity=.85)
    box(layout,x+2,y+2,3,height-4,theme_color('highlight')[:3]+(.64,),4)
    optional_art_image(layout,'R3_HOLO',x+9,y+8,width-18,65,z=4,opacity=.18)
    crown_emblem(layout,x+18,y+18,34)
    text(layout,'CROWN / FIELD DOCK',x+62,y+16,width-132,28,theme_color('text'),.88,8)
    if State.controller_mode and State.r10_device not in ('KEYBOARD','MOUSE') and State.controller_enabled:r3_controller_strip(layout,x+62,y+45,width-130)
    else:text(layout,r12_input_prompt(),x+62,y+46,width-132,21,theme_color('accent'),.61,8)
    btn(layout,'X',x+width-55,y+20,36,36,close_menu,danger=True,small=True)
    third=(width-40)/3
    tab_width=(width-46)/4
    for i,label in enumerate(('QUICK','TOOLS','FARM','STYLE')):
        btn(layout,label,x+14+i*(tab_width+6),y+79,tab_width,34,lambda v=label:dock_view(v),active=State.dock_view==label,small=True)
    half=(width-38)/2
    if State.numeric_editor is not None:
        draw_numeric_editor(layout,x+14,y+126,width-28,45,None,None)
    elif State.dock_view=='QUICK':
        actions=_dock_actions_r3()
        if height>=500:
            optional_art_image(layout,'R9_FLIGHT',x+14,y+431,width-28,65,z=4,opacity=.68)
        for i,key in enumerate(_dock_favorites_valid(State.dock_favorites)):
            label,fn=actions[key]
            btn(layout,label,x+14+(i%2)*(half+10),y+130+(i//2)*51,half,45,fn,small=True,active=key=='GOD' and State.god)
        if height>=500:
            text(layout,'FAVOURITE TOOLS',x+18,y+295,width-36,24,theme_color('highlight'),.69)
            for i,page in enumerate(_validate_tool_pins(State.tool_pins)):
                btn(layout,DOCK_TOOL_LABELS.get(page,page),x+14,y+329+i*35,width-28,29,lambda p=page:r3_open_tool(p),small=True)
            if not State.tool_pins:
                text(layout,'Pin tools from the main studio. Customise quick actions in TOOLS.',x+18,y+331,width-36,54,theme_color('dim'),.69)
        else:text(layout,'TOOLS / customise your six quick actions' if State.dock_favorites else 'No quick actions pinned. Add them in TOOLS.',x+18,y+286,width-36,23,theme_color('dim'),.62)
    elif State.dock_view=='FARM':
        draw_farm_workspace(layout,x+14,y+128,width-28,True)
    elif State.dock_view=='TOOLS':
        choices=(('PLAYER',lambda:r3_open_tool('PLAYER')),('COMBAT',lambda:r3_open_tool('COMBAT','SANDBOX')),
          ('FORGE',lambda:r3_open_tool('SPAWN')),('INVENTORY',lambda:r3_open_tool('CAPACITY')),
          ('ENCOUNTERS',lambda:r3_open_tool('ARENA')),('PROGRESSION',studio_open),
          ('TRAVEL',lambda:r3_open_tool('WAYPOINTS')),('ALL TOOLS',lambda:r3_open_tool('FINDER')))
        for i,(label,fn) in enumerate(choices):btn(layout,label,x+14+(i%2)*(half+10),y+129+(i//2)*44,half,36,fn,small=True,icon=r10_heading_icon(('PLAYER','COMBAT','SPAWN','CAPACITY','ARENA','LOOT','WAYPOINTS','FINDER')[i]))
        keys=tuple(_dock_actions_r3());key=keys[State.dock_pick%len(keys)]
        text(layout,'QUICK SLOT / '+_dock_actions_r3()[key][0],x+18,y+325,width-36,29,theme_color('accent'),.69)
        for i,(label,fn) in enumerate((('PREV',lambda:(setattr(State,'dock_pick',(State.dock_pick-1)%len(keys)),redraw())),
          ('UNPIN' if key in State.dock_favorites else 'PIN',dock_pin_action),('NEXT',lambda:(setattr(State,'dock_pick',(State.dock_pick+1)%len(keys)),redraw())))):
            btn(layout,label,x+14+i*(third+6),y+365,third,34,fn,small=True)
        text(layout,'Pinned actions fill QUICK, up to six. Tool buttons open the full studio.',x+18,y+416,width-36,48,theme_color('dim'),.66)
        btn(layout,'MY RECIPES',x+14,y+470,width-28,32,recipe_open,small=True)
    else:
        slider(layout,'DOCK WIDTH',State.dock_width,360,560,x+14,y+130,width-28,lambda v:dock_stage('width',v))
        slider(layout,'DOCK OPACITY',State.dock_opacity,.3,.95,x+14,y+208,width-28,lambda v:dock_stage('opacity',v))
        slider(layout,'VERTICAL POSITION',State.dock_vertical,0,1,x+14,y+286,width-28,lambda v:dock_stage('vertical',v))
        btn(layout,'COMPACT: '+('ON' if State.dock_compact else 'OFF'),x+14,y+377,half,35,lambda:(setattr(State,'dock_compact',not State.dock_compact),save_preferences(),redraw()),small=True)
        btn(layout,'MOVE '+('LEFT' if State.dock_right else 'RIGHT'),x+24+half,y+377,half,35,toggle_dock_side,small=True)
    bottom=y+height-98
    box(layout,x+14,bottom,width-28,1,theme_color('highlight')[:3]+(.4,),5)
    State.status_widget=text(layout,_dock_status_message(),x+18,bottom+8,width-36,27,theme_color('dim'),.65,8)
    btn(layout,'FULL STUDIO',x+14,bottom+43,half,36,toggle_dock_mode,small=True)
    btn(layout,'CLOSE / B',x+24+half,bottom+43,half,36,close_menu,small=True)



def _restore_focus_index(old_name, old_rect):
    # Named actions may occur in the main pane AND quick bar. After a redraw,
    # favour the previous physical position rather than jumping to the first
    # unrelated button with the same words (dangerous on gamepads).
    candidates=[(i,b) for i,b in enumerate(State.buttons)
                if b['name']==old_name and not b['disabled'] and b.get('rect')]
    if not candidates:
        return _controller_initial_focus()
    if old_rect is None:
        return candidates[0][0]
    ox=old_rect[0]+old_rect[2]*.5
    oy=old_rect[1]+old_rect[3]*.5
    return min(candidates,key=lambda pair:
        (pair[1]['rect'][0]+pair[1]['rect'][2]*.5-ox)**2+
        (pair[1]['rect'][1]+pair[1]['rect'][3]*.5-oy)**2)[0]


def _finish_frame(layout,actual_w,actual_h,build_start,old_focus_name,old_focus_rect):
    if State.controller_mode:
        State.controller_focus=_restore_focus_index(old_focus_name,old_focus_rect)
    State.controller_focus_outline=[box(layout,-40,-40,1,1,theme_color('highlight'),20)
                                    for _ in range(4)]
    State.mouse_hover_frame=[box(layout,-50,-50,1,1,theme_color('accent'),21)
                             for _ in range(4)]
    _controller_update_focus_outline()
    create_mouse_cursor_aid(layout)
    State.draw_ok=True
    State.viewport_signature=(round(actual_w,1),round(actual_h,1))
    State.ui_last_ms=(time.perf_counter()-build_start)*1000.0
    State.ui_peak_ms=max(State.ui_peak_ms,State.ui_last_ms)
    State.ui_rebuild_count+=1
    _set_native_phase('REDRAW_READY')
    # Native widget rebuilds replace the old focus target. Request new UMG
    # focus only for active gamepad navigation, never while typing or mousing.
    editor_open=r10_editor_active()
    if State.controller_mode and not editor_open and State.root is not None:
        pc=get_pc(possibly_loading=True)
        if pc is not None:attempt(State.root,'SetUserFocus',pc)


def _commit_canvas_frame(candidate,old_frame,virtual_width,virtual_height):
    """Stage and validate the *new* UMG canvas before retiring the old one.

    Native AddChild can fail after partially mounting a UObject; cleanup owns
    that candidate in all failure paths. A missing/unusable CanvasPanelSlot
    must never leave a zero-sized live interface holding UIOnly input.
    """
    _set_native_phase('FRAME_COMMIT')
    parent=State.tree.RootWidget
    attach=getattr(parent,'AddChild',None)
    if not callable(attach):
        raise RuntimeError('UMG parent does not expose AddChild')
    attached=False
    try:
        # AddChild creates the slot. It is not available on a detached widget.
        result=attach(candidate)
        attached=True  # even a refusal could have created a partial child
        if result is False:
            raise RuntimeError('UMG parent explicitly rejected frame')
        slot=(result if callable(getattr(result,'SetSize',None)) else None)
        if slot is None:
            slot=getattr(candidate,'slot',None)
        if slot is None:
            slot=getattr(candidate,'Slot',None)
        if slot is None:
            raise RuntimeError('New UMG canvas has no valid panel slot')
        _set_native_phase('FRAME_SIZE')
        for operation,args in (
                ('SetPosition',(v2(0,0),)),
                ('SetSize',(v2(virtual_width,virtual_height),)),
                ('SetAutoSize',(False,)),
                ('SetZOrder',(0,))):
            func=getattr(slot,operation,None)
            if not callable(func) or func(*args) is False:
                raise RuntimeError('UMG frame layout refused '+operation)
        _set_native_phase('FRAME_RETIRE')
        if old_frame is not None and old_frame is not candidate:
            detach=getattr(old_frame,'RemoveFromParent',None)
            if not callable(detach) or detach() is False:
                raise RuntimeError('UMG old frame detach refused')
        State.canvas=candidate
        State.transition_canvas=candidate
        State.transition_started=time.monotonic()
        if not State.reduced_motion:call(candidate,'SetRenderOpacity',.82)
    except Exception:
        if attached:
            try:attempt(candidate,'RemoveFromParent')
            except Exception:pass
        raise

def _redraw_impl():
    if not State.opened:
        return
    build_start=time.perf_counter()
    State.draw_ok=False
    old_frame=State.canvas
    candidate=None
    _set_native_phase('REDRAW_BEGIN')
    try:
        # Capture live editing *before* detaching widgets. On several Unreal
        # versions an unparented editor's GetText no longer returns its draft.
        _capture_editor_drafts()
        if State.numeric_editor is not None and State.numeric_widget is not None:
            try:State.numeric_editor['text']=str(State.numeric_widget.GetText())[:40]
            except Exception:pass
        # Stage a detached frame first; do not destroy the currently visible
        # canvas before construction succeeds. The old frame remains interactive
        # only until the atomic commit below, on the same game callback.
        _set_native_phase('FRAME_STAGE')
        old_focus_name=(State.buttons[State.controller_focus]['name']
            if State.controller_mode and 0<=State.controller_focus<len(State.buttons) else None)
        old_focus_rect=(State.buttons[State.controller_focus].get('rect')
            if State.controller_mode and 0<=State.controller_focus<len(State.buttons) else None)
        State.frame_generation+=1
        State.r10_bonus_widget=None;State.r10_bonus_generation=-1
        State.palette_bindings=[]
        State.appearance_preview={}
        State.numeric_widget=None
        State.encounter_input=None
        State.profile_name_widget=None
        State.buttons=[]
        State.sliders=[]
        State.controller_focus_outline=[]
        State.search_widget=None
        State.level_widget=None
        State.status_widget=State.status_marker=State.status_label=None
        State.art_drawn_count=0
        State.art_imports_this_frame=0
        State.art_ambient_imports_this_frame=0
        State.art_deferred.clear()
        _set_native_phase('FRAME_ATTACH')
        layout=widget("CanvasPanel")
        candidate=layout
        actual_w,actual_h=viewport()
        # Virtual canvas scaling keeps compact layouts inside 720p and smaller.
        scale=min(1.0,actual_w/1280.0,actual_h/720.0)
        scale=max(0.25,scale)
        State.render_scale=scale
        w,h=actual_w/scale,actual_h/scale
        # The parent layout slot does not exist yet. _commit_canvas_frame()
        # positions the root only after AddChild creates its UMG slot.
        if not attempt(layout,"SetRenderTransformPivot",v2(0.0,0.0)):
            log("UI transform pivot unsupported; compact scaling may differ.")
        if not attempt(layout,"SetRenderScale",v2(scale,scale)):
            raise RuntimeError("Native UMG render scaling unavailable")
        if State.dock_mode=='SIDE':
            _draw_side_dock(layout,w,h,actual_w,actual_h,build_start)
            _commit_canvas_frame(layout,old_frame,w,h)
            _finish_frame(layout,actual_w,actual_h,build_start,old_focus_name,old_focus_rect)
            return

        w_scale=State.panel_scale
        # A slider can shrink the *window*, not the minimum layout needed by
        # six navigation rows, four action rows and the fixed quick bar. The
        # old 72% preset made a ~440px-high window and overlapped live buttons.
        width=min(w-28.0,max(870.0,min(1880.0,max(750.0,w*.77)*w_scale)))
        height=min(h-26.0,max(680.0,min(1140.0,max(645.0,h*.78)*w_scale)))
        x=max(8.0,min(w-width-8.0, float(State.window_x) if State.window_x is not None else (w-width)/2.0))
        y=max(8.0,min(h-height-8.0, float(State.window_y) if State.window_y is not None else (h-height)/2.0))
        State.panel_rect=(x,y,width,height,w,h)
        State._layout_dpi=_dpi_scale(get_pc(possibly_loading=True))
        sidebar=min(290.0,max(224.0,width*.18))
        left=x+sidebar+18.0
        main_width=width-sidebar-43.0
        row_width=(main_width-12.0)/2.0

        # COMMAND CENTRE: original glass rail, large brand and contextual tabs.
        # All decorative widgets ignore hit tests; native controls own input.
        box(layout,x+8,y+10,width,height, (0,0,0,.32),0)
        box(layout,x,y,width,height,theme_color('bg'),1)
        box(layout,x+2,y+2,width-4,height-4,theme_color('panel'),2)
        box(layout,x,y,4,height,theme_color('highlight'),5)
        box(layout,x+4,y,width-8,2,theme_color('border'),5)
        box(layout,x+4,y+height-2,width-8,2,theme_color('border'),5)
        box(layout,x+10,y+10,width-20,112,theme_color('header'),3)
        optional_art_image(layout,'R9_EXPEDITION',x+12,y+12,width-24,108,z=4,opacity=.96)
        optional_art_image(layout,'R3_HOLO',x+width-465,y+14,430,99,z=4,opacity=.15)
        optional_art_image(layout,'NEON_CIRCUITS',x+width-465,y+14,430,99,z=4,opacity=.20)
        crown_emblem(layout,x+26,y+27,56)
        if not optional_art_image(layout,'NEON_WORDMARK_COMPACT',x+101,y+20,min(500,width-735),56,z=6,opacity=1):
            text(layout,"CROWN'S FREEDOM",x+102,y+23,width-650,41,theme_color('text'),1.25,6)
        text(layout,'FIELDCRAFT R16 / '+RELEASE_VERSION,x+103,y+78,width-700,26,theme_color('highlight'),.77,6)
        btn(layout,'PLAYER LAB',x+width-575,y+80,125,23,studio_open,small=True)
        btn(layout,'MY RECIPES',x+width-575,y+28,125,42,lambda:recipe_open(current_recipe_kind()),small=True)
        btn(layout,'RESTORE ART' if State.safe_mode else 'SAFE UI',x+width-435,y+28,120,42,toggle_safe_mode,active=State.safe_mode,small=True)
        btn(layout,'QUICK DOCK',x+width-300,y+28,128,42,toggle_dock_mode,small=True)
        btn(layout,'CLOSE',x+width-155,y+28,125,42,close_menu,danger=True,small=True)
        chip(layout,r10_save_tag()[0],x+width-435,y+80,125,23,danger=r10_save_tag()[1])
        text(layout,session_role()+'  /  '+_visual_mode_label(),x+width-302,y+80,272,23,theme_color('dim'),.65,6)
        box(layout,x+18,y+126,width-36,1,theme_color('border'),5)
        State.echo_scan=None
        if not State.safe_mode and not State.reduced_motion:
            State.echo_scan=box(layout,x+width-58,y+145,25,2,theme_color('highlight')[:3]+(.5,),7)
            State.echo_scan_generation=State.frame_generation
        box(layout,x+12,y+136,sidebar-6,height-296,theme_color('bg'),3)
        optional_art_image(layout,'NEON_SIDEPANEL',x+12,y+136,sidebar-6,height-296,z=4,opacity=.26)
        rail_top,rail_pitch,rail_height=studio_rail_geometry(y,height)
        group_name=studio_section_for(State.page)
        for idx,name in enumerate(STUDIO_SECTIONS):
            btn(layout,name.upper(),x+24,rail_top+idx*rail_pitch,sidebar-29,rail_height,
                lambda n=name:studio_open_section(n),active=(name==group_name),small=True)
        # A single horizontal tool strip removes nested category navigation.
        pages=STUDIO_SECTIONS[group_name]
        if len(pages)>1:
            tw=min(210,(main_width-145-10*(len(pages)-1))/len(pages))
            for idx,page in enumerate(pages):
                label={'MOTION':'MOVEMENT','PRESETS':'LOADOUTS','GEAR':'CATALOGUE','WEEKLY':'WEEKLY','TROPHIES':'JOURNAL','CONTENT':'API STATUS','DEV':'RECOVERY'}.get(page,page)
                btn(layout,label,left+idx*(tw+10),y+132,tw,27,lambda p=page:show_page(p),active=State.page==page,small=True)
        else:
            text(layout,'CROWN  /  '+group_name.upper(),left,y+133,main_width-100,23,theme_color('dim'),.69,6)
        box(layout,left-6,y+216,main_width+14,max(130,height-384),theme_color('bg')[:3]+(.08,),3)
        optional_art_image(layout,'ECHO_CONTENT_GLASS',left-6,y+216,main_width+14,max(130,height-384),z=4,opacity=.22)
        optional_art_image(layout,('R9_FORGE' if State.page in ('SPAWN','GEAR','CAPACITY') else 'R9_ARENA' if State.page in ('ARENA','COMBAT','PARTY','EVENTS') else 'R9_FLIGHT' if State.page in ('MOTION','BOOSTS','WAYPOINTS','WORLD') else 'R9_EXPEDITION'),left+main_width*.57,y+216,main_width*.43,max(130,height-384),z=4,opacity=.12)
        page_desc={
            "DASHBOARD":"FIELD DECK / QUICK PLAY",
            "PLAYER":"VAULT HUNTER CONTROLS",
            "MOTION":"MOVEMENT, SPEED & GRAVITY",
            "BOOSTS":"BOOST & FLIGHT LAB / SESSION-ONLY",
            "COMMUNITY":"COMMUNITY TOOL BRIDGES / SOLO",
            "COMBAT":"QUICK COMBAT TOOLS",
            "LOOT":"CURRENCY & PROGRESSION",
            "CAPACITY":"CAPACITY STUDIO / LIVE MOD BRIDGE",
            "WORLD":"TIME CONTROL & BOOKMARKS",
            "WEEKLY":"ROTATING MAURICE & WEEKLY REWARDS",
            "PARTY":"CO-OP FRIEND TOOLS",
            "CONTENT":"BUILD, COMPATIBILITY & DLC",
            "PRESETS":"ONE-TAP LOADOUTS",
            "STYLE":"APPEARANCE STUDIO",
            "DEV":"RECOVERY & DEBUG",
            "SPAWN":"FORGE WORKBENCH",
            "EVENTS":"CUSTOM SANDBOX CHALLENGES",
            "TROPHIES":"ACHIEVEMENT JOURNAL",
            "WAYPOINTS":"12-SLOT ROADRUNNER TRAVEL HUB",
            "PROFILES":"CUSTOM MENU PRESETS",
            "GEAR":"GEAR QUICK FILTERS",
            "DISPLAY":"EXPANDED MENU & FONTS",
            "GUIDE":"SAVE & MOD SAFETY",
            "FINDER":"FIND ANY TOOL / QUICK SEARCH",
            "ARENA":"ENCOUNTER DIRECTOR",
        }
        page_tip={
            "DASHBOARD":("Direct play tools and essential workspaces in one place.","Actions marked REQUEST may not be confirmed by BL4. Back up your save."),
            "PLAYER":("EARL // Toggle temporary player cheats.","MARCUS // Most of this is session-only and may reset on travel."),
            "COMMUNITY":("OPTIONAL // XP, Arena & Bonk utilities.","Separate mods, solo only; level, item and currency actions can persist in your saved character. Commands are NOT proof of a result."),
            "BOOSTS":("BOOST LAB // Flight sprint and temporary movement presets.","Hold F5 only in NOCLIP to fly at x2.45. Release to restore. XP, perk points and character levels require separate verified backends."),
            "MOTION":("EARL // Make movement stupid fast or weird.","MARCUS // The game can overwrite movement after map changes."),
            "COMBAT":("EARL // Fast combat buttons. Minimal reading, maximum chaos.","MARCUS // Kill and ammo tools can be irreversible or unverified."),
            "CAPACITY":("STUDIO // Adjust backpack or bank slots safely.","Requires separately installed, running BL4Live; solo-only, two-click Apply and backend readback. PAK overrides can conflict."),
            "LOOT":("EARL // Cash and Eridium requests live here.","MARCUS // Currency can persist in your save. Back it up first."),
            "WORLD":("EARL // Time control and bookmark teleports.","MARCUS // Host, map and travel rules still apply."),
            "PARTY":("EARL // Friend tools need consent and a stable party.","MARCUS // Remote edits depend on host authority."),
            "SPAWN":("EARL // Browse, search and prep an item safely.","MARCUS // Spawning needs a second click. Check the ground after confirming."),
            "WEEKLY":("WEEKLY // Verified October 8-15, 2026 bulletin.","ROTATIONS EXPIRE. Save VENDOR slot 04 only when physically beside Maurice; travel requires same map and an in-date player bookmark."),
            "EVENTS":("EARL // Challenge presets for messing about in solo.","MARCUS // These are temporary sandbox presets, not official events."),
            "CONTENT":("EARL // See what the game session exposes right now.","MARCUS // Read-only checks only. No DLC unlocking magic."),
            "PRESETS":("EARL // One tap moods if you can’t be bothered.","MARCUS // Presets avoid touching money or permanent rewards."),
            "STYLE":("EARL // A little less blue, a little more bite.","MARCUS // Theme, size, popups and opacity save locally."),
            "DEV":("EARL // Recovery buttons and debug checks live here.","MARCUS // F6 closes the menu. F10 attempts a full restore."),
            "TROPHIES":("JOURNAL // Track all 63 Steam achievements.","READ ONLY // Never modifies or blocks Steam achievements."),
            "WAYPOINTS":("ROADRUNNER // 12 persistent travel bookmarks.","F8 opens this hub; occupied slots need two presses to overwrite."),
            "PROFILES":("STYLE // Three quick UI and Forge presets.","Profiles never load or edit character saves."),
            "GEAR":("FORGE // Jump to a weapon class.","Uses the published 68-pool catalogue; no invented pool tokens."),
            "DISPLAY":("XXL // Enlarge the whole menu.","L3+R3 opens/closes after a hold; F7 keyboard, F9 input recovery. Gamepad may still interfere with gameplay in certain BL4 states."),
            "GUIDE":("SAFETY // What CROWN can and cannot do.","No achievements, saves or unlock flags are silently edited."),
            "FINDER":("SEARCH // Find controls across every category.","Search never changes gameplay. Controller-friendly categories and a full alphabetical list are available."),
            "ARENA":("DIRECTOR // Stage a source-listed enemy or boss. Solo only.","Optional reviewed BMS + Oak Spawner + world tools required. Requests are queued, then checked for tracked actors. Passive spawn; levels and waves unavailable."),
        }
        heading_width=main_width-(308 if State.page=='STYLE' and not State.help_open else 135)
        title_line=('PLAYER LAB / '+State.r10_view if State.r10_view is not None and State.page=='LOOT' else 'MY RECIPES / '+State.recipe_kind if State.page=='PROFILES' and State.recipe_open else 'FARMING / RUN TELEMETRY' if State.page=='PROFILES' and State.farm_view else 'PROGRESSION LAB / EARNED XP' if State.page=='LOOT' and State.xp_view else 'GAMEPLAY SANDBOX / PRECISE TUNING' if State.page=='COMBAT' and State.sandbox_view else 'OWNED WEAPON LAB' if State.page=='GEAR' and State.weapon_view else page_desc[State.page])
        # Use a deliberate compact title instead of a clipped half-sentence.
        if heading_width < 610 and len(title_line)>36:
            title_line=page_desc[State.page]
        optional_art_image(layout,r10_heading_icon(State.page),left,y+167,27,27,z=6,opacity=.9)
        text(layout,title_line,left+38,y+166,heading_width-38,33,theme_color("accent"),1.08)
        btn(layout,"HIDE HELP" if State.help_open else "? HELP",left+main_width-96,y+166,96,28,toggle_page_help,small=True)
        if State.page=='STYLE' and not State.help_open:
            btn(layout,'PAD: PS' if State.gamepad_icons=='PLAYSTATION' else 'PAD: XB',
                left+main_width-300,y+166,94,28,cycle_gamepad_icons,small=True)
            btn(layout,'< BACK' if State.style_audio_open else 'AUDIO',
                left+main_width-198,y+166,94,28,toggle_style_audio,small=True)
        if State.page=='SPAWN':
            item=_forge_selection()
            if item is not None:
                # Show the actual candidate before entering the workbench,
                # without implying stats or successful drops were verified.
                page_tip['SPAWN']=('CANDIDATE / '+item[0][:36]+'   /   LV'+str(State.spawn_level)+
                    ' x'+str(State.spawn_count),page_tip['SPAWN'][1])
        # Page explanations live in Help/context cards; keep title baseline clear.
        if State.page=='SPAWN':
            label=('READY / NO DROP' if State.forge_stage=='READY_NOT_SPAWNED'
                   else 'REQUEST ONLY / UNVERIFIED' if State.forge_stage=='REQUEST_SENT_NOT_VERIFIED'
                   else 'CHECK BACKEND FIRST')
            text(layout,label,left,y+height-204,main_width-22,22,
                 theme_color('highlight') if State.forge_stage=='READY_NOT_SPAWNED'
                 else theme_color('accent'),.65,7)
        btn(layout,'UNPIN TOOL' if State.page in State.tool_pins else 'PIN TOOL',
            left+main_width-118,y+132,118,27,toggle_tool_pin,
            active=State.page in State.tool_pins,small=True,disabled=State.page=='FINDER')
        box(layout,left,y+206,main_width,2,theme_color("border"),5)
        box(layout,left,y+208,main_width*.18,2,theme_color("accent"),6)
        # Actual workbench body, with a continuous dark surface beneath all
        # tools, large click targets and a contrasting bottom telemetry card.
        box(layout,left-10,y+215,main_width+14,max(130.0,height-384.0),theme_color('muted')[:3]+(.06,),4)
        box(layout,left-8,y+217,main_width+10,3,theme_color('highlight')[:3]+(.35,),5)
        box(layout,left-5,y+height-171,main_width+4,2,theme_color('border'),5)
        box(layout,left-10,y+216,3,max(130.0,height-384.0),theme_color('accent'),5)
        # Original game-inspired blueprint grid: sparse lines in unused space,
        # below every button and text. Cheap native UMG borders; no 3D models.
        if height>=770:
            for gridline in range(3):
                gy=y+330+gridline*105
                if gy<y+height-196:
                    box(layout,left+8,gy,main_width-16,1,theme_color('border')[:3]+(.12,),4)
            for mark in range(5):
                box(layout,left+main_width-94+mark*15,y+216,8,3,theme_color('accent')[:3]+(.40,),5)

        State.r3_context_rect=None
        if (main_width>=1100 and height>=820 and State.page in ('PLAYER','MOTION','COMBAT','LOOT','ARENA','WORLD','CAPACITY','GEAR')
                and not State.help_open and State.numeric_editor is None):
            full_width=main_width
            main_width=max(680.,full_width*.62)
            State.r3_context_rect=(left+main_width+22,y+224,full_width-main_width-22,height-401)
            row_width=(main_width-12.)/2.
        row_y=y+224
        btn_height=43.0 if State.compact or height<650 else 51.0
        if State.page=='SPAWN' and State.spawn_view in ('TOOLS','BROWSE','INSPECT'):
            btn_height=min(btn_height,43.0)
        max_step=max(44.0,(height-376.0-btn_height)/3.0)
        step=min(61.0 if State.compact else 69.0,max_step)
        if State.page in ("PROFILES","DISPLAY"):
            step=min(step,max(43.,(height-370.-btn_height)/4))
        if State.page=='SPAWN' and not State.help_open and State.spawn_view in ('TOOLS','BROWSE'):
            step=min(step,max(47.0,(height-392.0-btn_height)/5.0))
        last_action_bottom=[row_y]
        last_note_bottom=[row_y]
        def action(label,fn,index,active=False,danger=False,disabled=False):
            xx=left+(index%2)*(row_width+12.0)
            yy=row_y+(index//2)*step
            btn(layout,label,xx,yy,row_width,btn_height,fn,active=active,danger=danger,disabled=disabled)
            last_action_bottom[0]=max(last_action_bottom[0],yy+btn_height)
        def info(label,offset=302):
            # Actual screenshots proved estimates could overlap the 3rd/4th row.
            # Never draw instructional panels across controls; HELP is always there.
            base=max(row_y+offset,last_action_bottom[0]+12,last_note_bottom[0]+12,
                     max((r.track[1]+18 for r in State.sliders if r.track),default=row_y))
            cap=y+height-156.0
            available=cap-base
            if available<64:return
            h_note=min(86.0,available)
            note_panel(layout,'WHAT TO EXPECT',label,left,base,main_width,h_note)
            last_note_bottom[0]=base+h_note

        if State.numeric_editor is not None:
            draw_numeric_editor(layout,left,row_y,main_width,step,action,info)
        elif State.page=='LOOT' and State.r10_view is not None and not State.help_open:
            draw_player_studio(layout,left,row_y,main_width)
            last_action_bottom[0]=row_y+(480 if State.r10_view=='BONUS' and height>=900 else 315)
        elif State.page=='DASHBOARD':
            draw_dashboard(layout,left,row_y,main_width,step,action,info)
        elif State.help_open:
            details=PAGE_HELP.get(State.page,("No help available.","Return to controls."))
            note_panel(layout,"WHAT THIS PAGE DOES",details[0],left,row_y,main_width,101)
            note_panel(layout,"SAVE / SAFETY / LIMITATIONS",details[1],left,row_y+111,main_width,102,warning=State.page in ('COMBAT','LOOT','PARTY','SPAWN'))
            # Optional original illustrated merchant busts on the HELP screen.
            # They are NOT official Gearbox character artwork and are not relied
            # on for navigation; import failure keeps all buttons working.
            portraits_y=row_y+224
            if portraits_y+103<y+height-145:
                box(layout,left,portraits_y,104,100,theme_color('bg'),5)
                box(layout,left+111,portraits_y,104,100,theme_color('bg'),5)
                optional_art_image(layout,'TRADER_LEFT',left+3,portraits_y+3,98,94,z=7,opacity=1.0)
                optional_art_image(layout,'TRADER_RIGHT',left+114,portraits_y+3,98,94,z=7,opacity=1.0)
                text(layout,'BLACK MARKET CONTACTS / ORIGINAL ART',left+225,portraits_y+16,
                     main_width-235,23,theme_color('accent'),.64)
                text(layout,"CROWN's unofficial shopkeeper portraits",left+225,portraits_y+42,
                     main_width-235,31,theme_color('dim'),.59)
        elif State.page=="COMBAT" and State.sandbox_view:
            draw_sandbox(layout,left,row_y,main_width)
            last_action_bottom[0]=row_y+313
        elif State.page=="LOOT" and State.xp_view:
            if State.xp_external_view:draw_xp_external(layout,left,row_y,main_width)
            else:draw_progression(layout,left,row_y,main_width)
            last_action_bottom[0]=row_y+(505 if height>=900 else 305)
        elif State.page in ("PLAYER","COMBAT") and State.resource_view:
            draw_resource_lab(layout,left,row_y,main_width)
            last_action_bottom[0]=row_y+314
        elif State.page=="PLAYER":
            action(("DISABLE GOD MODE" if State.god else "ENABLE GOD MODE"),
                   lambda:(set_god(),redraw()),0,State.god)
            action(("DISABLE NOCLIP" if State.noclip else "ENABLE NOCLIP"),
                   lambda:(set_noclip(),redraw()),1,State.noclip)
            action(("DISABLE NO TARGET" if State.target_off else "ENABLE NO TARGET"),
                   lambda:(toggle_no_target(),redraw()),2,State.target_off)
            action('RESTORE DEFAULT FOV',reset_fov,3)
            pc=get_pc(possibly_loading=True)
            actual_fov=_read_number(getattr(pc,'player',None),'BaseFOV') if pc is not None else None
            slider(layout,'CAMERA FOV',actual_fov if actual_fov is not None else 100,60,140,left,row_y+step*2,main_width,change_fov)
            btn(layout,"RESOURCE LAB / EXPERIMENTAL",left,row_y+step*2+84,main_width,36,resource_toggle,small=True)
            last_action_bottom[0]=row_y+step*2+120
            info('Temporary player controls. Camera FOV supports precise entry from 60 to 140. Movement and loadouts are in the tabs above.',step*3.6)
        elif State.page=="MOTION":
            draw_motion_workspace(layout,left,row_y,main_width)
            last_action_bottom[0]=row_y+328
        elif State.page=='COMMUNITY':
            mods=community_modules()
            action('SCAN OPTIONAL MODS',community_probe,0)
            action('OPEN XP LAB / 1-10x',lambda:r3_open_tool('LOOT','XP'),1)
            action('GAME +5 LEVELS (2x)',lambda:community_native_request('levels5'),2)
            action('GAME DEV LOOT DROP (2x)',lambda:community_native_request('loot'),3)
            action('BONK CASH +1,000 (2x)',lambda:community_request('cash1000'),4,
                   disabled=not mods['bonk'])
            action('BONK ERIDIUM +100 (2x)',lambda:community_request('eridium100'),5,
                   disabled=not mods['bonk'])
            action('ENEMY ARENA / SETUP HELP',community_arena_instructions,6)
            action('BACK TO FIELD DECK',lambda:show_page('DASHBOARD'),7)
            info(_status_brief(State.community_status,185)+' | '+community_modules_brief()+
                 ' / Direct developer requests and Bonk fallback require SOLO and second click. Saved changes cannot be undone.',step*4.3)
        elif State.page=='BOOSTS':
            action('SPRINT / SPEED x1.55',lambda:apply_movement_boost('SPRINT'),0,State.boost_preset=='SPRINT')
            action('ROCKET / SPEED x2.25',lambda:apply_movement_boost('ROCKET'),1,State.boost_preset=='ROCKET')
            action('HIGH JUMP / JUMP x2.25',lambda:apply_movement_boost('HIGH JUMP'),2,State.boost_preset=='HIGH JUMP')
            action('BALANCED / SPEED + JUMP',lambda:apply_movement_boost('BALANCED'),3,State.boost_preset=='BALANCED')
            action('RESTORE BOOSTS',reset_movement_boost,4)
            action('XP LAB / REAL REWARD TEST',lambda:r3_open_tool('LOOT','XP'),5)
            action('CHECK LEVEL/PERK ADD-ON',progression_bridge_status,6)
            action('FARM COMBAT BUFF / STAGE',lambda:stage_combat_booster('GENTLE FARM'),7)
            info('Hold F5 during NOCLIP for 2.45x flight speed; release to restore. '+
                 str(State.boost_status)[:94]+' / These are temporary movement values, NOT BL3 Science items, level edits or XP grants.',step*4.0)
        elif State.page=="COMBAT" and State.combat_view=="TUNING":
            draw_combat_tuning(layout,left,row_y,main_width,btn_height,info)
            last_action_bottom[0]=row_y+47+3*77+36
        elif State.page=="COMBAT":
            action("CONFIRM CLEAR ENEMIES" if State.confirm_kill_until>time.monotonic()
                   else "CLEAR ENEMIES (2 CLICKS)",confirm_kill,0)
            action("REFILL ACTION SKILL",refill_skills,1)
            action("INFINITE AMMO",
                   toggle_infinite_ammo,2)
            action("RESTORE TEMP CHANGES",restore,3)
            action('DAMAGE / PRECISE TUNING',combat_toggle_view,4)
            action('RESOURCE LAB / EXPERIMENTAL',resource_toggle,5)
            action('SANDBOX / 29 PRECISE CONTROLS',sandbox_toggle,6)
            info("Infinite Ammo requests the game toggle, but its actual state cannot be read. Confirm it in gameplay. Clear Enemies needs two clicks.",step*2.25)
        elif State.page=="LOOT":
            action('REQUEST CASH +1,000 (2x)',lambda:wallet_request('cash',1000),0)
            action('REQUEST CASH +10,000 (2x)',lambda:wallet_request('cash',10000),1)
            action('REQUEST ERIDIUM +100 (2x)',lambda:wallet_request('eridium',100),2)
            action('REQUEST ERIDIUM +1,000 (2x)',lambda:wallet_request('eridium',1000),3)
            action('CLEAR LOOT CONFIRM',wallet_clear,4)
            action('BACK UP SAVE REMINDER',backup_notice,5)
            action('PROGRESSION / COMBAT XP',xp_toggle,6)
            info('Cash and Eridium can persist in saves, so every reward request needs two clicks. Item spawning lives in FORGE > ITEM FORGE.',step*3.4)
        elif State.page=="CAPACITY":
            if State.capacity_view=='EDIT':
                if State.controller_mode:
                    text(layout,'CONTROLLER SLOT EDITOR / '+State.capacity_mode,
                         left,row_y,main_width,34,theme_color('accent'),.79)
                    text(layout,'STAGED: '+str(State.capacity_draft)+' SLOTS  /  NO GAME WRITE',
                         left,row_y+43,main_width,43,theme_color('text'),.81)
                    action('-100 SLOTS',lambda:capacity_step(-100),0)
                    action('+100 SLOTS',lambda:capacity_step(100),1)
                    action('-10 SLOTS',lambda:capacity_step(-10),2)
                    action('+10 SLOTS',lambda:capacity_step(10),3)
                    action('-1 SLOT',lambda:capacity_step(-1),4)
                    action('+1 SLOT',lambda:capacity_step(1),5)
                    action('USE THIS STAGED VALUE',capacity_step_commit,6)
                    action('CANCEL / KEEP OLD VALUE',capacity_edit_cancel,7)
                    info('A selects a step; B cancels. Only stages 20-5000 slots. Return to Capacity Studio, read live counts, then press Apply twice. Bank and backpack are independent.',step*4.0)
                else:
                    text(layout,'TYPE '+State.capacity_mode+' SLOT COUNT',left,row_y,main_width,34,theme_color('accent'),.79)
                    box(layout,left,row_y+41,main_width,54,theme_color('border'),9)
                    capacity_numeric_input(layout,left+5,row_y+46,main_width-10,43)
                    action('SET NUMBER (STAGED)',capacity_apply_text,4)
                    action('CANCEL EDIT',capacity_edit_cancel,5)
                    info('20-5000 only. Enter stages the value. Nothing changes in the game until a fresh live read and a second Apply confirmation.',step*3.0)
            else:
                action('CHECK LIVE BRIDGE',lambda:capacity_queue_request('PREFLIGHT'),0)
                action('READ BAG / BANK SIZE',lambda:capacity_queue_request('READ'),1)
                action('MODE: '+State.capacity_mode,capacity_mode_toggle,2)
                action('PRESET 40',lambda:capacity_set_draft(40),3,State.capacity_draft==40)
                restore_target=(0 if State.capacity_mode=='BACKPACK' else State.capacity_bank_original)
                restore_on=(State.capacity_confirm==(State.capacity_mode,restore_target,_session_anchor())
                            and time.monotonic()<State.capacity_confirm_until)
                action(('CONFIRM RESTORE BASELINE' if restore_on else 'RESTORE BASELINE (2x)'),
                       lambda:capacity_apply_request(True),4,active=restore_on,danger=restore_on)
                action('PRESET 160',lambda:capacity_set_draft(160),5,State.capacity_draft==160)
                action('TYPE CUSTOM / 20-5000',capacity_edit_open,6)
                confirm_on=(State.capacity_confirm==(State.capacity_mode,State.capacity_draft,_session_anchor()) and time.monotonic()<State.capacity_confirm_until)
                action(('CONFIRM '+State.capacity_mode+' '+str(State.capacity_draft) if confirm_on else 'APPLY '+State.capacity_mode+' '+str(State.capacity_draft)),capacity_apply_request,7,active=confirm_on,danger=confirm_on)
                # A native slider stages values, it does NOT modify live memory.
                # Presets and numeric input remain controller-accessible.
                if height>=760:
                    slider(layout,'STAGED SLOTS',State.capacity_draft,20,5000,left,row_y+step*4.0,main_width,
                           lambda v:capacity_set_draft(int(round(v)),True))
                live_current=(State.capacity_readback_anchor==_session_anchor()
                    and State.capacity_readback_at>0 and time.monotonic()-State.capacity_readback_at<=30)
                live_container='BackpackItems' if State.capacity_mode=='BACKPACK' else 'BankItems'
                live_slots=State.capacity_occupied.get(live_container) if live_current else None
                actual=State.capacity_readback.get(live_container) if live_current else None
                live_caption=('LIVE: '+str(actual)+' CAPACITY / '+str(live_slots)+' OCCUPIED SLOTS' if
                    type(actual) is int and type(live_slots) is int else 'LIVE: NOT VERIFIED / READ FIRST')
                info(live_caption+' // '+_status_brief(State.capacity_status,78)+' // BL4Live optional, SOLO ONLY. Disable fixed 9999-slot PAK before testing.',step*4.0)
        elif State.page=="WORLD":
            slider(layout,'WORLD SPEED',State.speed,.1,4.0,left,row_y,main_width,set_world_time)
            for i,(caption,fn) in enumerate((('OPEN TRAVEL HUB / F8',travel_hub),('RETURN TO LAST SPOT',bookmark_back),('TRAVEL SPRINT x3.0',lambda:tune_motion('speed',3.0)),('RESTORE WALK SPEED',restore_motion))):
                xx=left+(i%2)*(row_width+12);yy=row_y+90+(i//2)*61
                btn(layout,caption,xx,yy,row_width,btn_height,fn,disabled=(i==1 and State.checkpoint_return is None and State.travel_recovery_anchor is None))
                last_action_bottom[0]=max(last_action_bottom[0],yy+btn_height)
            info('World speed requests require local/host authority. The slider accepts finite 0.1x to 4x values. F8 opens your same-map bookmarks.',245)
        elif State.page=="PARTY":
            role=session_role()
            action('REFRESH PARTY LIST',refresh_party,0)
            action('FRIEND TOOL MODE: '+State.party_mode,cycle_party_mode,1)
            action(('CONSENT LOCK: ON' if State.party_approved else 'CONSENT LOCK: OFF'),
                   enable_party_changes,2,State.party_approved)
            remote=[p for p in State.party if not p['local']]
            for i in range(3):
                item=remote[i] if i<len(remote) else None
                action(('> ' if item and State.party_selected==item['key'] else '')+
                       ('P'+str(item['index']+1)+' '+item['name'] if item else 'NO FRIEND CONNECTED'),
                       (lambda i=item['index']:select_party(i)) if item else refresh_party,
                       3+i,bool(item and State.party_selected==item['key']),disabled=(item is None))
            details=coop_snapshot()
            can_change_friend=bool(details['remote_controls_eligible'] and details['selected_friend_valid'])
            # Travelling YOUR OWN pawn to a friend's location is a local swept
            # request. A guest may try it, but moving someone ELSE needs a
            # verified host and the separate consent acknowledgement.
            can_local_jump=bool(details['selected_friend_valid'] and role in ('HOST','GUEST'))
            if State.party_mode=='SESSION':
                action('CHECK CO-OP SESSION',show_coop_status,6)
                action('EXPORT CO-OP QA',export_qa_report,7)
            elif State.party_mode=='BOOSTS':
                action('TOGGLE FRIEND GOD MODE',remote_target_god,6,disabled=not can_change_friend)
                action('REFILL FRIEND SKILL',refill_friend_skill,7,disabled=not can_change_friend)
            elif State.party_mode=='TRAVEL':
                action('ME TO FRIEND (SWEPT)',jump_to_friend,6,disabled=not can_local_jump)
                action('BRING FRIEND TO ME (2x)',bring_friend,7,disabled=not can_change_friend)
            else:
                action('GIFT CASH +1,000 (2x)',lambda:friend_wallet_request('cash',1000),6,disabled=not can_change_friend)
                action('GIFT ERIDIUM +100 (2x)',lambda:friend_wallet_request('eridium',100),7,disabled=not can_change_friend)
            info(('ROLE: '+role+' / '+str(details['visible_players'])+' connected / '+
                  str(details['remote_players'])+' friends. '+
                  ('Host acknowledged; ask each friend first.' if details['host_consent_acknowledged'] else
                   'Friend modifications locked until host acknowledgement.')+
                  ' SESSION mode shows read-only status.'),step*4.15)
        elif State.page=="SPAWN":
            visible=_spawn_visible_indices()
            selection=_forge_selection()
            if State.spawn_view=='INSPECT':
                # Dedicated equipment card. Built out of live native UMG shapes
                # and the existing original ECHO art. No invented item stats or
                # unsafe secondary Unreal-side calls.
                item=forge_inspector_values()
                if item is None:
                    action('<< BROWSE CATALOGUE',lambda:show_page('SPAWN'),0)
                else:
                    card_x=left+main_width*.48
                    card_w=main_width*.52-8
                    card_y=row_y+1
                    card_h=max(250,min(320,height-390))
                    box(layout,card_x,card_y,card_w,card_h,
                        theme_color('bg')[:3]+(.93,),8)
                    box(layout,card_x+3,card_y+3,card_w-6,card_h-6,
                        theme_color('panel')[:3]+(.98,),9)
                    optional_art_image(layout,'ECHO_DOCK_PLATE',card_x+5,card_y+5,
                        card_w-10,card_h-10,z=9,opacity=.24)
                    optional_art_image(layout,'NEON_CIRCUITS',card_x+9,card_y+9,
                        card_w-18,56,z=9,opacity=.42)
                    box(layout,card_x+8,card_y+8,5,card_h-16,
                        theme_color('accent'),10)
                    box(layout,card_x+15,card_y+10,card_w-30,3,
                        theme_color('highlight'),10)
                    text(layout,'CATALOGUE / ITEM INSPECTOR',card_x+23,card_y+19,
                         card_w-36,24,theme_color('accent'),.76,12)
                    text(layout,item['name'][:54],card_x+23,card_y+55,
                         card_w-38,51,theme_color('text'),.92,12)
                    text(layout,'TYPE  /  '+str(item['category'])[:28],
                         card_x+23,card_y+117,card_w-38,25,
                         theme_color('highlight'),.69,12)
                    text(layout,'LEVEL  '+str(item['level'])+'     QUANTITY  '+str(item['quantity']),
                         card_x+23,card_y+150,card_w-38,26,
                         theme_color('text'),.73,12)
                    text(layout,'FAVOURITE  /  '+('YES' if item['favourite'] else 'NO'),
                         card_x+23,card_y+180,card_w-38,23,
                         theme_color('accent'),.63,12)
                    box(layout,card_x+21,card_y+210,card_w-42,2,
                        theme_color('border'),11)
                    text(layout,'VALID POOL / NOT A VERIFIED DROP',
                         card_x+23,card_y+219,card_w-39,24,
                         theme_color('accent'),.65,12)
                    text(layout,'STATS & PARTS: BACKEND READBACK REQUIRED',
                         card_x+23,card_y+245,card_w-40,42,
                         theme_color('dim'),.59,12)
                    # One short left column allows six large controller targets
                    # even at minimum 720p. The right card has NO hit targets.
                    inspect_x=left
                    inspect_w=main_width*.45
                    pitch=min(55.,max(44.,(height-385.)/6.))
                    for idx,(caption,fn,accent,danger,disabled) in enumerate((
                        ('<< BACK TO WORKBENCH',forge_close_inspector,False,False,False),
                        ('PREVIOUS ITEM',lambda:cycle_spawn_pool(-1),False,False,False),
                        ('NEXT ITEM',lambda:cycle_spawn_pool(1),False,False,False),
                        ('SAVE / REMOVE FAVOURITE',toggle_spawn_favorite,item['favourite'],False,False),
                        ('CHECK REAL FORGE API',forge_preflight,False,False,False),
                        (('CONFIRM DROP / SEND REQUEST' if State.spawn_pending is not None and time.monotonic()<State.spawn_expires else 'REQUEST DROP / TWO PRESSES'),spawn_request,False,True,False),
                    )):
                        yy=row_y+idx*pitch
                        btn(layout,caption,inspect_x,yy,inspect_w,pitch-5,
                            fn,active=accent,danger=danger,disabled=disabled,small=True)
                        last_action_bottom[0]=max(last_action_bottom[0],yy+pitch-5)
                    # Weapon damage / manufacturer / rarity require validated
                    # live item data. This card deliberately refuses to guess.
            elif State.spawn_view=='SEARCH':
                text(layout,'FIND A WEAPON / '+str(len(SPAWN_POOLS))+' KNOWN POOLS',
                     left,row_y,main_width,36,theme_color('accent'),.80)
                box(layout,left,row_y+46,main_width,54,theme_color('border'),9)
                forge_search_input(layout,left+5,row_y+51,main_width-10,44)
                action('APPLY SEARCH FILTER',forge_apply_search,4)
                action('CLEAR SEARCH FILTER',forge_clear_search,5)
                action('<< BACK TO BROWSER',forge_cancel_search,6)
                action('QUICK FILTER / PISTOL',lambda:forge_search_preset('pistol'),0)
                action('QUICK FILTER / SHOTGUN',lambda:forge_search_preset('shotgun'),1)
                action('RANDOM PICK (SAFE)',forge_lucky_pick,7)
                info('Search matches weapon names and their published pool IDs. '
                     'Controller: use quick filters or browse categories; hardware keyboard for free-text.',step*3.45)
            elif State.spawn_view=='LEVEL':
                if State.controller_mode:
                    text(layout,'FORGE LEVEL / CONTROLLER / 1-100',left,row_y,main_width,38,
                         theme_color('accent'),.81)
                    text(layout,'STAGED LEVEL: '+str(State.level_draft)+' / NO ITEM SPAWN',
                         left,row_y+43,main_width,38,theme_color('text'),.81)
                    action('-10 LEVELS',lambda:forge_controller_step(-10),0)
                    action('+10 LEVELS',lambda:forge_controller_step(10),1)
                    action('-1 LEVEL',lambda:forge_controller_step(-1),2)
                    action('+1 LEVEL',lambda:forge_controller_step(1),3)
                    action('PRESET LEVEL 40',lambda:forge_controller_step(40-int(State.level_draft)),4)
                    action('PRESET LEVEL 100',lambda:forge_controller_step(100-int(State.level_draft)),5)
                    action('USE THIS LEVEL',forge_controller_commit,6)
                    action('CANCEL',forge_cancel_level,7)
                    info('Controller: adjust any level between 1 and 100, then choose Use This Level. Selecting a level does not spawn anything.',step*4.0)
                else:
                    text(layout,'EXACT ITEM LEVEL / 1-100',left,row_y,main_width,38,
                         theme_color('accent'),.81)
                    box(layout,left,row_y+46,main_width,54,theme_color('border'),9)
                    forge_level_input(layout,left+5,row_y+51,main_width-10,44)
                    action('APPLY LEVEL',forge_apply_level,4)
                    action('40 / STANDARD',lambda:forge_set_level_preset(40),5)
                    action('PRESET LEVEL 70',lambda:forge_set_level_preset(70),6)
                    action('PRESET LEVEL 100',lambda:forge_set_level_preset(100),1)
                    action('<< CANCEL',forge_cancel_level,7)
                    info('1-100. No item spawning happens until an additional Forge confirmation.',step*3.45)
            elif State.spawn_view=='BLUEPRINTS':
                for slot in FORGE_BLUEPRINT_SLOTS:
                    recipe=State.forge_blueprints.get(str(slot))
                    pending=(slot,SPAWN_POOLS[State.spawn_pool_idx][1],
                             State.spawn_level,State.spawn_count)
                    confirming=(State.forge_blueprint_pending==pending
                                and time.monotonic()<State.forge_blueprint_pending_until)
                    caption=('CONFIRM OVERWRITE %d' if confirming else 'SAVE BLUEPRINT %d')%slot
                    action(caption,lambda i=slot:forge_save_blueprint(i),slot-1,
                           active=confirming,danger=confirming)
                    selected=_validated_forge_blueprints(State.forge_blueprints).get(str(slot))
                    label=(next((name for name,token,_ in SPAWN_POOLS
                                if token==selected['pool']),'UNKNOWN')[:15]
                           if selected else 'EMPTY')
                    summary=(label+' LV'+str(selected['level'])+' x'+str(selected['count']) if selected else 'EMPTY')
                    action(('LOAD %d / '%slot+summary),
                           lambda i=slot:forge_load_blueprint(i),slot+2,
                           disabled=(selected is None))
                action('<< BACK TO FORGE',forge_close_blueprints,6)
                action('BROWSE CATALOGUE',lambda:forge_blueprints_browse(),7)
                info('BLUEPRINTS // Three locally saved pool/level/quantity combinations. Loading stages a choice only; never creates an item. Forge requests still need their separate two-press confirmation.',step*4.05)
            elif State.spawn_view=='BROWSE':
                draw_forge_browser(layout,left,row_y,main_width)
                last_action_bottom[0]=row_y+134+forge_page_capacity()*40
            else:
                draw_forge_workspace(layout,left,row_y,main_width,height)
                last_action_bottom[0]=row_y+(584 if height>=1000 else 474 if height>=830 else 305)
        elif State.page=="TROPHIES":
            total=max(1,math.ceil(len(ACHIEVEMENT_NAMES)/6))
            State.trophy_page=max(0,min(total-1,State.trophy_page))
            action('<< PREVIOUS ACHIEVEMENTS',lambda:trophy_change_page(-1),0,disabled=State.trophy_page==0)
            action('NEXT ACHIEVEMENTS >>',lambda:trophy_change_page(1),1,disabled=State.trophy_page==total-1)
            begin=State.trophy_page*6
            for slot in range(6):
                index=begin+slot
                if index<len(ACHIEVEMENT_NAMES):
                    name=ACHIEVEMENT_NAMES[index]
                    is_marked=index in State.trophy_marked
                    title=('[X] ' if is_marked else '[ ] ')+name
                    action(title[:45],lambda i=index:trophy_mark(i),slot+2,is_marked)
            info('JOURNAL PAGE '+str(State.trophy_page+1)+'/'+str(total)+' / '+str(len(State.trophy_marked))+
                 '/63 locally checked. This does NOT read, grant or disable Steam achievements.',step*4.15)
        elif State.page=="WAYPOINTS":
            current_map=map_tag()
            begin=State.waypoint_page*6
            action('MODE: '+State.waypoint_mode+' / SWITCH',waypoint_cycle_mode,0,State.waypoint_mode=='SAVE')
            action(('SLOTS 7-12 >>' if State.waypoint_page==0 else '<< SLOTS 1-6'),travel_next_page,1,State.waypoint_page==1)
            for i in range(6):
                slot=begin+i+1
                entry=State.checkpoints.get(slot)
                valid=_valid_travel_record(slot,entry)
                on_map=valid and entry[0]==current_map
                label_name=TRAVEL_SLOT_NAMES[slot-1]
                if State.waypoint_mode=='SAVE':
                    pending=(State.travel_save_pending==slot and State.travel_save_expires>time.monotonic())
                    caption=('CONFIRM OVERWRITE' if pending else 'SAVE HERE')+' %02d / '%slot+label_name
                    action(caption,lambda n=slot:bookmark_save(n),i+2,active=pending,danger=pending)
                else:
                    prefix='GO' if on_map else ('OTHER MAP' if valid else 'EMPTY')
                    caption=prefix+' %02d / '%slot+label_name
                    action(caption,lambda n=slot:bookmark_go(n),i+2,disabled=not on_map)
            info('ROADRUNNER / %d of %d saved. F8 opens this hub. SAVE stores a spot; occupied slots require two presses. Collision-swept SAME-MAP requests; check terrain.'%(len(State.checkpoints),TRAVEL_SLOT_COUNT),step*4.12)
        elif State.page=="PROFILES" and State.recipe_open:
            draw_recipe_library(layout,left,row_y,main_width)
            last_action_bottom[0]=row_y+314
        elif State.page=="PROFILES" and State.farm_view:
            draw_farm_workspace(layout,left,row_y,main_width)
            last_action_bottom[0]=row_y+314
        elif State.page=="PROFILES" and State.profile_name_edit:
            text(layout,'NAME / PROFILE '+str(State.current_ui_profile),left,row_y,main_width,32,theme_color('highlight'),.90)
            field=widget('EditableTextBox');put(layout,field)
            size_position(field,left,row_y+47,main_width,45,20)
            call(field,'SetText',State.profile_name_draft)
            call(field,'SetVisibility',0);call(field,'SetIsReadOnly',False)
            State.profile_name_widget=field
            if not State.controller_mode:attempt(field,'SetKeyboardFocus')
            action('SAVE NAME',profile_rename_apply,4)
            action('CANCEL',lambda:(setattr(State,'profile_name_edit',False),redraw()),5)
            info('Names are CROWN-only labels, 1-24 characters. No character/save rename or gameplay operation.',step*3.2)
        elif State.page=="PROFILES" and State.profile_manage:
            draw_profile_manager(layout,left,row_y,main_width)
            last_action_bottom[0]=row_y+271
        elif State.page=="PROFILES":
            for slot in range(1,4):
                label=State.profile_names[str(slot)]
                action('SAVE '+str(slot)+' / '+label,lambda n=slot:save_ui_profile(n),(slot-1)*2)
                action('LOAD '+str(slot)+' / '+label,lambda n=slot:load_ui_profile(n),(slot-1)*2+1)
            action('RENAME PROFILE '+str(State.current_ui_profile),profile_rename_open,6)
            action('MANAGE / DUPLICATE / DELETE',profile_manage_toggle,7)
            action('EXPORT APPEARANCE',lambda:appearance_transfer(True),8)
            action('IMPORT AS DRAFT',lambda:_ui_batch(appearance_transfer),9)
            info('Three manual UI/Forge profiles. Names, theme, motion, HUD and pins are local metadata. Loading stages Forge choices, never grants items or edits saves.',step*4.1)
        elif State.page=="GEAR" and State.weapon_view:
            draw_weapon_lab(layout,left,row_y,main_width)
            last_action_bottom[0]=row_y+313
        elif State.page=="GEAR":
            btn(layout,'OWNED WEAPON LAB / FIRE, RELOAD & HANDLING',left,row_y,main_width,42,weapon_toggle,small=True)
            for i,category in enumerate(('ALL','SHOTGUN','SMG','RIFLE','PISTOL','SNIPER','FAVORITES','RECENT')):
                btn(layout,'OPEN '+category+' FORGE',left+(i%2)*(row_width+12),row_y+54+(i//2)*53,row_width,43,lambda c=category:gear_jump(c),small=True)
            last_action_bottom[0]=row_y+256
            info('Choose an owned-weapon experiment or browse the existing curated Forge pools. No stats, parts or delivered items are inferred.',280)
        elif State.page=="DISPLAY":
            action('MENU SIZE 100%',lambda:set_scale_preset(1.0),0)
            action('MENU SIZE 125%',lambda:set_scale_preset(1.25),1)
            action('POPUPS: '+State.toast_position.replace('_',' '),cycle_toast_position,2)
            action('LARGE UI / EASY READ',apply_couch_preset,3,State.panel_scale>=1.75)
            action('POPUPS 4 SEC',lambda:set_toast_duration(4.2),4,abs(State.toast_duration-4.2)<.1)
            action('POPUPS 6 SEC',lambda:set_toast_duration(6.0),5,abs(State.toast_duration-6)<.1)
            action('GAMEPAD: '+('ON' if State.controller_enabled else 'OFF'),toggle_controller_enabled,6,State.controller_enabled)
            action('CURSOR ALIGN: '+State.cursor_coordinates,cycle_cursor_coordinates,7)
            action('HIDE CROWN RIBBON' if State.hud_visible else 'SHOW CROWN RIBBON',lambda:(toggle_hud(),redraw()),8,State.hud_visible)
            action('RIBBON POSITION',cycle_hud_position,9)
            info('DISPLAY // LARGE UI is viewport-clamped with 120% text. 100%/125% and continuous sliders remain in Appearance. Popup duration remains adjustable via 4/6 sec and configuration.',step*4.1)
        elif State.page=="ARENA":
            draw_encounter_director(layout,left,row_y,main_width)
            last_action_bottom[0]=row_y+313
        elif State.page=="FINDER":
            if State.finder_mode=='EDIT':
                text(layout,'TYPE A TOOL OR FEATURE NAME',left,row_y,main_width,36,theme_color('accent'),.80)
                box(layout,left,row_y+48,main_width,55,theme_color('border'),9)
                finder_search_input(layout,left+5,row_y+53,main_width-10,44)
                action('APPLY SEARCH',apply_finder_search,4)
                action('<< BACK TO RESULTS',cancel_finder_search,5)
                action('CLEAR SEARCH',clear_finder_search,6)
            else:
                action('TYPE TO SEARCH',edit_finder_search,0)
                action('SHOW ALL TOOLS',clear_finder_search,1)
                action('<< PREVIOUS RESULTS',lambda:finder_change_page(-1),2)
                action('NEXT RESULTS >>',lambda:finder_change_page(1),3)
                results=finder_results()
                begin=State.finder_page*FINDER_PAGE_SIZE
                for j,entry in enumerate(results[begin:begin+FINDER_PAGE_SIZE]):
                    label=('PIN / ' if entry[0] in State.tool_pins else ('RECENT / ' if entry[0] in State.recent_tools else ''))+entry[1]+'  /  '+entry[0]
                    action(label,lambda dest=entry[0]:open_finder_result(dest),j+4,
                           active=False)
                info('%d matching tools. PIN a tool from its page; pinned and recent tools rise to the top. Controller and mouse both supported.'%len(results),step*4.0)
        elif State.page=="GUIDE" and State.guide_status_open:
            action('REFRESH STATUS',refresh_crown_capabilities,0)
            action('NEXT STATUS PAGE',capability_next_page,1)
            action('BACK TO GUIDE',toggle_capability_guide,2)
            action('OPEN XP / ENCOUNTERS',lambda:r3_open_tool('LOOT','XP'),3)
            rows=State.capability_status_rows or crown_capability_rows()
            low=row_y+step*2+11
            max_lines=5 if height>=760 else 3
            for i,line in enumerate(rows[State.capability_page*max_lines:(State.capability_page+1)*max_lines]):
                text(layout,line,left+5,low+i*34,main_width-12,31,
                     theme_color('text') if i else theme_color('accent'),.65,7)
            info('Read-only CROWN status. A loaded dependency or accepted API call is NOT proof a gameplay action worked.',step*4.55)
        elif State.page=="GUIDE":
            action('WHAT REALLY WORKS?',toggle_capability_guide,0)
            action('ART / SOUND DIAGNOSTICS',lambda:(show_page('DEV'),toggle_ui_diagnostics()),1)
            action('OPEN FORGE PREFLIGHT',lambda:show_page('CONTENT'),2)
            action('RESTORE TEMP CHANGES',restore,3)
            action('EDIT AUDIO / THEME',lambda:show_page('STYLE'),4)
            action('BACK UP SAVE REMINDER',backup_notice,5)
            action('OPEN 12 TELEPORTS',lambda:show_page('WAYPOINTS'),6)
            action('OPEN ITEM FORGE',lambda:show_page('SPAWN'),7)
            info('No forced unlocks, Steam achievement writes, universal save edits or invisible unlock-all controls. Test in SOLO first.',step*4.1)
        elif State.page=="WEEKLY":
            snap=_weekly_snapshot()
            if snap is None:
                text(layout,'ROTATION EXPIRED / CURRENT LOCATION UNKNOWN',left,row_y+7,main_width,42,theme_color('danger'),.78)
                action('CHECK ECHO MAP / OFFICIAL WEEKLY',weekly_summary,0)
                action('OPEN ROADRUNNER',lambda:show_page('WAYPOINTS'),1)
                info('This packaged bulletin has expired. No stale coordinates, rotations or weekly vendor teleports are available.',step*2.3)
            else:
                text(layout,'OCT 8-15 / MAURICE: '+snap['maurice_region'],left,row_y+7,main_width,32,theme_color('accent'),.75)
                text(layout,"MIMICRON  //  SAVAGE SALVAGE  //  AEGON'S DREAM",left,row_y+42,main_width,28,theme_color('text'),.62)
                row_y+=81
                action('SHOW WEEKLY DETAILS',weekly_summary,0)
                action('SAVE VENDOR HERE / SLOT 04',weekly_save_vendor,1)
                action('GO MY VENDOR BOOKMARK',weekly_go_vendor,2,disabled=not _maurice_anchor_ready())
                action('OPEN 12 ROADRUNNER SLOTS',lambda:show_page('WAYPOINTS'),3)
                info('SAVE only while beside Maurice. Slot 04 is user-saved, not auto-detected. Old-week or other-map travel is blocked. Weekly item inventory varies by player.',step*2.35)
        elif State.page=="EVENTS":
            action('BULLET BALLET / 0.5x',lambda:start_event('BULLET BALLET'),0,State.active_event=='BULLET BALLET')
            action('HYPERDRIVE / 2x',lambda:start_event('HYPERDRIVE'),1,State.active_event=='HYPERDRIVE')
            action('MOON BOOTS / LOW G',lambda:start_event('MOON BOOTS'),2,State.active_event=='MOON BOOTS')
            action('LAST STAND / GOD',lambda:start_event('LAST STAND'),3,State.active_event=='LAST STAND')
            action('COSMIC SLO-MO',lambda:start_event('COSMIC SLO-MO'),4,State.active_event=='COSMIC SLO-MO')
            action('LOW GRAV DASH',lambda:start_event('LOW GRAV DASH'),5,State.active_event=='LOW GRAV DASH')
            action('BULLET TIME RUN',lambda:start_event('BULLET TIME RUN'),6,State.active_event=='BULLET TIME RUN')
            action('STOP ACTIVE EVENT',stop_event,7,danger=(State.active_event!='NONE'),disabled=(State.active_event=='NONE'))
            info('Sandbox event presets for solo messing around. ACTIVE: '+State.active_event+'. Stop Event restores the temporary controls it changed.',step*4.1)
        elif State.page=="CONTENT":
            action('READ CURRENT MAP / SESSION',current_content,0)
            action('RUN COMPATIBILITY CHECK',compatibility_report,1)
            action('RUN API AUDIT + EXPORT',run_advanced_audit_and_export,2)
            action('FORGE PRE-FLIGHT CHECK',forge_preflight,3)
            for n,(label,_) in enumerate(DLC_RELEASE_INDEX):
                action(label,lambda i=n:weekly_dlc_info(i),n+4)
            info('DIAGNOSTICS // RUN API AUDIT + EXPORT saves a read-only report to sdk_mods/settings. Forge Pre-Flight checks APIs but never grants an item.',step*2.45)
        elif State.page=="PRESETS":
            action("VAULT VACATION",preset_vacation,0)
            action("WALKING APOCALYPSE",preset_mayhem,1)
            action("NORMAL-ISH",preset_normal,2)
            action("RESTORE EVERYTHING",restore,3)
            info("Presets are quick starting points. They only touch temporary gameplay values and avoid permanent currencies or save rewards.",step*2.2)
        elif State.page=="STYLE" and State.style_audio_open:
            action('SOUND: OFF',lambda:set_audio_mode('OFF'),0,State.audio_mode=='OFF')
            action('SOUND: LOW',lambda:set_audio_mode('LOW'),1,State.audio_mode=='LOW')
            action('SOUND: NORMAL',lambda:set_audio_mode('NORMAL'),2,State.audio_mode=='NORMAL')
            action('SOUND: HIGH',lambda:set_audio_mode('HIGH'),3,State.audio_mode=='HIGH')
            action(('HOVER CUES: ON' if State.audio_hover else 'HOVER CUES: OFF'),toggle_audio_hover,4,State.audio_hover)
            action('SFX: '+State.sfx_set,cycle_sfx_set,5,State.sfx_set=='ECHO')
            action('<< BACK TO STYLE',toggle_style_audio,6)
            action('TEST SOUND',lambda:(play_ui_sound('confirm',force=True),log('AUDIO // '+State.audio_status)),7)
            action('CROWN PERSONALITY: '+('ON' if State.echo_personality else 'OFF'),lambda:(setattr(State,'echo_personality',not State.echo_personality),save_preferences(),redraw()),8,State.echo_personality)
            info('AUDIO // Short CC0 click/switch WAVs through optional Windows playback. Volume and hover are saved. No BL4 sound settings are changed.',step*4.12)
        elif State.page=="STYLE":
            draw_appearance_studio(layout,left,row_y,main_width,row_width,step,btn_height,info)
            last_action_bottom[0]=row_y+step*3+btn_height
        elif State.page=="DEV" and State.diag_open:
            report=ui_diagnostic_lines()
            # Every report line is accessible, including the actual failure
            # reason. A page never crowds the footer at compact resolutions.
            per_page=4 if height>=700 else 3
            total_pages=max(1,math.ceil(len(report)/per_page))
            index=State.diag_page%total_pages
            action('<< BACK TO DEV',toggle_ui_diagnostics,0)
            action('NEXT DIAGNOSTICS '+str(index+1)+'/'+str(total_pages),next_ui_diagnostics,1)
            for i,report_line in enumerate(report[index*per_page:(index+1)*per_page]):
                text(layout,report_line,left,row_y+step*(i+1),main_width,
                     max(24.0,step-7),theme_color('text'),.59)
            info('DIAGNOSTICS '+str(index+1)+'/'+str(total_pages)+
                 ' // Read-only. Import availability does not prove art rendered.',step*4.4)
        elif State.page=="DEV" and State.feature_ledger_open:
            selected=feature_ledger_selected_page()
            mode,implemented,missing=PAGE_CAPABILITY_LEDGER[selected]
            action('<< BACK TO DEV',toggle_feature_ledger,0)
            action('PREVIOUS TOOL',lambda:feature_ledger_step(-1),1)
            action('NEXT TOOL',lambda:feature_ledger_step(1),2)
            action('OPEN SELECTED TOOL',open_feature_ledger_page,3)
            text(layout,'TOOL %02d / %d  //  %s'%(State.feature_ledger_index+1,len(PAGE_CAPABILITY_LEDGER),selected),
                 left,row_y+step*2+8,main_width-10,32,theme_color('accent'),.86,7)
            text(layout,'SOURCE STATUS: '+mode,left,row_y+step*2+45,
                 main_width-10,26,theme_color('highlight'),.69,7)
            note_panel(layout,'IMPLEMENTED IN SOURCE',implemented,
                       left,row_y+step*2+76,main_width,58)
            # Text-only to avoid a click-catching overlay below the quickbar.
            if height>=790:
                text(layout,'NEEDS LIVE PROOF: '+missing,
                     left,row_y+step*2+143,main_width,47,theme_color('dim'),.62,7)
        elif State.page=="DEV" and State.activity_open:
            action('<< BACK TO TOOLS',toggle_activity,0)
            action('CLEAR ACTIVITY',clear_activity,1)
            line_limit=3 if height<700 else 5
            for i,message in enumerate(State.activity_history[-line_limit:][::-1]):
                line=message[:88]
                text(layout,str(i+1)+'. '+line,left,row_y+step*(i+1),main_width,
                     38,theme_color('dim'),.64)
            info('Last five actions (session only; not saved to disk).',step*4.25)
        elif State.page=="DEV":
            action('RECOVER INPUT / F9',recover_ui_focus,0)
            action('READ LIVE STATUS',status_readback,1)
            action('UI DIAGNOSTICS',toggle_ui_diagnostics,2)
            action('OPEN ACTIVITY LOG',toggle_activity,3)
            action(('HIDE STATUS RIBBON' if State.hud_visible else 'SHOW STATUS RIBBON'),
                   lambda:(toggle_hud(),redraw()),4,State.hud_visible)
            action('SAFE MODE: '+('ON' if State.safe_mode else 'OFF'),toggle_safe_mode,5,State.safe_mode)
            action('RESTORE ALL TEMP CHANGES',restore,6)
            action('EXPORT QA REPORT',export_qa_report,7)
            action('FEATURE LEDGER / 24 TOOLS',toggle_feature_ledger,8)
            info("HUD is a noninteractive CROWN status ribbon, not a replacement for the game's health/ammo/minimap. F6 closes the menu; F10 restores temporary effects.",step*2.2)

        # Roadrunner uses the common contextual card below instead of an
        # independently positioned ornament that used to collide with it.
        # Compact, truthful state telemetry to fill otherwise empty menu space.
        # It is strictly noninteractive and NEVER overlaps the page's controls.
        if State.numeric_editor is None and not State.help_open and State.page in ('PLAYER','MOTION','WORLD','SPAWN','PARTY','COMBAT'):
            limit=y+height-168.0
            ry=max(last_action_bottom[0],last_note_bottom[0])+11
            if ry+34<=limit:
                if State.page=='SPAWN':
                    detail='FORGE: '+State.forge_stage.replace('_',' ')[:45]
                elif State.page=='MOTION':
                    detail='MOVE x%.2f / session only'%State.motion_scale
                elif State.page=='WORLD':
                    detail='TIME x%.2f / session only'%State.speed
                elif State.page=='PARTY':
                    detail='ROLE: '+session_role()+' / CONSENT: '+('ON' if State.party_approved else 'OFF')
                elif State.page=='COMBAT':
                    detail='AMMO: UNVERIFIED / ENEMY CLEAR: IRREVERSIBLE'
                else:
                    detail='GOD '+('REQ' if State.god else 'OFF')+' / NOCLIP '+('REQ' if State.noclip else 'OFF')+' / NO TARGET '+('REQ' if State.target_off else 'OFF')
                box(layout,left,ry,main_width,32,theme_color('header'),5)
                box(layout,left,ry,5,32,theme_color('highlight'),6)
                text(layout,'STATE',left+12,ry+5,45,20,theme_color('accent'),.59,7)
                text(layout,detail,left+60,ry+5,main_width-73,22,theme_color('text'),.63,7)

        # Original comic contact illustration / atmospheric readback in genuinely
        # unused vertical space. ALWAYS checks the next footer boundary.
        if (State.numeric_editor is None and not State.help_open and State.page in ('COMBAT','PRESETS','CONTENT','LOOT')
                and not State.compact and height>=750):
            art_y=max(last_action_bottom[0],last_note_bottom[0])+12
            if art_y+88 < y+height-165:
                box(layout,left,art_y,main_width,84,theme_color('bg'),4)
                box(layout,left,art_y,main_width,2,theme_color('accent'),5)
                optional_art_image(layout,'TRADER_LEFT',left+5,art_y+4,84,76,z=7,opacity=.98)
                optional_art_image(layout,'TRADER_RIGHT',left+94,art_y+4,84,76,z=7,opacity=.98)
                text(layout,'BLACK MARKET // SESSION ACCESS',left+192,art_y+10,
                    max(70,main_width-204),22,theme_color('accent'),.66,7)
                tagline=('Read-only checks. No automatic DLC unlocks.' if State.page=='CONTENT' else
                         r10_loot_tagline() if State.page=='LOOT' else
                         'Sandbox presets affect temporary values only.' if State.page=='PRESETS' else
                         'Combat requests may change the current encounter.')
                text(layout,tagline,left+192,art_y+37,max(70,main_width-204),40,
                    theme_color('text'),.57,7)

        # Context display makes the former empty half-screen useful without
        # inventing item stats or changing item pools. Fades away on small UI.
        if State.numeric_editor is None and not State.help_open and State.page in ('PLAYER','MOTION','WORLD','WAYPOINTS'):
            context_top=max(last_action_bottom[0],last_note_bottom[0])+53
            if State.page=='WAYPOINTS':context_top+=0
            remaining=y+height-178-context_top
            if remaining>=118:
                box(layout,left,context_top,main_width,min(remaining,174),theme_color('bg'),5)
                box(layout,left+1,context_top+1,main_width-2,min(remaining,174)-2,theme_color('header'),5)
                box(layout,left+2,context_top+3,5,min(remaining,174)-6,theme_color('highlight'),6)
                heads={
                    'PLAYER':'VAULT HUNTER / LIVE SETTINGS',
                    'MOTION':'MOTION / TUNING SNAPSHOT',
                    'SPAWN':'FORGE / SELECTED POOL',
                    'WORLD':'ROADRUNNER / TRAVEL SHORTCUT',
                    'WAYPOINTS':'TRAVEL / SWEPT MOVE CHECK'
                }
                title=heads[State.page]
                if State.page=='SPAWN':
                    sel=_forge_selection()
                    details=('SELECTED: '+sel[0]+' / LV'+str(State.spawn_level)+' / QTY '+str(State.spawn_count)
                             if sel else 'NO POOL SELECTED')
                    subline='Names are candidates; verify real drops and rarity in BL4.'
                elif State.page=='PLAYER':
                    details='GOD '+('REQ' if State.god else 'OFF')+'  /  NOCLIP '+('REQ' if State.noclip else 'OFF')+'  /  NO TARGET '+('REQ' if State.target_off else 'OFF')
                    subline='Active values may reset on map or character changes.'
                elif State.page=='MOTION':
                    details='SPEED x%.2f  /  JUMP x%.2f  /  GRAVITY x%.2f'%(State.motion_scale,State.jump_selected,State.gravity_selected)
                    subline='Changes are temporary. Restore movement defaults if needed.'
                else:
                    details='%d / %d BOOKMARKS SAVED'%(len(State.checkpoints),TRAVEL_SLOT_COUNT)
                    subline='F8 opens Roadrunner. Avoid unsafe or outdated destinations.'
                text(layout,title,left+16,context_top+11,main_width-32,30,theme_color('accent'),.85,7)
                text(layout,details,left+16,context_top+50,main_width-34,26,theme_color('text'),.70,7)
                text(layout,subline,left+16,context_top+82,main_width-34,29,theme_color('dim'),.59,7)
                if State.page=='SPAWN' and remaining>=164 and main_width>=600:
                    # Actual read-only Forge preflight from the workbench; it
                    # checks current game APIs but NEVER produces an item.
                    text(layout,'SAFE CHECK  /  NO ITEM SPAWN',left+17,context_top+122,
                         main_width-281,26,theme_color('highlight'),.64,7)
                    btn(layout,'CHECK FORGE API',left+main_width-250,
                        context_top+117,233,39,
                        lambda:(forge_preflight(),redraw()),small=True)
        # Decorative seam is intentionally BELOW footer text and hit targets.
        optional_art_image(layout,'HAZARD_STRIP',x+20,y+height-160,width-40,7,z=5,opacity=.60)
        r3_draw_context(layout,State.r3_context_rect)
        if State.controller_mode:r3_controller_strip(layout,x+258,y+height-145,min(300,width-710))
        # Quick actions always visible at foot of menu.
        foot=y+height-141.0
        box(layout,x+20,foot-7,width-40,2,theme_color("border"),5)
        text(layout,r10_footer_prompt(),
             x+width-420,foot-5,393,22,theme_color('dim'),.54)
        text(layout,"QUICK BAR",x+24,foot-4,220,26,theme_color("accent"),.71)
        quick_w=(width-48.0-24.0)/4.0
        quick_y=foot+21
        items=(
            ("GOD MODE: "+("ON" if State.god else "OFF"),lambda:(set_god(),redraw()),State.god),
            (_quick_pin_caption(),open_quick_pin,False),
            ("RESTORE TEMP",restore,False),
            ("FIND / SEARCH",open_finder,False),
        )
        for i,(label,fn,active) in enumerate(items):
            btn(layout,label,x+24+i*(quick_w+8),quick_y,quick_w,43,
                fn,active=active,danger=(i==2),small=True)
        box(layout,x+20,y+height-52,width-40,2,theme_color("border"),5)
        State.status_marker=box(layout,x+23,y+height-45,7,26,_status_tint(),9)
        State.hovered_control=None
        State.status_chars=max(37,int((width-68)/8.8))
        State.status_label=text(layout,_status_caption(),x+39,y+height-40,83,27,_status_tint(),.69)
        State.status_widget=text(layout,(_visual_mode_label() if State.safe_mode else
             _status_brief(State.message,max(32,State.status_chars-18))),
             x+122,y+height-40,width-149,27,theme_color('text'),.64)
        # Four moving native borders: controller focus changes do NOT rebuild
        # hundreds of text/art widgets on every D-pad press.
        State.controller_focus_outline=[box(layout,-40,-40,1,1,theme_color('highlight'),14)
                                        for _ in range(4)]
        State.mouse_hover_frame=[box(layout,-60,-60,1,1,theme_color('accent'),15)
                                 for _ in range(4)]
        # Rebuilds reorder button widgets. Never carry an old numeric focus
        # into a new action (a dangerous mis-selection on a gamepad).
        if State.controller_mode:
            State.controller_focus=_restore_focus_index(old_focus_name,old_focus_rect)
        _controller_update_focus_outline()
        create_mouse_cursor_aid(layout)
        _commit_canvas_frame(layout,old_frame,w,h)
        State.draw_ok=True
        State.viewport_signature=(round(actual_w,1),round(actual_h,1))
        State.ui_last_ms=(time.perf_counter()-build_start)*1000.0
        State.ui_peak_ms=max(State.ui_peak_ms,State.ui_last_ms)
        State.ui_rebuild_count+=1
        _set_native_phase('REDRAW_READY')
    except Exception as e:
        State.ui_error_count+=1
        record_runtime_fault('UMG_REDRAW',e)
        log("UMG layout failed: "+type(e).__name__)
        # In-game redraw failure must not leave an invisible UI capturing input.
        # This is the game-thread exception boundary. Even on initial opening
        # (before input is captured), discard the failed overlay immediately.
        if State.opened:
            close_menu()

def redraw():
    """Only one UMG tree rebuild at a time; coalesce nested callbacks.

    Prevents a redraw triggered by a synchronous native widget callback from
    tearing down the canvas while the previous redraw is still mounting it.
    One pending frame is permitted; recursive storms are never repeated.
    """
    if not State.opened:return
    if State.polling_ui:
        State.redraw_pending=True
        return
    if State.redraw_busy:
        State.redraw_pending=True
        return
    State.redraw_busy=True
    try:
        _redraw_impl()
        if State.redraw_pending and State.opened:
            State.redraw_pending=False
            _redraw_impl()
    finally:
        State.redraw_busy=False
        State.redraw_pending=False

def save_input(pc):
    if State.input_pc is not None:
        return
    State.input_pc=pc
    saved={}
    # bBlockInput belongs to the GAME and can change during cinematics or travel.
    # UIOnly is the confirmed CROWN-owned guard; never override bBlockInput.
    for flag in ("bShowMouseCursor","bEnableMouseOverEvents",
                 "bEnableClickEvents","bEnableTouchEvents"):
        try: saved[flag]=bool(getattr(pc,flag))
        except Exception: pass
    State.input_saved=saved
    try:
        _set_native_phase('INPUT_CAPTURE')
        lib=cls("/Script/UMG.WidgetBlueprintLibrary").ClassDefaultObject
        # UIOnly is required to prevent clicks, grenades and skill buttons from
        # passing through to gameplay. GameAndUI intentionally does NOT do this.
        guarded=(attempt(lib,"SetInputMode_UIOnlyEx",pc,State.root,0,False)
                 or attempt(lib,"SetInputMode_UIOnly",pc,State.root,False))
        State.input_guard_confirmed=bool(guarded)
        State.input_mode_owned=bool(guarded)
        if not guarded:
            State.input_mode_used='UI ONLY UNAVAILABLE / MENU REFUSED'
            # Failing closed is safer than a working-looking menu that can fire
            # guns or grenades underneath a click. F6 remains available.
            raise RuntimeError('SAFE INPUT UNAVAILABLE: UIOnly not exposed by this BL4 build; menu closed to prevent gameplay passthrough')
        State.input_mode_used='UI ONLY / INPUT REQUESTED' 
        for flag in ("bShowMouseCursor","bEnableMouseOverEvents","bEnableClickEvents"):
            try:setattr(pc,flag,True)
            except Exception:pass
        # bBlockInput is a route-breaking game flag on some BL4 builds.
        # Prefer controller movement/look ignores that preserve raw key polling.
        State.input_move_ignored_original=None
        State.input_look_ignored_original=None
        for getter,setter,attr in (("IsMoveInputIgnored","SetIgnoreMoveInput","input_move_ignored_original"),
                                  ("IsLookInputIgnored","SetIgnoreLookInput","input_look_ignored_original")):
            method=getattr(pc,getter,None)
            command=getattr(pc,setter,None)
            if callable(method) and callable(command):
                try:
                    previous=bool(method())
                    setattr(State,attr,previous)
                    if not previous:command(True)
                    if method() is not True:raise RuntimeError('Move/look ignore readback refused')
                except Exception:
                    State.input_guard_readback='MOVE/LOOK CAPTURE FAILED'
                    raise RuntimeError('SAFE INPUT UNAVAILABLE / Move-look guard refused')
        # No bBlockInput native write: the game owns that flag.
        _set_native_phase('UI_ONLY')
        State.input_last_status=State.input_mode_used 
    except Exception:
        # Caller will tear down the menu. Undo partial changes first.
        release_input()
        raise

def recover_ui_focus():
    """Best-effort explicit F9/onscreen recovery; never changes gameplay data.

    Native UIOnly is necessary to prevent gameplay actions passing through.
    Raw Win32 keyboard/XInput keeps close and controller navigation available.
    """
    if not State.opened or State.root is None:
        log('INPUT RECOVERY // Open CROWN with F7 first.')
        return False
    pc=get_pc(possibly_loading=True)
    if pc is None or (State.input_pc is not None and not same_unreal_object(pc,State.input_pc)):
        log('INPUT RECOVERY // Player controller changed; close with F6, then reopen.')
        return False
    if ((State.page=='SPAWN' and State.spawn_view in ('SEARCH','LEVEL'))
            or (State.page=='FINDER' and State.finder_mode=='EDIT')
            or ((State.page=='CAPACITY' and State.capacity_view=='EDIT') or (State.page=='ARENA' and State.encounter_view=='SEARCH'))):
        log('INPUT RECOVERY // Apply or cancel the current Forge editor first.')
        return False
    try:
        lib=cls('/Script/UMG.WidgetBlueprintLibrary').ClassDefaultObject
        good=(attempt(lib,'SetInputMode_UIOnlyEx',pc,State.root,0,False)
              or attempt(lib,'SetInputMode_UIOnly',pc,State.root,False))
        State.input_guard_confirmed=bool(good)
        # A failed second focus request must not forget a previously applied
        # UIOnly input mode, otherwise close could strand gameplay in UIOnly.
        if good:State.input_mode_owned=True
        if not good:
            log('INPUT RECOVERY BLOCKED // UIOnly is not supported. Closing instead of passing controls to gameplay.')
            close_menu()
            return False
        for flag in ('bShowMouseCursor','bEnableClickEvents','bEnableMouseOverEvents'):
            try:setattr(pc,flag,True)
            except Exception:pass
        attempt(State.root,'SetUserFocus',pc)
        State.input_last_status='UI ONLY / FOCUS REQUESTED'
        log('INPUT RECOVERED // Mouse shown and CROWN focus requested (F6 if stuck).')
        return True
    except Exception as exc:
        log('INPUT RECOVERY FAILED // '+str(exc)[:72])
        return False

def release_input():
    pc=State.input_pc
    if pc is None:return
    # Native UObject wrappers can become invalid on map travel or crash
    # recovery. Never call Unreal methods on an unowned/replaced controller.
    try:current_pc=get_pc(possibly_loading=True)
    except Exception:current_pc=None
    if current_pc is None or not same_unreal_object(current_pc,pc):
        State.input_pc=None
        State.input_saved=None
        State.input_move_ignored_original=State.input_look_ignored_original=None
        State.input_guard_confirmed=False
        State.input_mode_owned=False
        State.input_mode_used='STALE PC / NO NATIVE RESTORE'
        return
    # Never force GameOnly when no CROWN UIOnly request was accepted: the
    # user might be in a legitimate game menu/cinematic input mode.
    input_restored=not State.input_mode_owned
    if State.input_mode_owned:
        try:
            lib=cls("/Script/UMG.WidgetBlueprintLibrary").ClassDefaultObject
            input_restored=(attempt(lib,"SetInputMode_GameOnly",pc,True)
                            or attempt(lib,"SetInputMode_GameOnly",pc))
            attempt(lib,"SetFocusToGameViewport")
        except Exception:pass
    for name,original in (("SetIgnoreMoveInput",State.input_move_ignored_original),
                          ("SetIgnoreLookInput",State.input_look_ignored_original)):
        if original is False:
            _safe_pc_call(pc, name, False)
    State.input_move_ignored_original=State.input_look_ignored_original=None
    for flag,val in (State.input_saved or {}).items():
        if _pc_wrapper_valid(pc):
            try:setattr(pc,flag,val)
            except Exception:pass
    State.input_pc=None
    State.input_saved=None
    State.input_guard_confirmed=False
    State.input_mode_owned=False
    State.input_mode_used='GAME RESTORED'
    if not input_restored:
        log("Input-mode reset unconfirmed; pause/unpause or restart if controls stick.")

def stop_hook():
    # A registration can partially succeed before throwing; always remove by ID.
    try:remove_hook(HOOK,Type.POST,HOOK_ID)
    except Exception:pass
    State.hook_active=False

def close_menu():
    if State.opened:_set_native_phase('MENU_CLOSE')
    if State.opened:play_ui_sound('close')
    State.opened=False
    State.encounter_epoch+=1;State.encounter_job=None;State.encounter_confirm=None
    State.encounter_input=None;State.echo_scan=None;State.backend_hash_cache={}
    State.recipe_open=False;State.recipe_pending=None;State.recipe_import=None;State.farm_view=False;State.farm_widgets=[];State.farm_generation=-1
    State.weapon_confirm=None;State.weapon_choices=[];State.weapon_baselines={};State.weapon_draft={};State.weapon_scan_anchor=None
    stop_hook()
    try:
        if State.root is not None:call(State.root,"RemoveFromParent")
    except Exception as error:
        # A stale UE wrapper can reject removal during map travel. Log only
        # the exception type; release_input and marker cleanup must still run.
        record_runtime_fault('MENU_REMOVE',error)
    finally:
        State.root=State.tree=State.canvas=State.status_widget=State.status_marker=State.status_label=None
        State.buttons=[]
        State.sliders=[]
        State.palette_bindings=[]
        State.appearance_preview={}
        State.search_widget=State.level_widget=State.capacity_input=State.finder_input=None
        State.profile_name_widget=None
        State.profile_name_edit=False
        State.profile_pending=None
        State.profile_manage=False
        State.resource_view=False
        State.numeric_editor=State.numeric_widget=None
        State.appearance_draft=None
        State.transition_canvas=None
        State.redraw_pending=False
        State.drag_armed=False
        State.f7_down=State.f6_down=State.f9_down=False
        State.esc_down=False
        State.f11_down=False
        State.arrow_keys_down={}
        State.editor_enter_down=False
        State.controller_repeat_key=None
        State.controller_repeat_due=0.0
        State.focus_loss_count=0
        State.focus_repair_count=0
        State.foreground_suspended=False
        State.foreground_resume_after=0.0
        State.controller_focus=-1
        State.controller_focus_outline=[]
        State.mouse_hover_frame=[]
        State.cursor_shapes=[]
        State.cursor_last=State.mouse_last=None
        State.controller_last_keys={}
        _clear_native_click_guard()
        release_input()
        _clear_menu_marker()

# Windows raw device polling remains available when Unreal routes input to
# UIOnly and PlayerController.IsInputKeyDown stops receiving game input.
_RAW_KEY_CODES={'F6':0x75,'F7':0x76,'F8':0x77,'F9':0x78,'F10':0x79,
                'F11':0x7A,'Escape':0x1B,'Enter':0x0D,'Return':0x0D,
                'Up':0x26,'Down':0x28,'Left':0x25,'Right':0x27,
                'LeftMouseButton':0x01,'Tab':0x09,'LeftShift':0xA0,'RightShift':0xA1,'PageUp':0x21,'PageDown':0x22}
_XINPUT_MASK={'Gamepad_DPad_Up':0x0001,'Gamepad_DPad_Down':0x0002,
              'Gamepad_DPad_Left':0x0004,'Gamepad_DPad_Right':0x0008,
              'Gamepad_LeftShoulder':0x0100,'Gamepad_RightShoulder':0x0200,
              'Gamepad_FaceButton_Bottom':0x1000,'Gamepad_FaceButton_Right':0x2000,
              'Gamepad_LeftThumbstick':0x0040,'Gamepad_RightThumbstick':0x0080}
_raw_dll=None
_xinput_dll=None
_xinput_last_at=0.0
_xinput_last_buttons=0
_xinput_last_axes=None
_xinput_last_triggers=None
_XINPUT_TRIGGERS={'Gamepad_LeftTrigger':0,'Gamepad_RightTrigger':1}
_XINPUT_LEFT_STICK=frozenset(('Gamepad_LeftStick_Up','Gamepad_LeftStick_Down',
                            'Gamepad_LeftStick_Left','Gamepad_LeftStick_Right'))

_foreground_last_at = -1.0
_foreground_is_game = False
_foreground_user32 = None

def _game_window_foreground():
    """Read foreground-process ownership, cached for 50ms per camera tick.

    Win32 global keyboard and XInput polling must not respond to presses in
    other applications. Cache the Win32 call: controller scans sample many keys
    each frame, and repeated DLL loading otherwise harms frame times.
    """
    import sys
    if sys.platform!='win32':return True
    global _foreground_last_at,_foreground_is_game,_foreground_user32
    now=time.monotonic()
    if _foreground_last_at>=0 and now-_foreground_last_at<.05:
        return _foreground_is_game
    _foreground_last_at=now
    _foreground_is_game=False
    try:
        import os,ctypes
        from ctypes import wintypes
        if _foreground_user32 is None:
            _foreground_user32=ctypes.WinDLL('user32',use_last_error=True)
            _foreground_user32.GetForegroundWindow.restype=wintypes.HWND
            _foreground_user32.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
            _foreground_user32.GetWindowThreadProcessId.restype=wintypes.DWORD
        hwnd=_foreground_user32.GetForegroundWindow()
        if hwnd:
            process_id=wintypes.DWORD(0)
            if _foreground_user32.GetWindowThreadProcessId(hwnd,ctypes.byref(process_id)):
                _foreground_is_game=(process_id.value==os.getpid())
    except Exception:
        pass # Fail closed: unknown focus never authorizes a global input.
    return _foreground_is_game

def _windows_raw_key(name):
    global _raw_dll,_xinput_dll,_xinput_last_at,_xinput_last_buttons,_xinput_last_axes,_xinput_last_triggers
    import sys
    if sys.platform!='win32':return None
    if not _game_window_foreground():return False
    try:
        import ctypes
        from ctypes import wintypes
        if name in _RAW_KEY_CODES:
            if _raw_dll is None:_raw_dll=ctypes.WinDLL('user32',use_last_error=True)
            _raw_dll.GetAsyncKeyState.argtypes=[ctypes.c_int]
            _raw_dll.GetAsyncKeyState.restype=ctypes.c_short
            return bool(_raw_dll.GetAsyncKeyState(_RAW_KEY_CODES[name]) & 0x8000)
        if name in _XINPUT_MASK or name in _XINPUT_LEFT_STICK or name in _XINPUT_TRIGGERS:
            if _xinput_dll is None:
                for module in ('xinput1_4.dll','xinput1_3.dll','xinput9_1_0.dll'):
                    try:_xinput_dll=ctypes.WinDLL(module);break
                    except OSError:continue
                if _xinput_dll is None:return None
            now=time.monotonic()
            if now-_xinput_last_at>.008:
                class Pad(ctypes.Structure):
                    _fields_=[('buttons',ctypes.c_ushort),('left_trigger',ctypes.c_ubyte),
                              ('right_trigger',ctypes.c_ubyte),('left_x',ctypes.c_short),
                              ('left_y',ctypes.c_short),('right_x',ctypes.c_short),('right_y',ctypes.c_short)]
                class StatePacket(ctypes.Structure):
                    _fields_=[('packet',ctypes.c_uint),('pad',Pad)]
                _xinput_dll.XInputGetState.argtypes=[ctypes.c_uint,ctypes.POINTER(StatePacket)]
                _xinput_dll.XInputGetState.restype=ctypes.c_uint
                packet=StatePacket()
                result=_xinput_dll.XInputGetState(0,ctypes.byref(packet))
                _xinput_last_buttons=packet.pad.buttons if result==0 else None
                _xinput_last_axes=(packet.pad.left_x,packet.pad.left_y) if result==0 else None
                _xinput_last_triggers=(packet.pad.left_trigger,packet.pad.right_trigger) if result==0 else None
                _xinput_last_at=now
            if _xinput_last_buttons is None:return None  # Steam Input or non-XInput fallback
            if name in _XINPUT_MASK:
                return bool(_xinput_last_buttons & _XINPUT_MASK[name])
            if name in _XINPUT_TRIGGERS:
                return bool(_xinput_last_triggers and _xinput_last_triggers[_XINPUT_TRIGGERS[name]]>=180)
            # Intentional strong deadzone and dominant-axis gating: a
            # diagonal/near-centre stick must never select two controls or
            # drift the cursor. No settings writes or game commands here.
            if _xinput_last_axes is None:return None
            horizontal,vertical=_xinput_last_axes
            threshold=20316  # ~=62% of XInput full-scale, beyond normal drift.
            if name=='Gamepad_LeftStick_Up':
                return vertical>threshold and abs(vertical)>abs(horizontal)*1.15
            if name=='Gamepad_LeftStick_Down':
                return vertical<-threshold and abs(vertical)>abs(horizontal)*1.15
            if name=='Gamepad_LeftStick_Left':
                return horizontal<-threshold and abs(horizontal)>abs(vertical)*1.15
            if name=='Gamepad_LeftStick_Right':
                return horizontal>threshold and abs(horizontal)>abs(vertical)*1.15
    except Exception:
        return None
    return None

def key_down(pc, name):
    raw=_windows_raw_key(name)
    if raw is not None:return raw
    if pc is None or not _pc_wrapper_valid(pc): return False
    try:
        key=unrealsdk.make_struct("Key",KeyName=name)
        return bool(_safe_pc_call(pc, 'IsInputKeyDown', key, default=False))
    except Exception:
        try: return bool(_safe_pc_call(pc, 'IsInputKeyDown', name, default=False))
        except Exception: return False


def _menu_foreground_guard(pc, now):
    """Block stale UMG releases when the game loses and regains foreground.

    Unlike native button callbacks, SDK polling can miss the release while the
    window is unfocused.  On return, that release must not activate Forge,
    currency or a destructive menu action. Do not recapture OS window focus.
    This only guards CROWN; BL4 remains responsible for its gameplay input.
    """
    if not State.opened:
        return False
    if not _game_window_foreground():
        if not State.foreground_suspended:
            State.foreground_suspended=True
            State.foreground_resume_after=now+.25
            State.foreground_guard_count+=1
            # Cancel an interrupted placement, never commit an old drag.
            if State.drag_armed and State.canvas is not None:
                try:State.canvas.SetRenderTranslation(v2(0,0))
                except Exception:pass
            State.drag_armed=False
            State.drag_origin=State.drag_start=State.drag_last=None
            State.mouse_was_down=False
            State.controller_repeat_key=None
            State.controller_repeat_due=0.0
            _clear_native_click_guard()
            State.input_last_status='UI SUSPENDED / BL4 NOT FOREGROUND'
        for item in State.buttons:
            item['pressed']=False
        return True

    if State.foreground_suspended:
        State.foreground_suspended=False
        State.foreground_resume_after=now+.25
        State.focus_watch_at=now+1.0
        State.focus_loss_count=0
        State.focus_repair_count=0
        State.input_last_status='UI ONLY / FOREGROUND RESUMED'

    if State.foreground_resume_after<=0:
        return False

    # Synchronise UMG and raw key edges during reacquisition, even when held.
    # Simply sleeping for a fixed 250ms would allow a long mouse hold to
    # become an accidental native click on release.
    for item in State.buttons:
        item['pressed']=False
    State.mouse_was_down=False
    State.editor_enter_down=key_down(pc,'Enter') or key_down(pc,'Return')
    State.r10_input_keys={n:key_down(pc,n) for n in ('Tab','PageUp','PageDown','Gamepad_LeftTrigger','Gamepad_RightTrigger','MouseScrollUp','MouseScrollDown')}
    State.f6_down=key_down(pc,'F6')
    State.f7_down=key_down(pc,'F7')
    State.f8_down=key_down(pc,'F8')
    State.f9_down=key_down(pc,'F9')
    State.f10_down=key_down(pc,'F10')
    State.f11_down=key_down(pc,'F11')
    State.esc_down=key_down(pc,'Escape')
    for name in ('Up','Down','Left','Right'):
        State.arrow_keys_down[name]=key_down(pc,name)
    controller_keys=(*CONTROLLER_DIRECTIONS,*CONTROLLER_CHORD,
                     'Gamepad_FaceButton_Bottom','Gamepad_FaceButton_Right',
                     'Gamepad_LeftShoulder','Gamepad_RightShoulder','Gamepad_LeftTrigger','Gamepad_RightTrigger')
    for key in controller_keys:
        State.controller_last_keys[key]=key_down(pc,key)
    try:umg_down=any(bool(item['widget'].IsPressed()) for item in State.buttons)
    except Exception:umg_down=False  # raw mouse/button-release guard remains active
    pressed=(umg_down or key_down(pc,'LeftMouseButton') or
             State.editor_enter_down or any(State.controller_last_keys.values()))
    if pressed:
        State.foreground_resume_after=max(State.foreground_resume_after,now+.12)
    elif now>=State.foreground_resume_after:
        State.foreground_resume_after=0.0
        return False
    return True


# ---------- Controller: fail-safe chord, focus navigation and recovery ----------
# Unreal Engine FKey names: only poll input; no memory writes or synthetic key events.
# Hold both stick clicks; the older shoulder chord remains a backup for controllers
# whose driver does not report stick click keys to the SDK.
CONTROLLER_CHORD=('Gamepad_LeftThumbstick','Gamepad_RightThumbstick')
LEGACY_CONTROLLER_CHORD=('Gamepad_LeftShoulder','Gamepad_RightShoulder','Gamepad_DPad_Up')
CONTROLLER_TRAVEL_CHORD=('Gamepad_LeftShoulder','Gamepad_RightShoulder','Gamepad_DPad_Down')
CONTROLLER_DIRECTIONS={
    'Gamepad_DPad_Up':'UP','Gamepad_DPad_Down':'DOWN',
    'Gamepad_DPad_Left':'LEFT','Gamepad_DPad_Right':'RIGHT',
    'Gamepad_LeftStick_Up':'UP','Gamepad_LeftStick_Down':'DOWN',
    'Gamepad_LeftStick_Left':'LEFT','Gamepad_LeftStick_Right':'RIGHT',
}

def _controller_chord(pc):
    return State.controller_enabled and pc is not None and (
        all(key_down(pc,name) for name in CONTROLLER_CHORD) or
        all(key_down(pc,name) for name in LEGACY_CONTROLLER_CHORD))

def _gamepad_edge(pc, name):
    value=key_down(pc,name)
    before=State.controller_last_keys.get(name,False)
    State.controller_last_keys[name]=value
    return value and not before

def _controller_update_focus_outline():
    borders=State.controller_focus_outline
    if len(borders)!=4:return
    idx=State.controller_focus
    if not State.controller_mode or (not State.controller_enabled and State.r10_device!='KEYBOARD') or idx<0 or idx>=len(State.buttons):
        for border in borders:size_position(border,-50,-50,1,1,14)
        return
    entry=State.buttons[idx]
    if entry.get('disabled') or not entry.get('rect'):
        for border in borders:size_position(border,-50,-50,1,1,14)
        return
    x,y,w,h=entry['rect']
    outline=((x-3,y-3,w+6,3),(x-3,y+h,w+6,3),
             (x-3,y-3,3,h+6),(x+w,y-3,3,h+6))
    for border,rect in zip(borders,outline):size_position(border,*rect,14)

def _controller_initial_focus():
    if not State.buttons:return -1
    rect=State.panel_rect
    if rect is None:return 0
    if State.dock_mode=='SIDE':
        # Focus the first real action, never the tiny FULL/X window controls.
        actions=[(i,entry) for i,entry in enumerate(State.buttons)
                 if not entry.get('disabled') and entry.get('rect')
                 and entry['rect'][1]>=rect[1]+124
                 and entry['rect'][1]<rect[1]+rect[3]-120]
        if actions:
            return min(actions,key=lambda item:(item[1]['rect'][1],item[1]['rect'][0]))[0]
    left=rect[0]+min(234.0,max(160.0,rect[2]*.20))+18.0
    candidates=[(i,entry) for i,entry in enumerate(State.buttons)
                if not entry.get('disabled') and entry.get('rect')
                and entry['rect'][0]>=left-4
                and entry['rect'][1]>=rect[1]+210
                and entry['rect'][1]<rect[1]+rect[3]-158]
    if not candidates:
        candidates=[(i,entry) for i,entry in enumerate(State.buttons) if not entry.get('disabled')]
    if not candidates:return -1
    return min(candidates,key=lambda item:(item[1]['rect'][1],item[1]['rect'][0]))[0]

def _controller_focus_direction(direction):
    if direction not in ('UP','DOWN','LEFT','RIGHT') or not State.buttons:return
    idx=State.controller_focus
    if idx<0 or idx>=len(State.buttons) or State.buttons[idx].get('disabled'):
        State.controller_focus=_controller_initial_focus();_controller_update_focus_outline();return
    current=State.buttons[idx]
    if direction in ('LEFT','RIGHT') and current.get('slider') is not None:
        current['slider'].adjust(-1 if direction=='LEFT' else 1);return
    x,y,w,h=current['rect'];cx=x+w/2;cy=y+h/2;candidates=[]
    for i,item in enumerate(State.buttons):
        rect=item.get('rect')
        if i==idx or item.get('disabled') or rect is None:continue
        a,b,c,d=rect;dx=a+c/2-cx;dy=b+d/2-cy
        if direction in ('UP','DOWN'):
            distance=dy if direction=='DOWN' else -dy
            beam=min(x+w,a+c)-max(x,a)>1;cross=abs(dx)
        else:
            distance=dx if direction=='RIGHT' else -dx
            beam=min(y+h,b+d)-max(y,b)>1;cross=abs(dy)
        if distance<=7:continue
        # Prefer the same row/column before jumping into navigation or footers.
        candidates.append(((0 if beam else 1,distance+cross*.35,cross),i))
    if not candidates:return
    State.controller_focus=min(candidates)[1]
    if State.audio_hover:play_ui_sound('hover')
    _controller_update_focus_outline()

def _controller_change_page(step):
    """LB/RB cycles the SIX visible categories, never an obsolete page list.

    Subtools remain directly selectable under each category using D-pad/A.
    This also makes Weekly / Maurice reachable on gamepad, which the previous
    hard-coded list of 18 pages omitted.
    """
    if State.dock_mode=='SIDE':
        modes=('QUICK','TOOLS','FARM','STYLE');dock_view(modes[(modes.index(State.dock_view)+int(step))%4]);return True
    if State.dock_mode=='FULL':
        sections=tuple(STUDIO_SECTIONS)
        current=studio_section_for(State.page)
        studio_open_section(sections[(sections.index(current)+int(step))%len(sections)])
        return True
    categories=tuple(UI_CATEGORY_PAGES)
    if not categories:return False
    current=_ui_category_for(State.page)
    index=categories.index(current) if current in categories else 0
    target=categories[(index+int(step))%len(categories)]
    State.controller_focus=-1
    show_category(target)
    State.controller_focus=_controller_initial_focus()
    _controller_update_focus_outline()
    return True

def _controller_back():
    State.controller_focus=-1
    if State.r10_view is not None and State.numeric_editor is None and not State.help_open:
        State.r10_view=None;redraw();return
    if State.recipe_open and State.numeric_editor is None:recipe_close();return
    if State.farm_view and State.numeric_editor is None:State.farm_view=False;redraw();return
    if State.dock_mode=='SIDE' and State.dock_view!='QUICK' and State.numeric_editor is None:
        dock_view('QUICK');return
    if State.page=='SPAWN' and State.forge_compare_view and State.numeric_editor is None:
        State.forge_compare_view=False;redraw();return
    if State.page=='ARENA' and State.encounter_view=='SEARCH':
        State.encounter_view='CATALOGUE';State.encounter_input=None;redraw();return
    if State.page=='COMBAT' and State.sandbox_view and State.numeric_editor is None:
        if State.sandbox_manage:State.sandbox_manage=False;redraw()
        else:sandbox_toggle()
        return
    if State.page=='LOOT' and State.xp_view and State.numeric_editor is None:
        xp_toggle();return
    if State.profile_name_edit:
        State.profile_name_edit=False;State.profile_name_widget=None;redraw();return
    if State.profile_manage:
        profile_manage_toggle();return
    if State.page=='STYLE' and State.appearance_view!='MAIN':
        appearance_view('MAIN');return
    if State.numeric_editor is not None:
        numeric_cancel()
        return
    if State.page=='STYLE' and State.appearance_draft is not None:
        appearance_cancel()
        show_page('DASHBOARD')
        return
    if State.help_open:
        State.help_open=False
    elif State.style_audio_open:
        State.style_audio_open=False
    elif State.diag_open:
        State.diag_open=False
    elif State.activity_open:
        State.activity_open=False
    elif State.page=='SPAWN' and State.spawn_view=='INSPECT':
        forge_close_inspector()
        return
    elif State.page=='SPAWN' and State.spawn_view=='BLUEPRINTS':
        forge_close_blueprints()
        return
    elif State.page=='SPAWN' and State.spawn_view=='LEVEL':
        State.spawn_pending=None
        State.spawn_view='TOOLS'  # Return to the item that was being tuned.
        State.level_widget=None
    elif State.page=='SPAWN' and State.spawn_view=='SEARCH':
        State.spawn_pending=None
        State.spawn_view='BROWSE'
        State.search_widget=None
    elif State.page=='SPAWN' and State.spawn_view!='BROWSE':
        State.spawn_pending=None
        State.spawn_view='BROWSE'
    elif State.page=='FINDER' and State.finder_mode=='EDIT':
        State.finder_mode='BROWSE'
    elif State.page=='CAPACITY' and State.capacity_view=='EDIT':
        capacity_edit_cancel()
        return
    else:
        close_menu()
        return
    if State.opened:redraw()

def monitor_controller_focus(pc, now):
    """Best-effort, rate-limited gamepad focus watchdog.

    UI-only ownership is requested on open, but some BL4 viewports can still
    shift keyboard focus. Do not steal focus from text editors or mouse users.
    Only act when native focus queries exist and explicitly say it is lost.
    """
    if (not State.opened or not State.controller_mode or State.root is None
            or State.numeric_editor is not None or State.profile_name_edit
            or ((State.page=='SPAWN' and State.spawn_view in ('SEARCH','LEVEL')) or (State.page=='FINDER' and State.finder_mode=='EDIT') or ((State.page=='CAPACITY' and State.capacity_view=='EDIT') or (State.page=='ARENA' and State.encounter_view=='SEARCH')))):
        return
    if now<State.focus_watch_at:return
    State.focus_watch_at=now+.80
    checks=[]
    for method in ('HasUserFocus','HasUserFocusedDescendants'):
        candidate=getattr(State.root,method,None)
        if callable(candidate):
            try:checks.append(bool(candidate(pc)))
            except Exception:pass
    if not checks or any(checks):
        State.focus_loss_count=0
        State.focus_repair_count=0
        return
    State.focus_loss_count+=1
    if State.focus_loss_count>=2:
        # One bounded recapture attempt, not an update every frame.
        if State.focus_repair_count>=2:
            log('INPUT FOCUS LOST REPEATEDLY // Closing CROWN to restore gameplay.')
            close_menu()
        elif recover_ui_focus():
            State.focus_repair_count+=1
            State.focus_loss_count=0
        else:
            close_menu()  # fail closed: don't leave an input-capturing ghost UI

def _clear_native_click_guard():
    State.native_activation_widget=None
    State.native_activation_ignore_until=0.0
    State.native_activation_source=None
    State.native_activation_released_at=None
    State.native_activation_saw_native_press=False


def _arm_native_click_guard(item, now, source='Gamepad_FaceButton_Bottom'):
    """Reserve ONE physical press for ONE logical action.

    Oak2 may surface controller/Enter first through raw polling, then again as
    UMG.Button.IsPressed on *release*. A 350ms time debounce was not adequate
    for long holds, and could apply two irreversible selections. This latch
    tracks the native widget and physical key separately until both settle.
    """
    State.native_activation_widget=item.get('widget')
    State.native_activation_ignore_until=now+30.0  # hard recovery ceiling
    State.native_activation_source=source
    State.native_activation_released_at=None
    State.native_activation_saw_native_press=False
    item['pressed']=False


def _native_release_is_duplicate(item, pc, now, old, pressed):
    """Deduplicate the UMG release after raw A/Enter; never by caption.

    A long hold remains protected even after the original 350ms interval.
    A separate mouse click is allowed once the raw key is up and a short
    native-event settling interval has elapsed. Raw/controller action does
    not itself grant any additional permissions to gameplay operations.
    """
    if item.get('widget') is not State.native_activation_widget:
        return False
    if State.native_activation_ignore_until<=0 or now>=State.native_activation_ignore_until:
        _clear_native_click_guard()
        return False
    if pressed:
        State.native_activation_saw_native_press=True
    source=State.native_activation_source
    source_down=bool(source and key_down(pc,source))
    if source_down:
        State.native_activation_released_at=None
    elif State.native_activation_released_at is None:
        State.native_activation_released_at=now
    if old and not pressed:
        # Every native release belonging to this one raw press is consumed.
        # Do NOT clear on the first release while the physical key remains down.
        # Keep a short post-release latch for duplicate native callbacks.
        # The next genuine controller press arms a NEW logical action instead.
        State.duplicate_native_releases_blocked+=1
        return True
    release_at=State.native_activation_released_at
    if release_at is not None and not pressed and now-release_at>=0.65:
        _clear_native_click_guard()
    return False

def controller_ui_tick(pc,now):
    if not State.controller_enabled:return
    # Sample all keys in one pass: simultaneous navigation and confirm inputs
    # must NEVER defer an unobserved A edge into the next frame.
    tracked=(*CONTROLLER_DIRECTIONS,*CONTROLLER_CHORD,'Gamepad_FaceButton_Bottom',
             'Gamepad_FaceButton_Right','Gamepad_LeftShoulder','Gamepad_RightShoulder','Gamepad_LeftTrigger','Gamepad_RightTrigger')
    pressed={key:key_down(pc,key) for key in tracked}
    edges={key:pressed[key] and not State.controller_last_keys.get(key,False) for key in tracked}
    State.controller_last_keys.update(pressed)
    if now<State.controller_open_block_until:return
    both_sticks=all(pressed[k] for k in CONTROLLER_CHORD)
    if both_sticks:
        if not State.controller_open_latched:
            if State.controller_hold_start<=0:
                State.controller_hold_start=now
            elif now-State.controller_hold_start>=.72:
                State.controller_open_latched=True
                close_menu()
        return
    State.controller_hold_start=0.0
    State.controller_open_latched=False
    # Reject simultaneous controls; never repeat D-pad while shoulders or
    # A/B are held. This stops a hold-to-open combo turning into a selection.
    logical_directions={CONTROLLER_DIRECTIONS[k] for k,v in pressed.items() if v and k in CONTROLLER_DIRECTIONS}
    other_buttons=sum(bool(v) for k,v in pressed.items() if k not in CONTROLLER_DIRECTIONS)
    if len(logical_directions)+other_buttons>1:
        State.controller_repeat_key=None
        State.controller_repeat_due=0.0
        return
    for key,direction in CONTROLLER_DIRECTIONS.items():
        if not pressed[key]:continue
        repeat=(State.controller_repeat_key==direction and now>=State.controller_repeat_due)
        if edges[key] or repeat:
            State.controller_mode=True;State.r10_device='CONTROLLER'
            if State.root is not None:attempt(State.root,'SetUserFocus',pc)
            _controller_focus_direction(direction)
            State.controller_repeat_key=direction
            State.controller_repeat_due=now+(.14 if repeat else .42)
            return
    if State.controller_repeat_key and State.controller_repeat_key not in logical_directions:
        State.controller_repeat_key=None
        State.controller_repeat_due=0.0
    if edges['Gamepad_FaceButton_Right']:
        State.controller_mode=True;State.r10_device='CONTROLLER'
        _controller_back()
        return
    if edges['Gamepad_LeftShoulder']:
        State.controller_mode=True;State.r10_device='CONTROLLER'
        _controller_change_page(-1)
        return
    if edges['Gamepad_RightShoulder']:
        State.controller_mode=True;State.r10_device='CONTROLLER'
        _controller_change_page(1)
        return
    if edges['Gamepad_FaceButton_Bottom']:
        State.controller_mode=True;State.r10_device='CONTROLLER'
        idx=State.controller_focus
        if idx<0 or idx>=len(State.buttons):
            State.controller_focus=_controller_initial_focus()
            _controller_update_focus_outline()
            return
        item=State.buttons[idx]
        if item.get('disabled'):return
        caption=str(item.get('name','')).upper()
        cue='warn' if 'KILL' in caption or 'CLEAR ENEMIES' in caption else ('confirm' if 'CONFIRM' in caption else 'select')
        play_ui_sound(cue)
        _arm_native_click_guard(item,now,'Gamepad_FaceButton_Bottom')
        try:item['run']()
        except Exception as error:log('GAMEPAD ACTION FAILED // '+str(error)[:80])
        return

def controller_watch_tick(*args):
    # The always-enabled watcher also retires cosmetic, hit-test-invisible
    # notifications; the rest remains read-only when CROWN is closed.
    now=time.monotonic()
    bonus_tick(now)
    r13_arena_tick(now)
    if State.toast_widget is not None or State.toast_queue:_toast_tick(now)
    if State.hud_visible and now-State.hud_refresh_at>=0.8:
        State.hud_refresh_at=now
        update_hud()
    if State.opened or not State.controller_enabled:return
    if now-State.controller_poll_last<1/30:return
    State.controller_poll_last=now
    pc=get_pc(possibly_loading=True)
    travel_chord=(State.controller_enabled and pc is not None and all(
        key_down(pc,name) for name in CONTROLLER_TRAVEL_CHORD))
    if not (_controller_chord(pc) or travel_chord):
        State.controller_hold_start=0.0
        State.controller_open_latched=False
        return
    if State.controller_open_latched:return
    if State.controller_hold_start<=0:
        State.controller_hold_start=now
        return
    if now-State.controller_hold_start<.72:return
    State.controller_open_latched=True
    State.controller_open_block_until=now+.42
    State.controller_mode=True
    State.controller_focus=-1
    if travel_chord:
        State.page='WAYPOINTS'
        State.nav_group='VAULT'
        State.waypoint_mode='TRAVEL'
    open_menu()
    if State.opened:
        State.controller_focus=_controller_initial_focus()
        _controller_update_focus_outline()

def install_controller_hook():
    if State.controller_watcher_installed:return
    try:
        add_hook(HOOK,Type.POST,GAMEPAD_HOOK_ID,controller_watch_tick)
        State.controller_watcher_installed=True
    except Exception as error:
        State.controller_watcher_installed=False
        log('GAMEPAD BACKGROUND HOOK UNAVAILABLE // F7 still works: '+str(error)[:45])

def uninstall_controller_hook():
    try:remove_hook(HOOK,Type.POST,GAMEPAD_HOOK_ID)
    except Exception:pass
    State.controller_watcher_installed=False
    State.controller_hold_start=0.0
    State.controller_open_latched=False
    State.controller_last_keys={}

def _session_anchor():
    world,_=world_and_state()
    actor=pawn()
    if world is None or actor is None:
        return None
    def key(obj):
        address=_native_address(obj)
        if address is not None:return ('native',address)
        try:
            path=obj._path_name()
            if isinstance(path,str) and path:return ('path',path)
        except Exception:pass
        # Test doubles and SDKs without native addresses: don't key by a
        # mutable repr whose text changes after normal player/world actions.
        return ('object',id(obj))
    return (key(world), key(actor), map_tag())

def _invalidate_pending_session(reason):
    if State.hud_visible:hide_hud() # never keep stale UMG widgets after travel
    _dismiss_toast(clear_queue=True)
    State.toast_render_failed=False # map loads may replace valid UMG implementations
    State.spawn_pending=None
    State.spawn_expires=0.0
    State.spawn_view="BROWSE"
    State.spawn_page=0
    State.search_widget=None
    State.level_widget=None
    State.wallet_pending=None
    State.wallet_expires=0.0
    State.xp_external_confirm=None
    State.confirm_kill_until=0.0
    State.last_confirm_action=''
    State.last_confirm_expires=0.0
    State.party_grant_armed=False
    State.friend_teleport_confirm=0.0
    State.friend_teleport_target=None
    State.friend_teleport_anchor=None
    State.coop_last_status='SESSION CHANGED / recheck friends'
    State.travel_save_pending=None
    State.travel_save_expires=0.0
    State.travel_cooldown_until=0.0
    State.checkpoint_return=None
    State.party_approved=False
    State.party_approved_roster=None
    State.party_selected=None
    State.party=[]
    State.session_resets+=1
    # Keep no capacities, original baselines or live bridge permissions from a
    # previous character/map. An in-flight thread cannot be cancelled after
    # sending, but its eventual reply must never be applied to the new session.
    State.capacity_bridge_generation+=1
    State.capacity_bridge_job=None
    State.capacity_readback.clear()
    State.capacity_occupied.clear()
    State.capacity_readback_anchor=None
    State.capacity_readback_at=0.0
    State.capacity_bag_original=None
    State.capacity_bank_original=None
    State.capacity_confirm=None
    State.capacity_confirm_until=0.0
    State.capacity_status='SESSION CHANGED / recheck bridge and inventory'
    # Previous character/world values can no longer safely be restored.
    # Never dereference stale Unreal wrappers after travel.
    State.saved_char=None
    State.damage_original=None
    State.collision_original=None
    State.world_saved=None
    State.world_original=None
    State.world_last=None
    State.fov_saved=None
    State.fov_original=None
    State.fov_last=None
    State.motion_owner=None
    State.motion_originals={}
    State.motion_last={}
    State.fov_last=None
    State.world_last=None
    State.remote_originals={}
    State.art_textures.clear()
    State.art_failed.clear()
    State.art_fail_reasons.clear()
    State.art_drawn_count=0
    State.art_status="SHAPES / session reset"
    State.god=State.noclip=State.target_off=False
    State.active_event='NONE'
    State.motion_scale=1.0
    State.jump_selected=State.gravity_selected=1.0
    State.fov_selected=None
    current_pc=get_pc(possibly_loading=True)
    if current_pc is None:
        # No valid controller during travel; don't dereference the old wrapper.
        State.input_pc=None
        State.input_saved=None
        State.input_move_ignored_original=None
        State.input_look_ignored_original=None
        State.input_guard_confirmed=False
        State.input_mode_owned=False
    elif State.input_pc is None or not same_unreal_object(current_pc,State.input_pc):
        # Ownership belongs to the ORIGINAL controller only. The replacement
        # may be in a cutscene, cinematic, map transition, or loading screen;
        # never set GameOnly or modify bBlockInput/cursor flags on that object.
        # The old UMG is removed by close_menu without touching the new PC.
        State.input_pc=None
        State.input_saved=None
        State.input_move_ignored_original=None
        State.input_look_ignored_original=None
        State.input_guard_confirmed=False
        State.input_mode_owned=False
        State.input_last_status='CONTROLLER REPLACED / NEW PC UNTOUCHED'
    close_menu()
    log('SESSION CHANGED // '+reason+'; pending actions canceled. Open F7 again.')

def _tick_impl(*args):
    if not State.opened:return
    capacity_consume_result()
    now=time.monotonic()
    if now-State.last_poll < 1/60:return
    # A long suspended game frame can skip every background tick; guard the
    # first resumed frame even if no explicit foreground-loss event was seen.
    if State.last_poll>0 and now-State.last_poll>1.0 and not State.foreground_suspended:
        State.foreground_suspended=True
    State.last_poll=now
    pc=get_pc(possibly_loading=True)
    if _menu_foreground_guard(pc,now):return
    if not r3_input_watch(pc,now):return
    if now-State.viewport_last_check>1.0:
        State.viewport_last_check=now
        try:
            actual=viewport()
            signature=(round(float(actual[0]),1),round(float(actual[1]),1))
            if State.viewport_signature is not None and signature!=State.viewport_signature:
                log('DISPLAY CHANGED // Resizing CROWN to fit the new viewport.')
                redraw()
                if not State.opened:return
                return
        except Exception:
            pass  # A transient loading viewport is never a reason to crash.
    if now-State.session_last_check>0.75:
        State.session_last_check=now
        current=_session_anchor()
        if current is None or State.session_anchor != current:
            _invalidate_pending_session('map, character or loading state changed')
            return
    # SDK keybinds may not receive keyboard events while UMG owns input.
    if State.input_pc is not None and not same_unreal_object(pc,State.input_pc):
        _invalidate_pending_session('player controller changed')
        return
    f6=key_down(pc,"F6")
    if f6 and not State.f6_down:
        State.f6_down=True
        close_menu()
        return
    State.f6_down=f6
    f11=key_down(pc,'F11')
    if f11 and not State.f11_down:
        State.f11_down=True
        toggle_dock_mode()
        return
    State.f11_down=f11
    esc=key_down(pc,'Escape')
    if esc and not State.esc_down:
        State.esc_down=True
        _controller_back()
        return
    State.esc_down=esc
    # Enter applies the current SEARCH, LEVEL or CAPACITY editor only. It cannot grant
    # items, trigger the quick bar, or operate outside these safe editors.
    if r10_input_tick(pc,now):return
    enter=key_down(pc,'Enter') or key_down(pc,'Return')
    if enter and not State.editor_enter_down:
        if State.page=='ARENA' and State.encounter_view=='SEARCH':
            State.editor_enter_down=True;encounter_search();return
        if State.profile_name_edit:
            State.editor_enter_down=True;profile_rename_apply();return
        if State.page=='FINDER' and State.finder_mode=='EDIT':
            State.editor_enter_down=True;apply_finder_search();return
        if State.numeric_editor is not None:
            State.editor_enter_down=True
            numeric_apply()
            return
        if State.page=='CAPACITY' and State.capacity_view=='EDIT':
            State.editor_enter_down=True
            capacity_apply_text()
            return
        if State.page=='SPAWN' and State.spawn_view=='SEARCH':
            State.editor_enter_down=True
            forge_apply_search()
            return
        if State.page=='SPAWN' and State.spawn_view=='LEVEL':
            State.editor_enter_down=True
            forge_apply_level()
            return
    if (enter and not State.editor_enter_down and
            not (((State.page=='SPAWN' and State.spawn_view in ('SEARCH','LEVEL')) or (State.page=='FINDER' and State.finder_mode=='EDIT') or ((State.page=='CAPACITY' and State.capacity_view=='EDIT') or (State.page=='ARENA' and State.encounter_view=='SEARCH'))))):
        idx=State.controller_focus
        if 0<=idx<len(State.buttons) and not State.buttons[idx]['disabled']:
            item=State.buttons[idx]
            _arm_native_click_guard(item,now,'Enter')
            try:item['run']()
            except Exception as err:log('KEYBOARD SELECTION FAILED // '+str(err)[:90])
            State.editor_enter_down=True
            return
    State.editor_enter_down=enter
    if State.numeric_editor is None and not State.profile_name_edit and not (((State.page=='SPAWN' and State.spawn_view in ('SEARCH','LEVEL')) or (State.page=='FINDER' and State.finder_mode=='EDIT') or ((State.page=='CAPACITY' and State.capacity_view=='EDIT') or (State.page=='ARENA' and State.encounter_view=='SEARCH')))):
        for name,direction in (('Up','UP'),('Down','DOWN'),('Left','LEFT'),('Right','RIGHT')):
            held=key_down(pc,name)
            if held and not State.arrow_keys_down.get(name,False):
                State.controller_mode=True;State.r10_device='KEYBOARD'
                if State.controller_focus<0:State.controller_focus=_controller_initial_focus()
                else:_controller_focus_direction(direction)
                _controller_update_focus_outline()
            State.arrow_keys_down[name]=held
    f7=key_down(pc,"F7")
    if f7 and not State.f7_down:
        State.f7_down=True
        close_menu()
        return
    State.f7_down=f7
    f8=key_down(pc,'F8')
    if f8 and not State.f8_down:
        State.f8_down=True
        travel_hub()
        return
    State.f8_down=f8
    f9=key_down(pc,'F9')
    if f9 and not State.f9_down:
        State.f9_down=True
        # @keybind replaces the Python function with a KeybindType object.
        # Calling focus_hotkey() here throws under real mods_base. Dispatch
        # through the undecorated action shared by SDK and raw F9 paths.
        _focus_recovery_action()
        if not State.opened:return
    State.f9_down=f9
    f10=key_down(pc,'F10')
    if f10 and not State.f10_down:
        State.f10_down=True
        reset_all()
        return
    State.f10_down=f10
    controller_ui_tick(pc,now)
    if not State.opened or State.redraw_pending:return
    monitor_controller_focus(pc,now)
    if not State.opened:return
    if _maybe_warmup_art(now):return
    update_mouse_cursor_aid(pc,now)
    if _poll_move(pc):return
    mouse_pressed=key_down(pc,'LeftMouseButton')
    for ref in list(State.sliders):
        if ref.generation!=State.frame_generation:continue
        try:
            value=ref.validate(ref.widget.GetValue())
            if value is None:continue
            if abs(value-ref.value)>.005:
                ref.value=value
                if ref.label is not None:
                    ref.label.SetText(ref.display(value))
                ref.update_fill(value)
                ref.dragged=True
            if ref.dragged and not mouse_pressed:
                ref.dragged=False
                _slider_apply_checked(ref,value)
                return
        except Exception as e:
            log('Slider disabled on this SDK: '+str(e))
            State.sliders.remove(ref)
    # Hover is informational. 15 Hz is plenty and saves dozens of UMG
    # IsHovered bridge calls per second on 18-page, art-heavy layouts.
    if now-State.hover_poll_last>=1/15:
        State.hover_poll_last=now
        poll_hover_help()
    for item in tuple(State.buttons):
        if item.get('disabled'):continue
        try:pressed=bool(item["widget"].IsPressed())
        except Exception:continue
        old=item["pressed"]
        item["pressed"]=pressed
        if item.get('widget') is State.native_activation_widget and not (old and not pressed):
            _native_release_is_duplicate(item,pc,now,old,pressed)
        if old and not pressed:
            if _native_release_is_duplicate(item,pc,now,old,pressed):
                item['pressed']=False
                continue
            State.controller_mode=False;State.r10_device='MOUSE'
            State.hovered_control=None  # force hover/focus visual update
            _controller_update_focus_outline()
            caption=str(item.get('name','')).upper()
            cue='warn' if ('KILL' in caption or 'CLEAR ENEMIES' in caption) else ('confirm' if 'CONFIRM' in caption else 'select')
            play_ui_sound(cue)
            try:item["run"]()
            except Exception as e:log("Control failed: "+str(e))
            break

def tick(*args):
    if not State.opened:return
    State.polling_ui=True
    try:
        _tick_impl(*args)
    finally:
        State.polling_ui=False
    if State.opened and State.redraw_pending:
        State.redraw_pending=False
        redraw()
    if State.opened:echo_scan_tick()
    if State.opened and State.transition_canvas is State.canvas and not State.reduced_motion:
        progress=min(1.0,max(0.0,(time.monotonic()-State.transition_started)/State.transition_duration))
        call(State.canvas,'SetRenderOpacity',.82+.18*(1-(1-progress)**3))
        if progress>=1:State.transition_canvas=None

def open_menu():
    if State.noclip_boost_active:release_noclip_flight_boost()
    if State.opened:return
    pc=get_pc(possibly_loading=True)
    if pc is None or pawn() is None:
        log("Load a playable character before pressing F7.")
        return
    try:
        ui=create("/Script/UMG.UserWidget",pc)
        if ui is None: raise RuntimeError("UMG UserWidget creation returned None")
        tree=create("/Script/UMG.WidgetTree",ui)
        if tree is None: raise RuntimeError("UMG WidgetTree creation returned None")
        ui.WidgetTree=tree
        root=create("/Script/UMG.CanvasPanel",tree)
        if root is None: raise RuntimeError("UMG CanvasPanel creation returned None")
        tree.RootWidget=root
        State.root=ui
        State.tree=tree
        State.opened=True
        State.art_warmup_steps=0
        State.art_warmup_due=0.0
        _mark_menu_opened()
        State.f7_down=True  # Ignore opening key until released.
        State.f6_down=False
        State.f10_down=False
        State.f9_down=False
        State.f8_down=False
        State.foreground_suspended=False
        State.foreground_resume_after=0.0
        State.controller_last_keys={}
        call(ui,"SetAlignmentInViewport",v2(0,0))
        call(ui,"SetPositionInViewport",v2(0,0),False)
        call(ui,"SetDesiredSizeInViewport",v2(*viewport()))
        call(ui,"SetVisibility",0)
        call(root,"SetVisibility",0)
        # A focused UMG root helps GameAndUIEx keep controller/keyboard focus.
        # Unsupported Oak2 versions ignore these optional hints.
        try:ui.bIsFocusable=True
        except Exception:pass
        call(root,"SetIsEnabled",True)
        if not attempt(ui,"AddToViewport",999995):
            raise RuntimeError("Native UMG AddToViewport failed")
        new_anchor=_session_anchor()
        if State.session_anchor is not None and State.session_anchor!=new_anchor:
            # Menu may be closed across character or map loads. Never reuse a
            # last-position return from a different character/session.
            State.checkpoint_return=None
            State.travel_recovery_anchor=None
            State.travel_cooldown_until=0.0
            State.travel_save_pending=None
            State.travel_save_expires=0.0
        State.session_anchor=new_anchor
        State.session_last_check=time.monotonic()
        if State.session_anchor is None:
            raise RuntimeError('Session identity unavailable; F7 requires a playable map')
        State.party=party_entries()
        State.party_approved=False
        State.party_approved_roster=None
        State.party_selected=None
        State.friend_teleport_confirm=0.0
        State.friend_teleport_target=None
        State.friend_teleport_anchor=None
        redraw()
        if not State.draw_ok or State.canvas is None or len(State.buttons)<8:
            raise RuntimeError("Native menu failed to create controls")
        save_input(pc)
        State.focus_watch_at=time.monotonic()+.75
        State.focus_loss_count=0
        State.focus_repair_count=0
        # Native focus is best-effort. Never claim that API acceptance is a
        # verified game-input lock until the user's BL4 session confirms it.
        attempt(ui,'SetUserFocus',pc)
        attempt(ui,'SetKeyboardFocus')
        log('INPUT / UI-ONLY requested (not game-verified). F6 emergency close.')
        if not State.controller_mode:
            attempt(ui,'SetUserFocus',pc)
        add_hook(HOOK,Type.POST,HOOK_ID,tick)
        State.hook_active=True
        log("CROWNs Freedom // Welcome to the black market.")
        play_ui_sound('open')
    except Exception as e:
        record_runtime_fault('MENU_OPEN',e)
        # Preserve the actionable safety warning without leaking arbitrary
        # engine exception text, which may contain profile or file paths.
        warning=('SAFE INPUT UNAVAILABLE / UIOnly was refused'
                 if 'SAFE INPUT UNAVAILABLE' in str(e) else type(e).__name__)
        log('Native menu could not open: '+warning)
        close_menu()

@keybind("CROWNs Freedom - Hold Noclip Boost", "F5", event_filter=None)
def flight_hotkey(event):
    boost_hotkey_event(event)

@keybind("CROWNs Freedom - Open/Close", "F7")
def toggle():
    close_menu() if State.opened else open_menu()

@keybind("CROWNs Freedom - Toggle Side Dock", "F11")
def dock_hotkey():
    if not State.opened:
        State.dock_mode='SIDE'
        open_menu()
    else:
        toggle_dock_mode()
    State.f11_down=True

@keybind("CROWNs Freedom - Travel Hub", "F8")
def open_travel_hub():
    travel_hub()

def _focus_recovery_action():
    """Dispatchable F9 action shared by native and raw input paths.

    mods_base.keybind decorates this with a KeybindType, which is *not*
    callable. Keep raw polling free of decorated-object invocation.
    """
    now=time.monotonic()
    if now-State.f9_last_action<0.35:return False
    State.f9_last_action=now
    if State.opened:
        return recover_ui_focus()
    return export_qa_report()

@keybind("CROWNs Freedom - Recover Input Focus / Export Diagnostics", "F9")
def focus_hotkey():
    return _focus_recovery_action()

@keybind("CROWNs Freedom - Unstuck", "F6")
def emergency():
    close_menu()
    log("Native UI closed; game input restored.")

def _cleanup_safely(stage,action):
    """A broken optional cleanup must never skip later input restoration."""
    try:
        action()
        return True
    except Exception as error:
        record_runtime_fault(stage,error)
        try:logging.info('[CROWNs Freedom] CLEANUP '+stage+' / '+type(error).__name__)
        except Exception:pass
        return False

def reset_all():
    release_noclip_flight_boost()
    _dismiss_toast(clear_queue=True)
    # Input release is the first priority. A bad HUD or weapon API must not
    # strand native UI focus or prevent subsequent restoration attempts.
    if not _cleanup_safely('RESET_CLOSE',close_menu):
        _cleanup_safely('RESET_INPUT_FALLBACK',release_input)
        _cleanup_safely('RESET_MARKER_FALLBACK',_clear_menu_marker)
    _cleanup_safely('RESET_HUD',hide_hud)
    _cleanup_safely('RESET_WALLET',wallet_clear)
    State.spawn_pending=None
    State.active_event='NONE'
    _cleanup_safely('RESET_EFFECTS',restore)

@keybind("CROWNs Freedom - Restore", "F10")
def restore_hotkey():
    reset_all()

def on_disable():
    _cleanup_safely('DISABLE_FLIGHT',release_noclip_flight_boost)
    _cleanup_safely('DISABLE_TOAST',lambda:_dismiss_toast(clear_queue=True))
    if not _cleanup_safely('DISABLE_CLOSE',close_menu):
        _cleanup_safely('DISABLE_INPUT_FALLBACK',release_input)
        _cleanup_safely('DISABLE_MARKER_FALLBACK',_clear_menu_marker)
    _cleanup_safely('DISABLE_HOOK',uninstall_controller_hook)
    _cleanup_safely('DISABLE_HUD',hide_hud)
    State.wallet_pending=None
    State.spawn_pending=None
    State.active_event='NONE'
    _cleanup_safely('DISABLE_EFFECTS',restore)
    _dismiss_toast(clear_queue=True) # suppress stale messages after re-enable

def _valid_accent(value):
    if value is None:return None
    if not isinstance(value,str) or len(value)!=7 or value[0]!='#' or any(c not in '0123456789abcdefABCDEF' for c in value[1:]):
        raise ValueError('Use #RRGGBB for an accent colour')
    return value.upper()

def _appearance_extra_validate(data):
    if not isinstance(data,dict):raise ValueError('Expected appearance settings')
    result={}
    for key,lo,hi,default in (('background',.2,1.,.75),('duration',.08,.4,.16)):
        value=data.get(key,default)
        if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:raise ValueError('Invalid '+key)
        result[key]=float(value)
    result['accent']=_valid_accent(data.get('accent'))
    return result

def appearance_view(name):
    if name not in ('MAIN','THEMES','COLOURS'):return False
    State.appearance_view=name;redraw();return True

def appearance_choose_theme(index):
    if type(index) is not int or not 0<=index<len(THEMES):return False
    appearance_stage('theme',index);redraw();return True

def appearance_channel(channel,value):
    if type(channel) is not int or channel not in (0,1,2):return False
    if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=255:return False
    draft=appearance_begin()
    accent=draft.get('accent') or THEMES[draft['theme']]['accent']
    channels=[int(accent[i:i+2],16) for i in (1,3,5)]
    channels[channel]=int(round(value))
    return appearance_stage('accent','#%02X%02X%02X'%tuple(channels))

def draw_appearance_extras(layout,left,y,width,half,info):
    draft=appearance_begin();xx=left+half+12
    if State.appearance_view=='THEMES':
        for i,theme in enumerate(THEMES):
            btn(layout,theme['name'],left+(i%2)*(half+12),y+(i//2)*45,half,37,
                lambda n=i:appearance_choose_theme(n),active=draft['theme']==i,small=True)
        btn(layout,'BACK TO STUDIO',xx,y+180,half,37,lambda:appearance_view('MAIN'),small=True)
        text(layout,'Choose directly / '+THEMES[draft['theme']]['name'],left,y+220,width,24,theme_color('dim'),.65)
    else:
        accent=draft.get('accent') or THEMES[draft['theme']]['accent']
        for i,name in enumerate(('RED','GREEN','BLUE')):
            slider(layout,'ACCENT '+name,int(accent[1+i*2:3+i*2],16),0,255,left,y+i*83,half,
                lambda v,c=i:appearance_channel(c,v))
        slider(layout,'BACKGROUND OPACITY',draft['background'],.2,1.,xx,y,half,lambda v:appearance_stage('background',v))
        slider(layout,'FADE SECONDS',draft['duration'],.08,.4,xx,y+83,half,lambda v:appearance_stage('duration',v))
        btn(layout,'USE THEME ACCENT',xx,y+173,half,32,lambda:(appearance_stage('accent',None),redraw()),small=True)
        btn(layout,'BACK / '+accent,xx,y+213,half,28,lambda:appearance_view('MAIN'),small=True)
    cw=(width-16)/3
    for i,(label,fn) in enumerate((('APPLY',appearance_apply),('CANCEL',appearance_cancel),('RESET DRAFT',appearance_reset))):
        btn(layout,label,left+i*(cw+8),y+252,cw,39,fn,active=i==0,small=True)
    if State.panel_rect[3]>=900:
        py=y+335;ph=min(195.,State.panel_rect[1]+State.panel_rect[3]-185-py)
        if ph>=125:
            pal=dict(_THEME_RGBA[draft['theme']]);accent=_hex(draft.get('accent') or THEMES[draft['theme']]['accent'])
            box(layout,left+5,py+6,width,ph,(0.,0.,0.,.25),7)
            panel=box(layout,left,py,width,ph,pal['panel'][:3]+(draft['opacity'],),8)
            optional_art_image(layout,'NEON_CIRCUITS',left+8,py+5,width-16,ph-10,z=8,opacity=.12)
            box(layout,left,py,4,ph,accent,9)
            title=text(layout,'YOUR ECHO / '+THEMES[draft['theme']]['name'],left+23,py+16,width-46,36,pal['text'],.95,13)
            text(layout,'ACCENT / '+(draft.get('accent') or THEMES[draft['theme']]['accent'])+'    BACKDROP / %d%%'%round(draft['background']*100),left+23,py+61,width-46,26,pal['highlight'],.72,13)
            for i,col in enumerate((pal['bg'],pal['panel'],accent,pal['highlight'],pal['text'])):
                sw=(width-70)/5;box(layout,left+23+i*(sw+6),py+105,sw,27,col,12)
            State.appearance_preview={'panel':panel,'title':title}

def _slider_apply_checked(ref,value):
    if ref.generation!=State.frame_generation or ref not in State.sliders or not State.opened:return False
    value=ref.validate(value)
    if value is None:return False
    previous=ref.committed
    if abs(value-previous)<.000001:
        ref.value=previous;call(ref.widget,'SetValue',previous);ref.update_fill(previous)
        return True
    try:result=ref.apply(value)
    except Exception as error:
        record_runtime_fault('SLIDER_APPLY',error);log('VALUE FAILED // '+type(error).__name__);result=False
    ref.value=previous if result is False else value
    ref.committed=ref.value
    if ref.generation==State.frame_generation:
        call(ref.widget,'SetValue',ref.value);call(ref.label,'SetText',ref.display(ref.value));ref.update_fill(ref.value)
    if result is False:log('VALUE REJECTED // '+State.message)
    elif ref.generation==State.frame_generation:echo_feedback('slider')
    return result is not False

def _ui_batch(action):
    """One callback transaction, including actions called outside the UI poll."""
    prior=State.polling_ui;State.polling_ui=True
    try:return action()
    finally:
        State.polling_ui=prior
        if not prior and State.opened and State.redraw_pending:
            State.redraw_pending=False;redraw()

def _forge_numeric_stage(kind,value):
    if kind not in ('level','count'):return False
    lo,hi=(1,100) if kind=='level' else (1,3)
    if type(value) not in (int,float) or not math.isfinite(value) or value!=int(value) or not lo<=value<=hi:return False
    if kind=='level':State.spawn_level=int(value)
    else:State.spawn_count=int(value)
    State.spawn_pending=None;State.spawn_expires=0.
    State.forge_blueprint_pending=None;State.forge_blueprint_pending_until=0.
    State.forge_stage='STAGED_NOT_SPAWNED'
    log('FORGE // '+kind.upper()+' staged; confirmation cleared. No item created.')
    return True

def r14_forge_status():
    """Truthful human-facing status. This never queries or mutates a live item pool."""
    if getattr(State,'forge_uncertain_anchor',None)==_session_anchor() and State.forge_uncertain_anchor is not None:
        return ('UNRESOLVED NATIVE REQUEST','Possible partial item drop. Do not retry in this session; inspect the ground.')
    if State.spawn_pending is not None and time.monotonic()<State.spawn_expires:
        return ('AWAITING SECOND CONFIRMATION','Same selection, level, quantity and character required. No item sent yet.')
    states={
        'READY_NOT_SPAWNED':('BACKEND PREFLIGHT PASSED','An item-pool API was found. That is not proof an item can be created.'),
        'REQUEST_SENT_NOT_VERIFIED':('REQUEST DISPATCHED','Look for the item on the ground. No item receipt or inventory delivery verified.'),
        'STAGED_NOT_SPAWNED':('DRAFT ONLY','Changes are staged locally. A separate confirmation is required.'),
        'COOLDOWN':('WAIT BEFORE ANOTHER REQUEST','A brief request cooldown is active. No new request was sent.'),
        'NOT_CHECKED':('BACKEND NOT CHECKED','Select an item and run Check Readiness before requesting a drop.'),
        'SDK_EXCEPTION_PARTIAL_POSSIBLE':('NATIVE RESULT UNCERTAIN','A call failed and might have spawned items. Check the ground; do not retry.'),
        'BLOCKED_NOT_SOLO':('SOLO REQUIRED','Forge requests are blocked in multiplayer.'),
        'POOL_API_UNAVAILABLE':('ITEM API UNAVAILABLE','The reviewed native item-pool method was not found.'),
    }
    if State.forge_stage in states:return states[State.forge_stage]
    return ('REQUEST BLOCKED / '+State.forge_stage.replace('_',' ')[:36],
            'No verified delivery. Check session, character, item, and native backend.')

def forge_recover_catalogue():
    """Return to the complete local catalogue without touching BL4 or old requests."""
    State.spawn_search='';State.spawn_search_draft=''
    State.spawn_category_idx=SPAWN_CATEGORIES.index('ALL')
    State.spawn_page=0;State.spawn_view='BROWSE'
    State.spawn_pool_idx=0 if SPAWN_POOLS else -1
    State.search_widget=None
    State.spawn_pending=None;State.spawn_expires=0.
    State.forge_blueprint_pending=None;State.forge_blueprint_pending_until=0.
    # Never clear forge_uncertain_anchor, historical request ledger or native quarantine.
    State.forge_stage='STAGED_NOT_SPAWNED'
    log('FORGE / CATALOGUE RESET // Local filters cleared. No item request sent.')
    if State.opened:redraw()
    return True

def draw_forge_workspace(layout,left,y,width,height):
    if State.forge_compare_view:return draw_forge_comparison(layout,left,y,width)
    item=_forge_selection()
    if item is None:
        text(layout,'NO ITEMS MATCH THIS FILTER',left+10,y+10,width-20,42,theme_color('highlight'),.96)
        text(layout,'No item is selected. Clear the local search/category to return to the Forge catalogue. No game request will be sent.',left+10,y+65,width-20,78,theme_color('text'),.80)
        btn(layout,'SHOW ALL ITEMS',left+10,y+155,max(130.,width-20),40,forge_recover_catalogue,small=True)
        return
    optional_art_image(layout,'R9_FORGE',left,y,width,76,z=8,opacity=.64)
    box(layout,left,y,3,76,theme_color('accent'),9)
    text(layout,item[0],left+16,y+5,width-32,36,theme_color('accent'),1.02,13)
    text(layout,item[2]+' / ITEM POOL',left+16,y+46,width-32,27,theme_color('dim'),.78,13)
    half=(width-12)/2;cw=(width-16)/3
    slider(layout,'ITEM LEVEL',State.spawn_level,1,100,left,y+84,half,lambda v:_forge_numeric_stage('level',v))
    slider(layout,'QUANTITY',State.spawn_count,1,3,left+half+12,y+84,half,lambda v:_forge_numeric_stage('count',v))
    pending=State.spawn_pending is not None and time.monotonic()<State.spawn_expires
    actions=(('FIND ITEM',forge_toggle_view),('COMPARE',lambda:(setattr(State,'forge_compare_view',True),redraw())),
             ('CONFIRM REQUEST' if pending else 'REQUEST ITEM',spawn_request),
             ('BLUEPRINTS',forge_open_blueprints),('UNFAVOURITE' if item[1] in State.spawn_favorites else 'FAVOURITE',toggle_spawn_favorite),
             ('CANCEL REQUEST',lambda:(spawn_clear(),redraw())))
    for i,(label,fn) in enumerate(actions):
        btn(layout,label,left+(i%3)*(cw+8),y+174+(i//3)*45,cw,36,fn,small=True,danger=i==2)
    heading,detail=r14_forge_status()
    text(layout,heading,left+10,y+262,width-214,27,theme_color('highlight'),.83)
    btn(layout,'CHECK READINESS',left+width-198,y+262,192,32,forge_preflight,small=True)
    text(layout,detail,left+10,y+298,width-20,32,theme_color('text'),.75)
    if height>=830:
        last=State.forge_request_history[-1] if State.forge_request_history else None
        history=('LAST REQUEST / '+str(last.get('status','UNKNOWN'))+' / '+str(last.get('quantity',0))+' pool calls' if isinstance(last,dict) else 'NO REQUEST HISTORY')
        note_panel(layout,history,State.spawn_last+'\nNo verified item identity, thumbnail, ground pickup, or inventory receipt. Compare shows curated pool information only.',left,y+339,width,122)
    if height>=1000:
        text(layout,'SAVED BLUEPRINTS',left,y+493,width-260,28,theme_color('highlight'),.84)
        btn(layout,'INSPECT OWNED WEAPONS',left+width-252,y+487,252,34,r16_inspect_owned_weapons,small=True)
        valid=_validated_forge_blueprints(State.forge_blueprints)
        for i,slot in enumerate(FORGE_BLUEPRINT_SLOTS):
            recipe=valid.get(str(slot))
            title=('SLOT %d / LV %d / QTY %d'%(slot,recipe['level'],recipe['count'])) if recipe else 'SLOT %d / EMPTY'%slot
            btn(layout,title,left+i*(cw+8),y+533,cw,39,lambda n=slot:forge_load_blueprint(n),small=True,disabled=recipe is None)

def _transfer_appearance_validate(raw):
    allowed={'theme','opacity','scale','text','art','compact','reduced','accent','background','duration'}
    if not isinstance(raw,dict) or set(raw)!=allowed:raise ValueError('Unexpected appearance fields')
    out=_appearance_extra_validate(raw)
    for key,lo,hi in (('opacity',.65,1.),('scale',.72,2.),('text',.85,1.25)):
        value=raw[key]
        if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:raise ValueError('Invalid '+key)
        out[key]=float(value)
    if type(raw['theme']) is not int or not 0<=raw['theme']<len(THEMES):raise ValueError('Unknown theme')
    if raw['art'] not in ('AUTO','SHAPES'):raise ValueError('Unknown art mode')
    if type(raw['compact']) is not bool or type(raw['reduced']) is not bool:raise ValueError('Invalid toggle')
    for key in ('theme','art','compact','reduced'):out[key]=raw[key]
    return out

def appearance_transfer(export=False):
    if SETTINGS_DIR is None:log('TRANSFER UNAVAILABLE // Settings directory missing.');return False
    path=Path(SETTINGS_DIR)/'CROWNs_Freedom_UI_Transfer.json'
    try:
        if export:
            path.parent.mkdir(parents=True,exist_ok=True)
            pending=path.with_suffix('.json.tmp')
            pending.write_text(json.dumps({'format':'CROWN_APPEARANCE_1','appearance':_appearance_snapshot()},indent=2),encoding='utf-8')
            pending.replace(path)
            log('APPEARANCE EXPORTED // CROWNs_Freedom_UI_Transfer.json in SDK settings.');return True
        if path.stat().st_size>32768:raise ValueError('Transfer exceeds 32 KB')
        raw=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(raw,dict) or set(raw)!= {'format','appearance'} or raw['format']!='CROWN_APPEARANCE_1':raise ValueError('Unknown transfer format')
        draft=_transfer_appearance_validate(raw['appearance'])
        show_page('STYLE');State.appearance_view='MAIN';State.appearance_draft=draft
        redraw();log('APPEARANCE IMPORTED // Review draft, then Apply or Cancel.');return True
    except (OSError,ValueError,TypeError) as error:
        log('TRANSFER REJECTED // '+str(error)[:88]);return False

# Reviewed paths from Squ1ggs Resources & Cooldowns, MIT (notice in REFERENCE).
# No source hooks/BLImGui dependency copied. Conservative candidate ranges;
# controls require actual finite primitive Value/BaseValue pairs at runtime.
RESOURCE_FIELDS={
    'KIT_CHARGES':('HealthState','RepairKitMaxCharges',1.,10.,'REPAIR KIT CHARGES'),
    'KIT_COOLDOWN':('HealthState','RepairKitCooldown',.1,120.,'REPAIR KIT COOLDOWN'),
    'KIT_DURATION':('HealthState','RepairKitDuration',.1,30.,'REPAIR KIT DURATION'),
    'HEAL_RECEIVED':('DamageState','HealingReceivedMultiplier',.1,10.,'HEALING RECEIVED'),
    'HEAL_DEALT':('DamageCauserData','HealingDealtMultiplier',.1,10.,'HEALING DEALT'),
    'AMMO_REGEN':('','ammoregenrate',0.,10.,'AMMO REGEN RATE'),
    'SECOND_WIND_HEALTH':('DownState','SecondWindHealth',.1,1.,'SECOND WIND HEALTH'),
    'SECOND_WIND_SHIELD':('DownState','SecondWindShield',0.,1.,'SECOND WIND SHIELD'),
}
TUNING_FIELDS={**COMBAT_FIELDS,**RESOURCE_FIELDS}

def resource_toggle():
    State.resource_view=not State.resource_view
    redraw()

def resource_page(direction):
    State.resource_index=(State.resource_index+direction)%math.ceil(len(RESOURCE_FIELDS)/3)
    redraw()

def draw_resource_lab(layout,left,y,width):
    cw=(width-16)/3
    for i,(label,fn) in enumerate((('BACK TO TOOLS',resource_toggle),('PREVIOUS',lambda:resource_page(-1)),('NEXT / %d OF %d'%(State.resource_index+1,math.ceil(len(RESOURCE_FIELDS)/3)),lambda:resource_page(1)))):
        btn(layout,label,left+i*(cw+8),y,cw,32,fn,small=True)
    keys=list(RESOURCE_FIELDS)[State.resource_index*3:State.resource_index*3+3]
    for row,key in enumerate(keys):
        spec=RESOURCE_FIELDS[key];found=combat_pair(key)
        yy=y+43+row*77
        if found is None:
            text(layout,spec[4]+' / NOT EXPOSED',left+12,yy+9,width-24,38,theme_color('dim'),.70)
        elif not spec[2]<=found[1][0]<=spec[3]:
            text(layout,spec[4]+' / CURRENT %g OUTSIDE CANDIDATE RANGE'%found[1][0],left+12,yy+9,width-24,38,theme_color('dim'),.66)
        else:
            slider(layout,spec[4],found[1][0],spec[2],spec[3],left,yy,width,lambda v,k=key:combat_tune(k,v))
    btn(layout,'RESTORE OWNED TUNING / SAME PAWN',left,y+282,width,32,
        lambda:(log('TUNING RESTORE // %d pairs readback verified.'%restore_combat_tuning()),redraw()),small=True)
    # No per-frame sticky write. Travel, ownership and competing-mod guards are
    # inherited from the recovered combat adapter; actual effects unverified.

def profile_manage_toggle():
    State.profile_manage=not State.profile_manage;State.profile_pending=None
    redraw()

def profile_select_next():
    State.current_ui_profile=State.current_ui_profile%3+1
    State.profile_pending=None;redraw()

def _profile_revision(slot):
    raw=State.ui_profiles.get(str(slot))
    if not isinstance(raw,dict):return None
    try:
        encoded=json.dumps(raw,sort_keys=True,allow_nan=False)
        if len(encoded)>16384:return None
        if type(raw.get('theme_index')) is not int or not 0<=raw['theme_index']<len(THEMES):return None
        for key,lo,hi in (('scale',.72,2.),('text_scale',.85,1.25),('opacity',.65,1.)):
            val=raw.get(key)
            if type(val) not in (int,float) or not math.isfinite(val) or not lo<=val<=hi:return None
        _appearance_extra_validate(raw.get('echo_appearance',{}))
        return hashlib.sha256(encoded.encode('utf-8')).hexdigest()
    except (ValueError,TypeError):return None

def profile_manage_action(kind):
    if kind not in ('DUPLICATE','DELETE'):return False
    slot=State.current_ui_profile;revision=_profile_revision(slot)
    if revision is None:log('PROFILE BLOCKED // Selected slot empty or malformed.');return False
    target=slot%3+1
    target_revision=_profile_revision(target)
    # An overwrite/delete confirmation belongs to exact source AND target data.
    token=(kind,slot,target,revision,target_revision)
    now=time.monotonic()
    if State.profile_pending!=token or now>=State.profile_pending_until:
        State.profile_pending=token;State.profile_pending_until=now+6.
        log('CONFIRM PROFILE '+kind+' // Press the same action again within 6 seconds.')
        redraw();return False
    State.profile_pending=None
    if kind=='DELETE':
        State.ui_profiles.pop(str(slot),None)
        log('PROFILE DELETED // Local UI slot only; previous preferences backup preserved.')
    else:
        State.ui_profiles[str(target)]=json.loads(json.dumps(State.ui_profiles[str(slot)]))
        State.profile_names[str(target)]=(State.profile_names.get(str(slot),'PROFILE '+str(slot))+' COPY')[:24]
        log('PROFILE DUPLICATED // Slot %d to slot %d; no settings applied.'%(slot,target))
    save_preferences();redraw();return True

def draw_profile_manager(layout,left,y,width):
    slot=State.current_ui_profile;half=(width-12)/2
    text(layout,'LOCAL PROFILE / %d / '%slot+State.profile_names.get(str(slot),'PROFILE'),left,y,width,30,theme_color('accent'),.84)
    options=(('SELECT NEXT SLOT',profile_select_next),('RENAME SELECTED',profile_rename_open),
        ('DUPLICATE TO SLOT %d / 2 PRESSES'%(slot%3+1),lambda:profile_manage_action('DUPLICATE')),
        ('DELETE SELECTED / 2 PRESSES',lambda:profile_manage_action('DELETE')),
        ('RESET APPEARANCE DRAFT',lambda:(show_page('STYLE'),appearance_reset())),('BACK TO PROFILES',profile_manage_toggle))
    for i,(label,fn) in enumerate(options):
        btn(layout,label,left+(i%2)*(half+12),y+48+(i//2)*51,half,42,fn,small=True,danger=i==3)
    text(layout,'Duplicate and Delete affect local CROWN UI presets only. Confirmation expires after 6 seconds and cancels if either slot changes.',left,y+219,width,52,theme_color('dim'),.66)



REVIEWED_BMS_SHA='cee865777928ab314a677ae7ab5302e976b36a96f423e8790b3d87de82978f71'
REVIEWED_BL4LIVE_SHA='0e1e914e876a4000fbffdbfb031bc8dedefb0d692284aa559d7eac13edb647a9'
ENCOUNTER_CATALOGUE=(('Char_Cat_Mine_Boss_CityCat', 'Axemaul', 'BOSSES'), ('Char_Pangolin_Drill_Boss_Bango', 'Bango', 'BOSSES'), ('Char_GrassBoss_TrueBoss', 'Big Encore Idolator Sol', 'BOSSES'), ('Char_ShatterBoss_Elpis_TrueBoss', 'Big Encore Moon-Maddened Callis', 'BOSSES'), ('Char_GrassGuard_TrueBoss', 'Big Encore Primordial Guardian Inceptus', 'BOSSES'), ('Char_MountGuard_V02_TrueBoss', 'Big Encore Primordial Guardian Origo', 'BOSSES'), ('Char_ShatterGuard_TrueBoss', 'Big Encore Primordial Guardian Radix', 'BOSSES'), ('Char_TkGuard_TrueBoss', 'Big Encore Primordial Guardian Timekeeper', 'BOSSES'), ('Char_Thresher_SideGrass_Trash_True', 'Big Encore Sludgemaw', 'BOSSES'), ('Char_MountBoss_TrueBoss', 'Big Encore Vile Lictor', 'BOSSES'), ('Char_Brute_PlotGrass2b_Boss_Motherbase', 'Bio-Bulkhead', 'BOSSES'), ('Char_Bat_Mine_Boss_Destroyer', 'Bramblesong', 'BOSSES'), ('Char_DahlFather_Boss_Replay_True', 'Big Encore Captain Willis', 'BOSSES'), ('Char_DNMGrunt_Mission04_BossMini_Replay_True', 'Big Encore Colonel Crash', 'BOSSES'), ('Char_DahlMech_Mission02_BossMini_Replay_True', 'Big Encore Corporal Brennan', 'BOSSES'), ('Char_CrazyEarl_Boss_Replay_True', 'Big Encore Crazed Earl', 'BOSSES'), ('Char_PhalanxCreepyTrue', 'Big Encore Poison Ivan', 'BOSSES'), ('Char_Pangolin_BountyPack2_Boss_OrdiniteInfusedtrue', 'Big Encore Stone Demon', 'BOSSES'), ('Char_Striker_Cleaner_BossMini_Replay_True', 'Striker Cleaner Boss Mini Replay True', 'BOSSES'), ('Char_Striker_Fixer_BossMini_Replay_True', 'Striker Fixer Boss Mini Replay True', 'BOSSES'), ('Char_BatWithSplice', 'Aerial Spidananggal', 'BOSSES'), ('Char_Scav_AirRaiderSteve_BossMini', 'Air Raider Scremulous', 'BOSSES'), ('Char_PrisonBuddyBoss_Shared', 'Arjay', 'BOSSES'), ('Char_Mandolin_BruteSlaughterBoss', 'Beta Revision Avenging Daemon', 'BOSSES'), ('Char_DigiZaneKiller_Boss', 'Biff Fistful', 'BOSSES'), ('Char_Scav_HeavySplice_BossMini', 'Big Oil', 'BOSSES'), ('Char_Creep_Bitterblight_BossRift', 'Bitterblight', 'BOSSES'), ('Char_CreepRaid1', 'Bloomreaper the Invincible', 'BOSSES'), ('Char_Scav_BoneBoogy_BossRift', 'Bone Boogie', 'BOSSES'), ('Char_Phalanx_OrdiniteInfused_MiniBoss', 'Bore-Tex', 'BOSSES'), ('Char_Scav_Botpopper_BossRift', 'Botpopper', 'BOSSES'), ('Char_DigiZaneKiller_Boss_FloatingHead_DroneParent', 'Brain Zane', 'BOSSES'), ('Char_NPC_Amara', 'Amara', 'ENEMIES'), ('Char_NPC_Friendly_ScavGuntoter', 'Andy', 'ENEMIES'), ('Char_NPC_Friendly_ScavGuntoter_Romeo', 'Andy', 'ENEMIES'), ('Char_NPC_PrisonBuddy', 'Arjay', 'ENEMIES'), ('Char_NPC_NudgeCouncil04', 'Asha', 'ENEMIES'), ('Char_NPC_BrainWashedAugers_Male', 'Auger Ghoul', 'ENEMIES'), ('Char_NPC_GunToterBadass_Male', 'Badass Rat-a-tat', 'ENEMIES'), ('Char_NPC_GoldieScav', 'Barney', 'ENEMIES'), ('Char_NPC_QuarterMaster', 'Bash', 'ENEMIES'), ('Char_NPC_DemonHunterLeader', 'Belle', 'ENEMIES'), ('Char_NPC_GassyBeth', 'Beth', 'ENEMIES'), ('Char_NPC_DigiZane_Detective', 'Biff Fistful', 'ENEMIES'), ('Char_NPC_DigiZane_Blade', 'Blade Diaz', 'ENEMIES'), ('Char_NPC_DigiZane_Victim', 'Blade Diaz', 'ENEMIES'), ('Char_NPC_WaterBrenda', 'Brenda', 'ENEMIES'), ('Char_NPC_LifeCoach', 'Brody Sattva', 'ENEMIES'), ('Char_GunToterPistol4Arm_Female', "'Melic Plinker", 'ENEMIES'), ('Char_GunToterPistol4Arm_Male', "'Melic Plinker", 'ENEMIES'), ('Char_GunToterShotgun4Arm_Female', "'Melic Pulper", 'ENEMIES'), ('Char_GunToterShotgun4Arm_Male', "'Melic Pulper", 'ENEMIES'), ('Char_GunToterAssault4Arm_Female', "'Metic Rat-a-tat", 'ENEMIES'), ('Char_GunToterAssault4Arm_Male', "'Metic Rat-a-tat", 'ENEMIES'), ('Char_MeatheadEnrager', "'Rager Meathead", 'ENEMIES'), ('Char_StrikerLoot', 'Acquisition Engine', 'ENEMIES'), ('Char_BatRanged', 'Acrid Kratch', 'ENEMIES'), ('Char_BatRanged_Guardian', 'Acrid Kratch', 'ENEMIES'), ('Char_AI', 'AI', 'ENEMIES'), ('Char_BatBomber', 'Airstrike Kratch', 'ENEMIES'), ('Char_Kraggon_Alpha_Named', 'Alpha Kraggon', 'ENEMIES'), ('Char_Thresher_Alpha_Named', 'Alpha Thresher', 'ENEMIES'), ('Char_Robo_Totem_Arcane', 'Arcane Totem', 'ENEMIES'), ('Char_ScavOutlawArmored', 'Armored Outlaw', 'ENEMIES'))
REVIEWED_BMS_MODULES={'aggro': '0cc1a8bc3952305befbe41f44ef9ae5e53c6f57c2ce233583f8612d2bac78f8f', 'io_activate': 'b63a0e437a189e61c74a46743581fe391e84e14ab608f046e6ef66dd34995f39', 'io_spawner_tab': '3fe59579aa8677b1a575d0805c5782f392503b7c41859df44a32fb8b2999865e', 'lobby_stability': 'a2c1e37e4d0159d04dc01d39bd2d1d5980b1b26a1b37dc8a87ce04c50d4705a9', 'mix_spawn': 'd6fc99a1b54af2c6c58d4c4db578a05eb0b619a452897b2cc1bae4ee28424639', 'mob_catalog': '0213d8440262af3ce0bb8a089b483348b1b0fe83fac400ebe626d14257f64349', 'mob_favorites': '07f86a368020c3b7f5451362cb835c5430ed11306a27de5f6ad6ee23725e91b4', 'mod_data': '074f58be00dcda8e93b3a583d0540cb5cfbb8c9aede929583eb10a4e0d297db7', 'oak_spawn': 'efd3b8b880b1f29f352cf1e2b902fc8cc2eef78ea4b13fb651a8746781b5229f', 'oak_spawner': '682e39cc872f6201b52051a4481b95a2231a6b05a0c25ed0901f5d1de0870b7b', 'spawn_anchor': '197a632f7863f19445dfd4534607497463a96b89e15641c8a3b5a5143df66dd2', 'spawn_async': '5d2ed256a1b874aae72c9e33c8fc2f75da79b545827444ecd9d340ed4d04792a', 'spawn_core': '481f4f8708d3a6e5904bd09834ab71bf933fbaef5970ce130298d5e0149e4440', 'spawn_pause': 'd9ee8786e95deff1ade4b841c7b6e9bb69ae9d9d066d6e338cf28276b3983e01', 'spawn_safe': '3b78e0bded57da0bf5456fa70bdd3a194dc5f3ecc6c3678d5793d7319d9a7ec2', 'world_props_ui': 'de8423c7d8a788b2a1d7a098d8c52ef2af10f27749da6ffd87b19a68eab075af'}
ART_FILES['SANDBOX_PLATE']='CROWN_SANDBOX_PLATE.png'
ART_SHA256['SANDBOX_PLATE']='e5f1f83833e9a816edec5be1046b26b0c848c6978d48b8a5de586a83f167437c'
TOAST_COPY['CROWN_SANDBOX']=('CROWN / SANDBOX','Numbers checked. Chaos remains your department.','success')
TOAST_COPY['CROWN_ENCOUNTER']=('CROWN / DIRECTOR','Guest list updated. They brought their own weapons.','info')
# ECHO Sandbox R2: conditional source-reviewed integrations, no new native hooks.
SANDBOX_FIELDS={
 'SPLASH_OUT':('DamageCauserData','RadiusDamage_DamageMultiplier',.1,20.,'SPLASH DAMAGE'),
 'SPLASH_RADIUS':('DamageCauserData','RadiusDamage_RadiusMultiplier',.1,3.,'SPLASH RADIUS'),
 'SPLASH_IN':('DamageState','RadiusDamageTakenMultiplier',0.,5.,'SPLASH RECEIVED'),
 'STATUS_CHANCE':('DamageState','StatusEffectChanceModifierScalar',0.,5.,'STATUS CHANCE RECEIVED'),
 'STATUS_DPS':('DamageState','StatusEffectDPSModifierScalar',0.,5.,'STATUS DAMAGE RECEIVED'),
 'STATUS_CHARGE':('DamageState','StatusEffectChargeModifierScalar',0.,5.,'STATUS BUILDUP RECEIVED'),
 'FIRE':('DamageCauserData.ElementalDamageModifiers','FireModifier',0.,10.,'FIRE DAMAGE'),
 'SHOCK':('DamageCauserData.ElementalDamageModifiers','ShockModifier',0.,10.,'SHOCK DAMAGE'),
 'CORROSIVE':('DamageCauserData.ElementalDamageModifiers','CorrosiveModifier',0.,10.,'CORROSIVE DAMAGE'),
 'CRYO':('DamageCauserData.ElementalDamageModifiers','CryoModifier',0.,10.,'CRYO DAMAGE'),
 'RADIATION':('DamageCauserData.ElementalDamageModifiers','RadiationModifier',0.,10.,'RADIATION DAMAGE'),
 'CRIT_CHANCE':('DamageCauserData','DefaultCriticalHitChance',0.,1.,'BONUS CRIT CHANCE'),
 'LIFESTEAL':('DamageState','lifestealpercent',0.,3.,'LIFESTEAL SCALAR'),
 'LIFESTEAL_RATE':('DamageState','lifestealrate',0.,3.,'LIFESTEAL RATE'),
 'LIFESTEAL_CAP':('DamageState','lifestealratecap',0.,3.,'LIFESTEAL RATE CAP'),
 'OVERSHIELD_DURATION':('OvershieldManager','OvershieldDuration',0.,60.,'OVERSHIELD DURATION'),
 'REPEAT_DOWN':('DownState','RepeatDeathPenalty',0.,3.,'REPEATED DOWN PENALTY'),
 'KIT_THRESHOLD':('HealthState','minhealthpercentmissingtoheal',0.,1.,'KIT MISSING HEALTH THRESHOLD'),
}
TUNING_FIELDS.update(SANDBOX_FIELDS)
SANDBOX_GROUPS=(('SPLASH',('SPLASH_OUT','SPLASH_RADIUS','SPLASH_IN')),
 ('STATUS DEFENCE',('STATUS_CHANCE','STATUS_DPS','STATUS_CHARGE')),
 ('ELEMENTS I',('FIRE','SHOCK','CORROSIVE')),('ELEMENTS II',('CRYO','RADIATION','CRIT_CHANCE')),
 ('LIFESTEAL',('LIFESTEAL','LIFESTEAL_RATE','LIFESTEAL_CAP')),
 ('RECOVERY',('OVERSHIELD_DURATION','REPEAT_DOWN','KIT_THRESHOLD')),
 ('COMBAT',('OUTGOING','INCOMING','CRITICAL')),
 ('RESOURCES',('KIT_CHARGES','KIT_COOLDOWN','AMMO_REGEN')))
State.sandbox_view=False
State.sandbox_manage=False
State.sandbox_group=0
State.sandbox_stage={}
State.sandbox_anchor=None
State.sandbox_slot=1
State.sandbox_saved={}
State.xp_view=False
State.xp_draft=1.
State.xp_owner=None
State.xp_status='READ BACKEND before applying. Combat rewards only.'
State.xp_read=None
State.encounter_view='CATALOGUE'
State.encounter_filter='ENEMIES'
State.encounter_query=''
State.encounter_query_draft=''
State.encounter_input=None
State.encounter_page=0
State.encounter_selected=0
State.encounter_quantity=1
State.encounter_distance=600.
State.encounter_favorites=[]
State.encounter_confirm=None
State.encounter_job=None
State.encounter_epoch=0
State.encounter_owned={}
State.encounter_anchor=None
State.encounter_budget=0
State.encounter_status='Optional reviewed BMS + Oak Spawner + world tools required.'
State.echo_personality=True
State.echo_feedback_at=0.
State.echo_scan=None
State.echo_scan_generation=-1
State.echo_scan_at=0.
State.backend_hash_cache={}

def sandbox_toggle():
    State.sandbox_view=not State.sandbox_view;State.resource_view=False
    State.sandbox_stage={};State.sandbox_anchor=None;redraw()

def sandbox_solo_ready():
    try:return is_local_host_action() and pawn() is not None and pawn().HasAuthority() is True
    except Exception:return False

def sandbox_group_next():
    State.sandbox_group=(State.sandbox_group+1)%len(SANDBOX_GROUPS);redraw()

def sandbox_stage_value(key,value):
    if key not in TUNING_FIELDS or type(value) not in (int,float):return False
    spec=TUNING_FIELDS[key]
    if not math.isfinite(value) or not spec[2]<=value<=spec[3]:return False
    anchor=_session_anchor()
    if anchor is None:return False
    if State.sandbox_stage and anchor!=State.sandbox_anchor:
        State.sandbox_stage={};log('SANDBOX // Character changed. Draft cleared.');return False
    State.sandbox_anchor=anchor;State.sandbox_stage[key]=float(value)
    if State.opened:redraw()
    return True

def sandbox_apply():
    staged=dict(State.sandbox_stage)
    if not staged or _session_anchor()!=State.sandbox_anchor or not sandbox_solo_ready():
        log('SANDBOX BLOCKED // Fresh solo draft required.');return False
    before={}
    # Preflight every pair before any write; absent or out-of-range live fields
    # cannot be silently enabled by a saved preset.
    for key,value in staged.items():
        found=combat_pair(key)
        if found is None or not TUNING_FIELDS[key][2]<=found[1][0]<=TUNING_FIELDS[key][3]:
            log('SANDBOX BLOCKED // Field unavailable: '+key);return False
        before[key]=found[1]
    old_owner=State.combat_owner;old_originals=dict(State.combat_originals);old_last=dict(State.combat_last)
    written=[]
    def apply_batch():
        for key,value in staged.items():
            if not combat_tune(key,value):
                failed_pair=combat_pair(key)
                rollback_ok=failed_pair is not None and failed_pair[1]==before[key]
                for prior in reversed(written):
                    found=combat_pair(prior)
                    if found is None or found[1]!=(staged[prior],staged[prior]):rollback_ok=False;continue
                    try:
                        found[0].Value,found[0].BaseValue=before[prior]
                        if combat_pair(prior)[1]!=before[prior]:rollback_ok=False
                    except Exception:rollback_ok=False
                if rollback_ok:
                    State.combat_owner=old_owner;State.combat_originals=old_originals;State.combat_last=old_last
                log('SANDBOX FAILED // '+('Batch rolled back; draft kept.' if rollback_ok else 'Partial rollback; use Restore and inspect.'))
                echo_feedback('failure');return False
            written.append(key)
        State.sandbox_stage={}
        log('SANDBOX APPLIED // %d float pairs readback verified; gameplay effects unverified.'%len(written))
        echo_feedback('apply');redraw()
        return True
    return _ui_batch(apply_batch)

def sandbox_preset(kind):
    # These stage only: no automatic mutation or save editing.
    values={'BALANCED':{'OUTGOING':1.,'INCOMING':1.,'CRITICAL':1.},
            'GLASS CANNON':{'OUTGOING':3.,'INCOMING':2.},
            'GENTLE FARM':{'OUTGOING':2.,'INCOMING':.5,'KIT_COOLDOWN':5.}}.get(kind)
    if values is None:return False
    State.sandbox_stage={};State.sandbox_anchor=None
    for k,v in values.items():sandbox_stage_value(k,v)
    log('SANDBOX DRAFT // '+kind+' / Apply required.');redraw();return True

def _sandbox_saved_validate(raw):
    result={}
    if not isinstance(raw,dict):return result
    for slot,values in raw.items():
        if slot not in ('1','2','3') or not isinstance(values,dict) or not 1<=len(values)<=len(TUNING_FIELDS):continue
        if all(k in TUNING_FIELDS and type(v) in (int,float) and math.isfinite(v) and TUNING_FIELDS[k][2]<=v<=TUNING_FIELDS[k][3] for k,v in values.items()):
            result[slot]={k:float(v) for k,v in values.items()}
    return result

def sandbox_save():
    if not State.sandbox_stage or _session_anchor()!=State.sandbox_anchor:return False
    State.sandbox_saved[str(State.sandbox_slot)]=dict(State.sandbox_stage)
    save_preferences();log('SANDBOX DRAFT SAVED // Local slot %d; no auto-apply.'%State.sandbox_slot);return True

def sandbox_load():
    values=_sandbox_saved_validate(State.sandbox_saved).get(str(State.sandbox_slot))
    if not values:return False
    State.sandbox_stage={};State.sandbox_anchor=None
    for key,value in values.items():
        if not sandbox_stage_value(key,value):return False
    log('SANDBOX DRAFT LOADED // Apply required.');redraw();return True

def draw_sandbox(layout,left,y,width):
    third=(width-16)/3
    for i,(label,fn) in enumerate((('QUICK COMBAT',sandbox_toggle),('GROUP / '+SANDBOX_GROUPS[State.sandbox_group][0],sandbox_group_next),('RESTORE OWNED VALUES',lambda:(restore_combat_tuning(),redraw())))):
        btn(layout,label,left+i*(third+8),y,third,32,fn,small=True)
    if State.sandbox_manage:
        half=(width-12)/2
        actions=(('SLOT %d / NEXT'%State.sandbox_slot,lambda:(setattr(State,'sandbox_slot',State.sandbox_slot%3+1),redraw())),
          ('SAVE DRAFT',sandbox_save),('LOAD DRAFT',sandbox_load),('BACK TO CONTROLS',lambda:(setattr(State,'sandbox_manage',False),redraw())),
          ('PRESET / BALANCED',lambda:sandbox_preset('BALANCED')),('PRESET / GENTLE FARM',lambda:sandbox_preset('GENTLE FARM')))
        for i,(label,fn) in enumerate(actions):btn(layout,label,left+(i%2)*(half+12),y+48+(i//2)*45,half,36,fn,small=True)
        text(layout,'Presets stage only. Slots store your draft values locally; loading never applies gameplay changes.',left+12,y+205,width-24,60,theme_color('dim'),.71)
        return
    for row,key in enumerate(SANDBOX_GROUPS[State.sandbox_group][1]):
        spec=TUNING_FIELDS[key];found=combat_pair(key);yy=y+43+row*77
        if found is None or not spec[2]<=found[1][0]<=spec[3]:
            text(layout,spec[4]+' / FIELD UNAVAILABLE',left+12,yy+14,width-24,30,theme_color('dim'),.70)
        else:
            value=State.sandbox_stage.get(key,found[1][0])
            slider(layout,spec[4]+' / DRAFT',value,spec[2],spec[3],left,yy,width,lambda v,k=key:sandbox_stage_value(k,v))
    quarter=(width-24)/4
    for i,(label,fn) in enumerate((('APPLY %d VALUES'%len(State.sandbox_stage),sandbox_apply),('CANCEL DRAFT',lambda:(State.sandbox_stage.clear(),redraw())),('GLASS CANNON',lambda:sandbox_preset('GLASS CANNON')),
        ('SLOTS / PRESETS',lambda:(setattr(State,'sandbox_manage',True),redraw())))):
        btn(layout,label,left+i*(quarter+8),y+281,quarter,32,fn,small=True)

def _reviewed_module(names,expected):
    """Only already-loaded, exact reviewed Python source; never imports a mod.

    zipimport loader.get_data supports installed .sdkmod archives. Cache is
    tied to module and loader identity, and cleared on menu close.
    """
    import sys
    for name in names:
        module=sys.modules.get(name)
        if module is None:continue
        identity=(name,id(module),id(getattr(module,'__loader__',None)))
        if State.backend_hash_cache.get(identity)==expected:return module
        try:
            filename=module.__file__;loader=module.__loader__
            data=loader.get_data(filename) if callable(getattr(loader,'get_data',None)) else Path(filename).read_bytes()
            if len(data)>1500000 or hashlib.sha256(data).hexdigest()!=expected:continue
            State.backend_hash_cache[identity]=expected;return module
        except Exception:continue
    return None

def _reviewed_bms_package(module):
    identity=('bms_package',id(module),id(getattr(module,'__loader__',None)))
    if State.backend_hash_cache.get(identity)==REVIEWED_BMS_SHA:return True
    try:
        filename=Path(module.__file__);loader=module.__loader__
        for suffix,expected in REVIEWED_BMS_MODULES.items():
            path=str(filename.with_name(suffix+'.py'))
            raw=loader.get_data(path) if callable(getattr(loader,'get_data',None)) else Path(path).read_bytes()
            if len(raw)>1500000 or hashlib.sha256(raw).hexdigest()!=expected:return False
        State.backend_hash_cache[identity]=REVIEWED_BMS_SHA;return True
    except Exception:return False

def _xp_reviewed_backend():
    module=_reviewed_module(('bl4_live',),REVIEWED_BL4LIVE_SHA)
    if module is None:return None
    try:
        if not same_unreal_object(module._runtime_pawn(),pawn()):return None
        if not all(callable(getattr(module,n,None)) for n in ('_runtime_combat_xp_value','_runtime_set_combat_xp_scale')):return None
        if float(module._RUNTIME_STATE.get('experience_reward_scale',1.))!=float(module._RUNTIME_REGISTRY.get('xp_scale',1.)):return None
        return module
    except Exception:return None

def xp_read():
    module=xp_backend()
    if module is None or not sandbox_solo_ready():
        State.xp_read=None;State.xp_status='BLOCKED / '+State.xp_route+' backend unavailable for the local solo pawn.';redraw();return False
    try:
        value=module._runtime_combat_xp_value();scale=module._RUNTIME_STATE.get('experience_reward_scale',1.)
        if type(value) not in (int,float) or not math.isfinite(value) or value<=0:raise ValueError('attribute unavailable')
        if type(scale) not in (int,float) or not math.isfinite(scale) or not 1<=scale<=10:raise ValueError('invalid scale')
        if not r12_xp_observe_attempt(module,float(scale),float(value)):
            State.xp_read=None;State.xp_status='XP UNCERTAIN / Config or attribute differs; no retry in this context.';redraw();return False
        State.xp_read={'anchor':_session_anchor(),'module':module,'scale':float(scale),'attribute':float(value),'at':time.monotonic()}
        State.xp_draft=float(scale);State.xp_status='COMBAT XP / scale %gx / attribute %g / read only'%(scale,value)
        redraw();return True
    except Exception as error:
        State.xp_read=None;State.xp_status='READ FAILED / '+type(error).__name__;redraw();return False

def xp_stage(value):
    if type(value) not in (int,float) or not math.isfinite(value) or not 1<=value<=10:return False
    State.xp_draft=float(value);return True

def xp_apply(restore_owned=False):
    read=State.xp_read;module=xp_backend();anchor=_session_anchor()
    if (not read or module is None or module is not read['module'] or anchor!=read['anchor'] or
        not sandbox_solo_ready() or time.monotonic()-read['at']>30):
        State.xp_status='BLOCKED / Fresh same-character READ required.';redraw();return False
    if State.r12_xp_attempt is not None:
        if State.r12_xp_attempt['anchor']==anchor:
            State.xp_status='XP UNCERTAIN / Read result first; no repeated modifier call.';redraw();return False
        State.r12_xp_attempt=None
    owner=State.xp_owner
    try:
        scale=float(module._RUNTIME_STATE['experience_reward_scale'])
        current=module._runtime_combat_xp_value()
        if owner and (owner['anchor']!=anchor or owner['module'] is not module or scale!=owner['last']):
            raise ValueError('XP owner changed; use BL4Live to inspect')
        if not owner and (scale!=1. or getattr(module,'_RUNTIME_XP_MODIFIERS',())):
            raise ValueError('BL4Live already owns an XP modifier; restore it there first')
        if scale!=read['scale'] or type(current) not in (int,float) or not math.isfinite(current) or abs(current-read['attribute'])>max(.01,read['attribute']*.01):
            raise ValueError('backend changed; read again')
        if restore_owned:
            if not owner or owner['anchor']!=anchor or owner['module'] is not module or scale!=owner['last']:raise ValueError('owned XP value changed')
            desired=owner['original']
        else:desired=State.xp_draft
        if not math.isfinite(desired) or not 1<=desired<=10:return False
        if desired==scale:
            if restore_owned:State.xp_owner=None
            return True
        native_baseline=getattr(module,'original',None) if isinstance(module,NativeCombatXP) else None
        expected=native_baseline if desired==1. and native_baseline is not None else current/scale*desired
        State.r12_xp_attempt=dict(module=module,anchor=anchor,desired=desired,expected=expected,
            original=owner['original'] if owner else scale,restore=restore_owned)
        result=module._runtime_set_combat_xp_scale(desired)
        after=module._runtime_combat_xp_value();actual=module._RUNTIME_STATE.get('experience_reward_scale')
        expected=native_baseline if desired==1. and native_baseline is not None else current/scale*desired
        accepted=(isinstance(result,dict) and result.get('ok') is True and actual==desired)
        # Retain ownership even if attribute readback fails after an accepted
        # setter: a real modifier may now exist and must remain restorable.
        if accepted:
            original=owner['original'] if owner and owner['anchor']==anchor and owner['module'] is module else scale
            State.xp_owner={'module':module,'anchor':anchor,'original':original,'last':desired}
        verified=accepted and type(after) in (int,float) and math.isfinite(after) and abs(after-expected)<=max(.01,abs(expected)*.01)
        State.xp_read=None
        if not verified:
            State.xp_status='XP UNCONFIRMED / READ again; owned restore retained if accepted.';echo_feedback('failure');redraw();return False
        State.r12_xp_attempt=None
        State.xp_read={'anchor':anchor,'module':module,'scale':float(desired),'attribute':float(after),'at':time.monotonic()}
        State.xp_draft=desired
        if restore_owned:State.xp_owner=None
        State.xp_status='XP ATTRIBUTE READBACK / %gx / earned reward effect unverified'%desired
        log(State.xp_status);echo_feedback('apply');redraw();return True
    except Exception as error:
        State.xp_read=None;State.xp_status='XP BLOCKED / '+str(error)[:88];echo_feedback('failure');redraw();return False

def xp_toggle():
    State.xp_view=not State.xp_view;redraw()

def _xp_restore_reviewed():
    owner=State.xp_owner
    if not owner:return True
    module=xp_backend()
    if (module is not owner['module'] or _session_anchor()!=owner['anchor'] or
        module._RUNTIME_STATE.get('experience_reward_scale')!=owner['last']):
        log('XP RESTORE SKIPPED // Owner, pawn or value changed.');return False
    if not xp_read():return False
    return xp_apply(True)

def draw_progression(layout,left,y,width):
    third=(width-16)/3;fifth=(width-24)/5;half=(width-12)/2
    source='REWARD' if State.xp_external_view else State.xp_route
    for i,(label,key) in enumerate((('CROWN NATIVE','NATIVE'),('BL4LIVE','BL4LIVE'),('XP ADD-ON','REWARD'))):
        btn(layout,label,left+i*(third+8),y,third,32,lambda k=key:r13_xp_source(k),active=source==key,small=True)
    for i,value in enumerate((1.,2.,3.,5.,10.)):
        draft=State.external_xp_draft if State.xp_external_view else State.xp_draft
        btn(layout,'%gx'%value,left+i*(fifth+6),y+42,fifth,35,lambda v=value:r13_xp_preset(v),active=draft==value,small=True)
    slider(layout,'XP MULTIPLIER / DRAFT',State.external_xp_draft if State.xp_external_view else State.xp_draft,
           .1 if State.xp_external_view else 1.,10.,left,y+85,width,xp_external_stage if State.xp_external_view else xp_stage)
    for i,(label,fn) in enumerate((('READ CURRENT',r13_xp_read),('APPLY / CONFIRM',r13_xp_apply),('VANILLA / RESTORE',r13_xp_restore))):
        btn(layout,label,left+i*(third+8),y+169,third,35,fn,small=True)
    for i,(label,fn) in enumerate((('BEGIN REWARD',lambda:reward_sample('BEGIN')),('FINISH REWARD',lambda:reward_sample('FINISH')),('XP COMPARISONS',lambda:studio_open('REWARDS')))):
        btn(layout,label,left+i*(third+8),y+214,third,34,fn,small=True,disabled=(i==0 and State.r10_reward_start is not None) or (i==1 and State.r10_reward_start is None))
    status=str(State.xp_status)
    if len(status)>154:status=status[:151]+'...'
    text(layout,status,left+10,y+255,width-20,51,theme_color('text'),.80)
    if State.panel_rect and State.panel_rect[3]>=900:
        r13_xp_dashboard(layout,left,y+321,width)

def encounter_backend():
    module=_reviewed_module(('mob_spawner','bl4_mob_spawner'),REVIEWED_BMS_SHA)
    if module is None:return None
    try:
        import sys
        stability=sys.modules.get(module.__name__+'.lobby_stability')
        core=sys.modules.get(module.__name__+'.spawn_core')
        deferred=sys.modules.get('bl4_world_tools.deferred')
        controller=module.CONTROLLER
        if not _reviewed_bms_package(module):return None
        if not controller._spawn_tick_hooks or not module.oak_available()[0]:return None
        if not all(callable(fn) for fn in (controller.spawn_mob,stability.make_request,core.resolve_live_actor,core.snapshot_character_keys,module.prefer_combat_boss_code,deferred.queue_action)):return None
        return module,stability,core,deferred
    except Exception:return None

def encounter_reset_context():
    anchor=_session_anchor()
    if anchor!=State.encounter_anchor:
        State.encounter_epoch+=1;State.encounter_job=None;State.encounter_confirm=None
        State.encounter_owned={};State.encounter_budget=0;State.encounter_anchor=anchor
    return anchor

def encounter_rows():
    query=State.encounter_query.casefold().strip()[:64]
    return [(i,row) for i,row in enumerate(ENCOUNTER_CATALOGUE)
        if (State.encounter_filter=='ALL' or row[2]==State.encounter_filter or
            (State.encounter_filter=='FAVOURITES' and row[0] in State.encounter_favorites))
        and (not query or query in (' '.join(row)).casefold())]

def encounter_search():
    if State.encounter_input is None:return False
    raw=call(State.encounter_input,'GetText')
    if raw is None:return False
    State.encounter_query=str(raw).strip()[:64];State.encounter_query_draft=State.encounter_query
    State.encounter_page=0;State.arena_bridge_page=0;State.arena_bridge_selected=0;State.encounter_view='CATALOGUE';State.encounter_input=None;redraw();return True

def encounter_search_open():
    State.encounter_input=None;State.encounter_query_draft=State.encounter_query;State.encounter_view='SEARCH';redraw()

def encounter_filter_next():
    options=('ENEMIES','BOSSES','FAVOURITES','ALL')
    State.encounter_filter=options[(options.index(State.encounter_filter)+1)%len(options)]
    State.encounter_page=0;redraw()

def encounter_select(index):
    if type(index) is not int or not 0<=index<len(ENCOUNTER_CATALOGUE):return False
    State.encounter_selected=index;State.encounter_confirm=None;State.encounter_view='CONTROLS'
    if ENCOUNTER_CATALOGUE[index][2]=='BOSSES':
        State.encounter_quantity=1;State.encounter_distance=max(900.,State.encounter_distance)
    redraw();return True

def encounter_stage(key,value):
    if type(value) not in (int,float) or not math.isfinite(value):return False
    if key=='quantity':
        if value!=int(value) or not 1<=value<=3:return False
        if ENCOUNTER_CATALOGUE[State.encounter_selected][2]=='BOSSES' and value!=1:return False
        State.encounter_quantity=int(value)
    elif key=='distance':
        if not 350<=value<=2000:return False
        if ENCOUNTER_CATALOGUE[State.encounter_selected][2]=='BOSSES' and value<900:return False
        State.encounter_distance=float(value)
    else:return False
    State.encounter_confirm=None;return True

def encounter_favorite():
    code=ENCOUNTER_CATALOGUE[State.encounter_selected][0]
    values=State.encounter_favorites
    State.encounter_favorites=[v for v in values if v!=code] if code in values else ([code]+values)[:12]
    save_preferences();redraw()

def encounter_cancel():
    State.encounter_epoch+=1;State.encounter_job=None;State.encounter_confirm=None
    State.encounter_status='PENDING REQUEST CANCELLED / No cleanup of existing actors.';redraw()

def encounter_request():
    anchor=encounter_reset_context();backend=encounter_backend()
    code,label,category=ENCOUNTER_CATALOGUE[State.encounter_selected]
    n=State.encounter_quantity;distance=State.encounter_distance
    if (anchor is None or not sandbox_solo_ready() or backend is None or State.encounter_job is not None or
        type(n) is not int or not 1<=n<=3 or (category=='BOSSES' and n!=1) or
        type(distance) not in (int,float) or not math.isfinite(distance) or not 350<=distance<=2000):
        State.encounter_status='BLOCKED / Solo, reviewed loaded backend and idle queue required.';echo_feedback('failure');redraw();return False
    if State.encounter_budget+n>6:
        State.encounter_status='LIMIT / Six requests per world including unverified actors. Cleanup verified owned actors or travel.';redraw();return False
    token=('SPAWN',anchor,code,n,distance);now=time.monotonic()
    if State.encounter_confirm is None or State.encounter_confirm[0]!=token or now>=State.encounter_confirm[1]:
        State.encounter_confirm=(token,now+6.);State.encounter_status='CONFIRM / '+label+' x%d / press SPAWN again within 6 seconds.'%n
        echo_feedback('confirm');redraw();return False
    State.encounter_confirm=None;epoch=State.encounter_epoch
    job={'epoch':epoch,'anchor':anchor,'code':code,'count':n,'at':now};State.encounter_job=job
    module,stability,core,deferred=backend
    def execute():
        # Deferred closure holds no native actor/controller wrappers. A closed
        # menu, cancelled request, travel or changed backend cannot resurrect it.
        if (State.encounter_job is not job or State.encounter_epoch!=epoch or not State.opened or
            _session_anchor()!=anchor or not sandbox_solo_ready() or time.monotonic()-job['at']>12 or encounter_backend()!=backend):
            if State.encounter_job is job:
                State.encounter_job=None;State.encounter_status='EXPIRED / No spawn performed.'
            return False,'CROWN request expired'
        c=module.CONTROLLER;ui=c.ui
        if getattr(ui,'spawn_pending',False):
            State.encounter_job=None;State.encounter_status='BLOCKED / BMS has another pending spawn.';return False,State.encounter_status
        previous={k:getattr(ui,k) for k in ('spawn_anchor','spawn_distance','unlimited_world_spawns','aggro_mode','damage_wake','summon_fallback')}
        keys={m.key for m in c.tracker.mobs}
        world_keys=core.snapshot_character_keys()
        expected_code=module.prefer_combat_boss_code(code) if category=='BOSSES' else code
        State.encounter_budget+=n
        try:
            ui.spawn_anchor='local';ui.spawn_distance=distance;ui.unlimited_world_spawns=False
            ui.aggro_mode='passive';ui.damage_wake=False;ui.summon_fallback=False
            # Full mode takes its own pre-spawn world snapshot and honors
            # quantity. Lightweight mode silently clamps count to ONE and can
            # use fallback actors: it is not suitable for ownership tracking.
            ok,message=c.spawn_mob(code,count=n,defer=False,lightweight=False)
            matched=0
            for item in c.tracker.mobs:
                if item.key in keys or item.key in world_keys or item.code!=expected_code:continue
                actor=core.resolve_live_actor(item.key)
                address=_native_address(actor)
                if address is None or same_unreal_object(actor,pawn()):continue
                State.encounter_owned[item.key]={'address':address,'code':expected_code};matched+=1
                if matched>=n:break
            State.encounter_status=('TRACKED / %d of %d actors / passive / '%(matched,n) if matched else 'SPAWN UNVERIFIED / ')+str(message)[:100]
            echo_feedback('encounter' if matched else 'failure');log('ENCOUNTER // '+State.encounter_status);State.encounter_history=(State.encounter_history+[State.encounter_status[:120]])[-8:]
            return bool(matched),State.encounter_status
        except Exception as error:
            State.encounter_status='SPAWN FAILED / '+type(error).__name__;record_runtime_fault('ENCOUNTER',error);return False,State.encounter_status
        finally:
            for k,v in previous.items():
                try:setattr(ui,k,v)
                except Exception as error:record_runtime_fault('ENCOUNTER_UI_RESTORE',error)
            State.encounter_job=None
            if State.opened:redraw()
    try:
        request=stability.make_request('CROWN / '+label,execute,anchor='local')
        deferred.queue_action('CROWN / '+label,request.execute)
        State.encounter_status='QUEUED / Waiting for BMS PlayerTick; not a spawn confirmation.';redraw();return True
    except Exception as error:
        State.encounter_job=None;State.encounter_status='QUEUE FAILED / '+type(error).__name__;redraw();return False

def encounter_cleanup():
    anchor=encounter_reset_context();backend=encounter_backend()
    if anchor is None or not sandbox_solo_ready() or backend is None or State.encounter_job is not None:return False
    token=('CLEAN',anchor,tuple(sorted((k,v['address']) for k,v in State.encounter_owned.items())))
    if not token[2]:return False
    now=time.monotonic()
    if State.encounter_confirm is None or State.encounter_confirm[0]!=token or now>=State.encounter_confirm[1]:
        State.encounter_confirm=(token,now+6.);State.encounter_status='CONFIRM / Remove only CROWN-tracked actors; press CLEAN again.';redraw();return False
    State.encounter_confirm=None;core=backend[2];removed=0
    for key,owned in list(State.encounter_owned.items()):
        actor=core.resolve_live_actor(key)
        if actor is None:
            State.encounter_owned.pop(key,None);removed+=1;continue
        if _native_address(actor)!=owned['address'] or same_unreal_object(actor,pawn()):continue
        try:
            actor.K2_DestroyActor()
            if core.resolve_live_actor(key) is None:
                State.encounter_owned.pop(key,None);removed+=1
        except Exception as error:record_runtime_fault('ENCOUNTER_CLEANUP',error)
    State.encounter_budget=max(0,State.encounter_budget-removed)
    State.encounter_status='CLEANUP / %d absent after readback / %d retained or pending destruction.'%(removed,len(State.encounter_owned))
    log(State.encounter_status);State.encounter_history=(State.encounter_history+[State.encounter_status[:120]])[-8:];redraw();return removed>0

def draw_encounter_director(layout,left,y,width):
    if State.encounter_route=='ARENA' and State.encounter_view!='SEARCH':draw_arena_bridge(layout,left,y,width);return
    half=(width-12)/2;third=(width-16)/3
    third=(width-24)/4
    btn(layout,'SOURCE / BMS',left+3*(third+8),y,third,32,encounter_route_toggle,small=True)
    btn(layout,'CATALOGUE / '+State.encounter_filter,left,y,third,32,lambda:(setattr(State,'encounter_view','CATALOGUE'),encounter_filter_next()),small=True)
    btn(layout,'SPAWN CONTROLS',left+third+8,y,third,32,lambda:(setattr(State,'encounter_view','CONTROLS'),redraw()),small=True)
    btn(layout,'STATUS / CLEANUP',left+2*(third+8),y,third,32,lambda:(setattr(State,'encounter_view','STATUS'),redraw()),small=True)
    if State.encounter_view=='SEARCH':
        text(layout,'SEARCH SOURCE CANDIDATES / NAME OR ACTOR CODE',left+12,y+48,width-24,30,theme_color('accent'),.77)
        box(layout,left,y+91,width,49,theme_color('panel'),9)
        try:
            w=widget('EditableTextBox');call(w,'SetText',State.encounter_query_draft)
            call(w,'SetHintText','Enemy or boss name...');put(layout,w);size_position(w,left+5,y+96,width-10,39,16)
            call(w,'SetIsReadOnly',False);call(w,'SetIsEnabled',True);State.encounter_input=w
            if not State.controller_mode:attempt(w,'SetKeyboardFocus')
        except Exception:State.encounter_input=None
        actions=(('APPLY SEARCH',encounter_search),('CANCEL SEARCH',lambda:(setattr(State,'encounter_view','CATALOGUE'),redraw())),
          ('CLEAR SEARCH',lambda:(setattr(State,'encounter_query',''),setattr(State,'encounter_query_draft',''),setattr(State,'encounter_view','CATALOGUE'),redraw())))
        for i,(label,fn) in enumerate(actions):btn(layout,label,left+i*(third+8),y+159,third,36,fn,small=True)
        text(layout,'Enter applies this search only. Escape cancels. Category filtering and pagination also work with the controller.',left+12,y+215,width-24,48,theme_color('dim'),.68)
    elif State.encounter_view=='STATUS':
        actions=(('DEPENDENCY READBACK',encounter_dependency_readback),
          ('CHECK BACKEND FILES',arena_backend_check),('CLEAN OWNED / 2 PRESSES',encounter_cleanup),('CANCEL PENDING',encounter_cancel),('OPEN BMS / ENEMY SPAWNER',open_bms_interface),('BMS HELP / CONSOLE',show_bms_help))
        for i,(label,fn) in enumerate(actions):btn(layout,label,left+(i%2)*(half+12),y+46+(i//2)*43,half,35,fn,small=True,danger=i==2)
        text(layout,'CROWN TRACKED: %d / BUDGET USED: %d OF 6'%(len(State.encounter_owned),State.encounter_budget),left+12,y+190,width-24,29,theme_color('accent'),.75)
        text(layout,'Spawned actors start passive. Bosses: one at a time; distance at least 900 game units. Levels, difficulty and automatic waves are not exposed.',left+12,y+224,width-24,45,theme_color('dim'),.65)
    elif State.encounter_view=='CATALOGUE':
        btn(layout,'FIND / '+(State.encounter_query or 'NAME OR ACTOR CODE'),left,y+41,width,35,encounter_search_open,small=True)
        rows=encounter_rows();pages=max(1,math.ceil(len(rows)/3));State.encounter_page%=pages
        for row,(index,item) in enumerate(rows[State.encounter_page*3:State.encounter_page*3+3]):
            yy=y+86+row*43
            btn(layout,('PIN / ' if item[0] in State.encounter_favorites else '')+item[1],left,yy,width,35,lambda i=index:encounter_select(i),small=True)
        for i,(label,delta) in enumerate((('PREVIOUS',-1),('NEXT / %d OF %d'%(State.encounter_page+1,pages),1))):
            btn(layout,label,left+i*(half+12),y+219,half,32,lambda d=delta:(setattr(State,'encounter_page',(State.encounter_page+d)%pages),redraw()),small=True)
    else:
        item=ENCOUNTER_CATALOGUE[State.encounter_selected]
        optional_art_image(layout,'SANDBOX_PLATE',left,y+41,width,47,z=8,opacity=.72)
        text(layout,item[1]+' / '+item[2],left+12,y+49,width-24,27,theme_color('accent'),.83,13)
        if item[2]=='BOSSES':text(layout,'BOSS QUANTITY / 1 / BOUNDED SINGLE SPAWN',left+12,y+111,width-24,32,theme_color('text'),.77)
        else:slider(layout,'ENCOUNTER QUANTITY / DRAFT',State.encounter_quantity,1,3,left,y+90,width,lambda v:encounter_stage('quantity',round(v)))
        slider(layout,'SPAWN DISTANCE / GAME UNITS',State.encounter_distance,900 if item[2]=='BOSSES' else 350,2000,left,y+167,width,lambda v:encounter_stage('distance',v))
        spawn_ready=encounter_backend() is not None and sandbox_solo_ready()
        for i,(label,fn) in enumerate((('SPAWN / 2 PRESSES',encounter_request),('PIN ENCOUNTER',encounter_favorite),('CANCEL PENDING',encounter_cancel))):
            caption=(('SPAWN / 2x (BMS)' if spawn_ready else 'SPAWN BLOCKED / BMS') if i==0 else label)
            btn(layout,caption,left+i*(third+8),y+248,third,30,fn,small=True,disabled=(i==0 and not spawn_ready))
    text(layout,_status_brief(State.encounter_status,94),left+10,y+282,width-20,31,theme_color('dim'),.62)
    # Compact truthful footer; full external dependency diagnostics are under STATUS.
    # Do not trigger per-frame native imports or checksum scans when rendering.

def echo_feedback(event):
    now=time.monotonic()
    if now-State.echo_feedback_at<.35:return False
    State.echo_feedback_at=now
    cue={'apply':'confirm','failure':'warn','encounter':'confirm','confirm':'select','slider':'hover'}.get(event)
    if cue:play_ui_sound(cue)
    if event=='failure':_queue_toast('BLOCKED')
    elif event=='confirm':_queue_toast('CONFIRM')
    if State.echo_personality and event in ('apply','encounter'):
        # Context only; never substitutes for actual backend result reporting.
        _queue_toast('CROWN_SANDBOX' if event=='apply' else 'CROWN_ENCOUNTER')
    return True

def _echo_scan_tick_r3():
    # One existing Border, 12 Hz, no rebuild/texture import/tick hook additions.
    if State.echo_scan is None or State.echo_scan_generation!=State.frame_generation:return
    if State.safe_mode or State.reduced_motion:return
    now=time.monotonic()
    if now-State.echo_scan_at<1/12:return
    State.echo_scan_at=now
    x,y,w,h=State.panel_rect[:4]
    progress=((now-State.transition_started)%2.8)/2.8
    size_position(State.echo_scan,x+w-58,y+140+progress*max(1,h-330),25,2,7)



ART_FILES['R3_HEADER']='R3_HEADER.png'
ART_SHA256['R3_HEADER']='ff8ee98f6227ca588c1008cb4ac692a11beebcd17ffd4336187ddea9099983c6'
ART_FILES['R3_CARD']='R3_CARD.png'
ART_SHA256['R3_CARD']='6cd64d41cf6a29f655b4e43236766b15c7aaeade7cf20c354849ae55962ce333'
ART_FILES['R3_DOCK']='R3_DOCK.png'
ART_SHA256['R3_DOCK']='067484b636b1e2dd4141a8bcdbd7df954e25644d7987dee3c99d694cf1cec00d'
ART_FILES['R3_HOLO']='R3_HOLO.png'
ART_SHA256['R3_HOLO']='bb67c6997613c4c8710b125df1cd851a1bc62efececd6b94243d0f1cdd8c3182'
ART_FILES['R3_PAD_NAV']='R3_PAD_NAV.png'
ART_SHA256['R3_PAD_NAV']='10e27b4bb02ba3f6c9994e85998fca7bc002c6dc8297f8b67e80207273b202c6'
SOUND_HASHES['r3_high_close.wav']='8b4e1bc8d1c3f5d226aff66a846fa27c9ce86cf262271dfade39a3e4229feb5b'
SOUND_HASHES['r3_high_open.wav']='93c6ceeccc25665f3f9708d11f54d3182491e698b1f52598a3a2272d49a97a7e'
SOUND_HASHES['r3_low_close.wav']='4e123067110e6b701fd288821764a6768f4b03085db534465ffe580420da77cb'
SOUND_HASHES['r3_low_open.wav']='d55a9bc0211eaf41ee8ea41287b6b5566c7fe7be8b5a43f125eeee3d9a7fef0a'
SOUND_HASHES['r3_normal_close.wav']='9e77520ef41de924d8a87c1b58101213b7c8a319602e019b2ad09c0e105cd580'
SOUND_HASHES['r3_normal_open.wav']='8d955bb526967b5aed489c4e251ead90ab9e605bbe3d069cccd86e7081e58d0f'
# ECHO Full Studio R3. No display-mode, resolution or renderer settings writes.
STUDIO_SECTIONS={
 'Dashboard':('DASHBOARD',),
 'Player & Combat':('PLAYER','MOTION','BOOSTS','COMBAT','PRESETS'),
 'Forge & Equipment':('SPAWN','GEAR','CAPACITY'),
 'Loot & Progress':('LOOT','WEEKLY','TROPHIES'),
 'Encounter & World':('ARENA','WORLD','EVENTS','PARTY'),
 'Travel & Utilities':('WAYPOINTS',),
 'HUD & Appearance':('STYLE','DISPLAY'),
 'Profiles & Settings':('PROFILES','GUIDE','FINDER','COMMUNITY'),
 'Diagnostics':('DEV','CONTENT'),
}
State.r3_context_rect=None
State.dock_view='QUICK'
State.dock_width=430.
State.dock_opacity=.78
State.dock_vertical=.5
State.dock_compact=False
State.dock_favorites=['GOD','SKILL','FORGE','BOOSTS','TRAVEL','RECOVERY']
State.dock_pick=0
State.input_guard_check_at=0.
State.input_guard_readback='UIOnly API accepted; physical gameplay isolation unverified'
State.xp_route='NATIVE'
State.native_xp_adapter=None
State.xp_observation=None
State.xp_observation_status='Take an XP sample before a controlled combat reward.'
State.forge_compare=None
State.forge_compare_view=False
State.forge_request_history=[]
State.encounter_history=[]
State.weapon_view=False
State.weapon_group=0
State.weapon_choices=[]
State.weapon_index=0
State.weapon_scan_anchor=None
State.weapon_baselines={}
State.weapon_draft={}
State.weapon_owned={}
State.weapon_confirm=None
State.weapon_status='READ OWNED WEAPONS / source-grounded reflected fields only.'
WEAPON_FIELDS={
 'RATE':('firerate','fire',.25,3.,.001,120.,'FIRE RATE FIELD'),
 'RELOAD':('ReloadTime','reload',.25,2.,.03,60.,'RELOAD TIME'),
 'HEAT':('heatimpulse','',0.,2.,0.,100.,'HEAT PER SHOT'),
 'RECOIL':('RecoilScale','',0.,2.,0.,10.,'RECOIL SCALE'),
 'SPREAD':('spread','',0.,2.,0.,100.,'SPREAD FIELD'),
 'ACCURACY':('accuracyimpulse','',0.,2.,0.,100.,'ACCURACY IMPULSE'),
}

def weapon_toggle():
    State.weapon_view=not State.weapon_view;State.weapon_confirm=None;redraw()

def weapon_resolve(key,weapon):
    if key not in WEAPON_FIELDS:return None
    field,kind,*_=WEAPON_FIELDS[key]
    try:
        if not same_unreal_object(getattr(weapon,'Owner',None),pawn()) and not same_unreal_object(getattr(weapon,'OwningCharacter',None),pawn()):return None
        for behavior in list(weapon.behaviors)[:64]:
            if kind and kind not in str(behavior.Class.Name).lower():continue
            if _native_address(behavior) is None:continue
            value=getattr(behavior,field,None)
            if type(value) is float and math.isfinite(value):return behavior,(),(value,)
            if value is not None and all(type(getattr(value,k,None)) is float and math.isfinite(getattr(value,k)) for k in ('Value','BaseValue')):
                return behavior,('Value','BaseValue'),(value.Value,value.BaseValue)
    except Exception:return None
    return None

def weapon_read():
    if not sandbox_solo_ready():return False
    import itertools
    try:
        State.weapon_owned={k:row for k,row in State.weapon_owned.items() if row['anchor']==_session_anchor()}
        choices=[]
        for weapon in itertools.islice(unrealsdk.find_all('Weapon',False),128):
            if _native_address(weapon) is None:continue
            if any(weapon_resolve(key,weapon) for key in WEAPON_FIELDS):choices.append(weapon)
            if len(choices)>=8:break
        State.weapon_choices=choices;State.weapon_index=min(State.weapon_index,max(0,len(choices)-1))
        State.weapon_scan_anchor=_session_anchor();State.weapon_baselines={};State.weapon_draft={};State.weapon_confirm=None
        if choices:
            selected=choices[State.weapon_index]
            for key in WEAPON_FIELDS:
                resolved=weapon_resolve(key,selected)
                if resolved:
                    behavior,subs,values=resolved;identity=(_native_address(selected),_native_address(behavior),key)
                    owned=State.weapon_owned.get(identity)
                    if owned and (owned['anchor']!=State.weapon_scan_anchor or values!=owned['last']):continue
                    State.weapon_baselines[key]={'weapon':selected,'behavior':behavior,'subs':subs,'read':values,
                        'original':owned['original'] if owned else values,'identity':identity}
            label=str(getattr(selected,'Name','Owned weapon'))[:48]
            State.weapon_status='READ / %d OF %d / %s / %d fields / game effect unverified.'%(State.weapon_index+1,len(choices),label,len(State.weapon_baselines))
        else:State.weapon_status='UNAVAILABLE / No owned Weapon behaviours with supported float fields.'
        log('WEAPON LAB // '+State.weapon_status)
        redraw();return bool(choices)
    except Exception as error:
        State.weapon_choices=[];State.weapon_baselines={};State.weapon_status='READ FAILED / '+type(error).__name__;redraw();return False

def weapon_next():
    State.weapon_index=(State.weapon_index+1)%max(1,len(State.weapon_choices));return weapon_read()

def weapon_stage(key,value):
    if key not in State.weapon_baselines or type(value) not in (int,float) or not math.isfinite(value) or not WEAPON_FIELDS[key][2]<=value<=WEAPON_FIELDS[key][3]:return False
    if State.weapon_scan_anchor!=_session_anchor():return False
    State.weapon_draft[key]=float(value);State.weapon_confirm=None
    return True

def _weapon_assign(row,values):
    resolved=weapon_resolve(row['identity'][2],row['weapon'])
    if (_session_anchor()!=row.get('anchor',State.weapon_scan_anchor) or resolved is None or
        not same_unreal_object(resolved[0],row['behavior']) or resolved[1]!=row['subs']):raise RuntimeError('Weapon ownership changed')
    field=WEAPON_FIELDS[row['identity'][2]][0]
    if row['subs']:
        holder=getattr(row['behavior'],field)
        for sub,value in zip(row['subs'],values):setattr(holder,sub,value)
    else:setattr(row['behavior'],field,values[0])

def weapon_apply():
    if not sandbox_solo_ready() or _session_anchor()!=State.weapon_scan_anchor or not State.weapon_draft:return False
    import sys
    if 'bl4_live' in sys.modules:
        State.weapon_status='BLOCKED / BL4Live loaded; use one weapon-tuning owner.';log('WEAPON LAB // '+State.weapon_status);redraw();return False
    planned=[]
    for key,mult in State.weapon_draft.items():
        row=State.weapon_baselines.get(key)
        if not row:return False
        resolved=weapon_resolve(key,row['weapon'])
        if resolved is None or not same_unreal_object(resolved[0],row['behavior']) or resolved[1]!=row['subs'] or resolved[2]!=row['read']:
            State.weapon_status='BLOCKED / Owned weapon or value changed; Read again.';log('WEAPON LAB // '+State.weapon_status);redraw();return False
        desired=tuple(v*mult for v in row['original'])
        if not all(math.isfinite(v) and WEAPON_FIELDS[key][4]<=v<=WEAPON_FIELDS[key][5] for v in desired):
            State.weapon_status='BLOCKED / Result outside bounded native-field range.';log('WEAPON LAB // '+State.weapon_status);redraw();return False
        planned.append((key,row,desired))
    token=(_session_anchor(),tuple((row['identity'],desired) for key,row,desired in planned));now=time.monotonic()
    if State.weapon_confirm is None or State.weapon_confirm[0]!=token or now>=State.weapon_confirm[1]:
        State.weapon_confirm=(token,now+6.);State.weapon_status='CONFIRM / Apply the same draft again within 6 seconds.';log('WEAPON LAB // '+State.weapon_status);redraw();return False
    State.weapon_confirm=None;written=[]
    try:
        for key,row,desired in planned:
            # Record attempted writes BEFORE assignment so partial pair writes
            # remain included in rollback and the ownership ledger.
            written.append((key,row,desired))
            State.weapon_owned[row['identity']]=dict(row,anchor=State.weapon_scan_anchor,last=desired)
            _weapon_assign(row,desired)
            if weapon_resolve(key,row['weapon'])[2]!=desired:raise RuntimeError('Weapon readback disagrees')
        State.weapon_draft={};State.weapon_status='APPLIED / %d owned weapon fields readback verified; gameplay unverified.'%len(written)
        weapon_read();echo_feedback('apply');return True
    except Exception as error:
        failed=0
        for key,row,desired in reversed(written):
            try:
                current=weapon_resolve(key,row['weapon'])
                if current is None or any(v not in (old,new) for v,old,new in zip(current[2],row['read'],desired)):raise RuntimeError('Weapon changed outside batch')
                _weapon_assign(row,row['read'])
                if weapon_resolve(key,row['weapon'])[2]!=row['read']:raise RuntimeError('rollback refused')
                prior=State.weapon_owned.get(row['identity'])
                if row['read']==row['original']:State.weapon_owned.pop(row['identity'],None)
                elif prior:prior['last']=row['read']
            except Exception:failed+=1
        State.weapon_status='FAILED / '+('Rollback unconfirmed on %d fields; Read/Restore required.'%failed if failed else 'Batch rolled back; draft retained.')
        log('WEAPON LAB // '+State.weapon_status);record_runtime_fault('WEAPON_APPLY',error);redraw();return False

def weapon_restore():
    if not sandbox_solo_ready():return False
    restored=0
    for identity,row in list(State.weapon_owned.items()):
        if row['anchor']!=_session_anchor():continue
        key=identity[2];resolved=weapon_resolve(key,row['weapon'])
        if resolved is None or not same_unreal_object(resolved[0],row['behavior']) or resolved[2]!=row['last']:continue
        try:
            _weapon_assign(row,row['original'])
            if weapon_resolve(key,row['weapon'])[2]==row['original']:
                State.weapon_owned.pop(identity,None);restored+=1
        except Exception as error:record_runtime_fault('WEAPON_RESTORE',error)
    State.weapon_status='RESTORE / %d verified / %d retained or ownership changed.'%(restored,len(State.weapon_owned))
    State.weapon_draft={};State.weapon_confirm=None;log(State.weapon_status);redraw();return restored>0

def draw_weapon_lab(layout,left,y,width):
    third=(width-16)/3
    actions=(('READ / '+str(len(State.weapon_choices))+' ACTORS',weapon_read),('NEXT OWNED WEAPON',weapon_next),('VALUES' if State.weapon_detail else 'PRESETS / DETAILS',lambda:(setattr(State,'weapon_detail',not State.weapon_detail),redraw())))
    for i,(label,fn) in enumerate(actions):btn(layout,label,left+i*(third+8),y,third,34,fn,small=True)
    if State.weapon_detail:
        half=(width-12)/2
        for i,name in enumerate(('FACTORY','CONTROL','QUICK HANDS','COOL RUNNING')):
            btn(layout,'STAGE / '+name,left+i%2*(half+12),y+49+i//2*45,half,36,lambda n=name:weapon_preset(n),small=True)
        btn(layout,'SAVE / LOAD WEAPON RECIPES',left,y+147,width,36,lambda:recipe_open('WEAPON'),small=True)
        text(layout,'LAST READ  >  DRAFT TARGET / FIELD UNITS',left+10,y+189,width-20,21,theme_color('highlight'),.66)
        for i,(key,row) in enumerate(State.weapon_baselines.items()):
            target=row['original'][0]*State.weapon_draft[key] if key in State.weapon_draft else row['read'][0]
            text(layout,'%s / %g > %g'%(key,row['read'][0],target),left+(i//3)*(half+12)+10,y+213+(i%3)*20,half-20,19,theme_color('text'),.66)
        if not State.weapon_baselines:text(layout,'Read an owned weapon; no Forge receipt is inferred.',left+10,y+216,width-20,43,theme_color('dim'),.74)
    else:
        keys=tuple(WEAPON_FIELDS)[State.weapon_group*3:State.weapon_group*3+3]
        for i,key in enumerate(keys):
            row=State.weapon_baselines.get(key);spec=WEAPON_FIELDS[key];yy=y+43+i*77
            if row is None or not any(row['original']):text(layout,spec[6]+' / UNAVAILABLE / READ FIRST',left+12,yy+16,width-24,31,theme_color('dim'),.70)
            else:
                ratio=row['read'][0]/row['original'][0] if row['original'][0] else 1.
                label=spec[6]+' / READ %g'%row['read'][0]
                slider(layout,label,State.weapon_draft.get(key,ratio),spec[2],spec[3],left,yy,width,lambda v,k=key:weapon_stage(k,v))
    quarter=(width-24)/4
    for i,(label,fn) in enumerate((('APPLY / CONFIRM',weapon_apply),('RESTORE OWNED',weapon_restore),('CANCEL DRAFT',weapon_cancel_draft),('FIRE / HANDLING',lambda:(setattr(State,'weapon_group',1-State.weapon_group),redraw())))):
        btn(layout,label,left+i*(quarter+8),y+281,quarter,32,fn,small=True,disabled=(i==0 and not State.weapon_draft) or (i==1 and not State.weapon_owned) or (i==2 and not State.weapon_draft))


def r3_open_tool(page,view=None):
    def act():
        show_page(page)
        if view=='SANDBOX':State.sandbox_view=True
        elif view=='XP':State.xp_view=True
        if State.dock_mode=='SIDE':State.dock_mode='FULL'
        redraw()
    return _ui_batch(act)


def _dock_actions_r3():
    # Saved IDs select fixed local callables, never persisted Python or commands.
    return {
      'GOD':('GOD MODE / '+('ON' if State.god else 'OFF'),lambda:(set_god(),redraw())),
      'SKILL':('REFILL SKILL',refill_skills),
      'BOOSTS':('BOOSTS / F5 FLIGHT',lambda:r3_open_tool('BOOSTS')),
      'FORGE':('ITEM FORGE',lambda:r3_open_tool('SPAWN')),
      'DIRECTOR':('ENCOUNTERS',lambda:r3_open_tool('ARENA')),
      'SANDBOX':('COMBAT TUNING',lambda:r3_open_tool('COMBAT','SANDBOX')),
      'XP':('XP LAB (TEST)',lambda:r3_open_tool('LOOT','XP')),
      'INVENTORY':('BAG / BANK',lambda:r3_open_tool('CAPACITY')),
      'TRAVEL':('TELEPORTS',lambda:r3_open_tool('WAYPOINTS')),
      'STYLE':('APPEARANCE',lambda:r3_open_tool('STYLE')),
      'PROFILES':('UI PROFILES',lambda:r3_open_tool('PROFILES')),
      'SEARCH':('FIND A TOOL',lambda:r3_open_tool('FINDER')),
      'RECOVERY':('HELP / STATUS',lambda:r3_open_tool('GUIDE')),
    }

def _dock_favorites_valid(raw):
    if not isinstance(raw,list):return ['GOD','SKILL','FORGE','TRAVEL','STYLE','RECOVERY']
    allowed={'BOOSTS','GOD','SKILL','FORGE','DIRECTOR','SANDBOX','XP','INVENTORY','TRAVEL','STYLE','PROFILES','SEARCH','RECOVERY'}
    clean=[]
    for key in raw[:24]:
        if isinstance(key,str) and key in allowed and key not in clean:clean.append(key)
    return clean[:6]

def dock_pin_action():
    key=tuple(_dock_actions_r3())[State.dock_pick%len(_dock_actions_r3())]
    pins=_dock_favorites_valid(State.dock_favorites)
    State.dock_favorites=([k for k in pins if k!=key] if key in pins else [key]+pins)[:6]
    State.dock_favorites=_dock_favorites_valid(State.dock_favorites)
    save_preferences();redraw()

def dock_stage(key,value):
    if key not in ('width','opacity','vertical') or type(value) not in (int,float) or not math.isfinite(value):return False
    lo,hi={'width':(360.,560.),'opacity':(.3,.95),'vertical':(0.,1.)}[key]
    if not lo<=value<=hi:return False
    setattr(State,'dock_'+key,float(value));save_preferences();redraw();return True

def dock_view(view):
    if view not in ('QUICK','TOOLS','FARM','STYLE'):return False
    State.dock_view=view;State.controller_focus=-1;redraw();return True


def r3_draw_context(layout,rect):
    if rect is None:return
    x,y,w,h=rect
    box(layout,x+4,y+5,w,h,(0.,0.,0.,.21),5)
    box(layout,x,y,w,h,theme_color('panel')[:3]+(.66,),6)
    optional_art_image(layout,'R4_PLATE',x,y,w,h,z=7,opacity=.61)
    optional_art_image(layout,'R3_HOLO',x+5,y+5,w-10,h-10,z=7,opacity=.15)
    text(layout,'FIELD NOTES / '+studio_section_for(State.page).upper(),x+20,y+18,w-40,30,theme_color('accent'),.91,10)
    text(layout,'CURRENT STATE / DIRECT TOOLS',x+20,y+53,w-40,24,theme_color('highlight'),.67,10)
    readouts=[]
    if State.page in ('PLAYER','MOTION','COMBAT'):
        readouts=[('SESSION',session_role()),('OWNED TUNING',str(len(State.combat_last))+' pairs'),('STAGED VALUES',str(len(State.sandbox_stage))),('INPUT',State.input_guard_readback)]
        actions=(('GAMEPLAY SANDBOX',lambda:r3_open_tool('COMBAT','SANDBOX')),('RESOURCE LAB',lambda:(show_page('COMBAT'),setattr(State,'resource_view',True),redraw())),('MOVEMENT',lambda:show_page('MOTION')))
    elif State.page=='LOOT' and State.r10_view is not None:
        readouts=[('WORKSPACE',State.r10_view),('RESULT',State.r10_status if State.r10_view!='BONUS' else State.r10_bonus_status),('RESTORATION','Levels/points can persist; no save rollback. Timed bonuses restore only owned fields.')]
        if State.r10_view in ('LEVELS','POINTS'):
            actions=tuple(('STAGE +%d'%n,lambda amount=n:r16_progress_increment(amount)) for n in (1,5,10))
        else:
            actions=(('READ LIVE TRACK',studio_read),('XP MULTIPLIER',lambda:r3_open_tool('LOOT','XP')),('TIMED BONUS',lambda:studio_open('BONUS')))
    elif State.page=='LOOT' and not State.xp_view:
        readouts=[('WALLET REQUESTS',str(State.wallet_requests)),('LAST REQUEST',State.wallet_last),('READBACK','Cash '+str(wallet_balance('cash'))+' / Eridium '+str(wallet_balance('eridium'))+' / None means unavailable')]
        actions=(('PLAYER LAB',studio_open),('XP MULTIPLIER',lambda:r3_open_tool('LOOT','XP')),('CLEAR CONFIRMATION',wallet_clear))
    elif State.page=='LOOT':
        readouts=[('XP SOURCE', 'XP ADD-ON' if State.xp_external_view else State.xp_route),('CONFIGURATION',State.xp_status),('EARNED REWARD',State.xp_observation_status)]
        actions=(('XP CONTROLS',lambda:r3_open_tool('LOOT','XP')),('SAMPLE EARNED XP',xp_sample),('CLEAR XP SAMPLE',xp_sample_clear))
    elif State.page=='ARENA' and State.encounter_route=='ARENA':
        readouts=[('SOURCE','Reviewed BL4 Arena 1.0.5'),('LIFECYCLE',State.arena_bridge_status),('CLEANUP','Arena owns actors and spawners. CROWN never destroys them.')]
        actions=(('READ LIFECYCLE',arena_bridge_read),('BROWSE ARENA',lambda:(setattr(State,'encounter_view','CATALOGUE'),redraw())),('CHANGE SOURCE',encounter_route_toggle))
    elif State.page=='ARENA':
        readouts=[('DIRECTOR',State.encounter_status),('CROWN OWNED',str(len(State.encounter_owned))),('WORLD BUDGET',str(State.encounter_budget)+' / 6')]
        actions=(('STAGED ENCOUNTER',lambda:(setattr(State,'encounter_view','CONTROLS'),redraw())),('HISTORY / CLEANUP',lambda:(setattr(State,'encounter_view','STATUS'),redraw())),('WORLD SPEED',lambda:show_page('WORLD')))
    elif State.page=='CAPACITY':
        readouts=[('CONTAINER',State.capacity_mode),('BAG',str(State.capacity_readback.get('BackpackItems','READ FIRST')) if State.capacity_readback_anchor==_session_anchor() and time.monotonic()-State.capacity_readback_at<=30 else 'READ FIRST'),('BANK',str(State.capacity_readback.get('BankItems','READ FIRST')) if State.capacity_readback_anchor==_session_anchor() and time.monotonic()-State.capacity_readback_at<=30 else 'READ FIRST'),('BRIDGE',State.capacity_status)]
        actions=(('READ BAG / BANK',lambda:capacity_queue_request('READ')),('STAGE 50 SLOTS',lambda:capacity_set_draft(50)),('STAGE 250 SLOTS',lambda:capacity_set_draft(250)))
    elif State.page=='WORLD':
        readouts=[('WORLD SPEED','%gx'%State.speed),('BOOKMARKS',str(len(State.checkpoints))),('SESSION',session_role())]
        actions=(('ENCOUNTER DIRECTOR',lambda:show_page('ARENA')),('TRAVEL BOOKMARKS',lambda:show_page('WAYPOINTS')),('RESTORE MOVEMENT',restore_motion))
    elif State.page=='GEAR':
        readouts=[('WEAPON LAB',State.weapon_status),('LAST OWNED-ACTOR SCAN',str(len(State.weapon_choices))),('OWNED FIELDS',str(len(State.weapon_owned)))]
        actions=(('OPEN WEAPON LAB',lambda:(setattr(State,'weapon_view',True),redraw())),('READ OWNED WEAPONS',weapon_read),('RESTORE OWNED FIELDS',weapon_restore))
    else:return
    if h>=600:
        optional_art_image(layout,r12_context_art(State.page),x+16,y+86,w-32,105,z=8,opacity=.74)
    yy=y+(203 if h>=600 else 94)
    for label,value in readouts:
        text(layout,label,x+20,yy,w-40,22,theme_color('highlight'),.63,10)
        text(layout,str(value),x+20,yy+25,w-40,54 if h>=550 else 32,theme_color('text'),.76,10)
        yy+=90 if h>=550 else 74
    if yy+len(actions)*43<y+h-20:
        for label,fn in actions:
            btn(layout,label,x+16,yy,w-32,35,fn,small=True);yy+=43
    if State.page=='ARENA' and yy+95<y+h:
        recent=State.encounter_history[-2:]
        text(layout,'RECENT RESULTS\n'+'\n'.join(recent),x+20,yy+7,w-40,81,theme_color('dim'),.63,10)

class NativeCombatXP:
    """Own one opaque SDK modifier; no offsets, hooks, global-mod reset or saves.

    Contracts: reviewed BL4Live source + installed FGbxDefPtr SDK declaration.
    Removal must refresh to the captured baseline or further writes stop.
    """
    def __init__(self,actor,anchor,library,definition):
        self.actor=actor;self.actor_address=_native_address(actor);self.anchor=anchor;self.library=library;self.definition=definition
        self.handle=None;self.original=None;self.expected=None;self.unresolved=False;self.unknown_handle=False
        self._RUNTIME_STATE={'experience_reward_scale':1.}
        self._RUNTIME_REGISTRY={'xp_scale':1.}
    def _runtime_pawn(self):
        if _session_anchor()==self.anchor and same_unreal_object(self.actor,pawn()):return self.actor
        return None
    def _runtime_combat_xp_value(self):
        if self._runtime_pawn() is None:return None
        try:
            value=self.library.GetValueOfAttribute(AttributeDef='Att_CombatXP_Multiplier',ContextSource=self.actor,DefaultValue=-1.)
            return float(value) if type(value) in (int,float) and math.isfinite(value) and 0<value<=10000 else None
        except Exception:return None
    def _runtime_set_combat_xp_scale(self,value):
        if not sandbox_solo_ready() or self._runtime_pawn() is None or type(value) not in (int,float) or not math.isfinite(value) or not 1<=value<=10:return {'ok':False}
        if self.unknown_handle:return {'ok':False,'error':'Unrecognised native result; reload the character before retrying'}
        current=self._runtime_combat_xp_value()
        if current is None:return {'ok':False}
        if value!=1. and not self.unresolved and self.expected is not None and abs(current-self.expected)>max(.01,abs(self.expected)*.01):return {'ok':False,'error':'Attribute changed outside CROWN'}
        if self.unresolved:
            if self.handle is None and self.original is not None and abs(current-self.original)<=max(.01,abs(self.original)*.01):
                self.unresolved=False;self.expected=None
                self._RUNTIME_STATE['experience_reward_scale']=1.;self._RUNTIME_REGISTRY['xp_scale']=1.
            elif self.handle is None or value!=1.:return {'ok':False,'error':'Native removal or refresh remains unresolved'}
        if self.handle is not None:
            try:
                result=self.library.RemoveModifierFromGbxAttribute(ModifierHandle=self.handle,ModifierActionResult=0)
                if not isinstance(result,tuple) or len(result)<2:
                    self.unresolved=True;self.unknown_handle=True;return {'ok':False,'error':'Unrecognised removal result; reload character'}
                if int(result[-1])!=0:
                    self.handle=result[-2];return {'ok':False,'error':'Modifier removal refused'}
                self.handle=None
            except Exception:
                self.unresolved=True;self.unknown_handle=True;return {'ok':False,'error':'Modifier removal raised; reload character'}
            after=self._runtime_combat_xp_value()
            if after is None or abs(after-self.original)>max(.01,abs(self.original)*.01):
                self.unresolved=True;self.expected=None
                return {'ok':False,'error':'Native baseline refresh not confirmed'}
            self.expected=None;self.unresolved=False;self._RUNTIME_STATE['experience_reward_scale']=1.;self._RUNTIME_REGISTRY['xp_scale']=1.
            current=after
        if value==1.:
            self.original=None;return {'ok':True,'value':1.}
        self.original=current
        try:
            result=self.library.AddModifierToGbxAttribute(attribute=self.definition,ContextSource=self.actor,ModifierType=3,modifiervalue=float(value),bAutoRefresh=True,ModifierActionResult=0)
            if not isinstance(result,tuple) or len(result)<2 or result[0] is None:
                self.unresolved=True;self.unknown_handle=True;return {'ok':False,'error':'No recognised modifier handle; reload character'}
            self.handle=result[0]
            self._RUNTIME_STATE['experience_reward_scale']=float(value);self._RUNTIME_REGISTRY['xp_scale']=float(value)
            self.expected=current*value
            if int(result[-1])!=0:
                self.unresolved=True;return {'ok':False,'error':'Native modifier action refused; handle retained'}
            return {'ok':True,'value':float(value)}
        except Exception:
            self.unresolved=True;self.unknown_handle=True;return {'ok':False,'error':'Native call raised; reload character before retrying'}

def _native_xp_backend_r7():
    if not sandbox_solo_ready():return None
    import sys
    # The native path never stacks with a loaded external XP owner.
    external=sys.modules.get('bl4_live')
    if external is not None:
        try:
            if external._RUNTIME_XP_MODIFIERS or external._RUNTIME_STATE.get('experience_reward_scale',1.)!=1.:return None
        except Exception:return None
    anchor=_session_anchor()
    adapter=State.native_xp_adapter
    if adapter is not None and adapter.anchor==anchor:return adapter
    if adapter is not None and (adapter.handle is not None or adapter.unresolved) and adapter.actor_address==_native_address(pawn()):return None
    try:
        from unrealsdk.unreal import FGbxDefPtr
        if _native_address(pawn()) is None:return None
        definition=None
        for path in ('/Script/GbxEngine.GbxAttributeDef','/Script/GbxGame.GbxAttributeDef'):
            definition=unrealsdk.find_object('ScriptStruct',path)
            if definition is not None:break
        if definition is None:return None
        library=unrealsdk.find_class('GbxAttributeBlueprintLibrary').ClassDefaultObject
        if not all(callable(getattr(library,k,None)) for k in ('GetValueOfAttribute','AddModifierToGbxAttribute','RemoveModifierFromGbxAttribute')):return None
        pointer=FGbxDefPtr('Att_CombatXP_Multiplier',definition)
        adapter=NativeCombatXP(pawn(),anchor,library,pointer)
        if adapter._runtime_combat_xp_value() is None:return None
        previous=State.native_xp_adapter
        State.native_xp_adapter=adapter
        if State.xp_owner is not None and State.xp_owner['module'] is previous and State.xp_owner['anchor']!=anchor:
            State.xp_owner=None;log('XP OWNER RETIRED // New pawn context; no native call to the old pawn.')
        return adapter
    except Exception:return None

def _xp_backend_r7():
    if State.xp_route=='NATIVE':return native_xp_backend()
    adapter=State.native_xp_adapter
    if adapter is not None and (adapter.handle is not None or adapter.unresolved):return None
    return _xp_reviewed_backend()

def xp_route_toggle():
    return r13_xp_source('NATIVE' if State.xp_route=='BL4LIVE' else 'BL4LIVE')

def _xp_restore_owned_r7():
    adapter=State.native_xp_adapter
    if State.xp_route=='NATIVE' and adapter is not None and State.xp_owner is None and (adapter.handle is not None or adapter.unresolved):
        result=adapter._runtime_set_combat_xp_scale(1.)
        State.xp_status='NATIVE XP / '+('owned handle removed; baseline readback verified' if result.get('ok') else result.get('error','restore refused'))
        log(State.xp_status);redraw();return result.get('ok') is True
    return _xp_restore_reviewed()

def xp_sample_clear():
    State.xp_observation=None;State.xp_observation_status='XP sample cleared.';redraw()

def xp_sample():
    # Native reflected read-only counters, not BL4Live memory offsets.
    if not sandbox_solo_ready():return False
    pc=get_pc(possibly_loading=True)
    try:
        row=pc.PlayerState.ExperienceState[0]
        value=row.ExperiencePoints;level=row.ExperienceLevel
        if type(value) is not int or type(level) is not int or value<0 or not 1<=level<=1000:return False
    except Exception:
        State.xp_observation_status='UNAVAILABLE / Reflected character XP row not exposed.';redraw();return False
    anchor=_session_anchor();previous=State.xp_observation
    State.xp_observation={'anchor':anchor,'xp':value,'level':level,'at':time.monotonic()}
    if previous is None or previous['anchor']!=anchor:
        State.xp_observation_status='BASELINE / level %d / XP %d'%(level,value)
    elif level!=previous['level'] or value<previous['xp']:
        State.xp_observation_status='LEVEL / COUNTER CHANGED / fresh baseline taken.'
    else:State.xp_observation_status='OBSERVED +%d XP / not isolated from quests or other rewards.'%(value-previous['xp'])
    log('XP SAMPLE // '+State.xp_observation_status);redraw();return True

def forge_pin_compare():
    item=forge_inspector_values()
    if item is None:return False
    State.forge_compare={k:item[k] for k in ('name','pool','category','level','quantity')}
    State.forge_compare_view=True;State.spawn_pending=None;redraw();return True

def forge_compare_toggle():
    State.forge_compare_view=not State.forge_compare_view;State.spawn_pending=None;redraw()

def draw_forge_comparison(layout,left,y,width):
    item=forge_inspector_values();pinned=State.forge_compare
    if item is None:return
    half=(width-16)/2
    for i,(label,data) in enumerate((('STAGED RECIPE',item),('PINNED RECIPE',pinned))):
        x=left+i*(half+16)
        box(layout,x,y,half,217,theme_color('panel')[:3]+(.78,),8)
        optional_art_image(layout,'R3_CARD',x,y,half,217,z=9,opacity=.67)
        text(layout,label,x+15,y+13,half-30,23,theme_color('highlight'),.69,12)
        if data is None:
            text(layout,'Pin a catalogue recipe to compare it here.',x+15,y+55,half-30,65,theme_color('dim'),.78,12);continue
        text(layout,data['name'],x+15,y+49,half-30,55,theme_color('accent'),.88,12)
        text(layout,data['category'],x+15,y+108,half-30,25,theme_color('text'),.77,12)
        delta=item['level']-pinned['level'] if pinned is not None else 0
        text(layout,'LEVEL %d / QTY %d'%(data['level'],data['quantity']),x+15,y+145,half-30,26,theme_color('text'),.76,12)
        text(layout,('LEVEL DIFFERENCE %+d'%delta) if i==0 and pinned else 'CATALOGUE DATA / NOT LIVE GEAR STATS',x+15,y+183,half-30,25,theme_color('dim'),.61,12)
    third=(width-16)/3
    for i,(label,fn) in enumerate((('PIN CURRENT RECIPE',forge_pin_compare),('BACK TO WORKBENCH',forge_compare_toggle),('BROWSE / CHANGE ITEM',lambda:(setattr(State,'forge_compare_view',False),forge_toggle_view())))):
        btn(layout,label,left+i*(third+8),y+234,third,36,fn,small=True)
    btn(layout,'INSPECT POOL',left,y+282,half,32,lambda:(setattr(State,'forge_compare_view',False),forge_open_inspector()),small=True)
    btn(layout,'CHECK FORGE API',left+half+16,y+282,half,32,lambda:(forge_preflight(),redraw()),small=True)
    text(layout,'Comparison covers supported recipe metadata only. Damage, rarity, manufacturer and delivered identity are not inferred.',left+12,y+326,width-24,36,theme_color('dim'),.66)

def r3_input_watch(pc,now):
    if now<State.input_guard_check_at or not State.input_mode_owned:return True
    State.input_guard_check_at=now+.25
    if not same_unreal_object(pc,State.input_pc):return False
    for getter,original in (('IsMoveInputIgnored',State.input_move_ignored_original),('IsLookInputIgnored',State.input_look_ignored_original)):
        if original is None:continue
        try:
            if getattr(pc,getter)() is not True:
                State.input_guard_readback='GUARD LOST / menu closed';close_menu();log('INPUT GUARD LOST // Menu closed; use F7 to retry.');return False
        except Exception:
            State.input_guard_readback='GUARD READ FAILED / menu closed';close_menu();return False
    State.input_guard_readback='UIOnly requested / move-look readbacks checked' if State.input_move_ignored_original is not None else 'UIOnly requested / move-look readbacks unavailable'
    return True


def r3_controller_strip(layout,x,y,width):
    """Read-only glyphs above panels; text still works when imports are unavailable."""
    if State.r10_device in ('KEYBOARD','MOUSE'):
        text(layout,r12_input_prompt(),x,y,width,23,theme_color('dim'),.57,9);return
    if width<210:return
    for offset,key,label in ((0,'R3_PAD_NAV','MOVE'),(76,_gamepad_art('PAD_A'),'SELECT'),(166,_gamepad_art('PAD_B'),'BACK')):
        optional_art_image(layout,key,x+offset,y,23,23,z=8,opacity=.95)
        text(layout,label,x+offset+26,y+2,58,21,theme_color('dim'),.52,9)

ART_FILES['FIELD_CARD_FORGE']='CROWN_FIELD_CARD_FORGE.png'
ART_SHA256['FIELD_CARD_FORGE']='7de7eb7f9cd44a862c7aba42f01c4545fbbe8fab528155e39356d2cfdf6d6fe7'
ART_FILES['FIELD_CARD_XP']='CROWN_FIELD_CARD_XP.png'
ART_SHA256['FIELD_CARD_XP']='5cc74ee99838294beb03165fcbe1dfe964c179871a65337f73836c73b3161f0a'
ART_FILES['FIELD_CARD_ARENA']='CROWN_FIELD_CARD_ARENA.png'
ART_SHA256['FIELD_CARD_ARENA']='37e725ab1e82da283b49f7c90f8373203bd8dd16650fb9a8bf3c3d7159706fa8'
ART_FILES['FIELD_CARD_TRAVEL']='CROWN_FIELD_CARD_TRAVEL.png'
ART_SHA256['FIELD_CARD_TRAVEL']='ce2d0d766213ecc1adac21b1e7ea717e978e135a2cb8ce908d369014be7e0fac'
ART_FILES['FIELD_HEADER']='CROWN_FIELD_HEADER.png'
ART_SHA256['FIELD_HEADER']='4f3ef527e48b4e8b73b94e07b626045f5d4bd684c31f0a88e183a4629c7b8ceb'

REVIEWED_OPTIONAL_R8={'bl4_arena': '46c913af35f8787f0bd1b72b51695123ab6fea7ba908f4c8f65e87efbb7b6c5b', 'bl4_arena.arena': 'de31dab666e8fd168b38b9de962bc01bba9e2a78ac16c3f2c2f25dcbcf3a461e', 'bl4_arena.cart': '1975823a959e0c876af8dff7b6bbe1f6eb4b7ead3bf4bff1c8cd5d3e8cf14e70', 'bl4_arena.catalogue': 'e0594bbfd84bda696243a69096c6fef0aa9f0c7e86a0076cc831aefb516b6dfb', 'bl4_arena.catalogue_data': '3accdad350d2a63d2154994bc64aac26ccf32f1977e52eff14d75261042e2313', 'bl4_arena.spawners': '4703bd8a416fb019977eea220f7682c7dcd1aba706ffacfb8da72340eb2fd8be', 'bl4_arena.waves': '5817b8c4e121434e4f42fd6861cfbd283f69a12608fbb4ded237dac4d2c63988', 'bl4_arena.arena_settings': '3b77aa8c115c9ee42a19669e93efff3a81f46490e3d26dc01155613b9efef853', 'bl4_arena.lots': '6b6f7aa975316f17cdf79db3ef36249d88541c50a906683fa4d0ce9b747fbba9', 'bl4_arena.births': '9d01048a65ebcb4f687226728a7e67b02360229a51251b5ce5c7b4e212bad768', 'bl4_arena.limits': '7f353f7b520aab5c321d9d8579be8dca752b8c82e0d44221655d49a3bd137cfa', 'bl4_arena.placement': 'a9908793b5cacc9eb540402b77813b5925ac049a4ea5a7125b1d31d86490d9cf', 'bl4_arena.calls': 'f770db201eedf2917d39717660211880a6f45734f748723fec70e4efc00997b8', 'bl4_arena.moving': 'aa70b44511b08b9c14e391cbc143b683e8521f2ff0b4584305cbc4dba5a240d1', 'bl4_arena.game_pause': 'e07bbf1e48153c2ecff41ec7289ce910da7dd262976a273cc432e16b440e2cce', 'bl4_arena.ground': '77be40551e981e8037fd6fe10212e4c0ec752b41d41ea43d2d70e6c3b9aad33f', 'bl4_arena.allies': '7e464135f15b69e140aa6b5b89f0bf98a668ba14936e80f897567e8c55e43680', 'bl4_arena.budget': '85bccf88a1891536b0db3bb2780c56100586b7583676d13107d841f3e6f73ee3', 'bl4_arena.dome': '1c695ab3ac964121e9afab7b05f8e17232f81058d996d282f8de9bd2f9bbaf9b', 'bl4_arena.dome_watch': '77c7e876062feb47de89a5f4bd8629418d30cd96df7b0d46a7e52e78c24db871', 'bl4_arena.in_play': 'a0ec7c03fac3eace9f4a770c1952b26b08de8626fb298ecbbb1a6fdfb58a1147', 'xp_gain_multiplier': '2631eecc69a5a090eda58b1db01c1a24427da4b0a047b5a8b03097c7694e6f89'}
ART_FILES['R4_DOCK']='R4_DOCK.png'
ART_SHA256['R4_DOCK']='a0fa2454b6edd7e47dc7f6e5557f1d12bcb169c8ebc82e9d3969b978cb0b7b7c'
ART_FILES['R4_HERO']='R4_HERO.png'
ART_SHA256['R4_HERO']='38e3a7829da15d181e3b03d0455dee465f860b7265ec70ff08525f3aa8dd5097'
ART_FILES['R4_ICON_CAPACITY']='R4_ICON_CAPACITY.png'
ART_SHA256['R4_ICON_CAPACITY']='8274f4c4ab6bf0681c7e14a1a9c4e6baf6b52097019f98acfca61f77bfc685ba'
ART_FILES['R4_ICON_COMBAT']='R4_ICON_COMBAT.png'
ART_SHA256['R4_ICON_COMBAT']='d7d649c09c100c0543fb0b03ac77826d0fce56e91436bfbd9348763ed26c9d99'
ART_FILES['R4_ICON_ENCOUNTER']='R4_ICON_ENCOUNTER.png'
ART_SHA256['R4_ICON_ENCOUNTER']='ab019e605a5cc4afdc6fbbd82ccda4a6569fcc4b21f8aa94d1a255602b596472'
ART_FILES['R4_ICON_FORGE']='R4_ICON_FORGE.png'
ART_SHA256['R4_ICON_FORGE']='6e866dcb061be8a8f8587c90973228ac14dee104e270da000ea2185971c7d2f1'
ART_FILES['R4_ICON_MOVEMENT']='R4_ICON_MOVEMENT.png'
ART_SHA256['R4_ICON_MOVEMENT']='28f364b290c26f459ba2b0e19fd19d2a5550a57f001b6c79b80d8acba7f18b51'
ART_FILES['R4_ICON_WEAPON']='R4_ICON_WEAPON.png'
ART_SHA256['R4_ICON_WEAPON']='0d1af5462b83c0e7479b96a1e2c2ca8e01820804b21d43d56c1f6106ead5c8c7'
ART_FILES['R4_ICON_XP']='R4_ICON_XP.png'
ART_SHA256['R4_ICON_XP']='d78d63dea9f88c4fc82b771ca36bb0b70b6dbfb9a1eb35b23de2f22c50fd3290'
ART_FILES['R4_PLATE']='R4_PLATE.png'
ART_SHA256['R4_PLATE']='e0a270493e057c94de6912884a16dedbbb490f766f2ca80dcfa580351cf1d1e5'
# ECHO Production R4: portable staged recipes, owned movement and farming telemetry.
RECIPE_KINDS=('WEAPON','COMBAT','XP','FORGE','ENCOUNTER','CAPACITY','MOVEMENT')
State.recipe_kind='WEAPON'
State.recipe_slot=1
State.recipe_library={}
State.recipe_pending=None
State.recipe_import=None
State.recipe_status='Capture a draft, then save. Loading never applies gameplay changes.'
State.recipe_open=False
State.recipe_return='DASHBOARD'
State.farm_view=False
State.farm_run=None
State.farm_history=[]
State.farm_status='Read-only XP observations. Drops and laps are manual.'
State.motion_last={}
State.motion_anchor=None
State.motion_component=None
State.motion_draft={}
State.motion_status='Stage movement multipliers, then Apply. External changes block restoration.'
State.weapon_detail=False
State.r4_fx_at=0.
State.farm_widgets=[]
State.farm_generation=-1
State.farm_tick_at=0.

def _recipe_validate(kind,raw):
    if kind not in RECIPE_KINDS or not isinstance(raw,dict):raise ValueError('Unknown recipe')
    def number(value,lo,hi,integer=False):
        if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi or (integer and type(value) is not int):raise ValueError('Invalid bounded value')
        return int(value) if integer else float(value)
    def keys(expected):
        if set(raw)!=set(expected):raise ValueError('Unexpected recipe fields')
    if kind in ('WEAPON','COMBAT','MOVEMENT'):
        if not raw:raise ValueError('Empty draft')
        out={}
        for key,value in raw.items():
            if kind=='WEAPON':
                if key not in WEAPON_FIELDS:raise ValueError('Unknown weapon field')
                lo,hi=WEAPON_FIELDS[key][2:4]
            elif kind=='COMBAT':
                if key not in TUNING_FIELDS:raise ValueError('Unknown combat field')
                lo,hi=TUNING_FIELDS[key][2:4]
            else:
                if key not in ('speed','jump','gravity'):raise ValueError('Unknown movement field')
                lo,hi=.3,3.
            out[key]=number(value,lo,hi)
        return out
    if kind=='XP':
        keys(('scale','source'))
        if raw['source'] not in ('NATIVE','BL4LIVE','REWARD'):raise ValueError('Unknown XP source')
        return {'scale':number(raw['scale'],.1 if raw['source']=='REWARD' else 1,10),'source':raw['source']}
    if kind=='FORGE':
        keys(('pool','level','count'))
        if not isinstance(raw['pool'],str) or raw['pool'] not in {r[1] for r in SPAWN_POOLS}:raise ValueError('Unknown curated pool')
        return {'pool':raw['pool'],'level':number(raw['level'],1,100,True),'count':number(raw['count'],1,3,True)}
    if kind=='ENCOUNTER':
        keys(('code','quantity','distance'))
        row=next((r for r in ENCOUNTER_CATALOGUE if r[0]==raw['code']),None)
        if row is None:raise ValueError('Unknown encounter')
        return {'code':row[0],'quantity':number(raw['quantity'],1,1 if row[2]=='BOSSES' else 3,True),'distance':number(raw['distance'],900 if row[2]=='BOSSES' else 350,2000)}
    keys(('container','slots'))
    if raw['container'] not in ('BACKPACK','BANK'):raise ValueError('Unknown container')
    return {'container':raw['container'],'slots':number(raw['slots'],20,5000,True)}

def _recipe_library_validate(raw,strict=False):
    if not isinstance(raw,dict) or len(raw)>7:raise ValueError('Invalid recipe library')
    clean={}
    for kind,slots in raw.items():
        if kind not in RECIPE_KINDS or not isinstance(slots,dict) or len(slots)>6:raise ValueError('Unknown library group')
        clean[kind]={}
        for slot,record in slots.items():
            try:
                if slot not in ('1','2','3','4','5','6') or not isinstance(record,dict) or set(record)!= {'name','values'}:raise ValueError('Invalid slot')
                name=record['name']
                if not isinstance(name,str) or not 1<=len(name)<=32 or any(ord(c)<32 for c in name):raise ValueError('Invalid name')
                clean[kind][slot]={'name':name,'values':_recipe_validate(kind,record['values'])}
            except (ValueError,TypeError,KeyError,OverflowError):
                if strict:raise
    return clean

def recipe_capture(kind):
    if kind=='WEAPON':
        if State.weapon_scan_anchor!=_session_anchor():raise ValueError('Read the current weapon first')
        raw=dict(State.weapon_draft)
        if not raw:
            raw={k:r['read'][0]/r['original'][0] for k,r in State.weapon_baselines.items() if r['original'][0]}
    elif kind=='COMBAT':
        if State.sandbox_anchor!=_session_anchor():raise ValueError('Stage a current combat draft first')
        raw=dict(State.sandbox_stage)
    elif kind=='XP':raw={'scale':State.external_xp_draft if State.xp_external_view else State.xp_draft,'source':'REWARD' if State.xp_external_view else State.xp_route}
    elif kind=='FORGE':
        item=_forge_selection()
        if item is None:raise ValueError('Select a Forge pool first')
        raw={'pool':item[1],'level':State.spawn_level,'count':State.spawn_count}
    elif kind=='ENCOUNTER':raw={'code':ENCOUNTER_CATALOGUE[State.encounter_selected][0],'quantity':State.encounter_quantity,'distance':State.encounter_distance}
    elif kind=='CAPACITY':raw={'container':State.capacity_mode,'slots':State.capacity_draft}
    else:raw=dict(State.motion_draft) or {'speed':State.motion_scale,'jump':State.jump_selected,'gravity':State.gravity_selected}
    return _recipe_validate(kind,raw)

def recipe_open(kind=None):
    if kind in RECIPE_KINDS:State.recipe_kind=kind
    if not State.recipe_open:State.recipe_return=State.page
    State.recipe_pending=None;State.recipe_import=None;State.recipe_open=True;State.farm_view=False
    def action():
        show_page('PROFILES');State.recipe_open=True;State.dock_mode='FULL';redraw()
    _ui_batch(action)

def recipe_close():
    target=State.recipe_return;State.recipe_open=False;State.recipe_pending=None;State.recipe_import=None
    show_page(target if target!='PROFILES' else 'PROFILES')

def recipe_cycle(step):
    State.recipe_kind=RECIPE_KINDS[(RECIPE_KINDS.index(State.recipe_kind)+step)%len(RECIPE_KINDS)]
    State.recipe_pending=None;State.recipe_import=None;redraw()

def _recipe_confirm(token):
    now=time.monotonic()
    if State.recipe_pending is None or State.recipe_pending[0]!=token or now>=State.recipe_pending[1]:
        State.recipe_pending=(token,now+6);State.recipe_status='CONFIRM / Press the same action again within six seconds.';return False
    State.recipe_pending=None;return True

def recipe_action(action):
    kind=State.recipe_kind;slot=str(State.recipe_slot)
    try:
        library=_recipe_library_validate(State.recipe_library,True);slots=library.setdefault(kind,{})
        current=slots.get(slot)
        if action=='SAVE':
            values=recipe_capture(kind);record={'name':kind.title()+' / Slot '+slot,'values':values}
            if current and current!=record and not _recipe_confirm(('SAVE',kind,slot,json.dumps(current,sort_keys=True),json.dumps(record,sort_keys=True))):redraw();return False
            slots[slot]=record
        elif action=='DELETE':
            if current is None:return False
            if not _recipe_confirm(('DELETE',kind,slot,json.dumps(current,sort_keys=True))):redraw();return False
            del slots[slot]
        elif action=='DUPLICATE':
            if current is None:return False
            target=str(State.recipe_slot%6+1)
            if slots.get(target) and not _recipe_confirm(('DUPLICATE',kind,slot,target,json.dumps(current,sort_keys=True),json.dumps(slots[target],sort_keys=True))):redraw();return False
            slots[target]=json.loads(json.dumps(current))
        elif action=='LOAD':
            if current is None:return False
            return recipe_stage(kind,current['values'])
        else:return False
        State.recipe_library=library;State.recipe_pending=None;save_preferences()
        State.recipe_status=action+' / '+kind+' slot '+slot+' / local settings only.';echo_feedback('apply');redraw();return True
    except (ValueError,TypeError,KeyError,OverflowError) as error:
        State.recipe_status='RECIPE BLOCKED / '+str(error)[:84];log(State.recipe_status);redraw();return False

def recipe_stage(kind,raw):
    """Validate the complete recipe and every live prerequisite before staging anything."""
    try:
        values=_recipe_validate(kind,raw);anchor=_session_anchor()
        if kind=='WEAPON':
            if anchor is None or State.weapon_scan_anchor!=anchor:raise ValueError('Read an owned weapon before loading')
            for key in values:
                row=State.weapon_baselines.get(key)
                resolved=weapon_resolve(key,row['weapon']) if row else None
                if not row or resolved is None or not same_unreal_object(resolved[0],row['behavior']) or resolved[2]!=row['read']:raise ValueError('Weapon field missing or changed: '+key)
            State.weapon_draft=dict(values);State.weapon_confirm=None;page='GEAR';State.weapon_view=True
        elif kind=='COMBAT':
            if anchor is None or not sandbox_solo_ready():raise ValueError('Local solo character required')
            if any(combat_pair(k) is None for k in values):raise ValueError('One or more live combat fields are unavailable')
            State.sandbox_stage=dict(values);State.sandbox_anchor=anchor;State.sandbox_view=True;State.resource_view=False;page='COMBAT'
        elif kind=='XP':
            if State.r12_xp_attempt is not None or State.r13_xp_job is not None:raise ValueError('Resolve the pending XP request first')
            if values['source']!=('REWARD' if State.xp_external_view else State.xp_route) and (State.xp_owner is not None or (State.native_xp_adapter and (State.native_xp_adapter.handle is not None or State.native_xp_adapter.unresolved))):raise ValueError('Restore the current XP source first')
            State.xp_external_view=values['source']=='REWARD'
            if State.xp_external_view:State.external_xp_draft=values['scale']
            else:State.xp_route=values['source'];State.xp_draft=values['scale']
            State.xp_external_confirm=None;State.xp_view=True;page='LOOT'
        elif kind=='FORGE':
            choice=next(i for i,row in enumerate(SPAWN_POOLS) if row[1]==values['pool'])
            State.spawn_pool_idx=choice;State.spawn_level=values['level'];State.spawn_count=values['count']
            State.spawn_category_idx=SPAWN_CATEGORIES.index('ALL');State.spawn_search='';State.spawn_page=_spawn_visible_indices().index(choice)//max(1,forge_page_capacity())
            State.spawn_pending=None;State.spawn_expires=0.;State.spawn_view='TOOLS';State.forge_compare_view=False;page='SPAWN'
        elif kind=='ENCOUNTER':
            if State.encounter_job is not None or State.arena_bridge_issued is not None:raise ValueError('Resolve the current encounter first')
            State.encounter_route='BMS' # Existing encounter recipes use the BMS catalogue and distance contract.
            State.encounter_selected=next(i for i,row in enumerate(ENCOUNTER_CATALOGUE) if row[0]==values['code'])
            State.encounter_quantity=values['quantity'];State.encounter_distance=values['distance'];State.encounter_confirm=None;State.encounter_view='CONTROLS';page='ARENA'
        elif kind=='CAPACITY':
            if State.capacity_bridge_job is not None:raise ValueError('Wait for the inventory request')
            State.capacity_mode=values['container'];State.capacity_draft=values['slots'];State.capacity_drafts[values['container']]=values['slots'];State.capacity_confirm=None;State.capacity_view='BROWSE';page='CAPACITY'
        else:State.motion_draft=dict(values);page='MOTION'
        State.recipe_open=False;State.recipe_pending=None;State.recipe_import=None
        def commit():
            show_page(page);State.dock_mode='FULL'
            if kind=='COMBAT':State.sandbox_view=True;State.resource_view=False
            elif kind=='XP':State.xp_view=True;State.xp_read=None
            redraw()
        _ui_batch(commit);log('RECIPE STAGED // '+kind+' / Review and use the workspace Apply.');return True
    except (ValueError,TypeError,KeyError,StopIteration,AttributeError) as error:
        State.recipe_status='LOAD BLOCKED / '+str(error)[:86];log(State.recipe_status);redraw();return False

def recipe_transfer(export=False,accept=False):
    if SETTINGS_DIR is None:return False
    path=Path(SETTINGS_DIR)/'CROWNs_Freedom_Recipes.json'
    try:
        if export:
            payload={'format':'CROWN_RECIPES_1','library':_recipe_library_validate(State.recipe_library,True)}
            path.parent.mkdir(parents=True,exist_ok=True);pending=path.with_suffix('.json.tmp')
            pending.write_text(json.dumps(payload,indent=2),encoding='utf-8');pending.replace(path)
            State.recipe_status='EXPORTED / CROWNs_Freedom_Recipes.json in SDK settings.'
        elif accept:
            if State.recipe_import is None:return False
            baseline,incoming=State.recipe_import
            if json.dumps(State.recipe_library,sort_keys=True)!=baseline:raise ValueError('Library changed; preview import again')
            State.recipe_library=json.loads(json.dumps(incoming));State.recipe_import=None;State.recipe_pending=None;save_preferences()
            State.recipe_status='IMPORTED / Library replaced. Gameplay unchanged.'
        else:
            if path.stat().st_size>65536:raise ValueError('Import exceeds 64 KB')
            raw=json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(raw,dict) or set(raw)!= {'format','library'} or raw['format']!='CROWN_RECIPES_1':raise ValueError('Unknown recipe transfer format')
            incoming=_recipe_library_validate(raw['library'],True)
            State.recipe_import=(json.dumps(State.recipe_library,sort_keys=True),incoming)
            State.recipe_status='REVIEW / Replace library with %d validated recipes? Accept Import to continue.'%sum(len(s) for s in incoming.values())
        redraw();return True
    except (OSError,ValueError,TypeError,RecursionError) as error:
        State.recipe_import=None;State.recipe_status='TRANSFER REJECTED / '+str(error)[:80];log(State.recipe_status);redraw();return False

def draw_recipe_library(layout,left,y,width):
    third=(width-16)/3
    for i,(label,fn) in enumerate((('PREVIOUS SYSTEM',lambda:recipe_cycle(-1)),('RECIPES / '+State.recipe_kind,lambda:recipe_cycle(1)),('BACK TO WORKSPACE',recipe_close))):
        btn(layout,label,left+i*(third+8),y,third,34,fn,small=True)
    slots=State.recipe_library.get(State.recipe_kind,{})
    for i in range(6):
        xx=left+(i%3)*(third+8);yy=y+48+(i//3)*56;slot=i+1;record=slots.get(str(slot))
        title=record['name'] if record else 'SLOT %d / EMPTY'%slot
        btn(layout,title,xx,yy,third,45,lambda n=slot:(setattr(State,'recipe_slot',n),setattr(State,'recipe_pending',None),redraw()),active=slot==State.recipe_slot,small=True)
    actions=(('SAVE CURRENT DRAFT',lambda:recipe_action('SAVE')),('LOAD AS DRAFT',lambda:recipe_action('LOAD')),('DUPLICATE TO NEXT',lambda:recipe_action('DUPLICATE')),
             ('DELETE / CONFIRM',lambda:recipe_action('DELETE')),('EXPORT LIBRARY',lambda:recipe_transfer(True)),('ACCEPT IMPORT' if State.recipe_import else 'IMPORT / REVIEW',lambda:recipe_transfer(accept=State.recipe_import is not None)))
    for i,(label,fn) in enumerate(actions):btn(layout,label,left+i%3*(third+8),y+172+i//3*42,third,34,fn,small=True,danger=i==3,disabled=i in (1,2,3) and slots.get(str(State.recipe_slot)) is None)
    text(layout,State.recipe_status,left+10,y+263,width-20,49,theme_color('dim'),.67)
    record=slots.get(str(State.recipe_slot))
    tall=State.panel_rect and State.panel_rect[3]>=1000
    if tall:
        cw=(width-60)/7
        for i,kind in enumerate(RECIPE_KINDS):
            xx=left+i*(cw+10);yy=y+333
            optional_art_image(layout,'R4_PLATE',xx,yy,cw,111,z=7,opacity=.6)
            optional_art_image(layout,'R4_ICON_'+kind,xx+(cw-48)/2,yy+9,48,48,z=9,opacity=.9)
            btn(layout,kind,xx+5,yy+70,cw-10,32,lambda k=kind:recipe_kind_select(k),active=kind==State.recipe_kind,small=True)
    if record and State.panel_rect and State.panel_rect[3]>=850:
        summary='  /  '.join('%s: %s'%(k,'%g'%v if type(v) in (int,float) else v) for k,v in record['values'].items())
        note_panel(layout,'SAVED VALUES / STAGED ONLY',summary,left,y+(462 if tall else 328),width,70)

def _farm_sample():
    pc=get_pc(possibly_loading=True)
    try:
        entry=pc.PlayerState.ExperienceState[0];xp=entry.ExperiencePoints;level=entry.ExperienceLevel
        if type(xp) is not int or type(level) is not int or not 0<=xp<2**63 or not 0<=level<=10000:return None
        anchor=_session_anchor()
        return (anchor,level,xp) if anchor is not None else None
    except Exception:return None

def farm_action(action):
    now=time.monotonic();run=State.farm_run
    if action=='START':
        if run and run['running']:return False
        sample=_farm_sample()
        State.farm_run={'running':True,'anchor':_session_anchor(),'started':now,'elapsed':0.,'lap_at':now,'laps':[],'drops':0,'sample':sample,'xp':0,'xp_valid':sample is not None}
        State.farm_status='RUN STARTED / XP read-only; add drops and lap markers manually.'
    elif not run:return False
    elif action in ('DROP','UNDO'):
        if not run['running']:return False
        run['drops']=max(0,min(99999,run['drops']+(1 if action=='DROP' else -1)))
    elif action in ('LAP','STOP'):
        if not run['running']:return False
        if _session_anchor()!=run['anchor']:
            action='STOP';run['xp_valid']=False;State.farm_status='RUN ENDED / Character or world changed; XP comparison invalid.'
        sample=_farm_sample();initial=run['sample']
        if not initial or not sample or sample[:2]!=initial[:2] or sample[2]<initial[2]:run['xp_valid']=False
        if run['xp_valid']:run['xp']=sample[2]-initial[2]
        run['elapsed']=max(0.,now-run['started'])
        if action=='LAP':
            run['laps']=(run['laps']+[round(max(0.,now-run['lap_at']),2)])[-20:];run['lap_at']=now
            State.farm_status='LAP %d / %.1fs / Observed XP includes every reward source.'%(len(run['laps']),run['laps'][-1])
        else:
            run['running']=False
            State.farm_history=(State.farm_history+[{'seconds':run['elapsed'],'drops':run['drops'],'xp':run['xp'] if run['xp_valid'] else None,'laps':len(run['laps'])}])[-8:]
            if run['xp_valid']:State.farm_status='RUN FINISHED / %.1fs / %d observed XP / %d manual drops.'%(run['elapsed'],run['xp'],run['drops'])
    elif action=='CLEAR':
        if run['running']:State.farm_status='Stop the active run before clearing.';redraw();return False
        State.farm_run=None;State.farm_status='RUN CLEARED / History retained for this session.'
    else:return False
    redraw();return True

def farm_open():
    def act():
        State.recipe_open=False;show_page('PROFILES');State.farm_view=True;State.dock_mode='FULL';redraw()
    _ui_batch(act)

def farm_summary():
    run=State.farm_run
    if not run:return 'IDLE / START A RUN',('TIME / —','LAPS / 0','DROPS / MANUAL','XP / NOT SAMPLED')
    elapsed=max(0.,time.monotonic()-run['started']) if run['running'] else run['elapsed']
    minutes=elapsed/60.
    rate=run['xp']/minutes if minutes>0 and run['xp_valid'] else None
    return ('RUNNING' if run['running'] else 'FINISHED'),('TIME / %.1fs'%elapsed,'LAPS / %d'%len(run['laps']),'MANUAL DROPS / %d'%run['drops'],'OBSERVED XP / %s'%run['xp'] if run['xp_valid'] else 'XP / UNAVAILABLE',('XP / MIN / %.1f'%rate if rate is not None else 'XP / MIN / —'))

def draw_farm_workspace(layout,left,y,width,compact=False):
    status,values=farm_summary();half=(width-10)/2
    State.farm_widgets=[];State.farm_generation=State.frame_generation
    for i,line in enumerate(values[:4]):
        xx=left+(i%2)*(half+10);yy=y+(i//2)*55
        box(layout,xx,yy,half,46,theme_color('panel'),7)
        State.farm_widgets.append(text(layout,line,xx+10,yy+10,half-20,29,theme_color('accent') if i==0 else theme_color('text'),.72,9))
    actions=(('START NEW RUN',lambda:farm_action('START')),('LAP / SAMPLE XP',lambda:farm_action('LAP')),('STOP / SAMPLE XP',lambda:farm_action('STOP')),('MANUAL DROP +1',lambda:farm_action('DROP')),('UNDO DROP',lambda:farm_action('UNDO')),('CLEAR STOPPED RUN',lambda:farm_action('CLEAR')))
    for i,(label,fn) in enumerate(actions):btn(layout,label,left+(i%2)*(half+10),y+122+(i//2)*43,half,35,fn,small=True)
    text(layout,status+' / '+State.farm_status,left+8,y+260,width-16,50,theme_color('dim'),.64)
    if not compact and State.panel_rect[3]>=850:
        rows=['%.1fs / %s XP / %d manual drops / %d laps'%(r['seconds'],r['xp'] if r['xp'] is not None else 'unavailable',r['drops'],r['laps']) for r in State.farm_history[-4:][::-1]]
        note_panel(layout,'RECENT RUNS / SESSION ONLY','\n'.join(rows) or 'No completed runs. Telemetry does not spawn enemies, alter loot or infer kills.',left,y+333,width,138)

def weapon_preset(name):
    presets={'FACTORY':{k:1. for k in WEAPON_FIELDS},'CONTROL':{'RECOIL':.6,'SPREAD':.75,'ACCURACY':.75},'QUICK HANDS':{'RATE':1.25,'RELOAD':.8},'COOL RUNNING':{'HEAT':.5}}
    values=presets.get(name)
    if values is None:return False
    available={k:v for k,v in values.items() if k in State.weapon_baselines}
    if not available:State.weapon_status='PRESET UNAVAILABLE / Read supported weapon fields first.';redraw();return False
    return recipe_stage('WEAPON',available)

def weapon_cancel_draft():
    State.weapon_draft={};State.weapon_confirm=None;State.weapon_status='DRAFT CANCELLED / Applied owned values remain until Restore.';redraw()


def draw_motion_workspace(layout,left,y,width):
    for i,(label,key,current) in enumerate((('WALK SPEED','speed',State.motion_scale),('JUMP STRENGTH','jump',State.jump_selected),('GRAVITY','gravity',State.gravity_selected))):
        slider(layout,label+' / DRAFT',State.motion_draft.get(key,current),.3,3.,left,y+i*77,width,lambda v,k=key:motion_stage(k,v))
    quarter=(width-24)/4
    for i,(label,fn) in enumerate((('APPLY DRAFT',motion_apply),('RESTORE OWNED',restore_motion),('CANCEL',lambda:(State.motion_draft.clear(),redraw())),('RECIPES',lambda:recipe_open('MOVEMENT')))):
        btn(layout,label,left+i*(quarter+8),y+241,quarter,38,fn,small=True)
    text(layout,State.motion_status,left+9,y+290,width-18,38,theme_color('dim'),.64)

def motion_stage(key,value):
    if key not in ('speed','jump','gravity') or type(value) not in (int,float) or not math.isfinite(value) or not .3<=value<=3:return False
    State.motion_draft[key]=float(value);return True

def tune_motion(mode,mult):
    actor,component=movement_obj();anchor=_session_anchor()
    if component is None or actor is None or anchor is None:return False
    if State.motion_owner is not None:
        if State.motion_anchor!=anchor or not same_unreal_object(actor,State.motion_owner) or not same_unreal_object(component,State.motion_component):
            State.motion_last={};State.motion_originals={};State.motion_owner=None
        elif any(_read_number(component,k)!=v for k,v in State.motion_last.items()):
            State.motion_status='BLOCKED / Movement changed outside CROWN; owned originals retained.';log(State.motion_status);return False
    ok=_motion_tune_r3(mode,mult)
    if ok:
        State.motion_anchor=anchor;State.motion_component=component
        for key in State.motion_originals:State.motion_last[key]=_read_number(component,key)
    elif not State.motion_originals:State.motion_owner=None
    return ok

def motion_apply():
    draft=dict(State.motion_draft)
    if not draft or not sandbox_solo_ready():return False
    actor,component=movement_obj();anchor=_session_anchor()
    fields={'speed':('MinAnalogWalkSpeed','MaxWalkSpeed'),'jump':('JumpZVelocity',),'gravity':('GravityScale',)}
    before={k:_read_number(component,k) for mode in draft for k in fields[mode]}
    if any(v is None for v in before.values()):State.motion_status='BLOCKED / One or more movement fields unavailable.';redraw();return False
    ownership=(State.motion_owner,dict(State.motion_originals),dict(State.motion_last),State.motion_anchor,State.motion_component,State.motion_scale,State.jump_selected,State.gravity_selected)
    success=True
    def batch():
        nonlocal success
        for mode,value in draft.items():
            if not tune_motion(mode,value):success=False;break
    _ui_batch(batch)
    if not success:
        # Roll back only values still owned by this attempt in the same context.
        failed=[]
        for key,old in before.items():
            try:
                current=_read_number(component,key)
                if current==old:continue
                if _session_anchor()!=anchor or not same_unreal_object(actor,pawn()) or current!=State.motion_last.get(key):raise RuntimeError('Outside movement change')
                setattr(component,key,old)
                if _read_number(component,key)!=old:raise RuntimeError('Movement rollback refused')
            except Exception:failed.append(key)
        if not failed:
            (State.motion_owner,State.motion_originals,State.motion_last,State.motion_anchor,State.motion_component,State.motion_scale,State.jump_selected,State.gravity_selected)=ownership
        State.motion_status='FAILED / '+('Rollback incomplete; Restore retained owned fields.' if failed else 'Batch rolled back; draft retained.')
    else:
        State.motion_draft={};State.motion_status='APPLIED / %d movement modes readback verified; gameplay unverified.'%len(draft);echo_feedback('apply')
    log(State.motion_status);redraw();return success


def encounter_dependency_readback():
    """Already-loaded objects only. Do not import/enable third-party mods or invoke spawn code."""
    import sys
    bms=next((sys.modules[n] for n in ('mob_spawner','bl4_mob_spawner') if n in sys.modules),None)
    oak=sys.modules.get('bl4_oak_spawner')
    world=sys.modules.get('bl4_world_tools.deferred')
    lines=['BMS / '+('MISSING' if bms is None else 'SOURCE MATCH' if _reviewed_module(('mob_spawner','bl4_mob_spawner'),REVIEWED_BMS_SHA) else 'DIFFERENT SOURCE'),
           'OAK SPAWNER / '+('LOADED; CONTRACT UNVERIFIED' if oak else 'MISSING'),
           'WORLD QUEUE / '+('LOADED; METHOD PRESENT' if world and callable(getattr(world,'queue_action',None)) else 'MISSING'),
           'CROWN SPAWN ADAPTER / '+('READY; GAME UNVERIFIED' if encounter_backend() else 'BLOCKED')]
    State.encounter_status=' / '.join(lines);log(State.encounter_status);redraw();return lines

def profile_snapshot():
    value=_profile_snapshot_r3()
    value['studio_dock']={'width':State.dock_width,'opacity':State.dock_opacity,'vertical':State.dock_vertical,'compact':State.dock_compact,'favorites':_dock_favorites_valid(State.dock_favorites),'right':State.dock_right}
    return value

def _profile_dock_validate(raw):
    if raw is None:return None
    if not isinstance(raw,dict) or set(raw)!= {'width','opacity','vertical','compact','favorites','right'}:raise ValueError('Invalid dock profile')
    for key,lo,hi in (('width',360,560),('opacity',.3,.95),('vertical',0,1)):
        if type(raw[key]) not in (int,float) or not math.isfinite(raw[key]) or not lo<=raw[key]<=hi:raise ValueError('Invalid dock '+key)
    if type(raw['compact']) is not bool or type(raw['right']) is not bool or not isinstance(raw['favorites'],list) or _dock_favorites_valid(raw['favorites'])!=raw['favorites']:raise ValueError('Invalid dock preferences')
    return raw

def load_ui_profile(slot):
    try:dock=_profile_dock_validate(State.ui_profiles.get(str(slot),{}).get('studio_dock'))
    except (ValueError,TypeError,AttributeError):log('PROFILE BLOCKED / Invalid Quick Dock preferences.');return False
    ok=False
    def act():
        nonlocal ok
        ok=_load_ui_profile_r3(slot)
        if ok and dock is not None:
            for key in ('width','opacity','vertical','compact','favorites','right'):setattr(State,'dock_'+key,json.loads(json.dumps(dock[key])))
            save_preferences();redraw()
    _ui_batch(act);return ok

def echo_scan_tick():
    _echo_scan_tick_r3()
    now=time.monotonic()
    if State.opened and State.farm_generation==State.frame_generation and now-State.farm_tick_at>=1.:
        State.farm_tick_at=now
        if State.farm_run and State.farm_run['running'] and State.farm_run['anchor']!=_session_anchor():farm_action('STOP');return
        _,values=farm_summary()
        for w,value in zip(State.farm_widgets,values[:4]):call(w,'SetText',value)
    if not State.opened or State.safe_mode or now-State.r4_fx_at<1/12:return
    State.r4_fx_at=now
    # Only animate the four currently-owned native focus borders; never rebuild a canvas.
    opacity=1. if State.reduced_motion else .78+.22*math.sin(now*4.)**2
    if State.controller_mode and 0<=State.controller_focus<len(State.buttons):
        for border in State.controller_focus_outline:call(border,'SetRenderOpacity',opacity)


def current_recipe_kind():
    return {'GEAR':'WEAPON','COMBAT':'COMBAT','LOOT':'XP','SPAWN':'FORGE','ARENA':'ENCOUNTER','CAPACITY':'CAPACITY','MOTION':'MOVEMENT'}.get(State.page,State.recipe_kind)


def recipe_kind_select(kind):
    if kind not in RECIPE_KINDS:return False
    State.recipe_kind=kind;State.recipe_pending=None;State.recipe_import=None;redraw();return True

# Original optional adapters. External Arena/XP packages are never imported or redistributed.
State.encounter_route='ARENA'
State.arena_bridge_selected=0
State.arena_bridge_filter='enemies'
State.arena_bridge_page=0
State.arena_bridge_confirm=None
State.arena_bridge_issued=None
State.arena_bridge_status='Install the reviewed Arena separately. CROWN never destroys its actors.'
State.external_xp_draft=1.5
State.r8_xp_restoring=False
State.xp_dual_sample=None
State.xp_dual_status='Sample character and specialisation tracks before and after a real reward.'

def arena_bridge_backend():
    import sys
    modules={}
    for name,expected in REVIEWED_OPTIONAL_R8.items():
        if not name.startswith('bl4_arena'):continue
        value=_reviewed_module((name,),expected)
        if value is None:return None
        modules[name]=value
    root=modules['bl4_arena']
    if getattr(getattr(root,'mod',None),'is_enabled',None) is not True:return None
    needed={'arena':('launch',),'cart':('Arena','Line'),'waves':('pending','endless'),'spawners':('POOL',),'catalogue':('ENTRIES',),'arena_settings':('choice',)}
    for suffix,attrs in needed.items():
        if any(not hasattr(modules['bl4_arena.'+suffix],a) for a in attrs):return None
    return modules

def arena_bridge_rows(backend=None):
    backend=backend or arena_bridge_backend()
    if backend is None:return []
    rows=[];query=State.encounter_query.casefold().strip()[:64]
    try:
        entries=backend['bl4_arena.catalogue'].ENTRIES
        for index,entry in enumerate(entries):
            if index>=4096:break
            try:
                side,name,definition=entry.side,entry.name,entry.definition
                if (type(side) is str and type(name) is str and type(definition) is str
                    and side==State.arena_bridge_filter and len(name)<=160 and len(definition)<=512
                    and (not query or query in (name+' '+definition).casefold())):
                    rows.append(entry)
            except (AttributeError,TypeError,ValueError):continue
    except (AttributeError,TypeError,ValueError):return []
    return rows

def encounter_route_toggle():
    if State.encounter_job is not None or State.arena_bridge_issued is not None:return False
    State.encounter_route='ARENA' if State.encounter_route=='BMS' else 'BMS'
    State.encounter_view='CATALOGUE';State.arena_bridge_confirm=None;redraw();return True

def arena_bridge_select(index):
    if State.arena_bridge_issued is not None:
        State.arena_bridge_status='READ TRACKED FIRST / Finish observing the existing Arena launch before selecting another.'
        redraw();return False
    rows=arena_bridge_rows()
    if type(index) is not int or not 0<=index<len(rows):return False
    State.arena_bridge_selected=index;State.encounter_quantity=1
    State.encounter_view='CONTROLS';State.arena_bridge_confirm=None;redraw();return True

def arena_bridge_request():
    backend=arena_bridge_backend();anchor=_session_anchor();rows=arena_bridge_rows(backend);index=State.arena_bridge_selected
    if backend is None or anchor is None or not sandbox_solo_ready() or not 0<=index<len(rows):
        State.arena_bridge_status='BLOCKED / Reviewed enabled Arena and local solo character required.';redraw();return False
    if State.arena_bridge_issued is not None:
        State.arena_bridge_status='READ TRACKED FIRST / Previous launch remains owned by Arena; no repeated launch.';redraw();return False
    entry=rows[index];count=State.encounter_quantity;settings=backend['bl4_arena.arena_settings']
    if type(count) is not int or not 1<=count<=(1 if entry.side=='bosses' else 3):return False
    try:
        choice=settings.choice(count)
        waves,lot=choice.waves,choice.lot
        if type(waves) is not int or type(lot) is not int:
            raise ValueError('Unrecognised Arena configuration')
    except Exception as error:
        State.arena_bridge_confirm=None
        State.arena_bridge_status='ARENA CONFIG UNAVAILABLE / '+type(error).__name__+' / no spawn request sent.'
        log(State.arena_bridge_status);redraw();return False
    if waves!=1 or lot<count:
        State.arena_bridge_confirm=None
        State.arena_bridge_status='BLOCKED / Set Arena itself to one wave and a lot covering this request. Its preferences are preserved.';redraw();return False
    token=(anchor,id(backend['bl4_arena']),entry.side,entry.name,entry.definition,count);now=time.monotonic()
    if State.arena_bridge_confirm is None or State.arena_bridge_confirm[0]!=token or now>=State.arena_bridge_confirm[1]:
        State.arena_bridge_confirm=(token,now+7.);State.arena_bridge_status='CONFIRM / Arena-managed '+entry.name+' x%d / same button within 7s.'%count;redraw();return False
    State.arena_bridge_confirm=None
    # Disarm and record before the foreign call. Exceptions can follow a partial launch.
    job={'anchor':anchor,'backend':backend,'slots':[],'uncertain':True,'at':now,'definition':entry.definition,'seen':set(),'status':'REQUEST_STARTED'}
    State.arena_bridge_issued=job
    try:
        spawners=backend['bl4_arena.spawners'];previous={id(slot):slot.handed_ns for slot in spawners.POOL[:50]}
        cart=backend['bl4_arena.cart'];request=cart.Arena(lines=(cart.Line(entry.side,entry.name,count,False),),dome=False)
        result=backend['bl4_arena.arena'].launch(request)
        changed=[slot for slot in spawners.POOL[:50] if previous.get(id(slot))!=slot.handed_ns and slot.definition==entry.definition]
        job['slots']=changed[:count];job['tokens']={id(s):s.handed_ns for s in job['slots']}
        if result.refusal:
            State.arena_bridge_status='ARENA REFUSED / '+str(result.refusal)[:45]+' / read tracked before retrying.'
        else:State.arena_bridge_status='REQUEST SENT / %d of %d accepted by Arena / live births not yet confirmed.'%(result.asked,result.wanted)
        job['uncertain']=bool(result.asked) and not job['slots'];job['status']=State.arena_bridge_status
        if result.refusal and result.asked==0 and not changed:State.arena_bridge_issued=None
        log('ARENA BRIDGE // '+State.arena_bridge_status);redraw();return not bool(result.refusal)
    except Exception as error:
        State.arena_bridge_status='LAUNCH UNCONFIRMED / '+type(error).__name__+' / no automatic retry or actor destruction.'
        record_runtime_fault('ARENA_BRIDGE',error);log(State.arena_bridge_status);redraw();return False

def arena_bridge_read(quiet=False):
    job=State.arena_bridge_issued;prior=State.arena_bridge_status
    if not quiet:State.r13_arena_fault=False
    def publish(message):
        State.arena_bridge_status=message
        if State.r13_arena_generation==State.frame_generation:call(State.r13_arena_widget,'SetText',message)
        if not quiet:log(message);redraw()
    if job is None:publish('NO CROWN LAUNCH / Arena may own other encounters.');return False
    if _session_anchor()!=job['anchor']:
        State.arena_bridge_issued=None;publish('WORLD CHANGED / Observation retired without touching old actors.');return False
    backend=arena_bridge_backend()
    if backend is None or any(backend.get(k) is not v for k,v in job['backend'].items()):
        publish('ARENA BACKEND CHANGED / Observation paused. Do not retry launch; existing actors remain Arena-owned.')
        return False
    if job['uncertain'] or not job['slots']:
        publish('UNRESOLVED LAUNCH / Use Arena and travel before another CROWN launch; no unsafe cleanup.');return False
    alive=dead=unconfirmed=0
    try:
        for slot in job['slots']:
            if slot.definition!=job['definition'] or slot.handed_ns!=job['tokens'].get(id(slot)):unconfirmed+=1;continue
            spawner=slot.pointer()
            if spawner is None:unconfirmed+=1;continue
            count=spawner.SpawnerComponent.GetNumAliveActors(2)
            if type(count) is not int or not 0<=count<=50:unconfirmed+=1;continue
            if count>0:alive+=count;job['seen'].add(id(slot))
            elif id(slot) in job['seen'] and spawner.SpawnerComponent.HaveAllDied(2) is True:dead+=1
            else:unconfirmed+=1
        State.r13_arena_snapshot=dict(alive=alive,ended=dead,unconfirmed=unconfirmed,requested=len(job['slots']))
        publish('SPAWNER READBACK / %d live / %d ended after observed birth / %d unconfirmed. Arena owns cleanup.'%(alive,dead,unconfirmed))
        if dead==len(job['slots']):
            State.arena_bridge_issued=None
            if quiet and State.opened:redraw()
        return alive>0 or dead>0
    except Exception as error:
        State.r13_arena_fault=True
        publish('READBACK UNAVAILABLE / '+type(error).__name__+' / automatic observation paused; Read to retry.')
        record_runtime_fault('ARENA_READ',error);return False

def draw_arena_bridge(layout,left,y,width):
    third=(width-16)/3;half=(width-12)/2;rows=arena_bridge_rows();per=r13_arena_capacity()
    for i,(label,fn) in enumerate((('ARENA / SOURCE',encounter_route_toggle),('BOSSES' if State.arena_bridge_filter=='bosses' else 'ENEMIES',lambda:(setattr(State,'arena_bridge_filter','enemies' if State.arena_bridge_filter=='bosses' else 'bosses'),setattr(State,'arena_bridge_page',0),setattr(State,'encounter_view','CATALOGUE'),redraw())),('SEARCH',encounter_search_open))):
        btn(layout,label,left+i*(third+8),y,third,34,fn,small=True)
    if State.encounter_view=='CATALOGUE':
        pages=max(1,math.ceil(len(rows)/per));State.arena_bridge_page%=pages
        for i,entry in enumerate(rows[State.arena_bridge_page*per:(State.arena_bridge_page+1)*per]):
            index=State.arena_bridge_page*per+i
            btn(layout,entry.name,left,y+48+i*44,width,36,lambda n=index:arena_bridge_select(n),small=True)
        if not rows:
            text(layout,'No matches or Arena unavailable. Requires the reviewed, enabled Arena 1.0.5; CROWN imports no foreign code.',left+14,y+54,width-28,104,theme_color('text'),.86)
        yy=y+48+per*44+7
        for i,(label,delta) in enumerate((('PREVIOUS',-1),('NEXT / %d OF %d'%(State.arena_bridge_page+1,pages),1))):
            btn(layout,label,left+i*(half+12),yy,half,34,lambda d=delta:(setattr(State,'arena_bridge_page',(State.arena_bridge_page+d)%pages),redraw()),small=True,disabled=not rows)
        status_y=yy+43
    elif rows and 0<=State.arena_bridge_selected<len(rows):
        entry=rows[State.arena_bridge_selected]
        optional_art_image(layout,'FIELD_CARD_ARENA',left,y+45,width,77,z=6,opacity=.56)
        text(layout,entry.name,left+14,y+49,width-28,29,theme_color('text'),.96,10)
        text(layout,'20m ahead / 10m ring / one wave / Arena owns cleanup',left+14,y+83,width-28,27,theme_color('dim'),.70,10)
        if entry.side=='bosses':text(layout,'BOSS / ONE AT A TIME',left+14,y+126,width-28,28,theme_color('accent'),.86)
        else:slider(layout,'ENCOUNTER QUANTITY',State.encounter_quantity,1,3,left,y+122,width,lambda v:arena_bridge_quantity(round(v)))
        btn(layout,'LAUNCH / CONFIRM',left,y+202,half,38,arena_bridge_request,small=True,disabled=State.arena_bridge_issued is not None)
        btn(layout,'READ LIVE STATUS',left+half+12,y+202,half,38,arena_bridge_read,small=True)
        btn(layout,'BROWSE',left,y+248,width,32,lambda:(setattr(State,'encounter_view','CATALOGUE'),redraw()),small=True)
        status_y=y+289
    else:status_y=y+70
    if State.arena_bridge_issued is not None and State.encounter_view!='CONTROLS':
        btn(layout,'READ TRACKED LAUNCH',left,status_y,width,34,arena_bridge_read,small=True)
        status_y+=39
    State.r13_arena_widget=text(layout,State.arena_bridge_status,left+9,status_y,width-18,48,theme_color('text'),.72)
    State.r13_arena_generation=State.frame_generation

def _xp_external_owned_conflict():
    import sys
    live=sys.modules.get('bl4_live')
    if live is not None:
        try:
            if live._RUNTIME_XP_MODIFIERS or live._RUNTIME_STATE.get('experience_reward_scale',1.)!=1.:return True
        except Exception:return True
    adapter=State.native_xp_adapter
    return State.xp_owner is not None or bool(adapter and (adapter.handle is not None or adapter.unresolved))

def xp_external_stage(value):
    if type(value) not in (int,float) or not math.isfinite(value) or not .1<=value<=10:return False
    State.external_xp_draft=float(value);State.xp_external_confirm=None;return True

def xp_external_probe():
    module=_reviewed_module(('xp_gain_multiplier',),REVIEWED_OPTIONAL_R8['xp_gain_multiplier'])
    if module is None:State.xp_external_status='BLOCKED / Reviewed XP Gain Multiplier v1.9 is not loaded.'
    else:
        value=getattr(getattr(module,'xp_multiplier',None),'value',None)
        State.xp_external_status='ADD-ON CONFIG / %s / Earned-XP payout unverified.'%('%gx'%value if type(value) in (int,float) and math.isfinite(value) else 'READBACK UNAVAILABLE')
    log(State.xp_external_status)
    if State.opened:redraw()
    return module is not None

def xp_external_request(status_only=False):
    if not State.xp_external_view and not r13_xp_source('REWARD'):return False
    return r13_xp_read() if status_only else r13_xp_apply()

def native_xp_backend():
    import sys
    # An independently loaded reward owner can reset the same attribute even at 1x.
    external=sys.modules.get('xp_gain_multiplier')
    if external is not None and getattr(getattr(external,'mod',None),'is_enabled',None) is not False and not State.r8_xp_restoring:return None
    return _native_xp_backend_r7()

def xp_tracks_sample():
    pc=get_pc(possibly_loading=True);anchor=_session_anchor();out=[]
    try:
        for index in (0,1):
            row=pc.PlayerState.ExperienceState[index];xp=row.ExperiencePoints;level=row.ExperienceLevel
            if type(xp) is not int or not 0<=xp<2**63 or type(level) is not int or not 0<=level<=10000:raise ValueError('Invalid XP track')
            out.append((level,xp))
    except Exception:
        State.xp_dual_status='READBACK UNAVAILABLE / Both character and specialisation XP tracks required.';redraw();return False
    if anchor is None:return False
    previous=State.xp_dual_sample;State.xp_dual_sample=(anchor,tuple(out))
    if previous and previous[0]==anchor and all(a[0]==b[0] and b[1]>=a[1] for a,b in zip(previous[1],out)):
        State.xp_dual_status='OBSERVED DELTA / Character +%d / Specialisation +%d / All reward sources; not proof of multiplier.'%(out[0][1]-previous[1][0][1],out[1][1]-previous[1][1][1])
    else:State.xp_dual_status='BASELINE / Character LV%d XP%d / Specialisation LV%d XP%d / Sample after a controlled reward.'%(*out[0],*out[1])
    log(State.xp_dual_status);redraw();return True

def draw_xp_external(layout,left,y,width):
    return draw_progression(layout,left,y,width)


def arena_bridge_quantity(value):
    rows=arena_bridge_rows();index=State.arena_bridge_selected
    if type(value) is not int or not 0<=index<len(rows) or not 1<=value<=(1 if rows[index].side=='bosses' else 3):return False
    State.encounter_quantity=value;State.arena_bridge_confirm=None;return True


def xp_restore_owned():
    State.r8_xp_restoring=True
    try:return _xp_restore_owned_r7()
    finally:State.r8_xp_restoring=False


def xp_backend():
    import sys
    if not State.r8_xp_restoring:
        for name in ('xp_gain_multiplier','xp_live_menu'):
            external=sys.modules.get(name)
            if external is not None and getattr(getattr(external,'mod',None),'is_enabled',None) is not False:return None
    return _xp_backend_r7()

def r9_art_card(parent,caption,detail,asset,x,y,w,h,action,number=''):
    """One native hit target over artwork; shared mouse/gamepad action registry."""
    box(parent,x,y,w,h,theme_color('panel'),7)
    optional_art_image(parent,asset,x,y,w,h,z=8,opacity=.94)
    box(parent,x,y+h-2,w*.36,2,theme_color('highlight'),9)
    inset=14 if h<105 else 22
    if number:text(parent,number,x+inset,y+10,w-2*inset,18,theme_color('accent'),.58,10)
    ty=y+(29 if number else 15)
    text(parent,caption,x+inset,ty,w-2*inset,31,theme_color('text'),.86 if h<105 else 1.02,10)
    if h>=88:text(parent,detail,x+inset,ty+36,w*.69-inset,min(48,h-ty+y-43),theme_color('dim'),.64,10)
    b=widget('Button');put(parent,b);size_position(b,x,y,w,h,12)
    call(b,'SetVisibility',0);attempt(b,'SetIsFocusable',False);call(b,'SetIsEnabled',True);call(b,'SetRenderOpacity',.015)
    call(b,'SetToolTipText','')
    State.buttons.append({'widget':b,'run':action,'pressed':False,'name':caption,
                          'rect':(float(x),float(y),float(w),float(h)),'disabled':False})
    return b

def r9_fault_sites(exc):
    """Only code names and line numbers: no paths, messages, locals or player data."""
    sites=[];tb=exc.__traceback__
    while tb is not None and len(sites)<12:
        sites.append({'function':tb.tb_frame.f_code.co_name[:80],'line':tb.tb_lineno})
        tb=tb.tb_next
    return sites
ART_FILES['R9_EXPEDITION']='R9_EXPEDITION.png'
ART_SHA256['R9_EXPEDITION']='9f927107070fc2516ac9d06b2a24edde0bfdbba4cf161c86560dfa1b6d9d0a2a'
ART_FILES['R9_FORGE']='R9_FORGE.png'
ART_SHA256['R9_FORGE']='6ad9fd295f4ef3bb02394fd3e7c94109b2100693e4f15f78c0e89e3b34e8a923'
ART_FILES['R9_ARENA']='R9_ARENA.png'
ART_SHA256['R9_ARENA']='89d1f007cb407d5ef1e8314fa4889cbde8d62e3ee544cea409f45f74935e5c1b'
ART_FILES['R9_FLIGHT']='R9_FLIGHT.png'
ART_SHA256['R9_FLIGHT']='310bd2b028909a2558f8707a04c6e73a9c3d0132a1a8a1f58753314134067877'
ART_FILES['R9_DOCK']='R9_DOCK.png'
ART_SHA256['R9_DOCK']='12893c78f0b393f9ee54c2328d9a07a2ff91985511ff3a51c981cab6172aed41'

State.r10_view=None

State.r10_track=0

State.r10_level_draft=1

State.r10_points_draft=0

State.r10_confirm=None

State.r10_progress_job=None

State.r10_status='Choose a track, read live values, then stage a change.'

State.r10_reward_start=None

State.r10_rewards=[]

State.r10_reward_group='BASELINE'

State.r10_bonus=None

State.r10_bonus_duration=30.

State.r10_bonus_scale=1.5

State.r10_bonus_status='Choose a timed profile. Glass Cannon increases damage dealt AND taken; Healing changes supported healing factors.'

State.r10_bonus_internal=False

State.r10_bonus_widget=None

State.r10_bonus_generation=-1

State.r10_bonus_refresh=0.

State.r10_wallet_job=None

State.r10_wallet_history=[]

def studio_context():
    anchor=_session_anchor();pc=get_pc(possibly_loading=True)
    if anchor is None or pc is None:return None
    try:
        ps=pc.PlayerState
        if ps is None:return None
        return (anchor,_native_address(pc) or id(pc),_native_address(ps) or id(ps))
    except Exception:return None

def studio_can_write():
    try:return is_local_host_action() and studio_context() is not None and pawn().HasAuthority() is True
    except Exception:return False

def studio_xp_busy():
    import sys
    for name in ('xp_gain_multiplier','xp_live_menu'):
        module=sys.modules.get(name)
        if module is not None:
            try:
                if module.mod.is_enabled is not False:return True
            except Exception:return True
    return _xp_external_owned_conflict()

def studio_track_read(track=None):
    track=State.r10_track if track is None else track
    if type(track) is not int or track not in (0,1):return None
    context=studio_context();anchor=_session_anchor();pc=get_pc(possibly_loading=True)
    if context is None or anchor is None or pc is None:return None
    try:
        ps=pc.PlayerState;row=ps.ExperienceState[track]
        level,xp=row.ExperienceLevel,row.ExperiencePoints
        if type(level) is not int or type(xp) is not int or not 0<=level<=10000 or not 0<=xp<2**63:return None
        if (anchor!=_session_anchor() or context!=studio_context() or context[0]!=anchor
                or context[1]!=(_native_address(pc) or id(pc)) or context[2]!=(_native_address(ps) or id(ps))):return None
        return dict(anchor=anchor,context=context,track=track,level=level,xp=xp,ps=ps)
    except Exception:return None

def studio_live_backend():
    module=_reviewed_module(('bl4_live',),REVIEWED_BL4LIVE_SHA)
    maintenance=_reviewed_module(('bl4_live.runtime_maintenance',),R10_MAINTENANCE_SHA)
    if module is None or maintenance is None:return None
    try:
        pc=get_pc(possibly_loading=True)
        if module.mod.is_enabled is not True or not callable(module._runtime_action):return None
        if not same_unreal_object(module._runtime_pawn(),pawn()):return None
        if not same_unreal_object(module.GAME.player_state,pc.PlayerState):return None
        return module
    except Exception:return None

def studio_points_read(track=None):
    track=State.r10_track if track is None else track
    if type(track) is not int or track not in (0,1):return None
    context=studio_context();anchor=_session_anchor();actor=pawn()
    if context is None or anchor is None or actor is None:return None
    try:
        manager=actor.GbxProgressionManager;container=manager.ProgressPointsContainer
        values=container.PointsAcquiredPerPool
        if not 2<=len(values)<=16:return None
        points=values[track]
        if type(points) is not int or not 0<=points<=10000:return None
        token=('characterprogresspoints','specializationtokenpool')[track]
        graphs=manager.ProgressGraphs
        if not 1<=len(graphs)<=64:return None
        matched=False;spent=0
        for i in range(len(graphs)):
            graph=graphs[i];definition=graph.ProgressGraphDef
            if str(definition.PointPool._name).lower()!=token or int(definition.GraphType)!=0:continue
            matched=True;nodes=graph.nodes
            if len(nodes)>512:return None
            for j in range(len(nodes)):
                value=nodes[j].ProgressPointsSpent
                if type(value) is not int or not 0<=value<=10000:return None
                spent+=value
        dirty=manager.ProgressGraphsArrayDirty
        if (not matched or type(dirty) is not int or spent>points or anchor!=_session_anchor()
                or context!=studio_context() or context[0]!=anchor or not same_unreal_object(manager,actor.GbxProgressionManager)):return None
        return dict(anchor=anchor,context=context,actor=actor,manager=manager,values=values,points=points,spent=spent,track=track,dirty=dirty)
    except Exception:return None

def studio_open(view='LEVELS'):
    if view not in ('LEVELS','POINTS','REWARDS','BONUS'):return False
    def act():
        State.dock_mode='FULL';show_page('LOOT');State.xp_view=False;State.r10_view=view;State.r10_confirm=None;redraw()
    _ui_batch(act);return True

def studio_select_track():
    State.r10_track=1-State.r10_track;State.r10_confirm=None
    return studio_read()

def studio_read():
    row=studio_track_read();points=studio_points_read()
    if row:State.r10_level_draft=min((60,701)[State.r10_track],max((1,0)[State.r10_track],row['level']))
    if points:State.r10_points_draft=points['points']
    State.r10_confirm=None
    State.r10_status=('LEVEL %d / XP %d'% (row['level'],row['xp']) if row else 'Experience track unavailable')
    State.r10_status+=(' / ALLOWANCE %d / SPENT %d'%(points['points'],points['spent']) if points else ' / Point pool contract unavailable')
    log('PLAYER LAB // '+State.r10_status);redraw();return row is not None

def studio_stage(kind,value):
    if type(value) not in (int,float) or not math.isfinite(value) or float(value)!=int(value):return False
    value=int(value);track=State.r10_track
    if kind=='LEVEL' and (1,0)[track]<=value<=(60,701)[track]:State.r10_level_draft=value
    elif kind=='POINTS' and 0<=value<=(500,1000)[track]:State.r10_points_draft=value
    else:return False
    State.r10_confirm=None;return True

def studio_progress_readback():
    job=State.r10_progress_job
    if job is None:return False
    if job['anchor']!=_session_anchor() or job['context']!=studio_context():
        State.r10_progress_job=None;State.r10_status='Context changed; old progression request retired without native access.';redraw();return False
    if job['kind']=='LEVEL':
        row=studio_track_read(job['track']);value=row['level'] if row else None
    else:
        row=studio_points_read(job['track']);value=row['points'] if row else None
        manager_id=(_native_address(row['manager']) or id(row['manager'])) if row else None
        if manager_id!=job.get('manager_id') or not job.get('notification_returned',False):
            State.r10_status='PARTIAL / allowance read %s; original manager/update notification unconfirmed. No retry.'%str(value)
            redraw();return False
    if value==job['target']:
        State.r10_status='VALUE READBACK MATCHED / %s %d. Save/UI effects need BL4 acceptance.'%(job['kind'],value)
        State.r10_progress_job=None;redraw();return True
    State.r10_status='UNCONFIRMED / expected %d, read %s. No retry in this context.'%(job['target'],str(value))
    redraw();return False

def studio_apply(kind):
    if kind not in ('LEVEL','POINTS') or not studio_can_write():return False
    actor=pawn();anchor=_session_anchor();pc=get_pc(possibly_loading=True)
    if anchor is None or actor is None or pc is None or actor.HasAuthority() is not True:return False
    if State.r10_progress_job is not None:
        if State.r10_progress_job['anchor']==anchor:
            State.r10_status='Previous request unresolved. Read result or travel; no repeat.';redraw();return False
        State.r10_progress_job=None
    track=State.r10_track;module=None
    if kind=='LEVEL':
        row=studio_track_read(track);module=studio_live_backend();target=State.r10_level_draft
        if row is None or module is None or studio_xp_busy():
            State.r10_status='Requires reviewed enabled BL4Live on this player, and no active XP owner.';redraw();return False
        before=row['level'];fingerprint=(before,row['xp'],id(module),_native_address(pc.PlayerState))
        if type(target) is not int or not before<target<=(60,701)[track]:return False
    else:
        row=studio_points_read(track);target=State.r10_points_draft
        if row is None:return False
        before=row['points'];fingerprint=(before,row['spent'],_native_address(row['manager']) or id(row['manager']))
        # Point allowance is TOTAL acquired, never a claim of unspent points.
        if type(target) is not int or not before<target<=min(before+25,(500,1000)[track]):
            State.r10_status='Raise total allowance by 1–25 per confirmed change; lowering is blocked.';redraw();return False
    context=studio_context()
    if context is None:return False
    token=(kind,track,target,context,fingerprint);now=time.monotonic()
    if State.r10_confirm is None or State.r10_confirm[0]!=token or now>=State.r10_confirm[1]:
        State.r10_confirm=(token,now+7.)
        State.r10_status='CONFIRM PERMANENT %s %d → %d. Backup required; F10 cannot undo.'%(kind,before,target)
        log(State.r10_status);redraw();return False
    State.r10_confirm=None
    # Quarantine BEFORE native execution; exceptions can follow partial effects.
    job=dict(kind=kind,track=track,anchor=anchor,context=context,before=before,target=target)
    if kind=='POINTS':
        job.update(manager_id=_native_address(row['manager']) or id(row['manager']),notification_returned=False)
    State.r10_progress_job=job
    try:
        if kind=='LEVEL':
            if studio_live_backend() is not module or studio_context()!=context:raise RuntimeError('backend or context changed')
            module._runtime_action('set_experience_level',{'track':('character','specialization')[track],'level':target})
        else:
            latest=studio_points_read(track)
            if (latest is None or studio_context()!=context or not same_unreal_object(row['manager'],latest['manager'])
                    or latest['points']!=before or latest['spent']!=row['spent']):raise RuntimeError('context changed')
            # Reviewed reflected contract, original bounded transaction. No raw pointers.
            row['values'][track]=target
            if studio_context()!=context:raise RuntimeError('context changed after value write')
            row['manager'].ProgressGraphsArrayDirty=3
            # Matching points cannot prove notification; its flag can be consumed immediately.
            job['notification_returned']=True
        State.r10_status='REQUEST DISPATCHED / reading actual field; no save rollback promised.'
        return studio_progress_readback()
    except Exception as error:
        record_runtime_fault('PROGRESSION_REQUEST',error)
        State.r10_status='PARTIAL RESULT POSSIBLE / '+type(error).__name__+' / read result; no automatic retry.'
        log(State.r10_status);redraw();return False

def reward_sample(action):
    if action in ('BASELINE','SCALED'):
        State.r10_reward_group=action;State.r10_reward_start=None
        State.r10_status=action+' group selected / any unfinished sample discarded.';redraw();return True
    if action=='CLEAR':
        State.r10_reward_start=None;State.r10_rewards=[];State.r10_status='Observations cleared. Exported files unchanged.';redraw();return True
    if action=='BEGIN' and State.r10_reward_start is not None:
        State.r10_status='A sample is already running. Finish it, or select a group to discard it.';redraw();return False
    rows=[studio_track_read(i) for i in (0,1)]
    if any(r is None for r in rows) or rows[0]['context'] is None or rows[0]['context']!=rows[1]['context']:return False
    snapshot=dict(anchor=rows[0]['anchor'],context=rows[0]['context'],levels=tuple(r['level'] for r in rows),xp=tuple(r['xp'] for r in rows),group=State.r10_reward_group,started=time.monotonic())
    if action=='BEGIN':State.r10_reward_start=snapshot;State.r10_status='Sample started. Complete ONE comparable reward, then Finish.';redraw();return True
    start=State.r10_reward_start
    if action!='FINISH' or start is None:return False
    State.r10_reward_start=None
    delta=tuple(v-b for v,b in zip(snapshot['xp'],start['xp']))
    if snapshot['context']!=start['context'] or snapshot['levels']!=start['levels'] or any(v<0 for v in delta):
        State.r10_status='Sample rejected: context, level or XP counter changed.';redraw();return False
    State.r10_rewards=(State.r10_rewards+[dict(group=start['group'],delta=delta,levels=start['levels'],anchor=start['anchor'],context=start['context'],seconds=round(max(0,time.monotonic()-start['started']),3))])[-12:]
    State.r10_status='OBSERVED XP / Character +%d / Specialisation +%d. Reward identity is not verified.'%delta
    redraw();return True

def reward_summary():
    context=studio_context();groups={k:[r for r in State.r10_rewards if r['group']==k and r['context']==context] for k in ('BASELINE','SCALED')}
    a,b=groups['BASELINE'],groups['SCALED'];summary='Samples: baseline %d / scaled %d.'%(len(a),len(b))
    if len(a)>=3 and len(b)>=3 and len({r['levels'] for r in a+b})==1:
        ratios=[]
        for i,name in enumerate(('CHAR','SPEC')):
            baseline=sum(r['delta'][i] for r in a)/len(a);scaled=sum(r['delta'][i] for r in b)/len(b)
            ratios.append(name+' '+('n/a' if baseline<=0 else '%.2fx observed'%(scaled/baseline)))
        summary+=' / '+' / '.join(ratios)
    return summary+' / Match reward conditions yourself; ratio is not proof.'

def export_reward_samples():
    """Opt-in, fixed-path, atomic observations export. Never reads/writes saves."""
    if SETTINGS_DIR is None or not State.r10_rewards:
        State.r10_status='EXPORT UNAVAILABLE / SDK settings path and at least one completed sample required.'
        redraw();return False
    temporary=None
    try:
        import tempfile
        context=studio_context()
        samples=[dict(group=r['group'],delta=list(r['delta']),levels=list(r['levels']),
                      seconds=r['seconds'],current_context=context is not None and r['context']==context)
                 for r in State.r10_rewards[-12:]]
        payload=dict(format='CROWN_XP_OBSERVATIONS_1',build_id=BUILD_ID,captured_unix_time=int(time.time()),
                     samples=samples,summary=reward_summary(),game_verified=False,
                     note='Observed counters only. Reward identity, equivalent conditions and actual multiplier effects are unverified. No player names, native addresses, world identifiers, positions or save contents included.')
        path=Path(SETTINGS_DIR)/'CROWNs_Freedom_XP_Observations.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',prefix='.crown_xp_',suffix='.tmp',dir=path.parent,delete=False) as handle:
            temporary=Path(handle.name);json.dump(payload,handle,indent=2,allow_nan=False)
        temporary.replace(path);temporary=None
        State.r10_status='EXPORTED / %d observations / CROWNs_Freedom_XP_Observations.json in SDK settings.'%len(samples)
        log(State.r10_status);redraw();return True
    except Exception as error:
        record_runtime_fault('XP_OBSERVATIONS_EXPORT',error)
        State.r10_status='EXPORT FAILED / '+type(error).__name__+' / previous report retained.'
        log(State.r10_status);redraw();return False
    finally:
        if temporary is not None:
            try:temporary.unlink(missing_ok=True)
            except OSError:pass

def bonus_start():
    if State.r10_bonus is not None or State.combat_originals or not sandbox_solo_ready() or not State.controller_watcher_installed:return False
    factor=State.r10_bonus_scale;seconds=State.r10_bonus_duration;profile=State.r13_bonus_profile
    if (profile not in R13_BONUSES or type(factor) not in (int,float) or type(seconds) not in (int,float)
            or not math.isfinite(factor) or not math.isfinite(seconds) or not 1.1<=factor<=3 or not 15<=seconds<=180):return False
    anchor=_session_anchor();planned=[]
    if anchor is None:return False
    for key,direction in R13_BONUSES[profile][1]:
        row=combat_pair(key)
        if row is None or row[1][0]!=row[1][1] or row[1][0]<=0:
            State.r10_bonus_status='Unavailable field: '+TUNING_FIELDS[key][4]+'. Nothing applied.';redraw();return False
        value=row[1][0]*(factor if direction=='UP' else 1./factor)
        if not TUNING_FIELDS[key][2]<=value<=TUNING_FIELDS[key][3]:return False
        planned.append((key,value))
    job=dict(anchor=anchor,until=time.monotonic()+seconds,profile=profile,duration=float(seconds),scale=float(factor),keys=tuple(k for k,v in planned),last=None)
    State.r10_bonus=job;State.r10_bonus_internal=True
    def apply():
        for key,value in planned:
            if _session_anchor()!=anchor or not combat_tune(key,value):return False
        return True
    try:ok=_ui_batch(apply)
    finally:State.r10_bonus_internal=False
    if not ok:
        bonus_stop();State.r10_bonus_status='Bonus batch failed. Owned rollback attempted; unresolved records remain for Restore.';redraw();return False
    job['last']=State.combat_last.get('OUTGOING')
    State.r10_bonus_status=R13_BONUSES[profile][0]+' / %d field readbacks matched / gameplay unverified.'%len(planned)
    if State.opened:play_ui_sound('confirm')
    redraw();return True

def bonus_stop():
    job=State.r10_bonus;State.r10_bonus=None
    if job is None:return False
    if job['anchor']!=_session_anchor():State.r10_bonus_status='Context changed; no stale restoration write.';return False
    count=restore_combat_tuning();ok=not State.combat_originals
    State.r10_bonus_status='Owned bonus fields restored.' if ok else 'Restore incomplete; conflicted originals retained. Use Restore after inspection.'
    if State.opened:
        play_ui_sound('confirm' if ok else 'warn');redraw()
    return ok and count>0

def bonus_tick(now):
    job=State.r10_bonus
    if job is None:return
    if job['anchor']!=_session_anchor():
        State.r10_bonus=None;State.r10_bonus_status='Context changed; old timer retired without writes.';return
    if State.opened and State.r10_bonus_generation==State.frame_generation and now-State.r10_bonus_refresh>=1.:
        State.r10_bonus_refresh=now
        r16_bonus_bar_tick(now)
        call(State.r10_bonus_widget,'SetText',str(max(0,round(job['until']-now)))+'s remaining / '+State.r10_bonus_status)
    if now>=job['until']:bonus_stop()

def wallet_balance(kind,pc=None):
    if kind not in CURRENCY_CODES:return None
    try:
        pc=get_pc(possibly_loading=True) if pc is None else pc
        rows=pc.CurrencyManager.currencies
        if len(rows)>64:return None
        found=[]
        for i in range(len(rows)):
            row=rows[i]
            if str(row.type.Name).casefold()!=CURRENCY_CODES[kind].casefold():continue
            value=getattr(row,'Amount',getattr(row,'amount',None))
            if type(value) is int and 0<=value<=2**31-1:found.append(value)
        return found[0] if len(found)==1 else None
    except Exception:return None

def wallet_rpc(pc,kind):
    """Bonk's documented server RPC, resolved by exact currency definition name."""
    try:
        call=getattr(pc,'Server_AddCurrency',None);rows=pc.CurrencyManager.currencies
        if not callable(call) or len(rows)>64:return None
        matches=[rows[i].type for i in range(len(rows)) if str(rows[i].type.Name).casefold()==CURRENCY_CODES[kind].casefold()]
        return (call,matches[0]) if len(matches)==1 else None
    except Exception:return None

State.r10_input_keys={}

State.r10_input_prompt='TAB / NEXT • SHIFT+TAB / PREVIOUS • ENTER / SELECT • ESC / BACK'

State.r10_device='AUTO'

def r10_save_tag():
    if State.page=='LOOT' and State.r10_view=='REWARDS':return ('READ ONLY',False)
    if State.page=='LOOT' and State.r10_view=='BONUS':return ('TEMP/OWNED',False)
    risk=State.page in ('LOOT','SPAWN','COMBAT') or (State.page=='PARTY' and State.party_mode=='GIFTS')
    return ('SAVE: RISK' if risk else 'SAVE: TEMP',risk)

def r10_loot_tagline():
    if State.r10_view=='REWARDS':return 'Read-only XP counters; comparable rewards required.'
    if State.r10_view=='BONUS':return 'Only owned temporary fields; Stop / Restore. Glass Cannon increases damage taken.'
    if State.r10_view in ('LEVELS','POINTS'):return 'Permanent progression; F10 cannot undo.'
    if State.xp_view:return 'XP configuration is not proof of earned rewards.'
    return 'Wallet grants can persist; confirmations do not back up saves.'

def r10_footer_prompt():
    paging=(State.dock_mode=='FULL' and ((State.page=='SPAWN' and State.spawn_view=='BROWSE') or
            (State.page=='ARENA' and State.encounter_view=='CATALOGUE') or (State.page=='FINDER' and State.finder_mode=='BROWSE')))
    if State.controller_mode and State.r10_device!='KEYBOARD':
        idx=State.controller_focus
        coarse=0<=idx<len(State.buttons) and State.buttons[idx].get('slider') is not None
        return 'A SELECT / B BACK'+(' / LT-RT COARSE' if coarse else ' / LT-RT PAGE' if paging else '')
    return ('WHEEL PAGE / CLICK SELECT / ESC BACK' if State.r10_device=='MOUSE' and paging else 'TAB MOVE / ENTER SELECT / ESC BACK')

def draw_player_studio(layout,left,y,width):
    tabs=(('LEVELS','LEVELS'),('SKILL POINTS','POINTS'),('XP SAMPLES','REWARDS'),('TIMED BONUS','BONUS'),('XP MULTIPLIER',None))
    bw=(width-24)/5
    for i,(label,view) in enumerate(tabs):
        fn=(lambda v=view:studio_open(v)) if view else (lambda:(setattr(State,'r10_view',None),r3_open_tool('LOOT','XP')))
        btn(layout,label,left+i*(bw+6),y,bw,31,fn,active=State.r10_view==view,small=True)
    half=(width-12)/2;view=State.r10_view
    if view in ('LEVELS','POINTS'):
        row=studio_track_read();points=studio_points_read()
        text(layout,('CHARACTER' if State.r10_track==0 else 'SPECIALISATION')+' / '+('LEVEL '+str(row['level']) if row else 'NO LIVE READ'),left+12,y+45,half-24,28,theme_color('text'),.85)
        btn(layout,'SWITCH TRACK',left+half+12,y+43,half,34,studio_select_track,small=True)
        if view=='LEVELS':
            text(layout,'EXPERIMENTAL / BL4Live 0.10.30 / raise only / permanent',left+12,y+79,width-24,21,theme_color('dim'),.69)
            slider(layout,'TARGET LEVEL / DRAFT',State.r10_level_draft,(1,0)[State.r10_track],(60,701)[State.r10_track],left,y+106,width,lambda v:studio_stage('LEVEL',v))
            enabled=(studio_live_backend() is not None and row is not None and not studio_xp_busy()
                     and row['level']<State.r10_level_draft<=(60,701)[State.r10_track])
        else:
            text(layout,('TOTAL %d / SPENT %d'%(points['points'],points['spent']) if points else 'Named pool/graph contract unavailable')+' / permanent; no lowering',left+12,y+79,width-24,21,theme_color('dim'),.63)
            slider(layout,'TOTAL POINT ALLOWANCE / DRAFT',State.r10_points_draft,0,(500,1000)[State.r10_track],left,y+106,width,lambda v:studio_stage('POINTS',v))
            enabled=points is not None and points['points']<State.r10_points_draft<=min(points['points']+25,(500,1000)[State.r10_track])
        third=(width-16)/3
        for i,(label,fn) in enumerate((('READ LIVE',studio_read),('APPLY / CONFIRM',lambda:studio_apply('LEVEL' if view=='LEVELS' else 'POINTS')),('READ RESULT',studio_progress_readback))):
            blocked=(i==1 and (not enabled or not studio_can_write() or State.r10_progress_job is not None)) or (i==2 and State.r10_progress_job is None)
            btn(layout,label,left+i*(third+8),y+191,third,34,fn,small=True,danger=i==1,disabled=blocked)
        text(layout,State.r10_status,left+12,y+234,width-24,43,theme_color('dim'),.67)
    elif view=='REWARDS':
        text(layout,'OBSERVATION, NOT MULTIPLIER PROOF',left+12,y+44,width-24,28,theme_color('accent'),.82)
        for i,(label,key) in enumerate((('BASELINE GROUP','BASELINE'),('SCALED GROUP','SCALED'),('BEGIN REWARD','BEGIN'),('FINISH REWARD','FINISH'),('CLEAR SAMPLES','CLEAR'),('EXPORT OBSERVATIONS','EXPORT'))):
            fn=export_reward_samples if key=='EXPORT' else lambda k=key:reward_sample(k)
            disabled=(key=='FINISH' and State.r10_reward_start is None) or (key=='BEGIN' and State.r10_reward_start is not None) or (key=='EXPORT' and (SETTINGS_DIR is None or not State.r10_rewards))
            btn(layout,label,left+(i%2)*(half+12),y+83+(i//2)*43,half,35,fn,small=True,active=key==State.r10_reward_group,disabled=disabled)
        text(layout,reward_summary(),left+12,y+215,width-24,40,theme_color('dim'),.63)
        text(layout,State.r10_status,left+12,y+257,width-24,21,theme_color('text'),.62)
    else:
        third=(width-12)/3
        for i,(key,label) in enumerate((('DAMAGE','DAMAGE'),('GUARD','GUARD'),('ELEMENTAL','ELEMENTS'),('RECOVERY','RECOVERY'),('GLASS','GLASS CANNON'),('HEALING','HEALING'))):
            btn(layout,label,left+(i%3)*(third+6),y+43+(i//3)*34,third,29,lambda k=key:r13_bonus_choose(k),active=State.r13_bonus_profile==key,small=True,disabled=State.r10_bonus is not None)
        half=(width-12)/2
        slider(layout,'BONUS FACTOR',State.r10_bonus_scale,1.1,3.,left,y+116,half,lambda v:setattr(State,'r10_bonus_scale',float(v)))
        slider(layout,'DURATION / SECONDS',State.r10_bonus_duration,15,180,left+half+12,y+116,half,lambda v:setattr(State,'r10_bonus_duration',float(v)))
        btn(layout,'START OWNED TIMER',left,y+202,half,38,bonus_start,small=True,disabled=State.r10_bonus is not None)
        btn(layout,'STOP / RESTORE',left+half+12,y+202,half,38,bonus_stop,small=True,disabled=State.r10_bonus is None)
        remaining=max(0,round(State.r10_bonus['until']-time.monotonic())) if State.r10_bonus else 0
        State.r10_bonus_widget=text(layout,('%ds remaining / '%remaining if remaining else '')+State.r10_bonus_status,left+12,y+251,width-24,(44 if State.panel_rect and State.panel_rect[3]>=900 else 26),theme_color('dim'),.67)
        State.r10_bonus_generation=State.frame_generation
        r16_bonus_bar(layout,left,y+244,width)
        if State.panel_rect and State.panel_rect[3]>=900:r16_bonus_review(layout,left,y+330,width)

def r10_editor_active():
    return (State.numeric_editor is not None or State.profile_name_edit or
            (State.page=='SPAWN' and State.spawn_view in ('SEARCH','LEVEL')) or
            (State.page=='ARENA' and State.encounter_view=='SEARCH') or
            (State.page=='FINDER' and State.finder_mode=='EDIT') or
            (State.page=='CAPACITY' and State.capacity_view=='EDIT'))

def r10_focus_cycle(direction):
    valid=[i for i,b in enumerate(State.buttons) if not b.get('disabled') and b.get('rect')]
    if not valid:return False
    idx=State.controller_focus
    State.controller_focus=(valid[(valid.index(idx)+direction)%len(valid)] if idx in valid else _controller_initial_focus())
    State.controller_mode=True;_controller_update_focus_outline();return True

def r10_page_step(direction):
    if State.dock_mode=='SIDE':return False
    if State.page=='SPAWN' and State.spawn_view=='BROWSE':forge_change_page(direction);return True
    if State.page=='FINDER' and State.finder_mode=='BROWSE':finder_change_page(direction);return True
    if State.page=='ARENA' and State.encounter_view=='CATALOGUE':
        if State.encounter_route=='ARENA':
            pages=max(1,math.ceil(len(arena_bridge_rows())/r13_arena_capacity()));State.arena_bridge_page=(State.arena_bridge_page+direction)%pages
        else:
            pages=max(1,math.ceil(len(encounter_rows())/3));State.encounter_page=(State.encounter_page+direction)%pages
        redraw();return True
    return False

def r10_input_tick(pc,now):
    if not State.opened:
        State.r10_input_keys={};return False
    names=('Tab','PageUp','PageDown','Gamepad_LeftTrigger','Gamepad_RightTrigger','MouseScrollUp','MouseScrollDown')
    values={n:key_down(pc,n) for n in names}
    enter=key_down(pc,'Enter') or key_down(pc,'Return');pad=key_down(pc,'Gamepad_FaceButton_Bottom');mouse=key_down(pc,'LeftMouseButton')
    if (enter and pad) or (mouse and pad):
        State.editor_enter_down=enter;State.controller_last_keys['Gamepad_FaceButton_Bottom']=pad
        for item in State.buttons:item['pressed']=False
        State.r10_input_keys=values;return True
    if r10_editor_active():
        State.arrow_keys_down={n:key_down(pc,n) for n in ('Up','Down','Left','Right')}
    if r10_editor_active() or now<State.controller_open_block_until:
        State.r10_input_keys=values;return False
    edges={n:v and not State.r10_input_keys.get(n,False) for n,v in values.items()}
    State.r10_input_keys=values
    active=[n for n in names if values[n]]
    if not any(edges.values()):return False
    others=('Enter','Return','Up','Down','Left','Right','Gamepad_FaceButton_Bottom','Gamepad_FaceButton_Right','Gamepad_LeftShoulder','Gamepad_RightShoulder',*CONTROLLER_DIRECTIONS)
    if len(active)!=1 or any(key_down(pc,n) for n in others) or key_down(pc,'LeftMouseButton'):
        State.editor_enter_down=key_down(pc,'Enter') or key_down(pc,'Return')
        for n in others:
            if n.startswith('Gamepad_'):State.controller_last_keys[n]=key_down(pc,n)
            if n in ('Up','Down','Left','Right'):State.arrow_keys_down[n]=key_down(pc,n)
        return True
    key=next(n for n in names if edges[n])
    if key=='Tab':
        State.r10_device='KEYBOARD'
        State.r10_input_prompt='TAB / FOCUS • ENTER / SELECT • ESC / BACK'
        return r10_focus_cycle(-1 if key_down(pc,'LeftShift') or key_down(pc,'RightShift') else 1)
    direction=-1 if key in ('PageUp','Gamepad_LeftTrigger','MouseScrollUp') else 1
    if key.startswith('MouseScroll'):
        # Only consume wheel over a live content control, never a sidebar/window.
        hovered=None
        for item in State.buttons:
            if item.get('disabled'):continue
            try:
                if item['widget'].IsHovered() is True:hovered=item;break
            except Exception:pass
        rect=State.panel_rect
        if hovered is None or rect is None or hovered['rect'][0]<rect[0]+min(290.,max(224.,rect[2]*.18)) or hovered['rect'][1]<rect[1]+216:return False
        State.controller_mode=False;State.r10_input_prompt='WHEEL / PAGE • CLICK / SELECT • ESC / BACK'
        State.r10_device='MOUSE'
        ref=hovered.get('slider')
        if ref is not None:
            ref.adjust(-direction);_controller_update_focus_outline();return True
        return r10_page_step(direction)
    if key.startswith('Gamepad_'):
        State.r10_device='CONTROLLER'
        State.controller_mode=True;State.r10_input_prompt='D-PAD / MOVE • A / SELECT • B / BACK • LT/RT / PAGE OR COARSE SLIDER'
        idx=State.controller_focus
        if 0<=idx<len(State.buttons):
            ref=State.buttons[idx].get('slider')
            if ref is not None:ref.adjust(direction,coarse=True);return True
    else:State.r10_device='KEYBOARD'
    return r10_page_step(direction)

def r10_heading_icon(page):
    return {'SPAWN':'R4_ICON_FORGE','GEAR':'R4_ICON_WEAPON','ARENA':'R4_ICON_ENCOUNTER',
            'LOOT':'R4_ICON_XP','CAPACITY':'R4_ICON_CAPACITY','MOTION':'R4_ICON_MOVEMENT',
            'BOOSTS':'R4_ICON_MOVEMENT','WORLD':'R4_ICON_MOVEMENT','WAYPOINTS':'R4_ICON_MOVEMENT'}.get(page,'R4_ICON_COMBAT')
R10_MAINTENANCE_SHA='aab0674fc4b3178aa291c19b0d444b03459cdf1edb083744bda9539b6451910e'

State.r12_xp_attempt=None

State.r12_grant_uncertain=None

State.r12_player_fields={}

State.r12_player_anchor=None

State.r12_player_component=None

State.r12_restore_status='No restoration run in this session.'

State.r12_kill_confirm=None

State.r12_target_pc=None

def r12_grant_context():
    context=studio_context()
    if context is not None and State.r12_grant_uncertain is not None and State.r12_grant_uncertain!=context:
        State.r12_grant_uncertain=None
    return context

def r12_player_read(actor,key):
    try:
        if key=='MODE':
            value=actor.OakCharacterMovement.MovementMode
            return int(value) if not isinstance(value,bool) and 0<=int(value)<=6 else None
        value=getattr(actor,key)
        return value if type(value) is bool else None
    except Exception:return None

def r12_player_set(actor,key,value):
    if key=='MODE':actor.OakCharacterMovement.SetMovementMode(value,0)
    else:setattr(actor,key,value)

def r12_player_change(actor,planned):
    protect_character(actor);anchor=_session_anchor()
    if anchor is None or anchor!=State.r12_player_anchor:return False
    if 'MODE' in planned and not same_unreal_object(getattr(actor,'OakCharacterMovement',None),State.r12_player_component):
        log('PLAYER BLOCKED // Movement component replaced; no stale baseline applied.');return False
    before={key:r12_player_read(actor,key) for key in planned}
    if any(value is None for value in before.values()):
        log('PLAYER BLOCKED // Reflected originals unavailable; no assumed defaults.');return False
    for key,value in before.items():
        owned=State.r12_player_fields.get(key)
        if owned and value!=owned['last'] and value!=planned[key]:
            # Mode calls can be asynchronous; a mode already at its original
            # is safe only for a restore request targeting that same original.
            log('PLAYER BLOCKED // '+key+' changed outside CROWN; originals retained.');return False
    prior={key:dict(value) for key,value in State.r12_player_fields.items()};attempted=[]
    try:
        for key,value in planned.items():
            if _session_anchor()!=anchor:raise RuntimeError('player context changed')
            if key=='MODE' and State.movement_original is None:raise RuntimeError('movement baseline unavailable')
            row=State.r12_player_fields.setdefault(key,dict(original=before[key],last=before[key]))
            row['last']=value;attempted.append(key)
            r12_player_set(actor,key,value)
            # MovementMode is a request, as in R11; only bool readbacks are
            # treated as immediate. Native flight behavior remains unverified.
            if key!='MODE' and r12_player_read(actor,key)!=value:raise RuntimeError('player field readback differs')
        return True
    except Exception as error:
        if _session_anchor()==anchor:
            for key in reversed(attempted):
                try:
                    current=r12_player_read(actor,key)
                    if current==planned[key]:r12_player_set(actor,key,before[key])
                    if r12_player_read(actor,key)==before[key]:
                        if key in prior:State.r12_player_fields[key]=prior[key]
                        else:State.r12_player_fields.pop(key,None)
                except Exception:pass
        record_runtime_fault('PLAYER_TRANSACTION',error)
        log('PLAYER FAILED // Owned rollback attempted; unresolved fields retained.');return False

def r12_restore_player():
    actor=pawn();saved=State.saved_char;fields=State.r12_player_fields
    if not fields:return True
    if actor is None or _session_anchor() is None:return False
    if not same_unreal_object(actor,saved) or _session_anchor()!=State.r12_player_anchor:
        # Retire stale wrappers, never try to restore the replacement actor.
        State.r12_player_fields={};State.god=State.noclip=False;State.saved_char=None;return False
    for key,row in list(fields.items()):
        try:
            if key=='MODE' and not same_unreal_object(getattr(actor,'OakCharacterMovement',None),State.r12_player_component):continue
            current=r12_player_read(actor,key)
            if current==row['original']:fields.pop(key);continue
            if current!=row['last']:continue
            r12_player_set(actor,key,row['original'])
            if r12_player_read(actor,key)==row['original']:fields.pop(key)
        except Exception as error:record_runtime_fault('PLAYER_RESTORE',error)
    if 'bCanBeDamaged' not in fields:State.god=False
    if 'bActorEnableCollision' not in fields:State.noclip=False
    if not fields:
        State.god=State.noclip=False;State.saved_char=State.damage_original=State.collision_original=None
    return not fields

def r12_restore_world():
    if State.world_saved is None:return True
    # Restore already-owned world state after restore_friends revoked consent;
    # this does not authorize a new shared adjustment or a guest write.
    if session_role() not in ('SOLO','HOST'):return False
    try:
        current=get_worldsettings()
        if current is None or not same_unreal_object(current,State.world_saved):
            State.world_saved=State.world_original=State.world_last=None;return False
        value=_read_number(current,'TimeDilation')
        if value!=State.world_original:
            if value is None or State.world_last is None or abs(value-State.world_last)>max(.02,abs(State.world_last)*.01):return False
            current.TimeDilation=State.world_original
            if _read_number(current,'TimeDilation')!=State.world_original:return False
        State.world_saved=State.world_original=State.world_last=None;State.speed=1.;return True
    except Exception as error:record_runtime_fault('WORLD_RESTORE',error);return False

def r12_xp_observe_attempt(module,scale,value):
    job=State.r12_xp_attempt
    if job is None:return True
    if job['anchor']!=_session_anchor():State.r12_xp_attempt=None;return True
    if module is not job['module']:return False
    if (scale==job['desired'] and type(value) in (int,float) and math.isfinite(value)
            and abs(value-job['expected'])<=max(.01,abs(job['expected'])*.01)):
        State.xp_owner=None if job['restore'] else dict(module=module,anchor=job['anchor'],original=job['original'],last=job['desired'])
        State.r12_xp_attempt=None;return True
    return False

def r12_restore_summary():
    return ('PLAYER %d / FRIEND %d / TARGET %d / COMBAT %d / WEAPON %d / MOVEMENT %d / WORLD %d / FOV %d / XP %d / XP UNCERTAIN %d'%(
        len(State.r12_player_fields),len(State.remote_originals),int(State.target_off),len(State.combat_originals),len(State.weapon_owned),len(State.motion_originals),
        int(State.world_saved is not None),int(State.fov_saved is not None),int(State.xp_owner is not None),int(State.r12_xp_attempt is not None)))

def r12_input_prompt():
    if State.controller_mode and State.r10_device not in ('KEYBOARD','MOUSE') and State.controller_enabled:return 'A SELECT / B BACK / D-PAD MOVE'
    if State.r10_device=='MOUSE':return 'CLICK SELECT / ESC BACK / F6 CLOSE'
    return 'TAB FOCUS / ENTER SELECT / ESC BACK'

def r12_context_art(page):
    return ('R9_FORGE' if page in ('SPAWN','GEAR','CAPACITY') else 'R9_ARENA' if page in ('ARENA','COMBAT','PARTY')
            else 'R9_FLIGHT' if page in ('PLAYER','MOTION','BOOSTS','WORLD','WAYPOINTS') else 'R9_EXPEDITION')

def r12_restore_target():
    if not State.target_off:return True
    pc=get_pc(possibly_loading=True)
    if pc is None:return False
    if State.r12_target_pc is None or not same_unreal_object(pc,State.r12_target_pc):
        State.target_off=False;State.r12_target_pc=None;return False
    try:
        lib=unrealsdk.find_class('GbxTargetingFunctionLibrary').ClassDefaultObject
        lib.LockTargetableByAI(pc,'crown_native',False,False)
        State.target_off=False;State.r12_target_pc=None;return True
    except Exception as error:record_runtime_fault('TARGET_RESTORE',error);return False

State.r13_xp_job=None

State.r13_bonus_profile='DAMAGE'

State.r13_arena_widget=None

State.r13_arena_generation=-1

State.r13_arena_next=0.

State.r13_arena_fault=False

State.r13_arena_snapshot={}

R13_BONUSES={
 'DAMAGE':('Damage boost',(('OUTGOING','UP'),)),
 'GUARD':('Damage resistance',(('INCOMING','DOWN'),)),
 'ELEMENTAL':('Elemental boost',(('FIRE','UP'),('SHOCK','UP'),('CORROSIVE','UP'))),
 'RECOVERY':('Faster healing kits',(('KIT_COOLDOWN','DOWN'),)),
}

def r13_xp_module():
    module=_reviewed_module(('xp_gain_multiplier',),REVIEWED_OPTIONAL_R8['xp_gain_multiplier'])
    if module is None:return None
    try:
        if module.mod.is_enabled is not True:return None
        if not same_unreal_object(module._player_state(),get_pc(possibly_loading=True).PlayerState):return None
        value=module.xp_multiplier.value
        if type(value) not in (int,float) or not math.isfinite(value) or not .1<=value<=10:return None
        return module
    except Exception:return None

def r13_xp_source(source):
    if source not in ('NATIVE','BL4LIVE','REWARD'):return False
    job=State.r13_xp_job;context=studio_context()
    if job and context is not None and context!=job['context']:
        State.r13_xp_job=None # Retire only a departed context, never a transient loading state.
    adapter=State.native_xp_adapter
    if (State.xp_owner is not None or State.r12_xp_attempt is not None or State.r13_xp_job is not None
            or (adapter and (adapter.handle is not None or adapter.unresolved))):
        State.xp_status='Restore or resolve the current XP owner before changing source.';redraw();return False
    State.xp_external_view=source=='REWARD'
    if source!='REWARD':State.xp_route=source
    State.xp_read=None;State.xp_external_confirm=None
    State.xp_status='Source selected. Read its current configuration before applying.';redraw();return True

def r13_xp_read():
    if not State.xp_external_view:return xp_read()
    module=r13_xp_module();context=studio_context()
    if module is None or context is None or not sandbox_solo_ready() or _xp_external_owned_conflict():
        State.xp_status='XP add-on unavailable: reviewed enabled XP Gain Multiplier 1.9 on this solo player required.';redraw();return False
    value=float(module.xp_multiplier.value);job=State.r13_xp_job
    if job and job['context']!=context:State.r13_xp_job=None;job=None
    if job:
        if job['module'] is not module or not job['returned'] or value!=job['target']:
            State.xp_status='Previous add-on result unresolved. No repeated command in this player context.';redraw();return False
        State.r13_xp_job=None
    State.external_xp_draft=value
    armed=getattr(module,'_armed',None);topups=getattr(module,'_topups',None)
    State.xp_status='ADD-ON CONFIG %gx / %s / top-ups %s. Earned payout still unverified.'%(value,'ARMED' if armed is True else 'CALIBRATING',str(topups) if type(topups) is int else 'unknown')
    State.xp_external_status=State.xp_status;redraw();return True

def r13_xp_preset(value):
    if value not in (1.,2.,3.,5.,10.) or type(value) not in (int,float):return False
    def stage():
        if not r13_xp_read():return False
        ok=xp_external_stage(value) if State.xp_external_view else xp_stage(value)
        if ok:State.xp_status='DRAFT %gx / press Apply to change the selected backend; reward payout is not yet proven.'%value
        redraw();return ok
    return _ui_batch(stage)

def r13_xp_apply():
    if not State.xp_external_view:return xp_apply()
    module=r13_xp_module();context=studio_context();value=State.external_xp_draft
    if (module is None or context is None or not sandbox_solo_ready() or _xp_external_owned_conflict()
            or type(value) not in (int,float) or not math.isfinite(value) or not .1<=value<=10):return False
    job=State.r13_xp_job
    if job and job['context']==context:
        State.xp_status='Add-on result unresolved. Read it; do not send another command.';redraw();return False
    if job:State.r13_xp_job=None
    token=('R13_REWARD',context,id(module),float(value),float(module.xp_multiplier.value));now=time.monotonic()
    confirm=State.xp_external_confirm
    if confirm is None or confirm[0]!=token or now>=confirm[1]:
        State.xp_external_confirm=(token,now+7.)
        State.xp_status='Confirm %gx on XP Gain Multiplier. Press Apply again within 7 seconds.'%value;redraw();return False
    State.xp_external_confirm=None
    job=dict(context=context,module=module,target=float(value),returned=False);State.r13_xp_job=job
    try:
        if studio_context()!=context or r13_xp_module() is not module:raise RuntimeError('XP player/backend changed')
        numeric=('%.2f'%value) if round(value,2)==value else repr(float(value))
        get_pc(possibly_loading=True).ConsoleCommand('xp_mult '+numeric)
        job['returned']=True
        actual=module.xp_multiplier.value
        if type(actual) not in (int,float) or not math.isfinite(actual) or actual!=value:
            State.xp_status='Command returned; config differs. Read again without sending another request.';redraw();return False
        State.r13_xp_job=None
        State.xp_status='CONFIG READBACK %gx / payout unverified; observe the next reward on both XP tracks.'%value
        State.xp_external_status=State.xp_status;redraw();return True
    except Exception as error:
        record_runtime_fault('XP_REWARD_REQUEST',error)
        State.xp_status='Add-on command unconfirmed; partial effects possible. No repeat in this context.';redraw();return False

def r13_xp_restore():
    if State.xp_external_view:
        # External add-on owns its hooks and awards. Stage vanilla, then use
        # its normal two-press command; never remove its native handles.
        if State.r13_xp_job is not None:return False
        xp_external_stage(1.);State.xp_external_confirm=None
        State.xp_status='Vanilla 1x staged for the add-on. Apply twice; previously earned XP is permanent.';redraw();return False
    return xp_restore_owned()

def r13_xp_dashboard(layout,left,y,width):
    rows=[studio_track_read(i) for i in (0,1)];half=(width-14)/2
    for i,(name,row) in enumerate(zip(('CHARACTER','SPECIALISATION'),rows)):
        xx=left+i*(half+14)
        optional_art_image(layout,'FIELD_CARD_XP',xx,y,half,97,z=6,opacity=.52)
        text(layout,name,xx+14,y+10,half-28,24,theme_color('highlight'),.78,10)
        text(layout,('LEVEL %d / XP %d'%(row['level'],row['xp'])) if row else 'Load a compatible character',xx+14,y+43,half-28,39,theme_color('text'),.87,10)
    text(layout,reward_summary(),left+12,y+111,width-24,61,theme_color('dim'),.76)

def r13_bonus_choose(profile):
    if profile not in R13_BONUSES or State.r10_bonus is not None:return False
    State.r13_bonus_profile=profile;State.r10_bonus_status='Staged '+R13_BONUSES[profile][0]+'. Start applies only available owned fields.';redraw();return True

def r13_arena_capacity():
    return 5 if State.panel_rect and State.panel_rect[3]>=1000 else 3

def r13_arena_tick(now):
    if (not State.opened or State.page!='ARENA' or State.encounter_route!='ARENA' or State.arena_bridge_issued is None
            or State.r13_arena_fault or now<State.r13_arena_next):return
    State.r13_arena_next=now+1.
    arena_bridge_read(quiet=True)

State.r16_forge_sort='SOURCE'

State.r16_bonus_fill=None

State.r16_bonus_rect=None

State.r16_bonus_generation=-1

R13_BONUSES.update({
 'GLASS':('Glass cannon: more damage dealt AND taken',(('OUTGOING','UP'),('INCOMING','UP'))),
 'HEALING':('Healing support',(('HEAL_RECEIVED','UP'),('HEAL_DEALT','UP'))),
})

def r16_forge_sort():
    modes=('SOURCE','A-Z','Z-A','TYPE','FAVOURITES')
    State.r16_forge_sort=modes[(modes.index(State.r16_forge_sort)+1)%len(modes)]
    State.spawn_page=0;State.spawn_pending=None;State.spawn_expires=0.
    if State.opened:redraw()
    return State.r16_forge_sort

def r16_sorted_pools(indices):
    # Recent source order remains meaningful unless the user explicitly sorts.
    mode=State.r16_forge_sort
    if mode=='SOURCE':return indices
    def key(i):
        row=SPAWN_POOLS[i];name=(row[0].casefold(),row[1])
        return ((row[2].casefold(),)+name if mode=='TYPE' else
                (row[1] not in State.spawn_favorites,)+name if mode=='FAVOURITES' else name)
    return sorted(indices,key=key,reverse=mode=='Z-A')

def draw_forge_browser(layout,left,y,width):
    half=(width-10)/2;rows=forge_page_indices();capacity=forge_page_capacity()
    columns=2 if width>=850 and State.panel_rect and State.panel_rect[3]>=870 else 1
    btn(layout,'CATEGORY: '+_spawn_category(),left,y,half,34,cycle_spawn_category,small=True)
    btn(layout,'SORT: '+State.r16_forge_sort,left+half+10,y,half,34,r16_forge_sort,small=True)
    btn(layout,'FIND BY NAME'+(' / '+State.spawn_search if State.spawn_search else ''),left,y+43,width,34,forge_open_search,small=True)
    for i,(label,step) in enumerate((('<< PREVIOUS PAGE',-1),('NEXT PAGE >>',1))):
        btn(layout,label,left+i*(half+10),y+86,half,32,lambda d=step:forge_change_page(d),small=True)
    for slot in range(capacity):
        yy=y+130+(slot//columns)*(72 if columns==2 else 40)
        xx=left+(slot%columns)*(half+10) if columns==2 else left
        cw=half if columns==2 else width;ch=62 if columns==2 else 34
        if slot<len(rows):
            index=rows[slot];name,token,kind=SPAWN_POOLS[index]
            caption=str(State.spawn_page*capacity+slot+1)+'. '+('* ' if token in State.spawn_favorites else '')+name
            if columns==2:optional_art_image(layout,'FIELD_CARD_FORGE',xx,yy,cw,ch,z=8,opacity=.38)
            btn(layout,caption if columns==1 else '',xx,yy,cw,ch,lambda n=slot:forge_choose(n),active=State.spawn_pool_idx==index,small=True)
            if columns==2:
                # Keep the real action name for focus/help; native text layers
                # use explicit title/subtitle bands rather than a centered label.
                State.buttons[-1]['name']=caption
                text(layout,caption,xx+11,yy+3,cw-47,34,theme_color('accent') if State.spawn_pool_idx==index else theme_color('text'),.82,14)
                text(layout,kind+' / CURATED POOL',xx+11,yy+39,cw-22,22,theme_color('dim'),.62,14)
        elif not rows and slot==0:btn(layout,'SHOW ALL ITEMS',left,yy,width,34,forge_recover_catalogue,small=True)
    if State.panel_rect and State.panel_rect[3]>=830:
        text(layout,'%d matching pools / page %d of %d / select to review level and quantity'%
             (len(_spawn_visible_indices()),State.spawn_page+1,forge_pages()),left+10,y+134+math.ceil(capacity/columns)*(72 if columns==2 else 40),width-20,37,theme_color('dim'),.76)

def r16_inspect_owned_weapons():
    # An inventory observation, never an asserted correlation with a pool request.
    def inspect():
        show_page('GEAR');State.weapon_view=True;State.weapon_detail=True
        ok=weapon_read()
        State.weapon_status=('OWNED WEAPONS OBSERVED / ' if ok else 'OWNED WEAPON READ UNAVAILABLE / ')+State.weapon_status
        redraw();return ok
    return _ui_batch(inspect)

def r16_progress_increment(amount):
    if type(amount) is not int or amount not in (1,5,10):return False
    view=State.r10_view
    row=studio_points_read() if view=='POINTS' else studio_track_read() if view=='LEVELS' else None
    if row is None or State.r10_progress_job is not None:return False
    current=row['points'] if view=='POINTS' else row['level']
    maximum=(500,1000)[State.r10_track] if view=='POINTS' else (60,701)[State.r10_track]
    target=min(maximum,current+amount)
    if target<=current:return False
    return studio_stage('POINTS' if view=='POINTS' else 'LEVEL',target)

def r16_bonus_bar(layout,left,y,width):
    job=State.r10_bonus
    box(layout,left,y,width,4,theme_color('muted'),8)
    if job:
        duration=job.get('duration',State.r10_bonus_duration)
        ratio=max(0.,min(1.,(job['until']-time.monotonic())/duration))
        State.r16_bonus_fill=box(layout,left,y,max(.1,width*ratio),4,theme_color('accent'),9)
        State.r16_bonus_rect=(left,y,width)
        State.r16_bonus_generation=State.frame_generation

def r16_bonus_bar_tick(now):
    job=State.r10_bonus;rect=State.r16_bonus_rect
    if not (job and rect and State.opened and State.r16_bonus_generation==State.frame_generation):return
    x,y,w=rect;ratio=max(0.,min(1.,(job['until']-now)/job.get('duration',State.r10_bonus_duration)))
    size_position(State.r16_bonus_fill,x,y,max(.1,w*ratio),4,9)

def r16_bonus_review(layout,left,y,width):
    profile=State.r13_bonus_profile;job=State.r10_bonus
    optional_art_image(layout,'FIELD_CARD_XP',left,y,width,141,z=6,opacity=.36)
    text(layout,'OWNED FIELD REVIEW' if job else 'FIELD REVIEW / STAGED ONLY',left+14,y+8,width-28,27,theme_color('accent'),.84,10)
    for i,(key,direction) in enumerate(R13_BONUSES[profile][1]):
        row=combat_pair(key);expected=State.combat_last.get(key) if job else None
        if row is None:line=key+' / NOT AVAILABLE ON THIS CHARACTER'
        else:
            read=row[1][0]
            target=expected if expected is not None else read*(State.r10_bonus_scale if direction=='UP' else 1./State.r10_bonus_scale)
            valid=row[1][0]==row[1][1] and TUNING_FIELDS[key][2]<=target<=TUNING_FIELDS[key][3]
            line=key+' / READ %g / TARGET %g'%(read,target)+(' / NOT READY' if not valid else '')
        text(layout,line,left+14,y+43+i*27,width-28,25,theme_color('text'),.73,10)

load_preferences()
_detect_unclean_menu_close()

_mod_settings_file = SETTINGS_DIR / "CROWNs_Freedom_ModState.json" if SETTINGS_DIR is not None else None
_first_install = _mod_settings_file is None or not _mod_settings_file.exists()

CROWNS_MOD=build_mod(
    name="CROWNs Freedom | ECHO Fieldcraft R23",
    author="CROWN",
    version=RELEASE_VERSION,
    description="Premium ECHO Command Centre: redesigned holographic interface, staged local tools, owned temporary restoration and audited optional integrations. Native gameplay acceptance pending.",
    keybinds=[toggle,dock_hotkey,open_travel_hub,emergency,restore_hotkey,focus_hotkey,flight_hotkey],
    on_enable=install_controller_hook,
    on_disable=on_disable,
    auto_enable=True,
    settings_file=_mod_settings_file,
)
# Unlike auto_enable (which ONLY restores an existing enabled:true record),
# a brand-new CROWN install must be explicitly enabled once in the code.
# The stable settings file then retains the user's enabled/disabled choice.
if _first_install:
    _enable=getattr(CROWNS_MOD,'enable',None)
    if callable(_enable):
        try:_enable()
        except Exception as error:log('FIRST-RUN AUTOSTART FAILED // '+str(error)[:80])



def xp_external_backend():
    """Presence probe for independently enabled community XP mods.

    This is NOT proof a command will run or that earned XP was changed. Only
    explicit known mod/module names qualify; no imports and no method probing.
    """
    import sys
    mods=tuple(sys.modules)
    if 'xp_gain_multiplier' in mods:
        return ('XP GAIN MULTIPLIER','xp_mult','xp_mult_status')
    if 'xp_live_menu' in mods:
        return ('XP LIVE MENU','xplive','xplive')
    return None


def _xp_external_probe_r7():
    backend=xp_external_backend()
    if backend is None:
        State.xp_external_status=('ADD-ON NOT LOADED / Install and enable either '
            'xp_gain_multiplier or xp_live_menu separately, then restart BL4.')
    elif not sandbox_solo_ready():
        State.xp_external_status='BLOCKED / Solo character only for this integration.'
    else:
        State.xp_external_status='AVAILABLE TO REQUEST / '+backend[0]+'; earned XP still unverified.'
    log('XP ADD-ON // '+State.xp_external_status)
    if State.opened:redraw()
    return backend is not None and sandbox_solo_ready()


def _xp_external_request_r7(status_only=False):
    """Validated optional console command; never asserts a successful effect.

    Two-click confirmation prevents accidentally stacking XP from another mod.
    After one request, the external add-on exclusively owns its modifications;
    CROWN does not try to restore or overwrite its modifier handles.
    """
    backend=xp_external_backend()
    if backend is None or not sandbox_solo_ready():
        State.xp_external_confirm=None
        return xp_external_probe()
    pc=get_pc(possibly_loading=True)
    if pc is None or not callable(getattr(pc,'ConsoleCommand',None)):
        State.xp_external_status='NO CONSOLE API / BL4 controller not ready.'
        log('XP ADD-ON // '+State.xp_external_status)
        if State.opened:redraw()
        return False
    now=time.monotonic()
    amount=State.external_xp_draft
    if type(amount) not in (int,float) or not math.isfinite(amount) or amount<.1 or amount>10:
        State.xp_external_status='INVALID / Choose external XP multiplier between 0.1 and 10.'
        if State.opened:redraw()
        return False
    if not status_only:
        token=(backend[0],_session_anchor(),round(float(amount),2))
        if (State.xp_external_confirm is None or State.xp_external_confirm[0]!=token or
                now>State.xp_external_confirm[1]):
            State.xp_external_confirm=(token,now+6.)
            State.xp_external_status='CONFIRM / Request '+format(float(amount),'.2f')+'x in '+backend[0]+'? Press AGAIN within 6 s.'
            log('XP ADD-ON // '+State.xp_external_status)
            if State.opened:redraw()
            return False
    State.xp_external_confirm=None
    command=backend[2] if status_only else backend[1]+' '+format(float(amount),'.2f')
    try:
        result=pc.ConsoleCommand(command)
        # ConsoleCommand's return value does not verify which mod received it.
        State.xp_external_status=('STATUS COMMAND SENT' if status_only else 'XP REQUEST SENT')+' / '+backend[0]+' / verify mod console and NEXT real earned reward.'
        log('XP ADD-ON // '+State.xp_external_status)
        if State.opened:redraw()
        return True
    except Exception as exc:
        State.xp_external_status='CONSOLE REQUEST FAILED / '+type(exc).__name__
        record_runtime_fault('XP_EXTERNAL_CONSOLE',exc)
        log('XP ADD-ON // '+State.xp_external_status)
        if State.opened:redraw()
        return False


def xp_external_view():
    return r13_xp_source(State.xp_route if State.xp_external_view else 'REWARD')


def _draw_xp_external_r7(layout,left,y,width):
    half=(width-12.)/2.
    backend=xp_external_backend()
    text(layout,'OPTIONAL XP MOD LINK / NO AUTOMATIC INSTALL',left+8,y+9,width-16,31,theme_color('accent'),.8,12)
    text(layout,'Supports independent XP Gain Multiplier or XP Live Menu. They must be installed and enabled.',
         left+8,y+47,width-16,43,theme_color('dim'),.68,12)
    slider(layout,'EXTERNAL XP DRAFT (1x-10x)',State.xp_draft,1.,10.,left,y+94,width,xp_stage)
    actions=(('CHECK XP ADD-ON',xp_external_probe),('STATUS IN ADD-ON',lambda:xp_external_request(True)),
        ('SEND XP REQUEST (2x)',xp_external_request),('BACK TO XP LAB',xp_external_view),
        ('STAGE 2x',lambda:(xp_stage(2.),redraw())),('STAGE 5x',lambda:(xp_stage(5.),redraw())))
    for i,(caption,fn) in enumerate(actions):
        btn(layout,caption,left+(i%2)*(half+12.),y+161+(i//2)*41.,half,34.,fn,small=True,
            disabled=(i in (1,2) and backend is None))
    text(layout,_status_brief(State.xp_external_status,121),left+9,y+296,width-18,46,theme_color('highlight'),.66,12)




# COMMUNITY BRIDGE R7: this is original glue, NOT copied third-party mod source.
# Depend on the authors' independently installed/enabled modules and commands.
# The mod-manager can load disabled modules, so even module presence is a *hint*,
# never evidence that a command actually ran or changed gameplay.
COMMUNITY_ACTIONS={
    'levels5':('give5levels','BONK +5 LEVELS'),
    'loot':('spawnitems','BONK DEVELOPER LOOT REQUEST'),
    'cash1000':('addcurrency money 1000','BONK +1000 CASH'),
    'eridium100':('addcurrency eridium 100','BONK +100 ERIDIUM'),
}

def community_modules():
    import sys
    names=tuple(sys.modules)
    return {
        'bonk':any(n=='BonkUtilities' or n.startswith('BonkUtilities.') for n in names),
        'xp':any(n=='xp_gain_multiplier' or n.startswith('xp_gain_multiplier.') for n in names),
        'arena':any(n=='bl4_arena' or n.startswith('bl4_arena.') for n in names),
        'bl4live':any(n=='bl4_live' or n.startswith('bl4_live.') for n in names),
    }

def community_modules_brief():
    mods=community_modules()
    return ' / '.join(k.upper()+(' SEEN (NOT PROVEN ENABLED)' if mods[k] else ' NOT LOADED')
                    for k in ('bonk','xp','arena'))

def community_probe():
    State.community_confirm=None
    State.community_status=('MODULE SCAN / '+community_modules_brief()
        +' / Inspect SDK Mods menu for enabled state. XP: XP Lab; Arena: own F6 panel.')
    log('COMMUNITY // '+State.community_status)
    if State.opened:redraw()
    return community_modules()

def community_arena_instructions():
    State.community_confirm=None
    State.community_status=('BL4 ARENA / Install bl4_arena.sdkmod separately and enable in SDK Mods. '
        'Close CROWN (F6) then use Arena F6 or its rebindable key. '
        'Arena owns its own spawning and cleanup; CROWN will not hijack those actors.')
    log('COMMUNITY // '+State.community_status)
    if State.opened:redraw()
    return community_modules()['arena']

# The following game's *developer perk IDs* are independently source-reviewed
# against Bonk Utilities v1.0.9 (MIT): 0=its +5 levels request, 7=its
# developer item spawn request. This invokes CROWN's existing reflected API,
# not the Bonk module, so no third-party code is copied or bundled. Actual game
# effects are UNVERIFIED until the player checks readback on a test character.
COMMUNITY_NATIVE_PERKS={
    'levels5':(0,'GAME DEVELOPER +5 LEVELS REQUEST'),
    'loot':(7,'GAME DEVELOPER ITEM DROP REQUEST'),
}

def community_native_request(action):
    if action not in COMMUNITY_NATIVE_PERKS:
        State.community_confirm=None
        return False
    if not sandbox_solo_ready():
        State.community_confirm=None
        State.community_status='BLOCKED / Authoritative SOLO character required.'
        log('COMMUNITY // '+State.community_status)
        if State.opened:redraw()
        return False
    context=r12_grant_context()
    if context is None or State.r12_grant_uncertain==context:
        State.community_status='BLOCKED / Previous grant uncertain or player context unavailable; no repeat.';log(State.community_status)
        if State.opened:redraw()
        return False
    anchor=_session_anchor()
    pc=get_pc(possibly_loading=True)
    method=getattr(pc,'ServerActivateDevPerk',None) if pc is not None else None
    if anchor is None or not callable(method):
        State.community_confirm=None
        State.community_status='BLOCKED / Current character or developer-perk API unavailable.'
        if State.opened:redraw()
        return False
    perk,label=COMMUNITY_NATIVE_PERKS[action]
    token=('GAME',action,anchor,context)
    now=time.monotonic()
    confirm=State.community_confirm
    if confirm is None or confirm[0]!=token or now>=confirm[1]:
        State.community_confirm=(token,now+7.)
        State.community_status=('CONFIRM / '+label+'? Press SAME button again within 7 seconds. '
            'Save a backup; level/item grants may persist.')
        log('COMMUNITY // '+State.community_status)
        if State.opened:redraw()
        return False
    State.community_confirm=None
    try:
        if studio_context()!=context:raise RuntimeError('player changed before grant')
        State.r12_grant_uncertain=context
        method(perk)
        State.r12_grant_uncertain=None
    except Exception as exc:
        State.community_status='GAME REQUEST ERROR / '+type(exc).__name__+' / no success claimed.'
        record_runtime_fault('COMMUNITY_NATIVE_PERK',exc)
        log('COMMUNITY // '+State.community_status)
        if State.opened:redraw()
        return False
    State.community_status=('GAME REQUEST SENT / '+label+' / Verify actual level or dropped items; '
        'API acceptance is not proof of a reward.')
    log('COMMUNITY // '+State.community_status)
    if State.opened:redraw()
    return True

def community_request(action):
    # No arbitrary text reaches the game console. Strong session and consent gating.
    if action not in COMMUNITY_ACTIONS:
        State.community_confirm=None
        return False
    installed=community_modules()
    if not installed['bonk'] or not sandbox_solo_ready():
        State.community_confirm=None
        State.community_status='BLOCKED / Bonk Utilities must be loaded, enabled, and session must be authoritative SOLO.'
        log('COMMUNITY // '+State.community_status)
        if State.opened:redraw()
        return False
    context=r12_grant_context()
    if context is None or State.r12_grant_uncertain==context:
        State.community_status='BLOCKED / Previous grant uncertain or player context unavailable; no repeat.';log(State.community_status)
        if State.opened:redraw()
        return False
    anchor=_session_anchor()
    if anchor is None:
        State.community_confirm=None
        State.community_status='BLOCKED / Stable local character needed.'
        if State.opened:redraw()
        return False
    pc=get_pc(possibly_loading=True)
    if pc is None or not callable(getattr(pc,'ConsoleCommand',None)):
        State.community_confirm=None
        State.community_status='BLOCKED / Player console is unavailable.'
        if State.opened:redraw()
        return False
    command,label=COMMUNITY_ACTIONS[action]
    now=time.monotonic()
    token=(action,anchor,context)
    confirmation=State.community_confirm
    if confirmation is None or confirmation[0]!=token or now>=confirmation[1]:
        State.community_confirm=(token,now+7.)
        State.community_status=('CONFIRM / '+label+'? Press SAME button within 7 seconds. '
            'May permanently change character. Have a backup.')
        log('COMMUNITY // '+State.community_status)
        if State.opened:redraw()
        return False
    # Disarm BEFORE attempting the console call; never queue or retry writes.
    State.community_confirm=None
    try:
        if studio_context()!=context:raise RuntimeError('player changed before grant')
        State.r12_grant_uncertain=context
        pc.ConsoleCommand(command)
        State.r12_grant_uncertain=None
    except Exception as exc:
        State.community_status='CONSOLE ERROR / '+type(exc).__name__+' / no success claimed.'
        record_runtime_fault('COMMUNITY_BRIDGE',exc)
        log('COMMUNITY // '+State.community_status)
        if State.opened:redraw()
        return False
    State.community_status=('REQUEST SENT / '+label+' / verify in actual BL4; '
        'console return does not prove level, loot or money changed.')
    log('COMMUNITY // '+State.community_status)
    if State.opened:redraw()
    return True

def capability_next_page():
    count=len(State.capability_status_rows or crown_capability_rows())
    per=5 if (State.panel_rect and State.panel_rect[3]>=760) else 3
    pages=max(1,math.ceil(count/per))
    State.capability_page=(State.capability_page+1)%pages
    if State.opened:redraw()
    return State.capability_page


def _maybe_warmup_art(now):
    if (not State.opened or State.safe_mode or State.art_mode!='AUTO' or
            not State.art_deferred or State.art_warmup_steps>=4 or now<State.art_warmup_due or
            State.redraw_pending or State.numeric_editor is not None or State.profile_name_edit):
        return False
    if ((State.page=='ARENA' and State.encounter_view=='SEARCH') or
            (State.page=='SPAWN' and State.spawn_view in ('SEARCH','LEVEL')) or
            (State.page=='FINDER' and State.finder_mode=='EDIT') or
            (State.page=='CAPACITY' and State.capacity_view=='EDIT')):
        return False
    State.art_warmup_steps+=1
    State.art_warmup_due=now+.9
    redraw()  # same game tick; importer itself remains on the game thread
    return True
