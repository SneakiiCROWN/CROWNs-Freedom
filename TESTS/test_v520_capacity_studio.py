"""Tests optional BL4Live capacity bridge; no game modification or real sockets."""
from pathlib import Path
import runpy, time, json, socket, struct, threading

def run():
 root=Path(__file__).resolve().parents[1]
 ctx=runpy.run_path(str(root/'TESTS/test_core.py'))
 ns=ctx['ns']; st=ns['State']; env=ns['capacity_queue_request'].__globals__
 assert ns['RELEASE_VERSION']=='5.26.0'
 assert 'CAPACITY' in ns['UI_CATEGORY_PAGES']['FREEDOM']
 assert 'CAPACITY' in ns['_KNOWN_PAGES']
 log=[]
 env.update(session_role=lambda:'SOLO',_session_anchor=lambda:('map','local'),log=log.append)
 st.capacity_mode='BACKPACK';st.capacity_draft=40;st.capacity_readback_anchor=None
 st.capacity_bridge_job=None;st.capacity_bridge_generation=0;st.opened=False
 assert not ns['capacity_apply_request']()  # requires readback
 assert 'READ' in log[-1]
 replies={
  'READ':{'ok':True,'containers':[{'container':'BackpackItems','max_size':240,'slots':81},{'container':'BankItems','max_size':100,'slots':10}]},
  'PREFLIGHT':{'ok':True,'write_enabled':True},
  'APPLY':{'ok':True,'actual':160,'after':160}
 }
 def fake(payload):
  return replies['PREFLIGHT' if payload['op']=='info' else 'READ' if payload['op']=='list' else 'APPLY']
 transport=ns['_capacity_bridge_exchange']
 env['_capacity_bridge_exchange']=fake
 def wait():
  for _ in range(150):
   if st.capacity_bridge_job and st.capacity_bridge_job.get('finished'):return ns['capacity_consume_result']()
   time.sleep(.01)
  raise AssertionError('bridge worker timed out')
 assert ns['capacity_queue_request']('PREFLIGHT') and wait()
 assert ns['capacity_queue_request']('READ') and wait()
 assert st.capacity_readback['BackpackItems']==240
 assert st.capacity_occupied['BackpackItems']==81
 assert st.capacity_readback_anchor==('map','local')
 assert not ns['capacity_apply_request']() # block shrinking below 81
 assert 'BLOCKED' in log[-1]
 assert ns['capacity_set_draft'](160)
 assert not ns['capacity_apply_request']() # arm
 assert st.capacity_bridge_job is None
 assert ns['capacity_apply_request']() # send
 assert wait() and 'ACCEPTED' in st.capacity_status
 # After a successful write, a fresh backend READ is required.
 assert not ns['capacity_apply_request']()
 assert ns['capacity_queue_request']('READ') and wait()
 assert ns['capacity_set_draft'](80)
 assert not ns['capacity_apply_request']() and 'BLOCKED' in log[-1]
 assert not ns['capacity_set_draft'](6000)
 assert ns['capacity_set_draft'](5000)
 assert not ns['capacity_apply_request']()
 # Changed target invalidates confirm
 assert ns['capacity_set_draft'](160)
 assert not ns['capacity_apply_request']()
 assert ns['capacity_apply_request']()
 wait()
 assert ns['capacity_queue_request']('READ') and wait()
 # Fail closed if backend refuses; no fake success.
 replies['APPLY']={'ok':False,'error':'unsupported native build'}
 assert ns['capacity_set_draft'](200)
 assert not ns['capacity_apply_request']()
 assert ns['capacity_apply_request']()
 wait()
 assert 'REFUSED' in st.capacity_status
 # Remote co-op disabled; no thread, even if preflight worked
 env['session_role']=lambda:'HOST'
 assert not ns['capacity_queue_request']('READ')
 assert not ns['capacity_apply_request']()
 env['session_role']=lambda:'SOLO'
 # stale replies from different session cannot update current state
 assert ns['capacity_queue_request']('READ')
 env['_session_anchor']=lambda:('newmap','local')
 assert not wait()
 assert st.capacity_readback_anchor is None, 'failed APPLY and stale replies cannot resurrect a write snapshot'
 # Worker protocol is length prefixed with strict response size.
 sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(1);port=sock.getsockname()[1]
 oldport=env['_CAPACITY_PORT'];env['_CAPACITY_PORT']=port
 requests=[]
 def serve():
  c,_=sock.accept()
  with c:
   size=struct.unpack('>I',c.recv(4))[0]
   data=b''
   while len(data)<size:data+=c.recv(size-len(data))
   requests.append(json.loads(data.decode()))
   reply=json.dumps({'ok':True,'containers':[]}).encode()
   c.sendall(struct.pack('>I',len(reply))+reply)
  sock.close()
 threading.Thread(target=serve,daemon=True).start()
 assert transport({'id':1,'op':'list'})['ok']
 assert requests==[{'id':1,'op':'list'}]
 env['_CAPACITY_PORT']=oldport
 # Native controls render in a mocked SDK without changing saves.
 env['session_role']=lambda:'SOLO'
 st.page='CAPACITY';st.safe_mode=True;st.art_mode='SHAPES';st.opened=False
 ns['viewport']=lambda:(1280,720)
 assert ns['open_menu']() is not False
 captions=[b['name'] for b in st.buttons]
 assert any('CHECK LIVE BRIDGE' in x for x in captions)
 assert any('APPLY BACKPACK' in x for x in captions)
 assert any('RESTORE BASELINE' in x for x in captions)
 ns['close_menu']()
 print('PASS v5.20 Capacity Studio: backend frame protocol, solo-only confirmation, inventory count guard, optional readback, native menu')
if __name__=='__main__':run()
