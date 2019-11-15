"""tests for vak.config.prep module"""
import os
import unittest
from configparser import ConfigParser
import tempfile
import shutil

import vak.config.prep
import vak.utils

HERE = os.path.dirname(__file__)
TEST_DATA_DIR = os.path.join(HERE, '..', '..', 'test_data')
TEST_CONFIGS_DIR = os.path.join(TEST_DATA_DIR, 'configs')


class TestParseDataConfig(unittest.TestCase):
    def setUp(self):
        self.config_file = os.path.join(TEST_DATA_DIR, 'configs', 'test_learncurve_config.ini')
        self.config_obj = ConfigParser()
        self.config_obj.read(self.config_file)

        self.tmp_data_dir = tempfile.mkdtemp()
        self.config_obj['PREP']['data_dir'] = self.tmp_data_dir

    def tearDown(self):
        shutil.rmtree(self.tmp_data_dir)

    def test_parse_prep_config_returns_DataConfig_instance(self):
        prep_config_obj = vak.config.prep.parse_prep_config(self.config_obj, self.config_file)
        self.assertTrue(type(prep_config_obj) == vak.config.prep.PrepConfig)

    def test_str_labelset(self):
        prep_config_obj = vak.config.prep.parse_prep_config(self.config_obj, self.config_file)
        self.assertEqual(
            prep_config_obj.labelset, list(self.config_obj['PREP']['labelset'])
        )

    def test_rangestr_labelset(self):
        a_rangestr = '1-9, 12'
        self.config_obj['PREP']['labelset'] = a_rangestr
        prep_config_obj = vak.config.prep.parse_prep_config(self.config_obj, self.config_file)
        self.assertEqual(
            prep_config_obj.labelset, vak.utils.data.range_str(a_rangestr)
        )

    def test_int_labelset(self):
        int_labels = '01234567'
        self.config_obj['PREP']['labelset'] = int_labels
        prep_config_obj = vak.config.prep.parse_prep_config(self.config_obj, self.config_file)
        self.assertEqual(
            prep_config_obj.labelset, list(int_labels)
        )

    def test_output_dir_default(self):
        # test that output_dir is added
        # and set to None if we don't specify it
        if self.config_obj.has_option('PREP', 'output_dir'):
            self.config_obj.remove_option('PREP', 'output_dir')
        prep_config_obj = vak.config.prep.parse_prep_config(self.config_obj, self.config_file)
        self.assertTrue(prep_config_obj.output_dir is None)

    def test_both_audio_and_spect_format_raises(self):
        # learncurve_config already has 'audio_format', if we
        # also add spect_format, should raise an error
        self.config_obj['PREP']['spect_format'] = 'mat'
        with self.assertRaises(ValueError):
            vak.config.prep.parse_prep_config(self.config_obj, self.config_file)

    def test_neither_audio_nor_spect_format_raises(self):
        # if we remove audio_format option, then neither that or
        # spect_format is specified, should raise an error
        self.config_obj.remove_option('PREP','audio_format')
        with self.assertRaises(ValueError):
            vak.config.prep.parse_prep_config(self.config_obj, self.config_file)

    def test_data_dir_default(self):
        # test that data_dir set to None if we don't specify it
        self.config_obj.remove_option('PREP', 'data_dir')
        prep_config_obj = vak.config.prep.parse_prep_config(self.config_obj, self.config_file)
        self.assertTrue(prep_config_obj.data_dir is None)

    def test_nonexistent_data_dir_raises_error(self):
        # test that mate_spect_files_path is added
        # and set to None if we don't specify it
        self.config_obj['PREP']['data_dir'] = 'theres/no/way/this/is/a/dir'
        with self.assertRaises(NotADirectoryError):
            vak.config.prep.parse_prep_config(self.config_obj, self.config_file)


if __name__ == '__main__':
    unittest.main()