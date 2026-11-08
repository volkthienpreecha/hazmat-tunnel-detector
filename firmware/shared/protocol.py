"""Bounded NDJSON framing. No machine imports, runs on both Python runtimes."""
import json
MAX_FRAME=1024
KINDS=('hello','heartbeat','telemetry','arm','drive','inspect','stop','reset','ack')

def encode(message):
    data=json.dumps(message).encode()+b'\n'
    if len(data)>MAX_FRAME:raise ValueError('frame too large')
    return data

class FrameParser:
    def __init__(self):self.buffer=bytearray();self.discard=False;self.errors=0
    def feed(self,data):
        out=[]
        for b in data:
            if b==10:
                if not self.discard and self.buffer:
                    try:
                        obj=json.loads(self.buffer.decode())
                        if isinstance(obj,dict):out.append(obj)
                        else:self.errors+=1
                    except (ValueError,UnicodeError):self.errors+=1
                self.buffer=bytearray();self.discard=False
            elif not self.discard:
                self.buffer.append(b)
                if len(self.buffer)>=MAX_FRAME:self.buffer=bytearray();self.discard=True;self.errors+=1
        return out

class Receiver:
    """A new session requires a hello. Old sessions remain rejected until reboot."""
    def __init__(self):self.session=None;self.seq=-1;self.retired=[];self.changed=False
    def accept(self,m):
        self.changed=False
        if m.get('v')!=1 or type(m.get('seq')) is not int or not 0<=m['seq']<2147483647:return False
        session=m.get('session');kind=m.get('kind')
        if not isinstance(session,str) or not 1<=len(session)<=32 or kind not in KINDS or not isinstance(m.get('data'),dict):return False
        if session!=self.session:
            if session in self.retired or (self.session is not None and kind!='hello') or (self.session is None and kind not in ('hello','heartbeat')):return False
            if self.session is not None:
                # Refuse further session churn instead of unbounded replay history.
                if len(self.retired)>=8:return False
                self.retired.append(self.session)
            self.session=session;self.seq=-1;self.changed=True
        if m['seq']<=self.seq:return False
        self.seq=m['seq'];return True
