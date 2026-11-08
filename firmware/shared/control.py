"""Pure, deterministic safety and mission logic. Thresholds are demo values."""
PERIOD=1<<30

def elapsed(now,then):return (now-then)%PERIOD

def number(value,low,high):
    return type(value) in (int,float) and value==value and low<=value<=high

class Motion:
    def __init__(self,allow_retreat=False):
        self.allow_retreat=allow_retreat;self.armed=False;self.latched=False
        self.throttle=0;self.steering=0;self.phase='idle';self.reason='startup'
        self.last_peer=None;self.last_drive=None;self.phase_at=0;self.inputs={};self.manual=(0,0)
    def heartbeat(self,now):self.last_peer=now
    def fault(self,now,allow_hazard=False):
        i=self.inputs
        if self.last_peer is None or elapsed(now,self.last_peer)>=1000:return 'peer timeout'
        if i.get('ready') is not True:return 'sensors not ready'
        for key,lo,hi in [('distance_cm',0,600),('tilt_deg',-180,180),('voltage',0,30),('current_a',-10,10)]:
            if not number(i.get(key),lo,hi):return 'invalid '+key
        if abs(i['tilt_deg'])>=30:return 'tilt limit'
        if i['voltage']<6.4 or abs(i['current_a'])>3:return 'power limit'
        if not allow_hazard and i['distance_cm']<25:return 'obstacle'
        if i.get('hazard') not in (('normal','warning','danger') if allow_hazard else ('normal',)):return 'hazard '+str(i.get('hazard'))
        return None
    def halt(self,reason,phase='idle'):
        self.throttle=0;self.steering=0;self.manual=(0,0);self.armed=False;self.phase=phase;self.reason=reason;self.last_drive=None
    def command(self,now,action,payload):
        if action=='stop':self.latched=True;self.halt('emergency stop');return True
        if action=='reset':
            if self.fault(now):return False
            self.latched=False;self.halt('reset');return True
        if self.latched:return False
        if action=='arm':
            if self.armed or self.fault(now):return False
            self.manual=(0,0);self.throttle=0;self.steering=0
            self.armed=True;self.phase='manual';self.last_drive=None;self.reason='armed';return True
        if action=='drive':
            if not self.armed or self.phase!='manual' or self.fault(now):return False
            t=payload.get('throttle');s=payload.get('steering')
            if not number(t,-.5,.5) or not number(s,-1,1):self.halt('invalid drive');return False
            self.manual=(t,s);self.last_drive=now;return True
        if action=='inspect':
            if not self.armed or self.fault(now):return False
            self.phase='inspect';self.phase_at=now;self.reason='autonomous inspection';return True
        return False
    def update(self,now,inputs):
        self.inputs=inputs
        if self.latched:self.halt('emergency stop');return
        mission=self.phase in ('inspect','ventilate','retreat')
        fatal=self.fault(now,allow_hazard=mission)
        if fatal:self.halt(fatal);return
        if not self.armed:self.throttle=0;return
        if self.phase=='manual':
            if self.last_drive is None:self.throttle=0;self.steering=0;return
            if elapsed(now,self.last_drive)>=500:self.halt('command expired');return
            self.throttle,self.steering=self.manual
        elif self.phase=='inspect':
            if inputs['distance_cm']<25:self.halt('obstacle');return
            if inputs['hazard']!='normal':
                self.phase='ventilate';self.phase_at=now;self.throttle=0;self.reason='hazard detected'
            else:self.throttle=.22;self.steering=0
        elif self.phase=='ventilate':
            self.throttle=0
            if elapsed(now,self.phase_at)>=5000:
                if self.allow_retreat:self.phase='retreat';self.phase_at=now;self.throttle=-.2;self.reason='timed retreat'
                else:self.halt('retreat path not enabled','finished')
        elif self.phase=='retreat':
            self.throttle=-.2
            if elapsed(now,self.phase_at)>=2000:self.halt('inspection complete','finished')
    def snapshot(self):
        return dict(armed=self.armed,latched=self.latched,throttle=self.throttle,steering=self.steering,phase=self.phase,reason=self.reason)

class Hazard:
    def __init__(self,warmup_ms=60000,gas_warning=30000,gas_danger=45000,temp_warning=35,temp_danger=45):
        self.warmup_ms=warmup_ms;self.gw=gas_warning;self.gd=gas_danger;self.tw=temp_warning;self.td=temp_danger
        self.level='warming';self.fan=True;self.samples=[];self.clear_at=None;self.started=None;self.gas=None;self.temp=None
    def update(self,now,gas,temp):
        if self.started is None:self.started=now
        self.gas=gas;self.temp=temp
        if not number(gas,0,65535) or not number(temp,-40,125):
            self.level='fault';self.fan=True;self.clear_at=None;self.samples=[];return
        if elapsed(now,self.started)<self.warmup_ms:self.level='warming';self.fan=True;return
        self.samples.append(gas)
        if len(self.samples)>5:self.samples.pop(0)
        avg=sum(self.samples)/len(self.samples)
        target='danger' if gas>=self.gd or temp>=self.td else ('warning' if avg>=self.gw or temp>=self.tw else 'normal')
        if target=='danger' or (target=='warning' and self.level!='danger'):
            self.level=target;self.clear_at=None
        elif self.level in ('danger','warning'):
            if avg<self.gw*.9 and temp<self.tw-2:
                if self.clear_at is None:self.clear_at=now
                if elapsed(now,self.clear_at)>=3000:self.level='normal'
            else:self.clear_at=None
        else:self.level=target
        self.fan=self.level!='normal'
