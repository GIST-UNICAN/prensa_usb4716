import unittest
from trial_detection import detect_test_interval


class IntervalTests(unittest.TestCase):
    def rows(self, end=6):
        result=[]
        for i in range(int(end*100)+1):
            t=i/100
            force=0 if t<1 or t>4 else (t-1)*100 if t<2.5 else (4-t)*100
            result.append(dict(t=t,force_kp=force))
        return result

    def test_idle_load_and_tail(self):
        rows=self.rows(); span=detect_test_interval(rows)
        self.assertIsNotNone(span)
        self.assertGreater(rows[span['start']]['t'],.9)
        self.assertLess(rows[span['start']]['t'],1.3)
        self.assertGreater(rows[span['end']]['t'],3.8)
        self.assertLess(rows[span['end']]['t'],4.3)

    def test_active_noise_and_single_spike(self):
        self.assertIsNone(detect_test_interval([dict(t=i/100,force_kp=(-1)**i*.1) for i in range(500)]))
        rows=[dict(t=i/100,force_kp=1000 if i==200 else 0) for i in range(500)]
        self.assertIsNone(detect_test_interval(rows))
        self.assertIsNone(detect_test_interval(self.rows(2))['end'])

    def test_offset_and_negative_loading(self):
        rows=self.rows()
        for row in rows: row['force_kp']=50-row['force_kp']
        self.assertIsNotNone(detect_test_interval(rows)['end'])
