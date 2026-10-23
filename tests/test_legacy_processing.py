import unittest
from legacy_processing import legacy_rows,legacy_text,legacy_tare
class LegacyTests(unittest.TestCase):
    def test_blocks_and_second_average(self):
        rows=[dict(t=i/100,vf=-1,vd=1,force_kp=100,deformation_mm=2) for i in range(20)]
        v=legacy_rows(rows)
        self.assertEqual(v[8]['force_kp'],0)
        self.assertEqual(v[9]['force_kp'],100)
        lines=legacy_text(rows).splitlines()
        self.assertEqual(lines[0],'20 * 10 * 0.090000')
        self.assertEqual(lines[1],'200 * 100 * 0.190000')
        self.assertEqual(rows[0]['force_kp'],100)
    def test_negative_int_is_floor(self):
        rows=[dict(t=i,vf=0,vd=0,force_kp=-1.1,deformation_mm=-.011) for i in range(20)]
        self.assertTrue(legacy_text(rows).splitlines()[1].startswith('-2 * 0 *'))
    def test_tare_arithmetic_mean_and_saturation(self):
        rows=[(i,.199 if i%2 else .201,-.5) for i in range(100)]
        self.assertAlmostEqual(legacy_tare(rows)['channels'][0]['mean_v'],.2)
        rows[-1]=(99,5,0)
        with self.assertRaises(ValueError): legacy_tare(rows)

    def test_noisy_tare_can_continue_when_requested(self):
        rows=[(i*.01, .3 if i%2 else -.3, -.5) for i in range(100)]
        with self.assertRaises(ValueError): legacy_tare(rows)
        result=legacy_tare(rows,allow_unstable=True)
        self.assertIn('warning',result['stability'])
        self.assertAlmostEqual(result['channels'][0]['mean_v'],0)
