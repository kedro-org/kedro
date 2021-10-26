# Copyright 2021 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
from pathlib import PurePosixPath

import pandas as pd
import pytest
from adlfs import AzureBlobFileSystem
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from plotly import graph_objects
from plotly.graph_objs import Scatter
from s3fs.core import S3FileSystem

from kedro.extras.datasets.plotly import PlotlyDataSet
from kedro.io import DataSetError
from kedro.io.core import PROTOCOL_DELIMITER


@pytest.fixture
def filepath_json(tmp_path):
    return (tmp_path / "test.json").as_posix()


@pytest.fixture
def plotly_data_set(filepath_json, load_args, save_args, fs_args, plotly_args):
    return PlotlyDataSet(
        filepath=filepath_json,
        load_args=load_args,
        save_args=save_args,
        fs_args=fs_args,
        plotly_args=plotly_args,
    )


@pytest.fixture
def plotly_args():
    return {
        "fig": {"orientation": "h", "x": "col1", "y": "col2"},
        "layout": {"title": "Test", "xaxis_title": "x", "yaxis_title": "y"},
        "type": "scatter",
    }


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


class TestPlotlyDataSet:
    def test_save_and_load(self, plotly_data_set, dummy_dataframe):
        """Test saving and reloading the data set."""
        plotly_data_set.save(dummy_dataframe)
        reloaded = plotly_data_set.load()
        assert isinstance(reloaded, graph_objects.Figure)
        assert "Test" in str(reloaded["layout"]["title"])
        assert isinstance(reloaded["data"][0], Scatter)

    def test_exists(self, plotly_data_set, dummy_dataframe):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not plotly_data_set.exists()
        plotly_data_set.save(dummy_dataframe)
        assert plotly_data_set.exists()

    def test_load_missing_file(self, plotly_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set PlotlyDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            plotly_data_set.load()

    @pytest.mark.parametrize(
        "filepath,instance_type,credentials",
        [
            ("s3://bucket/file.json", S3FileSystem, {}),
            ("file:///tmp/test.json", LocalFileSystem, {}),
            ("/tmp/test.json", LocalFileSystem, {}),
            ("gcs://bucket/file.json", GCSFileSystem, {}),
            ("https://example.com/file.json", HTTPFileSystem, {}),
            (
                "abfs://bucket/file.csv",
                AzureBlobFileSystem,
                {"account_name": "test", "account_key": "test"},
            ),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type, credentials, plotly_args):
        data_set = PlotlyDataSet(
            filepath=filepath, credentials=credentials, plotly_args=plotly_args
        )
        assert isinstance(data_set._fs, instance_type)

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)

    def test_catalog_release(self, mocker, plotly_args):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.json"
        data_set = PlotlyDataSet(filepath=filepath, plotly_args=plotly_args)
        data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)

    def test_fail_if_invalid_plotly_args_provided(self):
        plotly_args = []
        filepath = "test.json"
        data_set = PlotlyDataSet(filepath=filepath, plotly_args=plotly_args)
        with pytest.raises(DataSetError):
            data_set.save(dummy_dataframe)
