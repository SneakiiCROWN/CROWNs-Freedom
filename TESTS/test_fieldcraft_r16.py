"""Original workflow/failure-path stand-ins, no third-party or BL4 execution."""
from pathlib import Path
from types import SimpleNamespace as N
import runpy,unittest,time
R=Path(__file__).resolve().parents[1]
P=runpy.run_path(str(R/'TESTS/test_operations_r13.py'))
W=runpy.run_path(str(R/'TESTS/test_echo_full_studio_r3.py'))
class Fieldcraft(P['Operations']):
    def weapon(self):return W['FullStudioR3'].weapon(self)
    def test_sort_modes_are_complete_deterministic_and_local_only(self):
        self.s.spawn_pending=('armed',);self.s.forge_uncertain_anchor=self.call('_session_anchor')
        original=self.call('_spawn_visible_indices');self.s.spawn_favorites=[self.g['SPAWN_POOLS'][-1][1]]
        modes=[]
        for i in range(5):
            modes.append(self.call('r16_forge_sort'));rows=self.call('_spawn_visible_indices')
            self.assertEqual(set(rows),set(original));self.assertIsNone(self.s.spawn_pending)
            self.assertEqual(self.s.forge_uncertain_anchor,self.call('_session_anchor'))
            names=[self.g['SPAWN_POOLS'][n][0].casefold() for n in rows]
            if self.s.r16_forge_sort=='A-Z':self.assertEqual(names,sorted(names))
            if self.s.r16_forge_sort=='Z-A':self.assertEqual(names,sorted(names,reverse=True))
            if self.s.r16_forge_sort=='FAVOURITES':self.assertEqual(rows[0],len(self.g['SPAWN_POOLS'])-1)
        self.assertEqual(len(set(modes)),5)
    def test_multiword_query_matches_name_and_category(self):
        name,token,kind=self.g['SPAWN_POOLS'][0];self.s.spawn_search=name.split()[0].lower()+' '+kind.lower()
        self.assertIn(0,self.call('_spawn_visible_indices'))
        self.s.spawn_search+=' zz_no_match';self.assertEqual(self.call('_spawn_visible_indices'),[])
    def test_recent_sort_keeps_source_order_until_explicit_sort(self):
        pools=self.g['SPAWN_POOLS'];self.s.spawn_category_idx=self.g['SPAWN_CATEGORIES'].index('RECENT')
        self.s.spawn_recent=[pools[3][1],pools[0][1]];self.assertEqual(self.call('_spawn_visible_indices'),[3,0])
    def test_sorted_selection_and_blueprint_reveal_the_same_pool(self):
        self.s.r16_forge_sort='Z-A';rows=self.call('forge_page_indices')
        self.assertTrue(self.call('forge_choose',0));self.assertEqual(self.s.spawn_pool_idx,rows[0])
        pool=self.g['SPAWN_POOLS'][7][1];self.s.forge_blueprints={'1':{'pool':pool,'level':42,'count':2}}
        self.assertTrue(self.call('forge_load_blueprint',1));self.assertEqual(self.call('_forge_selection')[1],pool)
        self.call('forge_toggle_view');self.assertIn(7,self.call('forge_page_indices'))
    def test_browse_empty_recovery_preserves_uncertain_request(self):
        self.s.spawn_search='zz_nomatch';self.s.forge_uncertain_anchor=self.call('_session_anchor')
        self.g['redraw']=self.native_redraw;self.s.spawn_view='BROWSE';self.call('show_page','SPAWN')
        next(b for b in self.s.buttons if b['name']=='SHOW ALL ITEMS')['run']()
        self.assertEqual(self.s.spawn_search,'');self.assertEqual(self.s.forge_uncertain_anchor,self.call('_session_anchor'))
    def test_new_bonus_profiles_apply_all_fields_and_expire_with_menu_closed(self):
        for profile,keys in (('GLASS',('OUTGOING','INCOMING')),('HEALING',('HEAL_RECEIVED','HEAL_DEALT'))):
            before={k:self.call('combat_pair',k)[1] for k in keys}
            self.assertTrue(self.call('r13_bonus_choose',profile));self.assertTrue(self.call('bonus_start'))
            for k in keys:self.assertGreater(self.call('combat_pair',k)[1][0],before[k][0])
            until=self.s.r10_bonus['until'];self.s.opened=False;self.s.controller_enabled=False
            self.g['time']=N(monotonic=lambda:until+1);self.call('controller_watch_tick')
            self.assertIsNone(self.s.r10_bonus)
            for k in keys:self.assertEqual(self.call('combat_pair',k)[1],before[k])
    def test_new_bonus_preflight_missing_healing_field_never_writes(self):
        original=self.g['combat_pair'];self.g['combat_pair']=lambda key,*a:None if key=='HEAL_DEALT' else original(key,*a)
        self.call('r13_bonus_choose','HEALING');self.assertFalse(self.call('bonus_start'))
        self.assertEqual(original('HEAL_RECEIVED')[1],(1.,1.));self.assertFalse(self.s.combat_originals)
    def test_active_bonus_retains_applied_duration_when_draft_changes(self):
        self.assertTrue(self.call('bonus_start'));duration=self.s.r10_bonus['duration']
        self.s.r10_bonus_duration=180.;self.assertEqual(self.s.r10_bonus['duration'],duration)
        self.assertEqual(self.s.r10_bonus['scale'],self.s.r10_bonus_scale)
    def test_preset_screen_has_real_apply_and_restore_actions(self):
        weapon,behavior=self.weapon();self.g['redraw']=self.native_redraw
        self.s.weapon_view=True;self.s.weapon_detail=True;self.call('show_page','GEAR');self.s.weapon_view=True;self.call('redraw')
        names=[b['name'] for b in self.s.buttons];self.assertIn('APPLY / CONFIRM',names);self.assertIn('RESTORE OWNED',names)
        next(b for b in self.s.buttons if b['name']=='STAGE / QUICK HANDS')['run']()
        self.assertEqual(behavior.firerate,4.);self.assertFalse(self.call('weapon_apply'));self.assertTrue(self.call('weapon_apply'))
        self.assertEqual(behavior.firerate,5.);self.assertEqual(behavior.ReloadTime,1.6)
        self.assertTrue(self.call('weapon_restore'));self.assertEqual(behavior.firerate,4.)
    def test_preset_apply_refuses_changed_weapon_and_preserves_outside_value(self):
        weapon,behavior=self.weapon();self.call('weapon_preset','QUICK HANDS');behavior.firerate=9.
        self.assertFalse(self.call('weapon_apply'));self.assertEqual(behavior.firerate,9.)
    def test_result_inspection_reads_owned_weapons_never_claims_forge_delivery(self):
        self.weapon();self.s.spawn_requests=2;self.s.spawn_last='requested pool'
        self.assertTrue(self.call('r16_inspect_owned_weapons'));self.assertEqual(self.s.page,'GEAR')
        self.assertTrue(self.s.weapon_view and self.s.weapon_detail);self.assertIn('OBSERVED',self.s.weapon_status)
        self.assertNotIn('DELIVERED',self.s.weapon_status);self.assertEqual(self.s.spawn_requests,2)
    def test_focus_prefers_same_column_over_diagonal_shortcut(self):
        self.s.buttons=[dict(name=str(i),disabled=False,rect=r) for i,r in enumerate(((100,100,200,40),(320,145,100,40),(100,210,200,40)))]
        self.s.controller_focus=0;self.call('_controller_focus_direction','DOWN');self.assertEqual(self.s.controller_focus,2)
        self.s.buttons[2]['disabled']=True;self.s.controller_focus=0;self.call('_controller_focus_direction','DOWN');self.assertEqual(self.s.controller_focus,1)
    def test_horizontal_focus_respects_rows_and_slider_adjustment(self):
        changes=[];self.s.buttons=[dict(disabled=False,rect=(10,10,100,30),slider=N(adjust=lambda n:changes.append(n)))]
        self.s.controller_focus=0;self.call('_controller_focus_direction','RIGHT');self.assertEqual(changes,[1])
    def test_wheel_adjusts_hovered_slider_once_and_rejects_mixed_gesture(self):
        self.s.opened=True;self.s.panel_rect=(0.,0.,1200.,800.);changes=[]
        self.s.buttons=[dict(disabled=False,widget=N(IsHovered=lambda:True),rect=(350.,300.,500.,30.),slider=N(adjust=lambda n:changes.append(n)))]
        keys={'MouseScrollUp'};self.g['key_down']=lambda pc,n:n in keys;self.s.controller_open_block_until=0.
        self.assertTrue(self.call('r10_input_tick',self.pc,1.));self.assertEqual(changes,[1]);self.assertEqual(self.s.r10_device,'MOUSE')
        self.assertFalse(self.call('r10_input_tick',self.pc,2.));self.assertEqual(changes,[1])
        self.s.r10_input_keys={};keys.add('LeftMouseButton');self.call('r10_input_tick',self.pc,3.);self.assertEqual(changes,[1])
    def test_wheel_does_not_adjust_unhovered_or_disabled_slider(self):
        self.s.opened=True;self.s.panel_rect=(0.,0.,1200.,800.);changes=[]
        self.s.buttons=[dict(disabled=False,widget=N(IsHovered=lambda:False),rect=(350.,300.,500.,30.),slider=N(adjust=lambda n:changes.append(n)))]
        self.g['key_down']=lambda pc,n:n=='MouseScrollDown';self.s.controller_open_block_until=0.
        self.assertFalse(self.call('r10_input_tick',self.pc,1.));self.assertFalse(changes)
    def test_workspaces_fit_four_resolutions_and_both_weapon_views(self):
        self.g['redraw']=self.native_redraw
        for size in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
            self.g['viewport']=lambda size=size:size
            for page,view in (('SPAWN','BROWSE'),('GEAR','PRESETS'),('GEAR','VALUES'),('LOOT','BONUS')):
                self.call('show_page',page)
                if page=='SPAWN':self.s.spawn_view=view
                if page=='GEAR':self.s.weapon_view=True;self.s.weapon_detail=view=='PRESETS'
                if page=='LOOT':self.s.r10_view='BONUS'
                self.call('redraw');self.assertTrue(self.s.draw_ok,self.s.runtime_failures);self.bounds()

    def test_point_shortcuts_stage_from_actual_allowance_without_awarding(self):
        self.s.r10_view='POINTS';before=list(self.manager.ProgressPointsContainer.PointsAcquiredPerPool)
        self.assertTrue(self.call('r16_progress_increment',5));self.assertEqual(self.s.r10_points_draft,before[0]+5)
        self.assertEqual(self.manager.ProgressPointsContainer.PointsAcquiredPerPool,before)
        self.assertIsNone(self.s.r10_progress_job);self.assertFalse(self.call('r16_progress_increment',True))
    def test_level_shortcuts_clamp_to_supported_track_limit_and_pending_blocks(self):
        self.s.r10_view='LEVELS';self.ps.ExperienceState[0].ExperienceLevel=58
        self.assertTrue(self.call('r16_progress_increment',10));self.assertEqual(self.s.r10_level_draft,60)
        self.assertEqual(self.ps.ExperienceState[0].ExperienceLevel,58)
        self.s.r10_progress_job={};self.assertFalse(self.call('r16_progress_increment',1))

if __name__=='__main__':unittest.main(argv=[__file__],verbosity=2)
