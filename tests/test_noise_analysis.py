import unittest
from noise_analysis import summarize_noise


class NoiseTests(unittest.TestCase):
    def test_constant_signal(self):
        r=summarize_noise([(i/100, 1., -2.) for i in range(1001)])
        self.assertAlmostEqual(r['observed_hz'],100)
        self.assertEqual(r['channels']['force']['std_v'],0)
        self.assertEqual(r['channels']['deformation']['mean_v'],-2)
        self.assertEqual(r['channels']['force']['windows']['1.0']['blocks'],10)

    def test_drift_and_saturation(self):
        r=summarize_noise([(i/100, i/100, (-1)**i*.01) for i in range(1001)])
        self.assertAlmostEqual(r['channels']['force']['drift_v_per_s'],1)
        self.assertGreater(r['channels']['force']['saturated_samples'],0)
        self.assertLess(r['channels']['deformation']['windows']['1.0']['std_v'],1e-10)

    def test_invalid_capture(self):
        for rows in ([(0,1,1)], [(0,1,1)]*3, [(0,1,1),(1,float('nan'),1),(2,1,1)]):
            with self.assertRaises(ValueError): summarize_noise(rows)

class SignalQualityTests(unittest.TestCase):
    def test_repeated_large_changes(self):
        from noise_analysis import rapid_voltage_changes
        rows=[(i*.01,.3 if i%2 else -.15,0 if i%2 else -4) for i in range(101)]
        warnings=rapid_voltage_changes(rows)
        self.assertTrue(any('Deformación' in text for text in warnings))

    def test_negative_dc_and_single_step_are_not_oscillation(self):
        from noise_analysis import rapid_voltage_changes
        self.assertEqual(rapid_voltage_changes([(i*.01,0,-3) for i in range(101)]),[])
        self.assertEqual(rapid_voltage_changes([(i*.01,0,-3 if i<50 else -1) for i in range(101)]),[])
