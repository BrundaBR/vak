from collections import defaultdict
from pathlib import Path
from pprint import pprint
import re
import shutil

import numpy as np
import pandas as pd

from vak import split
from vak.datasets.window_dataset import WindowDataset
from vak.logging import log_or_print


# pattern used by path.glob to find all training data subset csvs within previous_run_path
CSV_GLOB = '**/*prep*csv'
# pattern used by re to get training subset duration
TRAIN_DUR_PAT = r'train_dur_(\d+\.\d+|\d+)s'


def from_dir(previous_run_path,
             train_set_durs,
             timebin_dur,
             num_replicates,
             results_path,
             window_size,
             spect_key,
             timebins_key,
             labelmap,
             logger=None):
    """return a ``dict`` mapping training dataset durations to dataset csv paths
    from a previous run of `vak.core.learncurve.learning_curve`.

    Recovers the previous subsets of the total training set, so that
    they can be used to re-run a different experiment on the same subsets for comparison.

    Parameters
    ----------
    previous_run_path : str, Path
        path to directory containing dataset .csv files
        that represent subsets of training set, created by
        a previous run of ``vak.core.learncurve.learning_curve``.
        Typically directory will have a name like ``results_{timestamp}``
        and the actual .csv splits will be in sub-directories with names
        corresponding to the training set duration
    train_set_durs : list
        of int, durations in seconds of subsets taken from training data
        to create a learning curve, e.g. [5, 10, 15, 20].
    timebin_dur : float
        duration of timebins in spectrograms
    num_replicates : int
        number of times to replicate training for each training set duration
        to better estimate metrics for a training set of that size.
        Each replicate uses a different randomly drawn subset of the training
        data (but of the same duration).
    results_path : str, pathlib.Path
        Directory where results will be saved, including
        files representing subsets of training data that this function makes.
        Path derived from the ``root_results_dir`` argument
         to ``vak.core.learncurve.learning_curve``, unless specified by user.
    window_size : int
        size of windows taken from spectrograms, in number of time bins,
        shonw to neural networks
    spect_key : str
        key for accessing spectrogram in files. Default is 's'.
    timebins_key : str
        key for accessing vector of time bins in files. Default is 't'.
    labelmap : dict
        that maps labelset to consecutive integers

    Other Parameters
    ----------------
    logger : logging.Logger
        instance created by ``vak.logging.get_logger``. Default is None.

    Returns
    -------
    train_dur_csv_paths : dict
        where keys are duration in seconds of subsets taken from training data,
        and corresponding values are lists of paths to .csv files containing
        those subsets

    Notes
    -----
    ``train_set_durs`` and ``num_replicates`` are used to verify that
    the correct number of training data subsets are found for each specified
    duration, i.e., that the new experiment will correctly use
    all datasets from a previous run
    """
    previous_run_path = Path(previous_run_path)
    csv_paths = sorted(previous_run_path.glob(CSV_GLOB))

    train_dur_csv_paths = defaultdict(list)
    for train_subset_path in csv_paths:
        train_dur = re.findall(TRAIN_DUR_PAT, train_subset_path.name)
        if len(train_dur) != 1:
            raise ValueError(
                f'did not find just a single training subset duration in filename:\n'
                f'{train_subset_path}\n'
                f'Instead found: {train_dur}'
            )
        train_dur = int(train_dur[0])
        train_dur_csv_paths[train_dur].append(train_subset_path)

    found_train_set_durs = sorted(train_dur_csv_paths.keys())
    if not found_train_set_durs == sorted(train_set_durs):
        raise ValueError(
            f'training set durations found in {previous_run_path} did not match '
            f'specified training set durations.\n'
            f'Specified: {sorted(train_set_durs)}\n'
            f'Found: {found_train_set_durs}'
        )

    if not all(
            [len(csv_paths) == num_replicates
             for csv_paths in train_dur_csv_paths.values()]
    ):
        raise ValueError(
            'did not find correct number of replicates for all training set durations.'
            f'Found the following:\n{pprint(train_dur_csv_paths, indent=4)}'
        )

    log_or_print(
        f'Using the following training subsets from previous run path:\n'
        f'{pprint(train_dur_csv_paths, indent=4)}',
        logger=logger, level='info'
    )

    # need to copy .csv files, and change path in train_dur_csv_paths to point to copies
    # so that `vak.train` doesn't try to write over existing results dir, causing a crash
    for train_dur in train_dur_csv_paths.keys():  # use keys so we can modify dict inside loop
        results_path_this_train_dur = results_path.joinpath(f'train_dur_{train_dur}s')
        results_path_this_train_dur.mkdir()
        csv_paths = train_dur_csv_paths[train_dur]
        new_csv_paths = []
        for replicate_num, csv_path in zip(range(1, len(csv_paths) + 1), csv_paths):
            results_path_this_replicate = results_path_this_train_dur.joinpath(f'replicate_{replicate_num}')
            results_path_this_replicate.mkdir()
            # copy csv using Path.rename() method, append returned new path to list
            new_csv_paths.append(
                shutil.copy(src=csv_path,
                            dst=results_path_this_replicate.joinpath(csv_path.name))
            )

            subset_df = pd.read_csv(csv_path)
            # ---- use *just* train subset to get spect vectors for WindowDataset
            (spect_id_vector,
             spect_inds_vector,
             x_inds) = WindowDataset.spect_vectors_from_df(subset_df,
                                                           window_size,
                                                           spect_key,
                                                           timebins_key,
                                                           crop_dur=train_dur,
                                                           timebin_dur=timebin_dur,
                                                           labelmap=labelmap)
            for vec_name, vec in zip(['spect_id_vector', 'spect_inds_vector', 'x_inds'],
                                     [spect_id_vector, spect_inds_vector, x_inds]):
                np.save(results_path_this_replicate.joinpath(f'{vec_name}.npy'),
                        vec)

            # also need to copy the spect_id_vectors, etc. used with WindowDataset
            for vec_name in ('spect_id_vector', 'spect_inds_vector', 'x_inds'):
                src_vec_path = csv_path.parent.joinpath(f'{vec_name}.npy')
                shutil.copy(
                    src=src_vec_path,
                    dst=results_path_this_replicate.joinpath(src_vec_path.name)
                )

        train_dur_csv_paths[train_dur] = new_csv_paths

    return train_dur_csv_paths


def from_df(dataset_df,
            csv_path,
            train_set_durs,
            timebin_dur,
            num_replicates,
            results_path,
            labelset,
            window_size,
            spect_key,
            timebins_key,
            labelmap,
            logger=None):
    """return a ``dict`` mapping training dataset durations to dataset csv paths.

    csv paths representing subsets of the training data are generated using ``vak.split``.

    Parameters
    ----------
    dataset_df : pandas.DataFrame
        representing an entire dataset of vocalizations.
    csv_path : str
        path to where dataset was saved as a csv.
    train_set_durs : list
        of int, durations in seconds of subsets taken from training data
        to create a learning curve, e.g. [5, 10, 15, 20].
    timebin_dur : float
        duration of timebins in spectrograms
    num_replicates : int
        number of times to replicate training for each training set duration
        to better estimate metrics for a training set of that size.
        Each replicate uses a different randomly drawn subset of the training
        data (but of the same duration).
    results_path : str, pathlib.Path
        Directory where results will be saved, including
        files representing subsets of training data that this function makes.
        Path derived from the ``root_results_dir`` argument
         to ``vak.core.learncurve.learning_curve``, unless specified by user.
    labelset : set
        of str or int, the set of labels that correspond to annotated segments
        that a network should learn to segment and classify. Note that if there
        are segments that are not annotated, e.g. silent gaps between songbird
        syllables, then `vak` will assign a dummy label to those segments
        -- you don't have to give them a label here.
    window_size : int
        size of windows taken from spectrograms, in number of time bins,
        shonw to neural networks
    spect_key : str
        key for accessing spectrogram in files. Default is 's'.
    timebins_key : str
        key for accessing vector of time bins in files. Default is 't'.
    labelmap : dict
        that maps labelset to consecutive integers

    Other Parameters
    ----------------
    logger : logging.Logger
        instance created by ``vak.logging.get_logger``. Default is None.

    Returns
    -------
    train_dur_csv_paths : dict
        where keys are duration in seconds of subsets taken from training data,
        and corresponding values are lists of paths to .csv files containing
        those subsets
    """
    train_dur_csv_paths = defaultdict(list)
    for train_dur in train_set_durs:
        log_or_print(f'subsetting training set for training set of duration: {train_dur}',
                     logger=logger, level='info')
        results_path_this_train_dur = results_path.joinpath(f'train_dur_{train_dur}s')
        results_path_this_train_dur.mkdir()
        for replicate_num in range(1, num_replicates + 1):
            results_path_this_replicate = results_path_this_train_dur.joinpath(f'replicate_{replicate_num}')
            results_path_this_replicate.mkdir()
            # get just train split, to pass to split.dataframe
            # so we don't end up with other splits in the training set
            train_df = dataset_df[dataset_df['split'] == 'train']
            subset_df = split.dataframe(train_df, train_dur=train_dur, labelset=labelset)
            subset_df = subset_df[subset_df['split'] == 'train']  # remove rows where split was set to 'None'
            # ---- use *just* train subset to get spect vectors for WindowDataset
            (spect_id_vector,
             spect_inds_vector,
             x_inds) = WindowDataset.spect_vectors_from_df(subset_df,
                                                           window_size,
                                                           spect_key,
                                                           timebins_key,
                                                           crop_dur=train_dur,
                                                           timebin_dur=timebin_dur,
                                                           labelmap=labelmap)
            for vec_name, vec in zip(['spect_id_vector', 'spect_inds_vector', 'x_inds'],
                                     [spect_id_vector, spect_inds_vector, x_inds]):
                np.save(results_path_this_replicate.joinpath(f'{vec_name}.npy'),
                        vec)
            # keep the same validation and test set by concatenating them with the train subset
            subset_df = pd.concat(
                (subset_df,
                 dataset_df[dataset_df['split'] == 'val'],
                 dataset_df[dataset_df['split'] == 'test'],
                 )
            )

            subset_csv_name = f'{csv_path.stem}_train_dur_{train_dur}s_replicate_{replicate_num}.csv'
            subset_csv_path = results_path_this_replicate.joinpath(subset_csv_name)
            subset_df.to_csv(subset_csv_path)
            train_dur_csv_paths[train_dur].append(subset_csv_path)

    return train_dur_csv_paths
