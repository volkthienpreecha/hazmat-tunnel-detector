import unittest
from firmware.shared.runtime import Peer
from firmware.shared.protocol import FrameParser
from simulator.server import Simulation,Wire
class TransportTests(unittest.TestCase):
    def test_repeated_hello_for_staggered_boot(self):
        a,b=Wire.pair();p=Peer(a,'one');p.send('hello',{});p.flush();b.buffer.clear()
        q=Peer(b,'two')
        for t in range(0,2200,100):
            p.poll(t);p.send('telemetry',{});p.flush()
            frames=q.poll(t)
            if frames:break
        self.assertIsNotNone(q.receiver.session)
    def test_stop_preempts_periodic_telemetry(self):
        sim=Simulation()
        for t in range(0,1500,50):sim.step(t)
        headers={'x-operator-token':'demo-token','x-operator-session':'one','x-command-seq':'0'}
        sim.gateway.command(1500,headers,'arm',{})
        for t in range(1500,1800,50):sim.step(t)
        headers['x-command-seq']='1';sim.gateway.command(1800,headers,'inspect',{})
        for t in range(1800,2001,50):sim.step(t)
        headers['x-command-seq']='2'
        self.assertNotIn('error',sim.gateway.command(2000,headers,'stop',{}))
        for t in range(2050,2400,50):sim.step(t)
        self.assertTrue(sim.motion.latched);self.assertEqual(sim.motion.throttle,0)
    def test_buffered_drive_expires(self):
        a,b=Wire.pair();p=Peer(a,'one');p.poll(0);p.send('drive',{'throttle':.3,'steering':0});p.now=600;p.flush()
        frames=FrameParser().feed(bytes(b.buffer));self.assertFalse(any(f['kind']=='drive' for f in frames))
    def test_release_cancels_buffered_drive(self):
        a,b=Wire.pair();p=Peer(a,'one');p.poll(0);p.send('drive',{'throttle':.3,'steering':0})
        p.now=50;self.assertTrue(p.send('drive',{'throttle':0,'steering':0}));p.flush()
        frames=FrameParser().feed(bytes(b.buffer));self.assertEqual([f['data']['throttle'] for f in frames],[0])
    def test_arm_never_revives_old_intent(self):
        from firmware.shared.control import Motion
        from test_core import inputs
        m=Motion();m.heartbeat(0);m.update(0,inputs());m.command(0,'arm',{});m.command(0,'drive',{'throttle':.3,'steering':0});m.update(1,inputs())
        self.assertFalse(m.command(600,'arm',{}));m.update(600,inputs());self.assertEqual(m.throttle,0)
        self.assertTrue(m.command(650,'arm',{}));m.update(651,inputs());self.assertEqual(m.throttle,0)
    def test_active_mission_cannot_be_rearmed(self):
        from firmware.shared.control import Motion
        from test_core import inputs
        m=Motion();m.heartbeat(0);m.update(0,inputs());m.command(0,'arm',{});m.command(0,'inspect',{})
        self.assertFalse(m.command(1,'arm',{}));self.assertEqual(m.phase,'inspect')
