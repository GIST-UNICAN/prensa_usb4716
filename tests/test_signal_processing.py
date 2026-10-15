import unittest
from signal_processing import time_average,detect_rupture
from taring import stable_tare

class SignalTests(unittest.TestCase):
    def test_irregular_time_average(self):
        self.assertEqual(time_average([0,.1,.2,1.5],[1,2,3,9]),[1,1.5,2,9])
    def test_rupture_requires_sustained_fall(self):
        rows=[dict(t=i/100,force_kp=0 if i<100 else min(100,(i-100)/2)) for i in range(500)]
        self.assertIsNone(detect_rupture(rows))
        rows += [dict(t=i/100,force_kp=max(0,100-(i-500)/2)) for i in range(500,800)]
        result=detect_rupture(rows)
        self.assertIsNotNone(result)
        self.assertGreater(result['confirmed_at'],result['t']+.5)
    def test_noise_does_not_trigger_rupture(self):
        rows=[dict(t=i/100,force_kp=(-1)**i*400) for i in range(800)]
        self.assertIsNone(detect_rupture(rows))
    def test_tare_preserves_zero_on_unstable_input(self):
        with self.assertRaises(ValueError): stable_tare([(i*.01,(-1)**i*.3,0) for i in range(301)])
        good=stable_tare([(i*.01,.2+(-1)**i*.001,-.5) for i in range(301)])
        self.assertAlmostEqual(good['channels'][0]['mean_v'],.2,places=4)
