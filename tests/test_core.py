import unittest
from firmware.shared.protocol import FrameParser, encode, Receiver
from firmware.shared.control import Motion, Hazard, elapsed

def inputs(**changes):
    value=dict(distance_cm=100,tilt_deg=0,voltage=7.5,current_a=0.2,hazard='normal',ready=True)
    value.update(changes)
    return value

class CoreTests(unittest.TestCase):
    def motion(self):
        m=Motion();m.update(0,inputs());m.heartbeat(0);self.assertTrue(m.command(0,'arm',{}));return m
    def test_lease_expires_despite_heartbeat(self):
        m=self.motion();m.command(0,'drive',{'throttle':.3,'steering':0});m.heartbeat(600);m.update(600,inputs());self.assertEqual(m.throttle,0);self.assertFalse(m.armed)
    def test_autonomy_and_retreat(self):
        m=self.motion();m.allow_retreat=True;m.command(0,'inspect',{});m.update(1,inputs());self.assertGreater(m.throttle,0)
        m.heartbeat(100);m.update(100,inputs(hazard='danger'));self.assertEqual(m.phase,'ventilate');self.assertEqual(m.throttle,0)
        m.heartbeat(5100);m.update(5100,inputs(hazard='danger'));self.assertEqual(m.phase,'retreat');self.assertLess(m.throttle,0)
        m.heartbeat(7100);m.update(7100,inputs(hazard='danger'));self.assertEqual(m.phase,'finished');self.assertEqual(m.throttle,0)
    def test_no_retreat_without_clear_path(self):
        m=self.motion();m.command(0,'inspect',{});m.update(1,inputs(hazard='danger'));m.heartbeat(6000);m.update(6000,inputs(hazard='danger'));self.assertEqual(m.throttle,0);self.assertEqual(m.phase,'finished')
    def test_peer_fault_blocks_retreat(self):
        m=self.motion();m.allow_retreat=True;m.command(0,'inspect',{});m.update(1,inputs(hazard='danger'));m.update(6000,inputs(hazard='danger'));self.assertEqual(m.throttle,0);self.assertFalse(m.armed)
    def test_obstacle_and_reset(self):
        m=self.motion();m.command(0,'inspect',{});m.update(1,inputs(distance_cm=10));self.assertEqual(m.throttle,0)
        m.command(2,'stop',{});self.assertFalse(m.command(3,'arm',{}));m.update(4,inputs());self.assertTrue(m.command(4,'reset',{}));self.assertFalse(m.armed)
    def test_invalid_values(self):
        m=self.motion()
        for val in [True,float('nan'),float('inf'),2,'1']:
            self.assertFalse(m.command(0,'drive',{'throttle':val,'steering':0}));self.assertEqual(m.throttle,0)
        m.update(1,inputs(distance_cm=None));self.assertEqual(m.throttle,0)
    def test_hazard_immediate_and_hysteresis(self):
        h=Hazard(warmup_ms=0);h.update(0,1000,23);self.assertEqual(h.level,'normal')
        h.update(1,50000,23);self.assertEqual(h.level,'danger');self.assertTrue(h.fan)
        h.update(2,1000,23);self.assertNotEqual(h.level,'normal')
        for t in range(1000,15000,500):h.update(t,1000,23)
        self.assertEqual(h.level,'normal');self.assertFalse(h.fan)
        h.update(16000,None,23);self.assertEqual(h.level,'fault');self.assertTrue(h.fan)
    def test_rollover(self):
        self.assertEqual(elapsed(5,(1<<30)-5),10)
    def test_frame_bounds_and_recovery(self):
        p=FrameParser();self.assertEqual(p.feed(b'x'*2048),[])
        self.assertEqual(p.feed(b'\n'+encode({'v':1,'kind':'heartbeat','session':'a','seq':0,'data':{}}))[0]['kind'],'heartbeat')
        self.assertEqual(p.feed(b'garbage\n'),[])
    def test_replay_and_session(self):
        r=Receiver();frame=dict(v=1,kind='heartbeat',session='a',seq=0,data={})
        self.assertTrue(r.accept(frame));self.assertFalse(r.accept(frame));frame['seq']=True;self.assertFalse(r.accept(frame))
        frame.update(session='b',seq=0,kind='drive');self.assertFalse(r.accept(frame))
        frame['kind']='hello';self.assertTrue(r.accept(frame));frame.update(session='a',seq=1,kind='heartbeat');self.assertFalse(r.accept(frame))
if __name__=='__main__':unittest.main()
