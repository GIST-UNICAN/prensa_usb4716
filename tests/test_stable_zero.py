import unittest
from stable_zero import StableValue,stable_channels
class StableZeroTests(unittest.TestCase):
    def test_noise_spike_and_sustained_motion(self):
        f=StableValue(2)
        for i in range(100): self.assertEqual(f.update(i*.01,(-1)**i),0)
        self.assertEqual(f.update(1,100),0)
        self.assertEqual(f.update(1.1,0),0)
        self.assertEqual(f.update(2,10),0)
        self.assertEqual(f.update(2.31,10),10)
        self.assertEqual(f.update(2.4,11),10)
        self.assertEqual(f.update(3,5),10)
        self.assertEqual(f.update(3.31,5),5)
    def test_no_tare_means_no_artificial_zero(self):
        self.assertIsNone(stable_channels({},None))
    def test_threshold_tracks_calibration(self):
        cfg=dict(force_factor_kp_per_v=-2000,deformation_factor_mm_per_v=2)
        tare=dict(stability=dict(channels=[dict(std_v=.001),dict(std_v=.001)]))
        f,d=stable_channels(cfg,tare)
        self.assertEqual(f.threshold,10)
        self.assertEqual(d.threshold,.02)
