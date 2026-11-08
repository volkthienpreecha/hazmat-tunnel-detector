import asyncio
import machine
import os
from shared.hardware import Hardware
from shared.runtime import Peer,load_config,run_motion
c=load_config()
if c['role']!='motion':raise ValueError('wrong board configuration')
hardware=Hardware(c)
uart=machine.UART(1,baudrate=115200,tx=c['pins']['uart_tx'],rx=c['pins']['uart_rx'],timeout=0,timeout_char=0,txbuf=2048,rxbuf=2048)
peer=Peer(uart,os.urandom(8).hex());peer.send('hello',{});peer.flush()
asyncio.run(run_motion(c,hardware,peer))
