import unittest
from plot_cleaning import clean_rows

class CleaningTests(unittest.TestCase):
    def rows(self, values):
        return [dict(t=i/100,vf=v,vd=v,force_kp=v,deformation_mm=v) for i,v in enumerate(values)]
    def test_spike_preserves_original_and_negative_baseline(self):
        rows=self.rows([-2.]*21); rows[10]['force_kp']=500
        cleaned=clean_rows(rows)
        self.assertEqual(cleaned[10]['force_kp'],-2)
        self.assertEqual(rows[10]['force_kp'],500)
    def test_step_and_ramp_unchanged(self):
        for values in ([0.]*20+[10.]*20, list(range(40))):
            rows=self.rows(values)
            self.assertEqual(clean_rows(rows),rows)

    def test_alternating_signal_not_selectively_removed(self):
        rows=self.rows([1. if i%2 else 2. for i in range(101)])
        self.assertEqual(clean_rows(rows),rows)

    def test_dip_needs_recovery_and_keeps_rupture(self):
        from plot_cleaning import correct_force_dips
        rows=self.rows([100+i*2 for i in range(30)])
        rows[10]['force_kp']=-200; rows[11]['force_kp']=-180
        clean=correct_force_dips(rows)
        self.assertAlmostEqual(clean[10]['force_kp'],120)
        self.assertEqual(rows[10]['force_kp'],-200)
        self.assertEqual(correct_force_dips(rows[:12]),rows[:12])
        for r in rows[10:]: r['force_kp']=50
        self.assertEqual(correct_force_dips(rows),rows)

    def test_deformation_reversal_preserves_sustained_unloading(self):
        from plot_cleaning import correct_transient_reversals
        rows=self.rows([1+i*.002 for i in range(30)])
        rows[10]['deformation_mm']=.7; rows[11]['deformation_mm']=.8
        clean=correct_transient_reversals(rows)
        self.assertAlmostEqual(clean[10]['deformation_mm'],1.02)
        self.assertAlmostEqual(clean[11]['deformation_mm'],1.022)
        self.assertEqual(rows[10]['deformation_mm'],.7)
        self.assertEqual(correct_transient_reversals(rows[:12]),rows[:12])
        for r in rows[10:]: r['deformation_mm']=.7
        self.assertEqual(correct_transient_reversals(rows),rows)

    def test_compression_fixed_zero_and_monotonic(self):
        from plot_cleaning import compression_deformation
        values=[-.01,.005,.015,.1,.08,.2,.17,.3]
        self.assertEqual(compression_deformation(values),[0,0,0,.1,.1,.2,.2,.3])
        self.assertEqual(values[4],.08)
