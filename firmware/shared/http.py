"""Small bounded HTTP/1.1 server for MicroPython and CPython asyncio."""
import asyncio,json
MAX_HEADERS=4096
MAX_BODY=2048

def parse_head(data):
    if len(data)>MAX_HEADERS:raise ValueError('headers too large')
    lines=data.decode('ascii').split('\r\n');parts=lines[0].split(' ')
    if len(parts)!=3 or parts[0] not in ('GET','POST') or parts[2]!='HTTP/1.1':raise ValueError('bad request line')
    method,path,_=parts
    if not path.startswith('/') or len(path)>256:raise ValueError('bad path')
    headers={}
    for line in lines[1:]:
        if not line:continue
        if ':' not in line:raise ValueError('bad header')
        k,v=line.split(':',1);k=k.strip().lower()
        if k in headers:raise ValueError('duplicate header')
        headers[k]=v.strip()
    if 'transfer-encoding' in headers:raise ValueError('transfer encoding unsupported')
    length=int(headers.get('content-length','0'))
    if not 0<=length<=MAX_BODY:raise ValueError('body too large')
    return method,path,headers,length

class Server:
    def __init__(self,app,static_root='dashboard'):
        self.app=app;self.static_root=static_root;self.active=0
    async def handle(self,reader,writer):
        if self.active>=4:
            writer.close();return
        self.active+=1
        try:
            await asyncio.wait_for(self.request(reader,writer),2)
        except (Exception,):
            pass
        finally:
            self.active-=1;writer.close()
            if hasattr(writer,'wait_closed'):
                try:await writer.wait_closed()
                except Exception:pass
    async def request(self,reader,writer):
        try:
            head=bytearray()
            while not head.endswith(b'\r\n\r\n'):
                ch=await reader.read(1)
                if not ch:return
                head.extend(ch)
                if len(head)>MAX_HEADERS:raise ValueError('headers too large')
            method,path,headers,length=parse_head(head)
            body=bytearray()
            while len(body)<length:
                chunk=await reader.read(length-len(body))
                if not chunk:raise ValueError('incomplete body')
                body.extend(chunk)
            if method=='GET' and path in ('/','/style.css','/app.js'):
                filename={'/':'index.html','/style.css':'style.css','/app.js':'app.js'}[path]
                mime={'/':'text/html; charset=utf-8','/style.css':'text/css','/app.js':'text/javascript'}[path]
                try:
                    import os
                    name=self.static_root+'/'+filename;size=os.stat(name)[6]
                    await self.headers(writer,200,mime,size)
                    with open(name,'rb') as f:
                        while True:
                            chunk=f.read(1024)
                            if not chunk:break
                            writer.write(chunk);await writer.drain()
                    return
                except OSError:await self.respond(writer,404,{'error':'asset not found'});return
            if method=='GET' and path=='/api/state':result=self.app.state();status=200
            elif method=='POST' and path in ('/api/command','/api/scenario'):
                if headers.get('content-type','').split(';')[0]!='application/json':raise ValueError('JSON required')
                # Reject cross-origin browser requests, including opaque file origins.
                origin=headers.get('origin')
                if origin and origin not in ('http://'+headers.get('host',''),'https://'+headers.get('host','')):
                    await self.respond(writer,403,{'error':'origin rejected'});return
                obj=json.loads(body.decode())
                if not isinstance(obj,dict):raise ValueError('object required')
                result=self.app.request(path,headers,obj);status=400 if 'error' in result else 200
                if result.get('error')=='unauthorized':status=401
            else:result={'error':'not found'};status=404
            await self.respond(writer,status,result)
        except (ValueError,UnicodeError,TypeError):await self.respond(writer,400,{'error':'invalid request'})
    async def headers(self,writer,status,mime,length):
        writer.write(('HTTP/1.1 %s Response\r\nContent-Type: %s\r\nContent-Length: %s\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nContent-Security-Policy: default-src \'self\'; script-src \'self\'; style-src \'self\'; connect-src \'self\'; frame-ancestors \'none\'\r\nConnection: close\r\n\r\n'%(status,mime,length)).encode());await writer.drain()
    async def respond(self,writer,status,obj):
        data=json.dumps(obj).encode();await self.headers(writer,status,'application/json',len(data));writer.write(data);await writer.drain()
