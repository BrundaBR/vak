"""fixtures relating to .toml configuration files"""
import json
import shutil

import pytest
import toml


@pytest.fixture
def test_configs_root(test_data_root):
    """Path that points to test_data/configs

    Two types of config files in this directory:
    1) those used by the src/scripts/test_data/test_data_generate.py script.
       All configs that start with ``test_`` prefix.
    2) those used by tests that are static, e.g., ``invalid_section_config.toml``

    This fixture facilitates access to type (2), e.g. in test_config/test_parse
    """
    return test_data_root.joinpath('configs')


@pytest.fixture
def list_of_schematized_configs(test_configs_root):
    """returns list of configuration files,
    schematized with attributes
    so that fixtures and unit tests can specify those attributes
    to find the filename of a specific configuration file,
    that can then be used to get that file.

    Each element in the list is a dict with the following keys:
    `filename`, `config_type`, `audio_format`, `spect_format`, `annot_format`
    These keys define the schema for config files.

    For example, here is the first one:
    {
      "filename": "test_eval_audio_cbin_annot_notmat.toml",
      "config_type": "eval",
      "audio_format": "cbin",
      "spect_format": null,
      "annot_format": "notmat"
    }

    The ``specific_config`` factory fixture returns a function that
    itself return a configuration ``filename``, when provided values for
    all of the other keys.
    """
    with test_configs_root.joinpath('configs.json').open('r') as fp:
        return json.load(fp)['configs']


@pytest.fixture
def invalid_section_config_path(test_configs_root):
    return test_configs_root.joinpath('invalid_section_config.toml')


@pytest.fixture
def invalid_option_config_path(test_configs_root):
    return test_configs_root.joinpath('invalid_option_config.toml')


@pytest.fixture
def generated_test_configs_root(generated_test_data_root):
    return generated_test_data_root.joinpath('configs')


# ---- path to config files ----
@pytest.fixture
def all_generated_configs(generated_test_configs_root):
    return sorted(generated_test_configs_root.glob('test*toml'))


@pytest.fixture
def specific_config(generated_test_configs_root,
                    list_of_schematized_configs,
                    tmp_path):
    """returns a factory function
    that will return the path
    to a specific configuration file, determined by
    characteristics specified by the caller:
    `config_type`, `audio_format`, `spect_format`, `annot_format`

    The factory function actually returns a copy,
    that will be copied into ``tmp_path``,
    so the original remains umodified.

    If ``root_results_dir`` argument is specified
    when calling the factory function,
    it will convert the value for that option in the section
    corresponding to ``config_type`` to the value
    specified for ``root_results_dir``.
    This makes it possible to dynamically change the ``root_results_dir``
    e.g. to the ``tmp_path`` fixture used by unit tests
    """
    def _specific_config(config_type,
                         annot_format,
                         audio_format=None,
                         spect_format=None,
                         options_to_change=None
                         ):
        """returns path to a specific configuration file,
        determined by characteristics specified by the caller:
        `config_type`, `audio_format`, `spect_format`, `annot_format`

        Parameters
        ----------
        config_type : str
            corresponding to a `vak` cli command
        annot_format : str
            annotation format, recognized by ``crowsetta``
        audio_format : str
        spect_format : str
        options_to_change : list, dict
            list of dicts with keys 'section', 'option', and 'value'.
            Can be a single dict, in which case only that option is changed.

        Returns
        -------
        config_path : pathlib.Path
            that points to temporary copy of specified config,
            with any options changed as specified
        """
        original_config_path = None

        for schematized_config in list_of_schematized_configs:
            if all(
                [
                    schematized_config['config_type'] == config_type,
                    schematized_config['annot_format'] == annot_format,
                    schematized_config['audio_format'] == audio_format,
                    schematized_config['spect_format'] == spect_format,
                ]
            ):
                original_config_path = generated_test_configs_root.joinpath(schematized_config['filename'])

        if original_config_path is None:
            raise ValueError(
                f"did not find a specific config with `config_type`='{config_type}', "
                f"`annot_format`='{annot_format}', `audio_format`='{audio_format}', "
                f"and `config_type`='{spect_format}', "
            )
        config_copy_path = tmp_path.joinpath(original_config_path.name)
        config_copy_path = shutil.copy(src=original_config_path,
                                       dst=config_copy_path)

        if options_to_change is not None:
            if isinstance(options_to_change, dict):
                options_to_change = [options_to_change]
            elif isinstance(options_to_change, list):
                pass
            else:
                raise TypeError(f'invalid type for `options_to_change`: {type(options_to_change)}')

            with config_copy_path.open('r') as fp:
                config_toml = toml.load(fp)

            for opt_dict in options_to_change:
                config_toml[opt_dict['section']][opt_dict['option']] = opt_dict['value']

            with config_copy_path.open('w') as fp:
                toml.dump(config_toml, fp)

        return config_copy_path

    return _specific_config


@pytest.fixture
def all_generated_train_configs(generated_test_configs_root):
    return sorted(generated_test_configs_root.glob('test_train*toml'))


@pytest.fixture
def all_generated_learncurve_configs(generated_test_configs_root):
    return sorted(generated_test_configs_root.glob('test_learncurve*toml'))


@pytest.fixture
def all_generated_eval_configs(generated_test_configs_root):
    return sorted(generated_test_configs_root.glob('test_eval*toml'))


@pytest.fixture
def all_generated_predict_configs(generated_test_configs_root):
    return sorted(generated_test_configs_root.glob('test_predict*toml'))


# ----  config toml from paths ----
def _return_toml(toml_path):
    """return config files loaded into dicts with toml library
    used to test functions that parse config sections, taking these dicts as inputs"""
    with toml_path.open('r') as fp:
        config_toml = toml.load(fp)
    return config_toml


@pytest.fixture
def specific_config_toml(specific_config):
    """returns a function that will return a dict
    containing parsed toml from a
    specific configuration file, determined by
    characteristics specified by the caller:
    `config_type`, `audio_format`, `spect_format`, `annot_format`
    """
    def _specific_config_toml(config_type,
                              annot_format,
                              audio_format=None,
                              spect_format=None,
                              ):
        config_path = specific_config(
            config_type,
            annot_format,
            audio_format,
            spect_format
        )
        return _return_toml(config_path)

    return _specific_config_toml


@pytest.fixture
def all_generated_configs_toml(all_generated_configs):
    return [_return_toml(config) for config in all_generated_configs]


@pytest.fixture
def all_generated_train_configs_toml(all_generated_train_configs):
    return [_return_toml(config) for config in all_generated_train_configs]


@pytest.fixture
def all_generated_learncurve_configs_toml(all_generated_learncurve_configs):
    return [_return_toml(config) for config in all_generated_learncurve_configs]


@pytest.fixture
def all_generated_eval_configs_toml(all_generated_eval_configs):
    return [_return_toml(config) for config in all_generated_eval_configs]


@pytest.fixture
def all_generated_predict_configs_toml(all_generated_predict_configs):
    return [_return_toml(config) for config in all_generated_predict_configs]


# ---- config toml + path pairs ----
@pytest.fixture
def all_generated_configs_toml_path_pairs(all_generated_configs):
    """zip of tuple pairs: (dict, pathlib.Path)
    where ``Path`` is path to .toml config file and ``dict`` is
    the .toml config from that path
    loaded into a dict with the ``toml`` library
    """
    return zip(
        [_return_toml(config) for config in all_generated_configs],
        all_generated_configs,
    )


@pytest.fixture
def all_generated_train_configs_toml_path_pairs(all_generated_train_configs):
    """zip of tuple pairs: (dict, pathlib.Path)
    where ``Path`` is path to .toml config file and ``dict`` is
    the .toml config from that path
    loaded into a dict with the ``toml`` library
    """
    return zip(
        [_return_toml(config) for config in all_generated_train_configs],
        all_generated_train_configs,
    )


@pytest.fixture
def all_generated_learncurve_configs_toml_path_pairs(all_generated_learncurve_configs):
    """zip of tuple pairs: (dict, pathlib.Path)
    where ``Path`` is path to .toml config file and ``dict`` is
    the .toml config from that path
    loaded into a dict with the ``toml`` library
    """
    return zip(
        [_return_toml(config) for config in all_generated_learncurve_configs],
        all_generated_learncurve_configs,
    )


@pytest.fixture
def all_generated_eval_configs_toml_path_pairs(all_generated_eval_configs):
    """zip of tuple pairs: (dict, pathlib.Path)
    where ``Path`` is path to .toml config file and ``dict`` is
    the .toml config from that path
    loaded into a dict with the ``toml`` library
    """
    return zip(
        [_return_toml(config) for config in all_generated_eval_configs],
        all_generated_eval_configs,
    )


@pytest.fixture
def all_generated_predict_configs_toml_path_pairs(all_generated_predict_configs):
    """zip of tuple pairs: (dict, pathlib.Path)
    where ``Path`` is path to .toml config file and ``dict`` is
    the .toml config from that path
    loaded into a dict with the ``toml`` library
    """
    return zip(
        [_return_toml(config) for config in all_generated_predict_configs],
        all_generated_predict_configs,
    )
