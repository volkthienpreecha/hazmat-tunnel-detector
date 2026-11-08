"""Offline two-node UART simulator. Run: python3 -m simulator.server"""
import asyncio,argparse,time,math
from firmware.shared.runtime import Peer,MotionNode
from firmware.hazard.gateway import Gateway
from firmware.shared.http import Server

class Wire:
    def __init__(self):self.buffer=bytearray();self.other=None;self.enabled=True
    @classmethod
    def pair(cls):
        a=cls();b=cls();a.other=b;b.other=a;return a,b
    def write(self,data):
        if self.enabled and self.other.enabled:
            if len(self.other.buffer)+len(data)<=4096:self.other.buffer.extend(data)
        return len(data)
    def read(self,count):
        data=bytes(self.buffer[:count]);del self.buffer[:count];return data

class SimHardware:
    def __init__(self,role='hazard'):
        self.role=role;self.scenario='normal';self.now=0;self.applied={}
    def read(self):
        if self.scenario=='sensor_fault':raise OSError('simulated sensor disconnection')
        if self.role=='hazard':
            return dict(gas_raw=51000 if self.scenario=='gas' else int(11500+900*math.sin(self.now/3000)),temperature_c=49 if self.scenario=='heat' else round(24+math.sin(self.now/7000),1))
        return dict(distance_cm=12 if self.scenario=='obstacle' else 125,tilt_deg=40 if self.scenario=='tilt' else 1.2,voltage=5.9 if self.scenario=='power' else 7.6,current_a=.35,acceleration_g=[0,0,1],gyro_dps=[0,0,0])
    def apply(self,state):self.applied=state
    def safe(self):self.applied={'throttle':0,'fan':True}

class SimGateway(Gateway):
    def request(self,path,headers,obj):
        if path=='/api/scenario':
            if headers.get('x-operator-token')!=self.config['operator_token']:return {'error':'unauthorized'}
            scenario=obj.get('scenario')
            if scenario not in ('normal','gas','heat','obstacle','tilt','power','sensor_fault','peer_loss'):return {'error':'unknown scenario'}
            self.hardware.scenario=scenario;self.sim.motion_hardware.scenario=scenario
            self.peer.uart.enabled=scenario!='peer_loss';self.event('Simulation: '+scenario);return {'scenario':scenario}
        return super().request(path,headers,obj)

class Simulation:
    def __init__(self,allow_retreat=False):
        a,b=Wire.pair();self.hardware=SimHardware();self.motion_hardware=SimHardware('motion')
        self.gateway=SimGateway(dict(operator_token='demo-token',gas_warmup_ms=0,allow_clear_path_retreat=allow_retreat),self.hardware,Peer(a,'hazard-sim'),simulation=True)
        self.node=MotionNode(dict(allow_clear_path_retreat=allow_retreat),self.motion_hardware,Peer(b,'motion-sim'));self.motion=self.node.motion;self.gateway.sim=self
        for peer in (self.gateway.peer,self.node.peer):peer.send('hello',{});peer.flush()
    def step(self,now):
        self.hardware.now=now;self.motion_hardware.now=now;self.node.step(now);self.gateway.step(now)

async def main(host,port,retreat):
    sim=Simulation(retreat);start=time.monotonic();server=Server(sim.gateway)
    listener=await asyncio.start_server(server.handle,host,port)
    print('Hazmat simulator: http://%s:%s | operator token: demo-token | retreat: %s'%(host,port,retreat),flush=True)
    try:
        while True:
            sim.step(int((time.monotonic()-start)*1000)%(1<<30));await asyncio.sleep(.02)
    finally:listener.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8080);p.add_argument('--allow-retreat',action='store_true');a=p.parse_args()
    asyncio.run(main(a.host,a.port,a.allow_retreat))
