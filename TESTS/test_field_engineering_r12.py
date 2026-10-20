"""Original stand-ins; failure/ownership/dispatch contracts, no native game proof."""
from pathlib import Path
from types import SimpleNamespace as N
import runpy,unittest,time
R=Path(__file__).resolve().parents[1]
prior=runpy.run_path(str(R/'TESTS/test_full_studio_r10.py'))
class FieldEngineering(unittest.TestCase):
    def setUp(self):
        prior['FullStudioR10'].setUp(self)
        self.actor.bCanBeDamaged=True;self.actor.bActorEnableCollision=True
        self.actor.OakCharacterMovement=N();move=self.actor.OakCharacterMovement
        move.MovementMode=1;move.SetMovementMode=lambda value,*args:setattr(move,'MovementMode',value)
    def call(self,name,*args):return self.g[name](*args)
    def test_dock_progression_actually_opens_full_studio(self):
        self.s.dock_mode='SIDE';self.call('studio_open','POINTS')
        self.assertEqual(self.s.dock_mode,'FULL');self.assertEqual(self.s.r10_view,'POINTS')
    def test_god_requires_readable_original_and_never_invents_true(self):
        del self.actor.bCanBeDamaged
        self.assertFalse(self.call('set_god',True));self.assertIsNone(self.s.damage_original)
        self.assertFalse(hasattr(self.actor,'bCanBeDamaged'))
    def test_god_refuses_outside_change_and_retains_original(self):
        self.assertTrue(self.call('set_god',True));self.actor.bCanBeDamaged=True
        self.assertFalse(self.call('set_god',True));self.assertTrue(self.actor.bCanBeDamaged)
        self.assertTrue(self.s.r12_player_fields['bCanBeDamaged']['original'])
    def test_noclip_and_god_share_damage_without_losing_original(self):
        self.assertTrue(self.call('set_god',True));self.assertTrue(self.call('set_noclip',True))
        self.assertTrue(self.call('set_noclip',False));self.assertFalse(self.actor.bCanBeDamaged)
        self.assertTrue(self.call('set_god',False));self.assertTrue(self.actor.bCanBeDamaged)
        self.assertTrue(self.actor.bActorEnableCollision);self.assertEqual(self.actor.OakCharacterMovement.MovementMode,1)
    def test_player_restore_retains_conflict_without_writing_it(self):
        self.call('set_noclip',True);self.actor.OakCharacterMovement.MovementMode=2
        self.assertFalse(self.call('r12_restore_player'));self.assertEqual(self.actor.OakCharacterMovement.MovementMode,2)
        self.assertIn('MODE',self.s.r12_player_fields)
        self.actor.OakCharacterMovement.MovementMode=5
        self.assertTrue(self.call('r12_restore_player'));self.assertEqual(self.actor.OakCharacterMovement.MovementMode,1)
    def test_noclip_partial_exception_restores_only_owned_attempt(self):
        original=self.g['r12_player_set']
        def setter(actor,key,value):
            original(actor,key,value)
            if key=='bActorEnableCollision' and value is False:raise RuntimeError('after effect')
        self.g['r12_player_set']=setter
        self.assertFalse(self.call('set_noclip',True));self.assertTrue(self.actor.bActorEnableCollision)
        self.assertTrue(self.actor.bCanBeDamaged);self.assertEqual(self.actor.OakCharacterMovement.MovementMode,1)
        self.assertFalse(self.s.r12_player_fields)
    def test_player_restore_never_writes_replacement_pawn_or_movement_component(self):
        self.call('set_noclip',True);old=self.actor.OakCharacterMovement
        replacement=N(MovementMode=2,SetMovementMode=lambda *args:self.fail('replacement written'))
        self.actor.OakCharacterMovement=replacement
        self.assertFalse(self.call('r12_restore_player'));self.assertEqual(replacement.MovementMode,2)
        self.assertIn('MODE',self.s.r12_player_fields)
        self.g['pawn']=lambda:N(bCanBeDamaged=True)
        self.assertFalse(self.call('r12_restore_player'));self.assertFalse(self.s.r12_player_fields)
    def test_world_conflict_survives_general_restore_then_can_be_restored(self):
        world=N(TimeDilation=1.);self.g['get_worldsettings']=lambda:world
        self.assertTrue(self.call('set_world_time',2.));world.TimeDilation=3.
        self.call('restore');self.assertIs(self.s.world_saved,world);self.assertEqual(world.TimeDilation,3.)
        world.TimeDilation=2.;self.assertTrue(self.call('r12_restore_world'));self.assertEqual(world.TimeDilation,1.)
    def test_camera_conflict_survives_general_restore(self):
        camera=N(BaseFOV=90.,VehicleFOV=95.);self.pc.player=camera
        self.assertTrue(self.call('change_fov',110));camera.VehicleFOV=120.
        self.call('restore');self.assertIs(self.s.fov_saved,camera);self.assertEqual(camera.VehicleFOV,120.)
        camera.VehicleFOV=110.;self.assertTrue(self.call('reset_fov'));self.assertEqual((camera.BaseFOV,camera.VehicleFOV),(90.,95.))
    def xp(self):
        module=N(_RUNTIME_STATE={'experience_reward_scale':1.},actual=2.)
        module._runtime_combat_xp_value=lambda:module.actual
        self.g['xp_backend']=lambda:module;self.g['sandbox_solo_ready']=lambda:True
        self.call('xp_read');self.call('xp_stage',2.)
        return module
    def test_xp_throw_after_effect_is_quarantined_and_read_recovers_owned_restore(self):
        module=self.xp();calls=[]
        def setter(value):
            calls.append(value);module._RUNTIME_STATE['experience_reward_scale']=value;module.actual=2.*value
            raise RuntimeError('after effect')
        module._runtime_set_combat_xp_scale=setter
        self.assertFalse(self.call('xp_apply'));self.assertIsNotNone(self.s.r12_xp_attempt)
        self.assertFalse(self.call('xp_apply'));self.assertEqual(calls,[2.])
        self.assertTrue(self.call('xp_read'));self.assertIsNone(self.s.r12_xp_attempt)
        self.assertEqual(self.s.xp_owner['last'],2.);self.assertEqual(self.s.xp_owner['original'],1.)
    def test_xp_unchanged_readback_does_not_prove_no_effect_or_allow_retry(self):
        module=self.xp();calls=[]
        module._runtime_set_combat_xp_scale=lambda value:calls.append(value) or {'ok':False}
        self.assertFalse(self.call('xp_apply'));self.assertFalse(self.call('xp_read'))
        self.assertFalse(self.call('xp_apply'));self.assertEqual(calls,[2.]);self.assertIsNotNone(self.s.r12_xp_attempt)
    def test_xp_pending_cannot_be_adopted_by_replacement_backend(self):
        module=self.xp();self.s.r12_xp_attempt=dict(module=module,anchor=self.call('_session_anchor'),desired=2.,expected=4.,original=1.,restore=False)
        self.assertFalse(self.call('r12_xp_observe_attempt',N(),2.,4.));self.assertIsNotNone(self.s.r12_xp_attempt)
    def test_native_community_exception_blocks_all_further_grants_same_context(self):
        calls=[]
        def perk(number):calls.append(number);raise RuntimeError('partial reward')
        self.pc.ServerActivateDevPerk=perk
        self.call('community_native_request','levels5');self.assertIsNotNone(self.s.community_confirm)
        self.assertFalse(self.call('community_native_request','levels5'))
        for _ in range(4):self.assertFalse(self.call('community_native_request','loot'))
        self.assertEqual(len(calls),1);self.assertIsNotNone(self.s.r12_grant_uncertain)
    def test_community_confirmation_rearms_when_player_state_changes(self):
        calls=[];self.pc.ServerActivateDevPerk=lambda number:calls.append(number)
        self.call('community_native_request','levels5');self.assertIsNotNone(self.s.community_confirm)
        old=self.s.community_confirm[0];self.pc.PlayerState=N(_get_address=lambda:991)
        self.assertFalse(self.call('community_native_request','levels5'));self.assertFalse(calls)
        self.assertNotEqual(old,self.s.community_confirm[0])
    def test_bonk_console_exception_has_same_quarantine(self):
        self.g['community_modules']=lambda:{'bonk':True};calls=[]
        def command(text):calls.append(text);raise RuntimeError('partial award')
        self.pc.ConsoleCommand=command;action=next(iter(self.g['COMMUNITY_ACTIONS']))
        self.call('community_request',action);self.assertFalse(self.call('community_request',action))
        for _ in range(3):self.assertFalse(self.call('community_request',action))
        self.assertEqual(len(calls),1)
    def test_transient_missing_context_does_not_clear_uncertain_grant(self):
        context=self.call('studio_context');self.s.r12_grant_uncertain=context
        original=self.g['studio_context'];self.g['studio_context']=lambda:None
        self.assertIsNone(self.call('r12_grant_context'));self.assertEqual(self.s.r12_grant_uncertain,context)
        self.g['studio_context']=original
        self.assertEqual(self.call('r12_grant_context'),context);self.assertEqual(self.s.r12_grant_uncertain,context)
    def test_transient_loading_does_not_replace_player_originals(self):
        self.call('set_god',True);original=self.g['_session_anchor'];self.g['_session_anchor']=lambda:None
        self.assertFalse(self.call('set_god',False));self.assertTrue(self.s.damage_original)
        self.g['_session_anchor']=original;self.assertTrue(self.call('r12_restore_player'));self.assertTrue(self.actor.bCanBeDamaged)
    def test_camera_partial_exception_never_overwrites_a_new_outside_value(self):
        class Camera:
            BaseFOV=90.;VehicleFOV=95.
            def __setattr__(obj,key,value):
                if key=='VehicleFOV' and value==110:obj.BaseFOV=140.;raise RuntimeError('outside effect')
                object.__setattr__(obj,key,value)
        camera=Camera();self.pc.player=camera
        self.assertFalse(self.call('change_fov',110));self.assertEqual(camera.BaseFOV,140.)
        self.assertIs(self.s.fov_saved,camera);self.assertFalse(self.call('reset_fov'))
    def test_world_partial_exception_never_overwrites_a_new_outside_value(self):
        class World:
            TimeDilation=1.
            def __setattr__(obj,key,value):
                if value==2.:object.__setattr__(obj,key,3.);raise RuntimeError('outside effect')
                object.__setattr__(obj,key,value)
        world=World();self.g['get_worldsettings']=lambda:world
        self.assertFalse(self.call('set_world_time',2.));self.assertEqual(world.TimeDilation,3.)
        self.assertIs(self.s.world_saved,world);self.assertFalse(self.call('r12_restore_world'))
    def test_frame_rebuild_does_not_grab_focus_from_numeric_editor(self):
        self.s.numeric_editor=N();self.s.controller_mode=True;calls=[];original=self.g['attempt']
        self.g['attempt']=lambda obj,name,*args:calls.append(name) or original(obj,name,*args)
        self.call('_finish_frame',self.s.canvas,1280.,720.,time.perf_counter(),None,None)
        self.assertNotIn('SetUserFocus',calls)
    def test_forge_rejects_invalid_public_drafts_before_confirmation_or_api(self):
        self.g['_spawn_api']=lambda:self.fail('invalid draft reached backend')
        for level,count in ((True,1),(1,True),(0,1),(101,1),(20,0),(20,4),(20.5,1)):
            self.s.spawn_level=level;self.s.spawn_count=count
            self.assertFalse(self.call('spawn_request'));self.assertIsNone(self.s.spawn_pending)
            self.assertEqual(self.s.forge_stage,'INVALID_DRAFT')
    def test_forge_stops_a_batch_after_context_changes_without_using_old_world_again(self):
        anchor=[('original','world')];self.g['_session_anchor']=lambda:anchor[0]
        self.g['_forge_selection']=lambda:('Test','test_pool','PISTOL')
        self.g['_actor_world_position']=lambda actor:N(X=0.,Y=0.,Z=0.)
        self.g['_actor_forward_xy']=lambda actor:(1.,0.);self.g['_spawn_transform']=lambda *args:object()
        calls=[]
        def drop(*args):calls.append(args);anchor[0]=('new','world')
        self.g['_spawn_api']=lambda:N(SpawnInventoryFromItemPool=drop)
        self.s.spawn_level=20;self.s.spawn_count=3
        self.call('spawn_request');self.assertFalse(self.call('spawn_request'))
        self.assertEqual(len(calls),1);self.assertEqual(self.s.forge_uncertain_anchor,('original','world'))
        self.assertEqual(self.s.forge_request_history[-1]['quantity'],1)
    def test_keyboard_focus_outline_visible_with_gamepad_disabled(self):
        self.s.controller_enabled=False;self.s.controller_mode=True;self.s.r10_device='KEYBOARD'
        self.s.controller_focus=0;self.s.buttons=[dict(rect=(10,20,100,30),disabled=False)]
        self.s.controller_focus_outline=[N() for _ in range(4)];calls=[]
        self.g['size_position']=lambda obj,*args:calls.append(args)
        self.call('_controller_update_focus_outline');self.assertEqual(calls[0][:2],(7,17))
    def test_held_arrow_during_editor_is_not_a_new_edge_on_exit(self):
        self.s.numeric_editor=N();self.g['key_down']=lambda pc,name:name=='Down'
        self.call('r10_input_tick',self.pc,time.monotonic());self.assertTrue(self.s.arrow_keys_down['Down'])
    def test_dock_prompts_follow_keyboard_and_mouse(self):
        self.s.r10_device='KEYBOARD';self.assertIn('TAB FOCUS',self.call('r12_input_prompt'))
        self.s.r10_device='MOUSE';self.assertIn('CLICK SELECT',self.call('r12_input_prompt'))
    def test_forge_backend_caption_stays_above_quick_bar(self):
        original=self.g['text'];captions=[]
        def text(parent,label,x,y,w,h,*args,**kwargs):
            if label=='CHECK BACKEND FIRST':captions.append((y,h))
            return original(parent,label,x,y,w,h,*args,**kwargs)
        self.g['text']=text;self.s.page='SPAWN';self.s.spawn_view='TOOLS';self.s.dock_mode='FULL'
        self.native_redraw();self.assertTrue(captions)
        panel=self.s.panel_rect;self.assertLessEqual(captions[-1][0]+captions[-1][1],panel[1]+panel[3]-175)
    def test_failed_friend_restore_retains_original_for_later_retry(self):
        class Friend:
            bCanBeDamaged=False;fail=True
            def HasAuthority(obj):return True
            def __setattr__(obj,key,value):
                if key=='bCanBeDamaged' and obj.fail:raise RuntimeError('refused restore')
                object.__setattr__(obj,key,value)
        friend=Friend();self.g['party_entries']=lambda:[{'key':990,'ps':N(),'local':False}]
        self.g['remote_pawn']=lambda ps:friend;self.s.remote_originals={990:(True,friend)}
        self.assertFalse(self.call('restore_friends'));self.assertIn(990,self.s.remote_originals)
        friend.fail=False;self.assertTrue(self.call('restore_friends'));self.assertFalse(self.s.remote_originals)
        self.assertTrue(friend.bCanBeDamaged)
    def test_target_restore_does_not_write_a_replacement_controller(self):
        self.s.target_off=True;self.s.r12_target_pc=self.pc
        self.pc=N(_get_address=lambda:992)
        self.assertFalse(self.call('r12_restore_target'));self.assertFalse(self.s.target_off)
    def test_target_lock_exception_keeps_its_owner_for_named_unlock(self):
        sdk=self.g['unrealsdk'];original=sdk.find_class;calls=[];fail=[True]
        def lock(pc,name,a,b):
            calls.append((pc,name,a,b))
            if fail[0]:raise RuntimeError('after possible lock')
        sdk.find_class=lambda name:N(ClassDefaultObject=N(LockTargetableByAI=lock))
        try:
            self.call('toggle_no_target');self.assertTrue(self.s.target_off);self.assertIs(self.s.r12_target_pc,self.pc)
            fail[0]=False;self.assertTrue(self.call('r12_restore_target'))
            self.assertEqual(calls[-1][1:],('crown_native',False,False));self.assertFalse(self.s.target_off)
        finally:sdk.find_class=original
    def test_kill_confirmation_binds_current_player_state(self):
        self.g['can_run_shared']=lambda name:True;calls=[]
        self.pc.ServerActivateDevPerk=lambda number:calls.append(number)
        self.call('confirm_kill');self.pc.PlayerState=N(_get_address=lambda:993)
        self.call('confirm_kill');self.assertFalse(calls)
        self.call('confirm_kill');self.assertEqual(calls,[3])
    def test_ambiguous_ammo_perk_cannot_be_implicitly_toggled_again(self):
        self.g['can_run_shared']=lambda name:True;calls=[]
        def perk(number):calls.append(number);raise RuntimeError('toggle may have occurred')
        self.pc.ServerActivateDevPerk=perk
        self.assertFalse(self.call('dev_perk',True,'Invalid'))
        self.assertFalse(self.call('dev_perk',5,'Ammo'));self.assertFalse(self.call('dev_perk',5,'Ammo'))
        self.assertEqual(calls,[5])

if __name__=='__main__':unittest.main(argv=[__file__],verbosity=2)
