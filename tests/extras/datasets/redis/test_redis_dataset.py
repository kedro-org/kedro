# Copyright (c) 2016 - present
# QuantumBlack Visual Analytics Ltd (a McKinsey company).
# All rights reserved.
#
# This software framework contains the confidential and proprietary information
# of QuantumBlack, its affiliates, and its licensors. Your use of these
"""Tests ``PickleDataSet``."""

import pickle

import numpy as np
import pandas as pd
import pytest
import redis

from kedro.extras.datasets.redis import PickleDataSet


@pytest.fixture
def dummy_object():
    """Test data for saving."""
    return pd.DataFrame(np.random.random((3, 3)), columns=["a", "b", "c"])


@pytest.fixture
def serialized_dummy_object(dummy_object):
    """Serialize test data."""
    return pickle.dumps(dummy_object)


@pytest.fixture
def from_url_args():
    return {"arg1": "1", "arg2": "2", "url": "redis://127.0.0.1:6379"}


@pytest.fixture
def save_args():
    return {"arg_1": "_1", "arg_2": "_2"}


def test_save_load_redis(
    dummy_object,
    serialized_dummy_object,
    mocker,
    from_url_args,
    save_args,
    redis_key: str = "redis_key",
):
    """Test save and load works as expected."""
    set_mocker = mocker.patch("redis.StrictRedis.set")
    from_url_mocker = mocker.patch(
        "redis.StrictRedis.from_url", return_value=redis.Redis.from_url("redis://")
    )
    get_mocker = mocker.patch(
        "redis.StrictRedis.get", return_value=serialized_dummy_object
    )
    io = PickleDataSet(redis_key, from_url_args, save_args)
    io.save(dummy_object)
    loaded_dummy_object = io.load()
    from_url_mocker.assert_called_once_with(**from_url_args)
    set_mocker.assert_called_once_with(redis_key, serialized_dummy_object, **save_args)
    get_mocker.assert_called_once_with(redis_key)
    pd.testing.assert_frame_equal(
        dummy_object,
        loaded_dummy_object,
    )
