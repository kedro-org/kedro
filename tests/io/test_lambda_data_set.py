# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
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
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest

from kedro.io import DataSetError, LambdaDataSet


@pytest.fixture
def mocked_save(mocker):
    return mocker.Mock()


@pytest.fixture
def mocked_data_set(mocked_save):
    return LambdaDataSet(None, mocked_save)


def test_data_set_describe():
    """Test `describe` method invocation"""

    def _dummy_load():
        pass  # pragma: no cover

    def _dummy_save():
        pass  # pragma: no cover

    def _dummy_exists():
        return False  # pragma: no cover

    def _dummy_release():
        pass  # pragma: no cover

    assert "LambdaDataSet(load=<tests.io.test_lambda_data_set._dummy_load>)" in str(
        LambdaDataSet(_dummy_load, None)
    )
    assert "LambdaDataSet(save=<tests.io.test_lambda_data_set._dummy_save>)" in str(
        LambdaDataSet(None, _dummy_save)
    )
    assert "LambdaDataSet(exists=<tests.io.test_lambda_data_set._dummy_exists>)" in str(
        LambdaDataSet(None, None, _dummy_exists)
    )
    assert (
        "LambdaDataSet(release=<tests.io.test_lambda_data_set._dummy_release>)"
        in str(LambdaDataSet(None, None, None, _dummy_release))
    )

    # __init__ keys alphabetically sorted, None values not shown
    expected = (
        "LambdaDataSet(exists=<tests.io.test_lambda_data_set._dummy_exists>, "
        "load=<tests.io.test_lambda_data_set._dummy_load>, "
        "save=<tests.io.test_lambda_data_set._dummy_save>)"
    )
    actual = str(LambdaDataSet(_dummy_load, _dummy_save, _dummy_exists, None))
    assert actual == expected


class TestLambdaDataSetLoad:
    def test_load_invocation(self, mocker):
        """Test the basic `load` method invocation"""
        mocked_load = mocker.Mock(return_value=42)
        data_set = LambdaDataSet(mocked_load, None)
        result = data_set.load()

        mocked_load.assert_called_once_with()
        assert result == 42

    def test_load_raises_error(self):
        """Check the error if loading the LambdaDataSet raises an exception"""
        error_message = "Internal load exception message"

        def internal_load():
            raise FileNotFoundError(error_message)

        data_set = LambdaDataSet(internal_load, None)
        with pytest.raises(DataSetError, match=error_message):
            data_set.load()

    def test_load_undefined(self):
        """Check the error if `LambdaDataSet.__load` is None"""
        with pytest.raises(DataSetError, match="Cannot load data set"):
            LambdaDataSet(None, None).load()

    def test_load_not_callable(self):
        pattern = (
            r"`load` function for LambdaDataSet must be a Callable\. "
            r"Object of type `str` provided instead\."
        )
        with pytest.raises(DataSetError, match=pattern):
            LambdaDataSet("load", None)


class TestLambdaDataSetSave:
    def test_save_invocation(self, mocked_save, mocked_data_set):
        """Test the basic `save` method invocation"""
        mocked_data_set.save("foo")
        mocked_save.assert_called_once_with("foo")

    def test_save_raises_error(self, mocked_save, mocked_data_set):
        """Check the error if saving the LambdaDataSet raises an exception"""
        error_message = "Cannot save to an existing file"
        mocked_save.side_effect = FileExistsError(error_message)

        pattern = (
            r"Failed while saving data to data set LambdaDataSet\(.+\)\.\n"
            + error_message
        )
        with pytest.raises(DataSetError, match=pattern):
            mocked_data_set.save("data")
        mocked_save.assert_called_once_with("data")

    def test_save_undefined(self):
        """Check the error if `LambdaDataSet.__save` is None"""
        with pytest.raises(DataSetError, match="Cannot save to data set"):
            LambdaDataSet(None, None).save(42)

    def test_save_none(self, mocked_save, mocked_data_set):
        """Check the error when passing None to `save` call"""
        pattern = "Saving `None` to a `DataSet` is not allowed"
        with pytest.raises(DataSetError, match=pattern):
            mocked_data_set.save(None)
        assert mocked_save.called == 0

    def test_save_not_callable(self):
        pattern = (
            r"`save` function for LambdaDataSet must be a Callable\. "
            r"Object of type `str` provided instead\."
        )
        with pytest.raises(DataSetError, match=pattern):
            LambdaDataSet(None, "save")


class TestLambdaDataSetExists:
    def test_exists_invocation(self, mocker):
        """Test the basic `exists` method invocation"""
        mocked_exists = mocker.Mock(return_value=True)
        data_set = LambdaDataSet(None, None, mocked_exists)
        result = data_set.exists()
        mocked_exists.assert_called_once_with()
        assert result is True

    def test_exists_not_implemented(self):
        """Check that `exists` method returns False by default"""
        data_set = LambdaDataSet(None, None)
        assert not data_set.exists()

    def test_exists_raises_error(self, mocker):
        """Check the error when `exists` raises an exception"""
        mocked_exists = mocker.Mock()
        error_message = "File not found"
        mocked_exists.side_effect = FileNotFoundError(error_message)
        data_set = LambdaDataSet(None, None, mocked_exists)

        with pytest.raises(DataSetError, match=error_message):
            data_set.exists()
        mocked_exists.assert_called_once_with()

    def test_exists_not_callable(self):
        pattern = (
            r"`exists` function for LambdaDataSet must be a Callable\. "
            r"Object of type `str` provided instead\."
        )
        with pytest.raises(DataSetError, match=pattern):
            LambdaDataSet(None, None, "exists")


class TestLambdaDataSetRelease:
    def test_release_invocation(self, mocker):
        """Test the basic `release` method invocation"""
        mocked_release = mocker.Mock()
        data_set = LambdaDataSet(None, None, None, mocked_release)
        data_set.release()
        mocked_release.assert_called_once_with()

    def test_release_not_implemented(self):
        """Check that `release` does nothing by default"""
        data_set = LambdaDataSet(None, None)
        data_set.release()

    def test_release_raises_error(self, mocker):
        """Check the error when `release` raises an exception"""
        mocked_release = mocker.Mock()
        error_message = "File not found"
        mocked_release.side_effect = FileNotFoundError(error_message)
        data_set = LambdaDataSet(None, None, None, mocked_release)

        with pytest.raises(DataSetError, match=error_message):
            data_set.release()
        mocked_release.assert_called_once_with()

    def test_release_not_callable(self):
        pattern = (
            r"`release` function for LambdaDataSet must be a Callable\. "
            r"Object of type `str` provided instead\."
        )
        with pytest.raises(DataSetError, match=pattern):
            LambdaDataSet(None, None, None, "release")
