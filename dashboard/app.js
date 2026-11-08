'use strict';
const $=id=>document.getElementById(id);
const title=s=>String(s||'unknown').replace(/_/g,' ').replace(/^./,c=>c.toUpperCase());
let requestSeq=0;
let token='',state=null,received=0,pollBusy=false,driveBusy=false,held=null,holdTimer=null,history=[],lastSample=null;
const session=Array.from(crypto.getRandomValues(new Uint8Array(12)),b=>b.toString(16).padStart(2,'0')).join('');
const format=(v,suffix='',digits=1)=>typeof v==='number'&&Number.isFinite(v)?v.toFixed(digits)+suffix:'—';
const fresh=()=>state&&performance.now()-received<1000&&state.connected&&state.local_age_ms!==null&&state.local_age_ms<500;
const manualReady=()=>token&&fresh()&&state.hazard==='normal'&&state.motion.armed&&state.motion.phase==='manual'&&!state.motion.latched;
async function post(path,obj){
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),700);
  try{
    const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Operator-Token':token,'X-Operator-Session':session,'X-Command-Seq':String(requestSeq++)},body:JSON.stringify(obj),signal:controller.signal,cache:'no-store'});
    const result=await response.json();if(!response.ok||result.error)throw new Error(result.error||'Request failed');return result;
  }finally{clearTimeout(timer)}
}
async function command(action,payload={}){
  if(!token){$('command-result').textContent='Enter the operator token first';return false}
  try{await post('/api/command',{action,payload});if(action!=='drive')$('command-result').textContent=title(action)+' requested; awaiting board state';return true}
  catch(error){$('command-result').textContent=error.message;return false}
}
function release(){
  const wasHeld=held!==null;held=null;clearInterval(holdTimer);holdTimer=null;
  document.querySelectorAll('.drive').forEach(b=>b.classList.remove('active'));
  if(wasHeld)command('drive',{throttle:0,steering:0});
}
async function renew(){
  if(!held||driveBusy)return;
  if(!manualReady()){release();return}
  const intent=held;driveBusy=true;
  try{const ok=await command('drive',{throttle:intent.throttle,steering:intent.steering});if(!ok)release()}
  finally{driveBusy=false}
}
function hold(button){
  if(!manualReady()||held)return;
  held={throttle:Number(button.dataset.throttle),steering:Number(button.dataset.steering)};
  button.classList.add('active');renew();holdTimer=setInterval(renew,150);
}
for(const button of document.querySelectorAll('.drive')){
  button.disabled=true;
  button.addEventListener('pointerdown',event=>{if(event.button!==0)return;event.preventDefault();button.setPointerCapture(event.pointerId);hold(button)});
  for(const event of ['pointerup','pointercancel','lostpointercapture'])button.addEventListener(event,release);
  button.addEventListener('keydown',event=>{if((event.key===' '||event.key==='Enter')&&!event.repeat){event.preventDefault();hold(button)}});
  button.addEventListener('keyup',event=>{if(event.key===' '||event.key==='Enter'){event.preventDefault();release()}});
}
const keys={ArrowUp:'.forward',w:'.forward',ArrowDown:'.reverse',s:'.reverse',ArrowLeft:'.left',a:'.left',ArrowRight:'.right',d:'.right'};
window.addEventListener('keydown',event=>{
  if(event.key==='Escape'){event.preventDefault();release();command('stop');return}
  if(event.target.matches('input,select,textarea,button')||event.repeat)return;
  const target=keys[event.key];if(target){event.preventDefault();hold(document.querySelector(target))}
});
window.addEventListener('keyup',event=>{if(keys[event.key])release()});
window.addEventListener('blur',release);
document.addEventListener('visibilitychange',()=>{if(document.hidden)release()});
window.addEventListener('pagehide',release);
$('stop').addEventListener('click',()=>{release();command('stop')});
$('arm').addEventListener('click',()=>command('arm'));
$('inspect').addEventListener('click',()=>{release();command('inspect')});
$('reset').addEventListener('click',()=>{release();command('reset')});
$('connect-form').addEventListener('submit',event=>{event.preventDefault();release();token=$('token').value.trim();$('command-result').textContent=token?'Token set for this tab; arm to request control':'Enter an operator token';render()});
$('scenario').addEventListener('change',async()=>{release();try{await post('/api/scenario',{scenario:$('scenario').value})}catch(e){$('command-result').textContent=e.message}});
function render(){
  if(!state)return;
  const live=fresh(),motion=state.motion,sim=state.mode==='simulation';
  $('mode').textContent=sim?'Simulation / no hardware':'Hardware / live sensors';
  $('simulation').hidden=!sim;$('token-help').textContent=sim?'Simulator token: demo-token':'Use your configured operator token';
  $('link-label').textContent=live?'Link active':'Link stale';
  for(const id of ['link-dot','motion-dot'])$(id).classList.toggle('live',live);
  $('hazard-dot').classList.toggle('live',performance.now()-received<1000);
  $('clock').textContent=new Date().toLocaleTimeString([],{hour12:false});
  $('age').textContent=state.peer_age_ms===null?'No samples':Math.round(state.peer_age_ms+performance.now()-received)+' ms';
  $('gas').textContent=format(state.gas_raw,'',0);$('temp').textContent=format(state.temperature_c,'°');
  $('hazard').textContent=live?title(state.hazard):'Unknown';
  $('fan').textContent=performance.now()-received<1000?(state.fan?'Running':'Standby'):'Unknown';
  $('fan-caption').textContent=state.fan?'Ventilation requested':'No ventilation requested';
  $('phase').textContent=motion.latched?'Emergency stop':title(motion.phase);
  $('distance').textContent=format(state.sensors.distance_cm,' cm',0);$('tilt').textContent=format(state.sensors.tilt_deg,'°');
  $('voltage').textContent=format(state.sensors.voltage,' V',2);$('current').textContent=format(state.sensors.current_a,' A',2);
  $('throttle').textContent=live?format(motion.throttle*100,'%',0):'Unknown';$('throttle').dataset.value=live?motion.throttle:0;
  const normal=live&&state.hazard==='normal'&&!motion.latched;
  $('arm').disabled=!token||!normal||motion.armed;
  $('inspect').disabled=!token||!normal||!motion.armed||motion.phase!=='manual';
  $('reset').disabled=!token||!live||state.hazard!=='normal';
  document.querySelectorAll('.drive').forEach(b=>b.disabled=!manualReady());
  $('control-status').textContent=!token?'Locked':motion.armed?'Armed':'Disarmed';
  $('retreat-note').textContent=state.retreat_enabled?'Timed retreat enabled · keep the rear path clear':'Retreat disabled · rover remains stopped after ventilation';
  let notice=sim?'Simulation mode. Values and motion are generated; no hardware is connected.':'Hardware mode. Verify pin assignments and calibration before testing.';
  if(!live)notice='Telemetry stale or disconnected. Motion is inhibited; reconnecting never resumes driving.';
  else if(motion.latched)notice='Emergency stop latched. Clear the fault, reset, then arm again.';
  else if(state.hazard!=='normal')notice=title(state.hazard)+': '+motion.reason+'. Fan '+(state.fan?'requested on':'off')+'.';
  $('notice').textContent=notice;$('notice').classList.toggle('alert',!live||motion.latched||state.hazard!=='normal');
  $('event-count').textContent=state.events.length+' events';
  const list=$('event-list');list.replaceChildren();
  for(const event of [...state.events].reverse()){
    const li=document.createElement('li'),time=document.createElement('time'),text=document.createElement('span');
    time.textContent=(event.ms/1000).toFixed(1)+'s';text.textContent=event.text;li.append(time,text);list.append(li);
  }
}
function draw(){
  const t=state.uptime_ms;if(lastSample===t)return;lastSample=t;
  if(typeof state.gas_raw==='number')history.push({t,gas:state.gas_raw});
  history=history.filter(s=>t-s.t<=60000&&t-s.t>=0).slice(-300);
  $('chart-empty').hidden=history.length>1;
  const points=history.map(s=>[52+692*(1-(t-s.t)/60000),180-156*s.gas/65535]);
  const d=points.map((p,i)=>(i?'L':'M')+p.map(v=>v.toFixed(1)).join(' ')).join(' ');
  $('gas-line').setAttribute('d',d);$('gas-area').setAttribute('d',points.length?d+' L744 180 L'+points[0][0].toFixed(1)+' 180 Z':'');
}
async function poll(){
  if(pollBusy)return;pollBusy=true;const abort=new AbortController();const timer=setTimeout(()=>abort.abort(),700);
  try{const r=await fetch('/api/state',{signal:abort.signal,cache:'no-store'});if(!r.ok)throw new Error('Telemetry unavailable');const value=await r.json();
    if(!value.motion||!value.sensors||!Array.isArray(value.events))throw new Error('Invalid telemetry');
    state=value;received=performance.now();draw();render();if(!manualReady()&&held)release();
  }catch(e){received=0;release();render();$('notice').textContent='Connection lost. Rover command leases expire locally; reconnect will not resume driving.';$('notice').classList.add('alert')}
  finally{clearTimeout(timer);pollBusy=false}
}
setInterval(poll,250);setInterval(()=>{if(!fresh()){release();render()}},200);poll();
