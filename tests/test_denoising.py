import math
import random
import statistics
import unittest
from denoising import VoltageKalman, NOISE_VARIANCES


class KalmanTests(unittest.TestCase):
    def test_constant_and_resets(self):
        f=VoltageKalman(NOISE_VARIANCES[0])
        for i in range(100): self.assertEqual(f.update(i*.01, .23), .23)
        self.assertEqual(f.update(3, 2), 2)
        self.assertEqual(f.update(1, -1), -1)
        f.reset()
        self.assertEqual(f.update(1, 5), 5)

    def test_noise_reduction_and_step_delay(self):
        rng=random.Random(4716)
        f=VoltageKalman(NOISE_VARIANCES[0])
        noisy=[.23+rng.gauss(0,.014) for _ in range(1000)]
        filtered=[f.update(i*.01,v) for i,v in enumerate(noisy)]
        self.assertLess(statistics.stdev(filtered[100:]),statistics.stdev(noisy[100:])*.3)
        f.reset()
        for i in range(200): f.update(i*.01,0)
        response=[f.update(2+i*.01,1) for i in range(100)]
        self.assertLessEqual(next(i*.01 for i,v in enumerate(response) if v>=.9),.4)
        self.assertTrue(all(0<=v<=1 for v in response))

    def test_finite_inputs_and_variable_cadence(self):
        with self.assertRaises(ValueError): VoltageKalman(0)
        f=VoltageKalman(.01)
        with self.assertRaises(ValueError): f.update(0,float('nan'))
        f.update(0,0)
        for t in (.01,.025,.03,.08,.14):
            self.assertTrue(math.isfinite(f.update(t,.1)))
        self.assertGreater(f.variance,0)

class TrainingTests(unittest.TestCase):
    def stable_rows(self, scale=1):
        rng=random.Random(123)
        return [(i/100,.2+rng.gauss(0,.01*scale),.01+rng.gauss(0,.002*scale)) for i in range(1001)]

    def test_training_changes_gain_and_uses_holdout(self):
        from denoising import train_stable_filter, voltage_filters
        low=train_stable_filter(self.stable_rows())
        high=train_stable_filter(self.stable_rows(3))
        self.assertAlmostEqual(high['channels'][0]['measurement_variance']/low['channels'][0]['measurement_variance'],9)
        self.assertEqual(high['channels'][0]['process_variance_per_second'],low['channels'][0]['process_variance_per_second'])
        self.assertGreater(high['channels'][0]['nominal_t90_s'],low['channels'][0]['nominal_t90_s'])
        self.assertLess(low['channels'][0]['validation_filtered_std_v'],low['channels'][0]['validation_raw_std_v'])
        self.assertEqual(len(voltage_filters(low)),2)

    def test_reject_drift_step_saturation_and_gaps(self):
        from denoising import train_stable_filter
        stable=self.stable_rows()
        bad=[[(t,f+t*.1,d) for t,f,d in stable],
             [(t,f+(1 if t>5 else 0),d) for t,f,d in stable],
             [(t,5,d) for t,f,d in stable],
             [(t,f,d) for t,f,d in stable if not 3<t<4]]
        for rows in bad:
            with self.assertRaises(ValueError): train_stable_filter(rows)

    def test_constant_capture_has_positive_variance_floor(self):
        from denoising import train_stable_filter
        p=train_stable_filter([(i/100, .1, .2) for i in range(1001)])
        self.assertGreater(p['channels'][0]['measurement_variance'],0)

    def test_large_periodic_interference_rejected_without_saturation(self):
        from denoising import train_stable_filter
        rows=[(i/137, .1, -2+2*math.sin(2*math.pi*50*i/137)) for i in range(1371)]
        with self.assertRaisesRegex(ValueError,'fluctuación excesiva'):
            train_stable_filter(rows)

    def test_negative_stable_level_is_valid(self):
        from denoising import train_stable_filter
        rows=[(t,f,d-3) for t,f,d in self.stable_rows()]
        self.assertEqual(len(train_stable_filter(rows)['channels']),2)

    def test_stronger_smoothing_reduces_variation(self):
        from denoising import voltage_filters
        rng=random.Random(42)
        values=[rng.gauss(0,1) for _ in range(3000)]
        deviations=[]
        for level in ('Normal','Alto','Muy alto'):
            f=voltage_filters(strength=level)[0]
            clean=[f.update(i/100,v) for i,v in enumerate(values)]
            deviations.append(statistics.stdev(clean[1000:]))
        self.assertGreater(deviations[0],deviations[1])
        self.assertGreater(deviations[1],deviations[2])
