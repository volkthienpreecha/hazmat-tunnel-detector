import unittest
from firmware.shared.hardware import validate_config, tmp36_c, imu_decode, power_decode
class HardwareTests(unittest.TestCase):
    def test_missing_and_conflicting_pins(self):
        with self.assertRaises(ValueError):validate_config({'role':'motion','pins':{}})
        pins=dict(uart_tx=1,uart_rx=2,sda=3,scl=4,motor_left_pwm=5,motor_left_a=6,motor_left_b=7,motor_right_pwm=8,motor_right_a=9,motor_right_b=10,servo=11,trig=12,echo=13)
        validate_config({'role':'motion','pins':pins,'hardware_confirmed':True})
        pins['echo']=12
        with self.assertRaises(ValueError):validate_config({'role':'motion','pins':pins,'hardware_confirmed':True})
    def test_temperature_and_signed_imu(self):
        self.assertAlmostEqual(tmp36_c(750000),25)
        data=b'\x00\x00\x00\x00\x00\x40'
        self.assertAlmostEqual(imu_decode(data)[2],.999424,places=5)
    def test_power_units(self):
        v,a=power_decode(16000,1000,.1)
        self.assertAlmostEqual(v,8);self.assertAlmostEqual(a,.1)
