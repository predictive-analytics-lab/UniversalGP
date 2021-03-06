"""Dataset with sensitive attribute from numpy files"""
from pathlib import Path

import numpy as np
import tensorflow as tf

from .definition import Dataset, to_tf_dataset, DATA

tf.compat.v1.app.flags.DEFINE_string('dataset_path', '',
                                     'Path to the numpy file that contains the data')
tf.compat.v1.app.flags.DEFINE_boolean('dataset_standardize', False,
                                      'If True, the inputs of the dataset are standardized')


def sensitive_from_numpy(flags):
    """Load all data from `dataset_path` and then construct a dataset

    You must specify a path to a numpy file in the flag `dataset_dir`. This file must contain the
    following numpy arrays: 'xtrain', 'ytrain', 'strain', 'xtest', 'ytest', 'stest'.
    """
    # Load data from `dataset_path`
    raw_data = np.load(Path(flags['dataset_path']))

    # Normalize input and create DATA tuples for easier handling
    input_normalizer = _get_normalizer(raw_data['xtrain'], flags['dataset_standardize'])
    train = DATA(x=input_normalizer(raw_data['xtrain']), y=raw_data['ytrain'], s=raw_data['strain'])
    test = DATA(x=input_normalizer(raw_data['xtest']), y=raw_data['ytest'], s=raw_data['stest'])

    # Construct the inducing inputs from the separated data
    inducing_inputs = _inducing_inputs(flags['num_inducing'], train, flags.get('s_as_input', False))

    return Dataset(
        train=to_tf_dataset(train.x, train.y, train.s),
        test=to_tf_dataset(test.x, test.y, test.s),
        input_dim=inducing_inputs.shape[1],
        # xtrain=train.x,
        # ytrain=train.y,
        # strain=train.s,
        xtest=test.x,  # needed for making predictions
        ytest=test.y,
        stest=test.s,
        num_train=train.x.shape[0],
        inducing_inputs=inducing_inputs,
        output_dim=train.y.shape[1],
        lik="LikelihoodLogistic",
        metric=["logistic_accuracy", "pred_rate_y1_s0", "pred_rate_y1_s1", "base_rate_y1_s0",
                "base_rate_y1_s1", "pred_odds_yhaty0_s0", "pred_odds_yhaty0_s1",
                "pred_odds_yhaty1_s0", "pred_odds_yhaty1_s1"],
    )


def _inducing_inputs(max_num_inducing, train, s_as_input):
    """Construct inducing inputs

    This could be done more cleverly with k means

    Args:
        train: the training data
        s_as_input: whether or not the sensitive attribute is part of the input

    Returns:
        inducing inputs
    """
    num_train = train.x.shape[0]
    num_inducing = min(num_train, max_num_inducing)
    if s_as_input:
        return np.concatenate((train.x[::num_train // num_inducing],
                               train.s[::num_train // num_inducing]), -1)
    return train.x[::num_train // num_inducing]


def _get_normalizer(base, do_standardize):
    """Construct normalizer to prevent Cholesky problems"""
    if do_standardize:
        mean, std = np.mean(base, axis=0), np.std(base, axis=0)
        std[std < 1e-7] = 1.

        def _standardizer(unstandardized):
            return (unstandardized - mean) / std
        return _standardizer
    elif base.min() == 0 and base.max() > 10:
        max_per_feature = np.amax(base, axis=0)

        def _normalizer(unnormalized):
            return np.where(max_per_feature > 1e-7, unnormalized / max_per_feature, unnormalized)
        return _normalizer

    def _do_nothing(inp):
        return inp
    return _do_nothing
