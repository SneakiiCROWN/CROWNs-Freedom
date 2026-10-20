"""Standalone host/interpreter probe. No CROWN source, SDK, audio or ctypes.

Not a product acceptance test. Models the fixtures' short-lived widget graphs.
"""
from types import SimpleNamespace
import sys

class W:
    def __init__(self,name=''):
        self.name=name;self.children=[];self.slot=None;self.WidgetTree=None
    def AddChild(self,w):
        self.children.append(w);w.slot=W('slot')
    def __getattr__(self,key):
        if key.startswith(('Set','Remove','Add','Force','Clear','Reset')):
            return lambda *args:None
        raise AttributeError(key)

palette={'bg':(.01,.02,.03,1.),'panel':(.02,.03,.04,1.),'text':(.9,.9,.9,1.)}
for frame in range(150):
    root=W('root');bindings=[]
    for i in range(900):
        cls=SimpleNamespace(ClassDefaultObject=SimpleNamespace(GetViewportScale=lambda pc:1.))
        w=W(str(cls));root.AddChild(w)
        w.SetVisibility(4);w.SetRenderOpacity(.9)
        col=palette['panel']
        for key,reference in palette.items():
            if all(abs(col[j]-reference[j])<.0001 for j in range(3)):
                bindings.append((w,'box',key,col[3]/reference[3]));break
    if frame%25==0:print('HOST PROBE',frame,len(root.children),flush=True)
print('HOST PROBE COMPLETE',sys.version,flush=True)
