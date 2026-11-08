import unittest, asyncio
from firmware.shared.http import parse_head
from firmware.hazard.gateway import Gateway
from simulator.server import SimHardware,Wire
class HttpTests(unittest.TestCase):
    def test_parse_bounds(self):
        self.assertEqual(parse_head(b'GET /api/state HTTP/1.1\r\nHost: localhost\r\n\r\n')[1],'/api/state')
        for b in [b'bad',b'POST / HTTP/1.1\r\nContent-Length: -1\r\n\r\n',b'POST / HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n']:
            with self.assertRaises(ValueError):parse_head(b)
    def test_token_and_control_lease(self):
        from firmware.shared.runtime import Peer
        a,b=Wire.pair();g=Gateway({'operator_token':'test-token','gas_warmup_ms':0},SimHardware(),Peer(a,'gateway'),simulation=True)
        self.assertEqual(g.command(0,{},'arm',{}).get('error'),'unauthorized')
        headers={'x-operator-token':'test-token','x-operator-session':'one','x-command-seq':'0'}
        # No telemetry means arming is refused before any UART command can be sent.
        self.assertIn('error',g.command(0,headers,'arm',{}))
        self.assertIn('error',g.command(0,headers,'drive',{'throttle':True,'steering':0}))
    def test_simulation_hazard_stop(self):
        from simulator.server import Simulation
        sim=Simulation()
        for t in range(0,1500,50):sim.step(t)
        h={'x-operator-token':'demo-token','x-operator-session':'one','x-command-seq':'0'}
        self.assertNotIn('error',sim.gateway.command(1500,h,'arm',{}))
        for t in range(1500,1800,50):sim.step(t)
        h['x-command-seq']='1';sim.gateway.command(1800,h,'inspect',{})
        for t in range(1800,2100,50):sim.step(t)
        self.assertGreater(sim.motion.throttle,0)
        sim.hardware.scenario='gas'
        for t in range(2100,2500,50):sim.step(t)
        self.assertEqual(sim.motion.throttle,0);self.assertTrue(sim.gateway.hazard.fan)
        self.assertEqual(sim.motion.phase,'ventilate')
