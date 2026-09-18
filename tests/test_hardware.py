import copy
import unittest
from app import DEFAULT_CONFIG
from hardware import validate_hardware, validate_channels, LEGACY_AGND

class HardwareTests(unittest.TestCase):
    def test_profile_maps_two_original_sensors(self):
        config=copy.deepcopy(DEFAULT_CONFIG); validate_hardware(config)
        self.assertEqual((config['force_channel'],config['deformation_channel']),(0,2))
        self.assertEqual(config['pinout']['legacy_force_low'],20)
        self.assertEqual(config['pinout']['legacy_deformation_low'],21)

    def test_bad_pairs_cannot_connect(self):
        for pair in [(0,0),(1,2),(0,15),(-2,2),(0,16)]:
            with self.assertRaises(ValueError): validate_channels(*pair)
        for key,value in [('usb_force_minus',2),('legacy_force_high',9),('legacy_deformation_low',20)]:
            config=copy.deepcopy(DEFAULT_CONFIG); config['pinout'][key]=value
            with self.assertRaises(ValueError): validate_hardware(config)

    def test_range_and_channel_inconsistency_rejected(self):
        for key,value in [('input_range','V_Neg10To10'),('input_mode','SingleEnded'),('force_channel',4)]:
            config=copy.deepcopy(DEFAULT_CONFIG); config[key]=value
            with self.assertRaises(ValueError):validate_hardware(config)
        self.assertEqual(LEGACY_AGND,(9,10,19,28,29))

if __name__=='__main__':unittest.main()
