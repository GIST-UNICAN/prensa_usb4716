import math
import unittest
from marshall_results import calculate
from une_marshall import normative,tenth

class UNETests(unittest.TestCase):
    def result(self):
        return dict(peak_kp=1000,peak_mm=5.,zero_mm=1.,slope_kp_mm=500.)
    def test_geometry_definitions_and_pending_dimensions(self):
        r=normative(self.result())
        self.assertEqual(r['flow_mm'],4)
        self.assertEqual(r['tangential_flow_mm'],2)
        self.assertEqual(r['total_flow_mm'],5)
        self.assertIsNone(r['stability_kn']);self.assertIsNone(r['quotient_kn_mm'])
    def test_height_and_volume_correction_and_rounding(self):
        h=63.5;raw=9.80665
        r=normative(self.result(),height=h)
        expected=5.2*math.exp(-.0259*h)
        self.assertAlmostEqual(r['correction_factor'],expected)
        self.assertEqual(r['stability_kn'],tenth(raw*expected))
        self.assertEqual(r['quotient_kn_mm'],tenth(raw*expected/4))
        volume=.0259*h/3.2e-6
        self.assertAlmostEqual(normative(self.result(),volume=volume)['correction_factor'],expected)
        self.assertEqual(tenth(2.15),2.2)
    def test_invalid_dimensions_and_tangent_do_not_invent_results(self):
        r=self.result();r['zero_mm']=6
        r=normative(r,height=-1,volume=float('nan'))
        self.assertIsNone(r['flow_mm']);self.assertIsNone(r['stability_kn'])
    def test_outside_height_range_is_identified(self):
        self.assertIn('fuera',normative(self.result(),height=80)['normative_note'])
