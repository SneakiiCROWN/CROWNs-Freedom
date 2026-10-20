"""New reconciled features tested against the full recovered SDK fixture.

Offline simulation only: no native lifetime, physical input or game proof.
"""
from pathlib import Path
from types import SimpleNamespace as NS
from tempfile import TemporaryDirectory
import runpy,sys,json,math,unittest
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
source=(root/'SOURCE/__init__.py').read_text(encoding='utf-8')

class EchoStudioTests(unittest.TestCase):
    def setUp(self):
        sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
        self.g={'__name__':'crown_echo_r1_qa'}
        exec(compile(source,'crown_echo_r1','exec'),self.g)
        self.S=self.g['State'];self.S.safe_mode=True;self.S.dock_mode='FULL'
        self.g['open_menu']();self.assertTrue(self.S.draw_ok,self.S.message)
    def draw(self,page):
        self.g['show_page'](page);self.assertTrue(self.S.draw_ok,self.S.message)
    def bounds(self):
        x,y,w,h,*_=self.S.panel_rect
        for i,a in enumerate(self.S.buttons):
            ax,ay,aw,ah=a['rect']
            self.assertTrue(x-1<=ax and ax+aw<=x+w+1 and y-1<=ay and ay+ah<=y+h+1,a['name'])
            for b in self.S.buttons[i+1:]:
                bx,by,bw,bh=b['rect']
                self.assertTrue(min(ax+aw,bx+bw)-max(ax,bx)<=1 or min(ay+ah,by+bh)-max(ay,by)<=1,(a['name'],b['name']))
    def test_new_views_four_viewports(self):
        for screen in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
            self.g['viewport']=lambda wh=screen:wh
            for page in ('DASHBOARD','PROFILES','DISPLAY'):
                self.draw(page);self.bounds()
            for view in ('MAIN','THEMES','COLOURS'):
                self.S.appearance_view=view;self.draw('STYLE');self.bounds()
            self.S.spawn_view='TOOLS';self.draw('SPAWN');self.bounds()
    def test_direct_theme_stages_and_cancels(self):
        self.draw('STYLE');old=self.S.theme_idx
        self.g['appearance_choose_theme'](3)
        self.assertEqual(self.S.theme_idx,old);self.assertEqual(self.S.appearance_draft['theme'],3)
        self.g['appearance_cancel']();self.assertEqual(self.S.theme_idx,old)
    def test_custom_accent_apply_no_rebuild(self):
        self.draw('STYLE');count=self.S.ui_rebuild_count
        self.assertTrue(self.g['appearance_stage']('accent','#12ABCD'))
        self.g['appearance_apply']();self.assertEqual(self.S.custom_accent,'#12ABCD')
        self.assertEqual(count,self.S.ui_rebuild_count)
        self.assertEqual(self.g['theme_color']('accent'),self.g['_hex']('#12ABCD'))
    def test_separate_background(self):
        self.draw('STYLE');panel=self.S.panel_opacity
        self.g['appearance_stage']('background',.4);self.g['appearance_apply']()
        self.assertEqual(self.S.panel_opacity,panel);self.assertEqual(self.g['theme_color']('bg')[3],.4)
        calls=[];original=self.g['box']
        def observe(parent,x,y,w,h,col,z=1):
            calls.append((x,y,w,h,col));return original(parent,x,y,w,h,col,z)
        self.g['box']=observe;self.g['redraw']()
        x,y,w,h,*_=self.S.panel_rect
        background=next(col for bx,by,bw,bh,col in calls if (bx,by,bw,bh)==(x,y,w,h))
        self.assertAlmostEqual(background[3],.4)
    def test_channel_limits_and_safe_stage(self):
        self.draw('STYLE');self.assertFalse(self.g['appearance_channel'](0,300))
        self.assertTrue(self.g['appearance_channel'](0,32));self.assertIsNone(self.S.custom_accent)
        self.assertTrue(self.S.appearance_draft['accent'].startswith('#20'))
    def test_bad_colour_rejected(self):
        self.assertFalse(self.g['appearance_stage']('accent','#bad'))
        self.assertIsNone(self.S.custom_accent)
    def test_extra_validation_is_atomic(self):
        self.draw('STYLE');before=self.g['_appearance_snapshot']()
        self.S.appearance_draft=dict(before,accent='broken',opacity=.7)
        self.assertFalse(self.g['appearance_apply']());self.assertEqual(before,self.g['_appearance_snapshot']())
    def test_fade_duration_persists(self):
        self.draw('STYLE');self.g['appearance_stage']('duration',.32);self.g['appearance_apply']()
        self.assertEqual(self.S.transition_duration,.32)
    def test_slider_decline_restores(self):
        self.draw('MOTION');ref=self.S.sliders[0];before=ref.value;ref.apply=lambda v:False
        self.assertFalse(ref.adjust(1));self.assertEqual(ref.value,before);self.assertEqual(ref.committed,before)
    def test_slider_nochange_never_calls_backend(self):
        self.draw('MOTION');ref=self.S.sliders[0];calls=[];ref.apply=lambda v:calls.append(v)
        self.assertTrue(self.g['_slider_apply_checked'](ref,ref.value));self.assertEqual(calls,[])
    def test_slider_stale_rejected(self):
        self.draw('MOTION');ref=self.S.sliders[0];calls=[];ref.apply=lambda v:calls.append(v)
        self.draw('STYLE');self.assertFalse(ref.adjust(1));self.assertEqual(calls,[])
        self.assertFalse(self.g['numeric_open'](ref))
    def test_numeric_backend_error_retains_text(self):
        self.draw('MOTION');ref=self.S.sliders[0];ref.apply=lambda v:False
        self.g['numeric_open'](ref);self.S.numeric_widget=NS(GetText=lambda:'2.375')
        self.assertFalse(self.g['numeric_apply']())
        self.assertEqual(self.S.numeric_editor['text'],'2.375');self.assertIn('declined',self.S.numeric_editor['error'])
        self.g['redraw']();self.assertIn('declined',self.S.numeric_editor['error'])
    def test_numeric_single_rebuild(self):
        self.draw('STYLE');self.g['numeric_open'](self.S.sliders[0]);self.S.numeric_widget=NS(GetText=lambda:'.82')
        count=self.S.ui_rebuild_count;self.assertTrue(self.g['numeric_apply']())
        self.assertEqual(count+1,self.S.ui_rebuild_count)
    def test_numeric_nochange_does_not_apply(self):
        self.draw('MOTION');ref=self.S.sliders[0];calls=[];ref.apply=lambda v:calls.append(v)
        self.g['numeric_open'](ref);self.S.numeric_widget=NS(GetText=lambda:str(ref.value))
        self.assertTrue(self.g['numeric_apply']());self.assertEqual(calls,[])
    def test_numeric_widget_failure_preserves_menu(self):
        self.draw('MOTION');ref=self.S.sliders[0];real=self.g['widget']
        def widget(kind):
            if kind=='EditableTextBox':raise RuntimeError('injected')
            return real(kind)
        self.g['widget']=widget;self.g['numeric_open'](ref)
        self.assertTrue(self.S.opened);self.assertTrue(self.S.draw_ok);self.assertIsNone(self.S.numeric_widget)
        self.g['numeric_step'](1);self.assertGreater(self.S.numeric_editor['value'],ref.value)
    def test_numeric_session_change_rejected(self):
        self.draw('MOTION');ref=self.S.sliders[0];calls=[];ref.apply=lambda v:calls.append(v)
        self.g['numeric_open'](ref);self.S.numeric_widget=NS(GetText=lambda:'2')
        self.g['_session_anchor']=lambda:('different',)
        self.assertFalse(self.g['numeric_apply']());self.assertEqual(calls,[])
    def test_forge_settings_cancel_pending_no_spawn(self):
        self.S.spawn_pending='armed';self.S.spawn_expires=99999;self.S.forge_blueprint_pending='armed'
        before=self.S.spawn_requests
        self.assertTrue(self.g['_forge_numeric_stage']('level',70));self.assertTrue(self.g['_forge_numeric_stage']('count',3))
        self.assertIsNone(self.S.spawn_pending);self.assertIsNone(self.S.forge_blueprint_pending)
        self.assertEqual(self.S.spawn_requests,before)
        for value in (0,4,float('nan'),True):self.assertFalse(self.g['_forge_numeric_stage']('count',value))
    def test_profile_rename_draft_survives_redraw(self):
        self.draw('PROFILES');self.g['profile_rename_open']();self.S.profile_name_widget=NS(GetText=lambda:'Forge Builder')
        self.g['redraw']();self.assertEqual(self.S.profile_name_draft,'Forge Builder')
    def test_profile_back_cancels_without_closing(self):
        self.draw('PROFILES');self.g['profile_rename_open']();self.g['_controller_back']()
        self.assertTrue(self.S.opened);self.assertFalse(self.S.profile_name_edit)
    def test_preferences_extra_roundtrip(self):
        with TemporaryDirectory() as folder:
            self.g['SETTINGS_DIR']=Path(folder);self.S.custom_accent='#123456';self.S.background_opacity=.45;self.S.transition_duration=.3
            self.g['save_preferences']();self.S.custom_accent=None;self.S.background_opacity=.75
            self.g['load_preferences']();self.assertEqual(self.S.custom_accent,'#123456');self.assertEqual(self.S.background_opacity,.45)
    def test_profiles_preserve_new_values(self):
        self.S.custom_accent='#123456';self.S.background_opacity=.45;self.g['save_ui_profile'](1)
        self.S.custom_accent=None;self.assertTrue(self.g['load_ui_profile'](1));self.assertEqual(self.S.custom_accent,'#123456')
    def test_invalid_profile_extras_preserve_everything(self):
        self.g['save_ui_profile'](1);self.S.ui_profiles['1']['echo_appearance']['accent']='broken'
        before=self.g['_appearance_snapshot']();self.assertFalse(self.g['load_ui_profile'](1))
        self.assertEqual(self.g['_appearance_snapshot'](),before)
    def test_transfer_stages_does_not_apply(self):
        with TemporaryDirectory() as folder:
            self.g['SETTINGS_DIR']=Path(folder);self.S.custom_accent='#123456';self.g['appearance_transfer'](True)
            self.S.custom_accent=None;self.assertTrue(self.g['_ui_batch'](self.g['appearance_transfer']))
            self.assertIsNone(self.S.custom_accent);self.assertEqual(self.S.appearance_draft['accent'],'#123456')
    def test_transfer_rejects_unknown_or_oversize(self):
        with TemporaryDirectory() as folder:
            self.g['SETTINGS_DIR']=Path(folder);path=Path(folder)/'CROWNs_Freedom_UI_Transfer.json'
            for raw in ('{}','a'*32769):
                path.write_text(raw);self.assertFalse(self.g['appearance_transfer']())
    def test_fov_failure_restores_both_fields(self):
        class Camera:
            BaseFOV=100;_vehicle=100
            @property
            def VehicleFOV(self):return self._vehicle
            @VehicleFOV.setter
            def VehicleFOV(self,value):
                if value==120:raise RuntimeError('injected second-field failure')
                self._vehicle=value
        obj=Camera();self.g['get_pc']=lambda: NS(player=obj)
        self.assertFalse(self.g['change_fov'](120));self.assertEqual((obj.BaseFOV,obj.VehicleFOV),(100,100))
    def test_fov_success_returns_true(self):
        obj=NS(BaseFOV=100,VehicleFOV=100);self.g['get_pc']=lambda: NS(player=obj)
        self.assertTrue(self.g['change_fov'](115));self.assertEqual(obj.BaseFOV,115)
    def test_world_failure_rolls_back(self):
        class World:
            value=1.
            @property
            def TimeDilation(self):return self.value
            @TimeDilation.setter
            def TimeDilation(self,value):self.value=2.5 if value==2. else value
        world=World();self.g['get_worldsettings']=lambda:world;self.g['can_run_shared']=lambda label:True
        self.assertFalse(self.g['set_world_time'](2.));self.assertEqual(world.TimeDilation,1.)
    def test_hud_controls_directly_available(self):
        self.draw('DISPLAY');self.assertTrue(any('CROWN RIBBON' in b['name'] for b in self.S.buttons))
    def resources(self):
        actor=ctx['pawn']
        actor.HealthState=NS(RepairKitMaxCharges=NS(Value=3.,BaseValue=3.),RepairKitCooldown=NS(Value=20.,BaseValue=20.),RepairKitDuration=NS(Value=8.,BaseValue=8.))
        actor.DamageState=NS(HealingReceivedMultiplier=NS(Value=1.,BaseValue=1.))
        actor.DamageCauserData=NS(HealingDealtMultiplier=NS(Value=1.,BaseValue=1.))
        actor.DownState=NS(SecondWindHealth=NS(Value=1.,BaseValue=1.),SecondWindShield=NS(Value=1.,BaseValue=1.))
        actor.ammoregenrate=NS(Value=0.,BaseValue=0.)
        self.g['session_role']=lambda:'SOLO'
        return actor
    def test_eight_resource_paths_write_readback_restore(self):
        actor=self.resources()
        values={'KIT_CHARGES':5.,'KIT_COOLDOWN':10.,'KIT_DURATION':6.,'HEAL_RECEIVED':2.,'HEAL_DEALT':2.,'AMMO_REGEN':1.,'SECOND_WIND_HEALTH':.5,'SECOND_WIND_SHIELD':.5}
        before={k:self.g['combat_pair'](k)[1] for k in values}
        for key,value in values.items():
            self.assertTrue(self.g['combat_tune'](key,value),key)
            self.assertEqual(self.g['combat_pair'](key)[1],(value,value))
        self.assertEqual(self.g['restore_combat_tuning'](),8)
        for key,value in before.items():self.assertEqual(self.g['combat_pair'](key)[1],value)
    def test_resource_missing_and_wrong_type_refused(self):
        actor=self.resources();actor.HealthState.RepairKitCooldown.Value=20
        self.assertIsNone(self.g['combat_pair']('KIT_COOLDOWN'))
        self.assertFalse(self.g['combat_tune']('KIT_COOLDOWN',5.))
        del actor.ammoregenrate;self.assertFalse(self.g['combat_tune']('AMMO_REGEN',2.))
    def test_resource_authority_and_competing_mod_guards(self):
        actor=self.resources();self.g['session_role']=lambda:'HOST'
        # A verified listen host owns their own pawn: local combat tuning allowed.
        self.assertTrue(self.g['combat_tune']('KIT_COOLDOWN',5.))
        self.assertEqual(actor.HealthState.RepairKitCooldown.Value,5.)
        self.g['session_role']=lambda:'SOLO'
        sys.modules['bl4_resources_and_cooldowns']=NS()
        try:self.assertFalse(self.g['combat_tune']('KIT_COOLDOWN',10.))
        finally:sys.modules.pop('bl4_resources_and_cooldowns')
        self.assertEqual(actor.HealthState.RepairKitCooldown.Value,5.)
    def test_resource_ranges_refuse_extremes(self):
        self.resources()
        for key,value in (('KIT_CHARGES',99.),('AMMO_REGEN',1000.),('KIT_COOLDOWN',float('nan'))):
            self.assertFalse(self.g['combat_tune'](key,value))
    def test_resource_views_four_viewports(self):
        self.resources()
        for screen in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
            self.g['viewport']=lambda wh=screen:wh
            self.draw('PLAYER');self.S.resource_view=True
            for page in range(3):
                self.S.resource_index=page;self.g['redraw']();self.assertTrue(self.S.draw_ok,self.S.message);self.bounds()
    def test_resource_restore_skips_changed_pairs_and_old_pawns(self):
        actor=self.resources();self.g['combat_tune']('KIT_DURATION',5.)
        actor.HealthState.RepairKitDuration.Value=6.
        self.assertEqual(self.g['restore_combat_tuning'](),0)
        self.assertEqual(actor.HealthState.RepairKitDuration.Value,6.)
        self.g['combat_tune']('KIT_COOLDOWN',5.);self.g['pawn']=lambda:NS()
        self.assertEqual(self.g['restore_combat_tuning'](),0)
    def test_profile_duplicate_requires_confirmation_and_is_independent(self):
        self.g['save_ui_profile'](1);before=self.g['_appearance_snapshot']()
        self.assertFalse(self.g['profile_manage_action']('DUPLICATE'))
        self.assertTrue(self.g['profile_manage_action']('DUPLICATE'))
        self.assertEqual(self.S.ui_profiles['1'],self.S.ui_profiles['2'])
        self.S.ui_profiles['2']['opacity']=.7
        self.assertNotEqual(self.S.ui_profiles['1']['opacity'],self.S.ui_profiles['2']['opacity'])
        self.assertEqual(before,self.g['_appearance_snapshot']())
    def test_profile_delete_requires_exact_revision(self):
        self.g['save_ui_profile'](1);self.g['profile_manage_action']('DELETE')
        self.S.ui_profiles['1']['opacity']=.8
        self.assertFalse(self.g['profile_manage_action']('DELETE'));self.assertIn('1',self.S.ui_profiles)
        self.assertTrue(self.g['profile_manage_action']('DELETE'));self.assertNotIn('1',self.S.ui_profiles)
    def test_profile_duplicate_target_changes_cancel_confirmation(self):
        self.g['save_ui_profile'](1);self.g['save_ui_profile'](2);self.S.current_ui_profile=1
        self.g['profile_manage_action']('DUPLICATE');self.S.ui_profiles['2']['opacity']=.7
        self.assertFalse(self.g['profile_manage_action']('DUPLICATE'))
        self.assertEqual(self.S.ui_profiles['2']['opacity'],.7)
    def test_profile_expired_confirmation_rearms(self):
        self.g['save_ui_profile'](1);self.g['profile_manage_action']('DELETE')
        self.S.profile_pending_until=0.
        self.assertFalse(self.g['profile_manage_action']('DELETE'));self.assertIn('1',self.S.ui_profiles)
    def test_profile_manager_compact_geometry(self):
        for screen in ((854.,480.),(1280.,720.),(2560.,1440.)):
            self.g['viewport']=lambda wh=screen:wh
            self.draw('PROFILES');self.S.profile_manage=True;self.g['redraw']();self.bounds()
    def test_repeated_new_appearance_cycles(self):
        for i in range(60):
            self.draw('STYLE');self.g['appearance_stage']('accent','#%06X'%(i*125))
            self.g['appearance_stage']('background',.2+(i%8)*.1);self.g['appearance_apply']()
            self.draw('DASHBOARD' if i%2 else 'SPAWN')
            self.assertLess(len(self.S.palette_bindings),1200);self.assertLessEqual(len(self.S.native_history),24)

unittest.main(verbosity=2,argv=[__file__])
