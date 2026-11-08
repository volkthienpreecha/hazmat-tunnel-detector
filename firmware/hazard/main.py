import asyncio,machine,network,os,time
from shared.hardware import Hardware
from shared.runtime import Peer,load_config
from shared.http import Server
from gateway import Gateway

async def main():
    c=load_config()
    if c['role']!='hazard':raise ValueError('wrong board configuration')
    if len(c.get('ap_password',''))<12 or c.get('ap_password')=='CHANGE-ME' or len(c.get('operator_token',''))<24:raise ValueError('set unique AP password and operator token')
    hardware=Hardware(c)
    uart=machine.UART(1,baudrate=115200,tx=c['pins']['uart_tx'],rx=c['pins']['uart_rx'],timeout=0,timeout_char=0,txbuf=2048,rxbuf=2048)
    peer=Peer(uart,os.urandom(8).hex());peer.send('hello',{});peer.flush()
    gateway=Gateway(c,hardware,peer)
    display=None
    if c.get('display',{}).get('enabled'):
        from shared.display import Display
        display=Display(c['display'])
    ap=network.WLAN(network.AP_IF);ap.active(True)
    ap.config(essid=c.get('ap_ssid','Hazmat-Rover'),password=c['ap_password'],authmode=3,max_clients=4)
    print('Dashboard address:',ap.ifconfig()[0])
    server=Server(gateway);listener=await asyncio.start_server(server.handle,'0.0.0.0',80)
    watchdog=machine.WDT(timeout=2000);last_display=None
    try:
        while True:
            now=time.ticks_ms();gateway.step(now)
            if display and (last_display is None or time.ticks_diff(now,last_display)>=500):display.show(gateway.state());last_display=now
            watchdog.feed();await asyncio.sleep_ms(20)
    finally:hardware.safe();listener.close()
asyncio.run(main())
