"""Minimal ST7789 text display. Geometry/pins must match the confirmed Feather."""
class Display:
    def __init__(self,c):
        import machine,time,framebuf
        P=machine.Pin;self.c=c;self.w=c['width'];self.h=c['height']
        for key in ('sck','mosi','cs','dc','reset','backlight'):
            if type(c.get(key)) is not int:raise ValueError('display pin unset: '+key)
        if c.get('power') is not None:P(c['power'],P.OUT,value=1)
        self.cs=P(c['cs'],P.OUT,value=1);self.dc=P(c['dc'],P.OUT,value=0)
        self.spi=machine.SPI(c['spi_id'],baudrate=20000000,sck=P(c['sck']),mosi=P(c['mosi']))
        reset=P(c['reset'],P.OUT,value=0);time.sleep_ms(20);reset.value(1);time.sleep_ms(120)
        self.cmd(0x01);time.sleep_ms(150);self.cmd(0x11);time.sleep_ms(120)
        self.cmd(0x3a,b'\x55');self.cmd(0x36,bytes([c.get('rotation',96)]));self.cmd(0x21);self.cmd(0x29)
        P(c['backlight'],P.OUT,value=1)
        self.buf=bytearray(self.w*self.h*2);self.fb=framebuf.FrameBuffer(self.buf,self.w,self.h,framebuf.RGB565)
    def cmd(self,cmd,data=None):
        self.cs.value(0);self.dc.value(0);self.spi.write(bytes([cmd]))
        if data:self.dc.value(1);self.spi.write(data)
        self.cs.value(1)
    def show(self,state):
        import struct
        self.fb.fill(0)
        lines=['HAZMAT MONITOR',state['hazard'],'Gas raw: '+str(state['gas_raw']),'Temp C: '+str(state['temperature_c']),'Fan: '+('ON' if state['fan'] else 'OFF'),'Peer: '+str(state['peer_age_ms'])+' ms']
        for i,line in enumerate(lines):self.fb.text(line[:29],4,8+i*20,0xffff)
        x=self.c.get('x_offset',40);y=self.c.get('y_offset',53)
        self.cmd(0x2a,struct.pack('>HH',x,x+self.w-1));self.cmd(0x2b,struct.pack('>HH',y,y+self.h-1));self.cmd(0x2c,self.buf)
