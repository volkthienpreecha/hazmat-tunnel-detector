"""Explicit hardware adapters. Importing this module does not touch GPIO."""
import math
import struct
from .control import number
MOTION_PINS=('uart_tx','uart_rx','sda','scl','motor_left_pwm','motor_left_a','motor_left_b','motor_right_pwm','motor_right_a','motor_right_b','servo','trig','echo')
HAZARD_PINS=('uart_tx','uart_rx','gas_adc','temp_adc','fan')

def validate_config(c):
    role=c.get('role')
    if role not in ('motion','hazard'):raise ValueError('role must be motion or hazard')
    pins=c.get('pins',{})
    required=MOTION_PINS if role=='motion' else HAZARD_PINS
    if c.get('hardware_confirmed') is not True:raise ValueError('confirm board, pinout and power design first')
    for key in required:
        if type(pins.get(key)) is not int or not 0<=pins[key]<=48:raise ValueError('unset/invalid GPIO: '+key)
    active=[v for v in pins.values() if v is not None]
    if len(active)!=len(set(active)):raise ValueError('conflicting GPIO assignments')
    if role=='hazard' and c.get('temperature_model')!='TMP36':raise ValueError('only explicitly selected TMP36 is supported')
    if role=='hazard' and (not number(c.get('gas_warmup_ms'),0,86400000) or not number(c.get('gas_adc_scale'),0.1,100)):raise ValueError('gas warmup and divider scale required')

def tmp36_c(microvolts):return (microvolts/1000000-.5)*100

def imu_decode(data):return [v*.000061 for v in struct.unpack('<hhh',data)]

def power_decode(bus,shunt,ohms):
    signed=shunt-65536 if shunt&32768 else shunt
    return (bus>>3)*.004,signed*.00001/ohms

class Hardware:
    def __init__(self,c):
        validate_config(c)
        import machine
        import time
        self.machine=machine;self.time=time;self.config=c;self.pins=c['pins'];self.outputs={};self.pwms={};self.adcs={}
        p=machine.Pin
        if c['role']=='motion':
            for side in ('left','right'):
                for suffix in ('a','b'):
                    name='motor_'+side+'_'+suffix;self.outputs[name]=p(self.pins[name],p.OUT,value=0)
                name='motor_'+side+'_pwm';self.pwms[name]=machine.PWM(p(self.pins[name]),freq=1000,duty_u16=0)
            self.pwms['servo']=machine.PWM(p(self.pins['servo']),freq=50,duty_u16=4915)
            if self.pins.get('i2c_power') is not None:p(self.pins['i2c_power'],p.OUT,value=1)
            self.i2c=machine.I2C(0,sda=p(self.pins['sda']),scl=p(self.pins['scl']),freq=100000,timeout=10000)
            self.imu=c.get('imu_address',0x6a);self.power=c.get('power_address',0x40)
            if self.i2c.readfrom_mem(self.imu,0x0f,1)[0]!=0x6c:raise ValueError('LSM6DSO/DSOX identity mismatch')
            for reg,val in ((0x12,0x44),(0x10,0x40),(0x11,0x40)):self.i2c.writeto_mem(self.imu,reg,bytes([val]))
            self.i2c.writeto_mem(self.power,0,struct.pack('>H',0x399f))
            self.trig=p(self.pins['trig'],p.OUT,value=0);self.echo=p(self.pins['echo'],p.IN)
        else:
            # Pull fan gate high for fault/warmup mitigation; external pulldown prevents floating gate at boot.
            self.outputs['fan']=p(self.pins['fan'],p.OUT,value=1)
            for key in ('gas_adc','temp_adc'):
                adc=machine.ADC(p(self.pins[key]));adc.atten(machine.ADC.ATTN_11DB);self.adcs[key]=adc
    def read(self):
        if self.config['role']=='hazard':
            return {'gas_raw':self.adcs['gas_adc'].read_u16(),'temperature_c':tmp36_c(self.adcs['temp_adc'].read_uv())}
        self.trig.value(0);self.time.sleep_us(2);self.trig.value(1);self.time.sleep_us(10);self.trig.value(0)
        pulse=self.machine.time_pulse_us(self.echo,1,20000)
        acc=imu_decode(self.i2c.readfrom_mem(self.imu,0x28,6))
        gyro=[v*.00875 for v in struct.unpack('<hhh',self.i2c.readfrom_mem(self.imu,0x22,6))]
        tilt=math.degrees(math.atan2(math.sqrt(acc[0]**2+acc[1]**2),acc[2]))
        bus=struct.unpack('>H',self.i2c.readfrom_mem(self.power,2,2))[0]
        shunt=struct.unpack('>H',self.i2c.readfrom_mem(self.power,1,2))[0]
        if bus&1:raise ValueError('INA219 overflow')
        v,a=power_decode(bus,shunt,self.config.get('shunt_ohms',.1))
        return dict(distance_cm=pulse/58 if pulse>=0 else None,tilt_deg=tilt,voltage=v,current_a=a,acceleration_g=acc,gyro_dps=gyro)
    def apply(self,state):
        if self.config['role']=='hazard':self.outputs['fan'].value(bool(state['fan']));return
        throttle=state['throttle'];steering=state['steering']
        for side in ('left','right'):
            # Disable PWM before changing direction.
            self.pwms['motor_'+side+'_pwm'].duty_u16(0)
            self.outputs['motor_'+side+'_a'].value(throttle>0);self.outputs['motor_'+side+'_b'].value(throttle<0)
            self.pwms['motor_'+side+'_pwm'].duty_u16(int(abs(throttle)*65535))
        us=self.config.get('servo_center_us',1500)+steering*self.config.get('servo_span_us',400)
        self.pwms['servo'].duty_u16(int(us/20000*65535))
    def safe(self):
        self.apply({'fan':True,'throttle':0,'steering':0})
