"""Board runtime and UART transport shared with simulator integration tests."""
import json
from .protocol import FrameParser, Receiver, encode
from .control import Motion,Hazard,elapsed

class Peer:
    def __init__(self,uart,session):
        self.uart=uart;self.session=session;self.seq=0;self.parser=FrameParser();self.receiver=Receiver();self.last_rx=None;self.last_tx=None;self.pending=None;self.offset=0
    def send(self,kind,data):
        # Only one bounded transmit buffer. Skip telemetry when serial is blocked.
        if self.pending is not None:return False
        self.pending=encode(dict(v=1,kind=kind,session=self.session,seq=self.seq,data=data));self.offset=0;self.seq+=1
        return True
    def flush(self):
        if self.pending is not None:
            n=self.uart.write(self.pending[self.offset:]) or 0;self.offset+=n
            if self.offset>=len(self.pending):self.pending=None
    def poll(self,now):
        self.flush();data=self.uart.read(256) or b'';out=[]
        for frame in self.parser.feed(data):
            if self.receiver.accept(frame):
                self.last_rx=now;out.append((frame,self.receiver.changed))
        return out

def load_config():
    with open('config.local.json') as f:return json.load(f)

async def run_motion(c,hardware,peer):
    import asyncio,time,machine
    m=Motion(c.get('allow_clear_path_retreat',False));last_sample=None;last_send=None;sensors={};hazard='fault';hazard_at=None
    watchdog=machine.WDT(timeout=2000)
    try:
        while True:
            now=time.ticks_ms()
            for frame,changed in peer.poll(now):
                if changed:m.halt('peer restarted');hazard_at=None
                if frame['kind']=='telemetry':
                    value=frame['data'].get('hazard')
                    if value in ('normal','warning','danger','warming','fault'):
                        hazard=value;hazard_at=now;m.heartbeat(now)
                elif frame['kind'] in ('arm','drive','inspect','stop','reset'):
                    ok=m.command(now,frame['kind'],frame['data']);peer.send('ack',dict(seq=frame['seq'],accepted=ok,motion=m.snapshot()))
            if last_sample is None or elapsed(now,last_sample)>=100:
                try:sensors=hardware.read()
                except Exception:sensors={}
                last_sample=now
            healthy=bool(sensors) and hazard_at is not None and elapsed(now,hazard_at)<1000
            m.update(now,dict(sensors,hazard=hazard,ready=healthy));hardware.apply(m.snapshot())
            if last_send is None or elapsed(now,last_send)>=200:
                peer.send('telemetry',dict(sensors,motion=m.snapshot()));last_send=now
            watchdog.feed();await asyncio.sleep_ms(20)
    finally:hardware.safe()
