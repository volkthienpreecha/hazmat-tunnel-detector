"""Environmental controller and single-operator UART gateway."""
try:
    from shared.control import Hazard,elapsed,number
except ImportError:
    from firmware.shared.control import Hazard,elapsed,number

class Gateway:
    def __init__(self,config,hardware,peer,simulation=False):
        self.config=config;self.hardware=hardware;self.peer=peer;self.simulation=simulation
        self.hazard=Hazard(warmup_ms=config.get('gas_warmup_ms',60000));self.now=0
        self.sensors={};self.motion={'armed':False,'latched':False,'throttle':0,'steering':0,'phase':'idle','reason':'awaiting motion board'}
        self.motion_at=None;self.last_sample=None;self.last_send=None;self.owner=None;self.owner_at=None;self.events=[];self.event_seq=0;self.previous=None;self.last_ack=None
    def event(self,text):
        self.event_seq+=1;self.events.append(dict(id=self.event_seq,ms=self.now,text=text))
        if len(self.events)>40:self.events.pop(0)
    def step(self,now):
        self.now=now
        for frame,changed in self.peer.poll(now):
            if changed:
                self.owner=None;self.motion_at=None;self.motion=dict(self.motion,armed=False,throttle=0,phase='idle',reason='motion board restarted');self.event('Motion board session changed')
            if frame['kind']=='telemetry':
                data=frame['data'];motion=data.get('motion')
                if isinstance(motion,dict) and type(motion.get('armed')) is bool and number(motion.get('throttle'),-.5,.5) and number(motion.get('steering'),-1,1):
                    self.motion=motion;self.sensors=data;self.motion_at=now
            elif frame['kind']=='ack':self.last_ack=frame['data']
        if self.last_sample is None or elapsed(now,self.last_sample)>=100:
            try:local=self.hardware.read()
            except Exception:local={}
            self.hazard.update(now,local.get('gas_raw'),local.get('temperature_c'));self.last_sample=now
            self.hardware.apply({'fan':self.hazard.fan})
        if self.last_send is None or elapsed(now,self.last_send)>=200:
            self.peer.send('telemetry',{'hazard':self.hazard.level});self.last_send=now
        state=(self.hazard.level,self.motion.get('phase'),self.motion.get('reason'))
        if state!=self.previous:self.event(' / '.join(str(x) for x in state));self.previous=state
    def healthy(self):return self.motion_at is not None and elapsed(self.now,self.motion_at)<1000 and self.hazard.level=='normal'
    def command(self,now,headers,action,payload):
        self.now=now
        if headers.get('x-operator-token')!=self.config['operator_token']:return {'error':'unauthorized'}
        session=headers.get('x-operator-session','')
        if not isinstance(session,str) or not 1<=len(session)<=64:return {'error':'operator session required'}
        if action not in ('arm','drive','inspect','stop','reset'):return {'error':'unknown action'}
        if not isinstance(payload,dict):return {'error':'invalid payload'}
        if action=='drive' and (not number(payload.get('throttle'),-.5,.5) or not number(payload.get('steering'),-1,1)):return {'error':'invalid drive'}
        if action not in ('stop',):
            if not self.healthy():return {'error':'fresh normal telemetry required'}
            if self.owner is not None and self.owner!=session and elapsed(now,self.owner_at)<2000:return {'error':'another operator holds control'}
            if action in ('drive','inspect') and self.owner!=session:return {'error':'arm first'}
        if not self.peer.send(action,payload):return {'error':'UART busy, command not queued'}
        if action=='stop':self.owner=None
        else:self.owner=session;self.owner_at=now
        if action!='drive':self.event('Requested '+action)
        return {'queued':True,'action':action}
    def state(self):
        age=elapsed(self.now,self.motion_at) if self.motion_at is not None else None
        return dict(mode='simulation' if self.simulation else 'hardware',uptime_ms=self.now,peer_age_ms=age,connected=age is not None and age<1000,
                    hazard=self.hazard.level,fan=self.hazard.fan,gas_raw=self.hazard.gas,temperature_c=self.hazard.temp,
                    sensors={k:v for k,v in self.sensors.items() if k!='motion'},motion=self.motion,events=self.events,last_ack=self.last_ack,
                    retreat_enabled=self.config.get('allow_clear_path_retreat',False),local_age_ms=elapsed(self.now,self.last_sample) if self.last_sample is not None else None)
    def request(self,path,headers,obj):
        if path=='/api/command':return self.command(self.now,headers,obj.get('action'),obj.get('payload',{}))
        return {'error':'scenario endpoint only available in simulation'}
