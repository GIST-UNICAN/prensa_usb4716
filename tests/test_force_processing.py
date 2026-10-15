import unittest
from force_processing import force_series
class ForceTests(unittest.TestCase):
    def test_negatives_are_omitted_not_zeroed(self):
        for method in ('Media móvil','Mediana','Media temporal 1 s'):
            result=force_series([0,.1,.2],[10,-100,20],method=method,window=3)
            self.assertEqual(result[-1],20 if method=='Mediana' else 15)
    def test_empty_and_kalman(self):
        self.assertEqual(force_series([0,1],[-1,-2],method='Mediana'),[0,0])
        self.assertEqual(force_series([0,.1,.2],[10,-100,10],method='Kalman',gain=2000),[10,10,10])
