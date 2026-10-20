"""v5.19 multiplayer: host/guest read-only snapshots, target-locked confirmations, UI and privacy."""
from pathlib import Path
import runpy, tempfile, json, sys

def run():
 root=Path(__file__).resolve().parents[1]
 ctx=runpy.run_path(str(root/'TESTS/test_core.py'))
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
                     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns=ctx['ns']; st=ns['State'];world=ctx['world'];role=ctx['role'];hostpawn=ctx['hostpawn']
 PS=ctx['PS'];Pawn=ctx['Pawn'];friendps=ctx['friendps'];friendpawn=ctx['friendpawn']
 assert ns['RELEASE_VERSION']=='5.26.0'
 role[0]=2
 st.party_approved=False;st.party_approved_roster=None;st.party_selected=None
 snap=ns['coop_snapshot']()
 assert snap['role']=='HOST' and snap['visible_players']==2 and snap['remote_players']==1
 assert snap['local_player_identified'] and snap['roster_stable']
 assert not snap['remote_controls_eligible']
 assert not any('Fil' in str(v) for v in snap.values())
 report=ns['show_coop_status']()
 assert report==snap and 'REMOTE EDITS LOCKED' in st.coop_last_status
 st.party_mode='BOOSTS'
 assert ns['cycle_party_mode']() is None and st.party_mode=='TRAVEL'
 ns['cycle_party_mode']();assert st.party_mode=='GIFTS'
 ns['cycle_party_mode']();assert st.party_mode=='SESSION'
 ns['cycle_party_mode']();assert st.party_mode=='BOOSTS'
 # Simulate friend joining, and selection switching between confirmation clicks.
 extra=Pawn('second');extra.loc=(400.,500.,600.)
 extra_ps=PS('SecretPlayer',extra)
 world.GameState.PlayerArray.append(extra_ps)
 ns['refresh_party']();ns['select_party'](1);ns['enable_party_changes']()
 assert ns['party_permission_ok']()
 snap=ns['coop_snapshot']()
 assert snap['remote_players']==2 and snap['remote_controls_eligible']
 hostpawn.loc=(880.,770.,660.)
 friendpawn.loc=(510.,410.,310.)
 ns['bring_friend']()
 assert friendpawn.loc==(510.,410.,310.)
 # Adversarial internal target change without select_party() must not reuse approval.
 st.party_selected=extra_ps._get_address()
 ns['bring_friend']()
 assert extra.loc==(400.,500.,600.) and friendpawn.loc==(510.,410.,310.)
 assert st.friend_teleport_target==extra_ps._get_address()
 # A second confirmation now applies ONLY to the chosen friend.
 ns['bring_friend']()
 assert extra.loc==hostpawn.loc and friendpawn.loc==(510.,410.,310.)
 # Changing through UI explicitly clears any pending confirmation.
 ns['select_party'](1)
 assert st.friend_teleport_target is None and st.friend_teleport_confirm==0
 # Changing role to guest blocks remote effects, even with stale consent.
 role[0]=3
 snap=ns['coop_snapshot']()
 assert snap['role']=='GUEST' and not snap['remote_controls_eligible']
 old=friendpawn.loc
 ns['bring_friend']()
 assert friendpawn.loc==old
 # Party departure invalidates host consent, friend selection and confirmation.
 role[0]=2
 world.GameState.PlayerArray.pop()
 ns['refresh_party']()
 assert not st.party_approved and st.party_selected==friendps._get_address()
 with tempfile.TemporaryDirectory() as tmp:
  ns['SETTINGS_DIR']=Path(tmp)
  assert ns['export_qa_report']()
  qa=json.loads((Path(tmp)/'CROWNs_Freedom_QA_Report.json').read_text())
  assert qa['co_op']['remote_players']==1
  assert qa['co_op']['host_consent_acknowledged'] is False
  assert 'Fil' not in json.dumps(qa['co_op']) and 'SecretPlayer' not in json.dumps(qa['co_op'])
 # Native-rendered session-mode controls, without executing any game changes.
 st.party_mode='SESSION';st.page='PARTY';st.opened=False;st.safe_mode=True
 st.art_mode='SHAPES';ns['viewport']=lambda:(1280,720)
 assert ns['open_menu']() is not False
 labels=[b['name'] for b in st.buttons]
 assert 'CHECK CO-OP SESSION' in labels and 'EXPORT CO-OP QA' in labels
 st.party_mode='TRAVEL';role[0]=3;st.party_selected=friendps._get_address();ns['redraw']()
 buttons={b['name']:b for b in st.buttons}
 assert 'ME TO FRIEND (SWEPT)' in buttons
 assert 'BRING FRIEND TO ME (2x)' in buttons
 # The guest's own swept request is accessible while editing friends remains locked.
 assert not buttons['ME TO FRIEND (SWEPT)'].get('disabled',False)
 assert buttons['BRING FRIEND TO ME (2x)'].get('disabled',False)
 ns['close_menu']()
 print('PASS v5.19 host/guest party report, privacy, roster consent expiry, target-bound teleport and native UI')

if __name__=='__main__':run()
