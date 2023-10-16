import pytest

from kedro.io import DatasetError, LambdaDataset


@pytest.fixture
def mocked_save(mocker):
    return mocker.Mock()


@pytest.fixture
def mocked_dataset(mocked_save):
    return LambdaDataset(None, mocked_save)


def test_dataset_describe():
    """Test `describe` method invocation"""

    def _dummy_load():
        pass  # pragma: no cover

    def _dummy_save():
        pass  # pragma: no cover

    def _dummy_exists():
        return False  # pragma: no cover

    def _dummy_release():
        pass  # pragma: no cover

    assert "LambdaDataset(load=<tests.io.test_lambda_dataset._dummy_load>)" in str(
        LambdaDataset(_dummy_load, None)
    )
    assert "LambdaDataset(save=<tests.io.test_lambda_dataset._dummy_save>)" in str(
        LambdaDataset(None, _dummy_save)
    )
    assert "LambdaDataset(exists=<tests.io.test_lambda_dataset._dummy_exists>)" in str(
        LambdaDataset(None, None, _dummy_exists)
    )
    assert (
        "LambdaDataset(release=<tests.io.test_lambda_dataset._dummy_release>)"
        in str(LambdaDataset(None, None, None, _dummy_release))
    )

    # __init__ keys alphabetically sorted, None values not shown
    expected = (
        "LambdaDataset(exists=<tests.io.test_lambda_dataset._dummy_exists>, "
        "load=<tests.io.test_lambda_dataset._dummy_load>, "
        "save=<tests.io.test_lambda_dataset._dummy_save>)"
    )
    actual = str(LambdaDataset(_dummy_load, _dummy_save, _dummy_exists, None))
    assert actual == expected


class TestLambdaDatasetLoad:
    def test_load_invocation(self, mocker):
        """Test the basic `load` method invocation"""
        mocked_load = mocker.Mock(return_value=42)
        dataset = LambdaDataset(mocked_load, None)
        result = dataset.load()

        mocked_load.assert_called_once_with()
        assert result == 42

    def test_load_raises_error(self):
        """Check the error if loading the LambdaDataset raises an exception"""
        error_message = "Internal load exception message"

        def internal_load():
            raise FileNotFoundError(error_message)

        dataset = LambdaDataset(internal_load, None)
        with pytest.raises(DatasetError, match=error_message):
            dataset.load()

    def test_load_undefined(self):
        """Check the error if `LambdaDataset.__load` is None"""
        with pytest.raises(DatasetError, match="Cannot load data set"):
            LambdaDataset(None, None).load()

    def test_load_not_callable(self):
        pattern = (
            r"'load' function for LambdaDataset must be a Callable\. "
            r"Object of type 'str' provided instead\."
        )
        with pytest.raises(DatasetError, match=pattern):
            LambdaDataset("load", None)


class TestLambdaDatasetSave:
    def test_save_invocation(self, mocked_save, mocked_dataset):
        """Test the basic `save` method invocation"""
        mocked_dataset.save("foo")
        mocked_save.assert_called_once_with("foo")

    def test_save_raises_error(self, mocked_save, mocked_dataset):
        """Check the error if saving the LambdaDataset raises an exception"""
        error_message = "Cannot save to an existing file"
        mocked_save.side_effect = FileExistsError(error_message)

        pattern = (
            r"Failed while saving data to data set LambdaDataset\(.+\)\.\n"
            + error_message
        )
        with pytest.raises(DatasetError, match=pattern):
            mocked_dataset.save("data")
        mocked_save.assert_called_once_with("data")

    def test_save_undefined(self):
        """Check the error if `LambdaDataset.__save` is None"""
        with pytest.raises(DatasetError, match="Cannot save to data set"):
            LambdaDataset(None, None).save(42)

    def test_save_none(self, mocked_save, mocked_dataset):
        """Check the error when passing None to `save` call"""
        pattern = "Saving 'None' to a 'Dataset' is not allowed"
        with pytest.raises(DatasetError, match=pattern):
            mocked_dataset.save(None)
        assert mocked_save.called == 0

    def test_save_not_callable(self):
        pattern = (
            r"'save' function for LambdaDataset must be a Callable\. "
            r"Object of type 'str' provided instead\."
        )
        with pytest.raises(DatasetError, match=pattern):
            LambdaDataset(None, "save")


class TestLambdaDatasetExists:
    def test_exists_invocation(self, mocker):
        """Test the basic `exists` method invocation"""
        mocked_exists = mocker.Mock(return_value=True)
        dataset = LambdaDataset(None, None, mocked_exists)
        result = dataset.exists()
        mocked_exists.assert_called_once_with()
        assert result is True

    def test_exists_not_implemented(self):
        """Check that `exists` method returns False by default"""
        dataset = LambdaDataset(None, None)
        assert not dataset.exists()

    def test_exists_raises_error(self, mocker):
        """Check the error when `exists` raises an exception"""
        mocked_exists = mocker.Mock()
        error_message = "File not found"
        mocked_exists.side_effect = FileNotFoundError(error_message)
        dataset = LambdaDataset(None, None, mocked_exists)

        with pytest.raises(DatasetError, match=error_message):
            dataset.exists()
        mocked_exists.assert_called_once_with()

    def test_exists_not_callable(self):
        pattern = (
            r"'exists' function for LambdaDataset must be a Callable\. "
            r"Object of type 'str' provided instead\."
        )
        with pytest.raises(DatasetError, match=pattern):
            LambdaDataset(None, None, "exists")


class TestLambdaDatasetRelease:
    def test_release_invocation(self, mocker):
        """Test the basic `release` method invocation"""
        mocked_release = mocker.Mock()
        dataset = LambdaDataset(None, None, None, mocked_release)
        dataset.release()
        mocked_release.assert_called_once_with()

    def test_release_not_implemented(self):
        """Check that `release` does nothing by default"""
        dataset = LambdaDataset(None, None)
        dataset.release()

    def test_release_raises_error(self, mocker):
        """Check the error when `release` raises an exception"""
        mocked_release = mocker.Mock()
        error_message = "File not found"
        mocked_release.side_effect = FileNotFoundError(error_message)
        dataset = LambdaDataset(None, None, None, mocked_release)

        with pytest.raises(DatasetError, match=error_message):
            dataset.release()
        mocked_release.assert_called_once_with()

    def test_release_not_callable(self):
        pattern = (
            r"'release' function for LambdaDataset must be a Callable\. "
            r"Object of type 'str' provided instead\."
        )
        with pytest.raises(DatasetError, match=pattern):
            LambdaDataset(None, None, None, "release")
