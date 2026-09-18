import tempfile
import unittest
from pathlib import Path
from measurement import fit_calibration, read_legacy, number

class MeasurementTests(unittest.TestCase):
    def test_negative_gain_and_offset(self):
        fit=fit_calibration([(0,10),(-1,2010),(-2,4010)])
        self.assertAlmostEqual(fit['factor'],-2000)
        self.assertAlmostEqual(fit['offset'],10)
        self.assertEqual(fit['r2'],1)

    def test_residuals(self):
        fit=fit_calibration([(0,0),(1,1.1),(2,2)])
        self.assertGreater(fit['max_error'],0)
        self.assertLess(fit['r2'],1)

    def test_invalid_patterns(self):
        for points in ([],[(1,1)],[(1,2),(1,3)],[(0,2),(1,2)],[(0,0),(float('nan'),2)]):
            with self.assertRaises(ValueError):fit_calibration(points)
        with self.assertRaises(ValueError):number('inf')

    def test_legacy_units_decimal_and_midnight(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'old.txt'; p.write_text('100 * 20,5 * 86399,9\n250 * 30 * 0,1\n')
            rows=read_legacy(p)
            self.assertEqual(rows[0],(0,20.5,1))
            self.assertAlmostEqual(rows[1][0],.2)
            self.assertEqual(rows[1][2],2.5)

    def test_original_files(self):
        root=Path(__file__).resolve().parents[1]
        rows=read_legacy(root/'version vieja/AD_SOFT/Probeta-9A.txt')
        self.assertGreater(len(rows),100)
        self.assertEqual(rows[0][0],0)

if __name__=='__main__':unittest.main()
