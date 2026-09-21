import unittest

from exports import chart_series, filtered_csv_text, selected_indices
from units import available_units, from_kp


class UnitsAndFiltersTests(unittest.TestCase):
    def setUp(self):
        self.session = {
            'configuration': {'specimen_area_mm2': 100.0},
            'samples': [
                {'t': 0, 'vf': 0, 'vd': 0, 'force_kp': 0, 'deformation_mm': 0},
                {'t': 1, 'vf': 0, 'vd': 0, 'force_kp': 10, 'deformation_mm': 1},
                {'t': 2, 'vf': 0, 'vd': 0, 'force_kp': 100, 'deformation_mm': 2},
                {'t': 3, 'vf': 0, 'vd': 0, 'force_kp': 50, 'deformation_mm': 3},
            ],
        }

    def test_si_legacy_and_pressure_conversions(self):
        self.assertAlmostEqual(from_kp(1, 'kgf'), 1)
        self.assertAlmostEqual(from_kp(1, 'N'), 9.80665)
        self.assertAlmostEqual(from_kp(1, 'kN'), .00980665)
        self.assertAlmostEqual(from_kp(1, 'MPa', 100), .0980665)
        self.assertAlmostEqual(from_kp(1, 'kgf/cm²', 100), 1)
        self.assertNotIn('MPa', available_units(0))
        self.assertIn('MPa', available_units(100))

    def test_legacy_5_95_filter_is_ascending_before_peak(self):
        self.assertEqual(selected_indices(self.session['samples'], 'Ascenso 5–95 %'), [1])
        series, _, label = chart_series(self.session, 'ft', 'N', method='Mediana', range_filter='Ascenso 5–95 %')
        self.assertEqual(label, 'Fuerza (N)')
        self.assertEqual(series[0][0], [0])
        self.assertAlmostEqual(series[0][1][0], 98.0665)
        text = filtered_csv_text(self.session, 'Media móvil', 3, 'Ascenso 5–95 %')
        self.assertIn('fuerza_N_filtrada', text)
        self.assertIn('10.0', text)


if __name__ == '__main__':
    unittest.main()
