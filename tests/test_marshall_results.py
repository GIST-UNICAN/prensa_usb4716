import unittest
from marshall_results import calculate
class MarshallTests(unittest.TestCase):
    def test_linear_loading_and_unloading(self):
        rows=[dict(t=i,deformation_mm=i/10,force_kp=100*(i/10-1) if 10<=i<=30 else 0 if i<10 else 200-(i-30)*5) for i in range(41)]
        r=calculate(rows)
        self.assertEqual(r['peak_kp'],200)
        self.assertEqual(r['def50_mm'],1.5)
        self.assertEqual(r['def95_mm'],2.9)
        self.assertAlmostEqual(r['slope_kp_mm'],100)
        self.assertAlmostEqual(r['zero_mm'],1)
        self.assertEqual(r['corrected_mm'],2)
    def test_short_constant_and_missing_threshold(self):
        self.assertIsNone(calculate([])['peak_kp'])
        r=calculate([dict(t=i,deformation_mm=1,force_kp=i) for i in range(10)])
        self.assertIsNone(r['slope_kp_mm'])
        self.assertIsNone(r['def50_mm'])

    def test_initial_calibration_preserves_physical_zero(self):
        from calibration_comparison import recalibrate
        cfg=dict(force_factor_kp_per_v=-2000,force_offset_kp=100,zero_force_v=.15,
            deformation_factor_mm_per_v=2,deformation_offset_mm=1,zero_deform_v=.7)
        original=dict(id='test',configuration=cfg,samples=[dict(t=0,vf=.2,vd=.2,force_kp=0,deformation_mm=0)])
        changed=recalibrate(original)
        self.assertAlmostEqual(changed['samples'][0]['force_kp'],0)
        self.assertAlmostEqual(changed['samples'][0]['deformation_mm'],0)
        self.assertEqual(original['configuration']['force_factor_kp_per_v'],-2000)

    def test_original_workbook_reference_points(self):
        import json
        from pathlib import Path
        references=json.loads((Path(__file__).parent/'fixtures'/'marshall_legacy.json').read_text(encoding='utf-8'))
        for sample in references:
            result=calculate(sample['rows'])
            self.assertAlmostEqual(result['peak_kp'],sample['peak_kp'])
            self.assertAlmostEqual(result['slope_kp_mm'],sample['slope_kp_mm'],places=3)
            self.assertAlmostEqual(result['zero_mm'],sample['zero_mm'],places=6)
            self.assertAlmostEqual(result['def50_mm'],sample['def50_mm'])

    def test_export_uses_exactly_ten_reading_blocks(self):
        from marshall_results import calculation_rows,session_results
        rows=[dict(t=i*.01,vf=0,vd=0,force_kp=i,deformation_mm=i*.01) for i in range(25)]
        session=dict(samples=rows)
        points=calculation_rows(session)
        self.assertEqual(len(points),3)
        self.assertEqual([r['samples_count'] for r in points],[10,10,5])
        self.assertEqual(points[0]['force_kp'],4.5)
        self.assertEqual(points[-1]['force_kp'],22)
        self.assertEqual(session_results(session)['rows'],points)
