import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from kedro.extras.datasets.pandas import AppendableExcelDataSet, ExcelDataSet
from kedro.io import DataSetError


@pytest.fixture
def filepath(tmp_path):
    return (tmp_path / "test.xlsx").as_posix()


@pytest.fixture(scope="module")
def dummy_dataframe():
    return pd.DataFrame({"col1": [7, 8], "col2": [5, 8]})


def setup_excel_dataset(path):
    excel_dataset = ExcelDataSet(path)
    df = pd.DataFrame({"col1": [1, 2]})
    excel_dataset.save(df)
    return excel_dataset, df


@pytest.fixture
def appendable_excel_dataset(filepath, save_args, load_args):
    return AppendableExcelDataSet(
        filepath=filepath, load_args=load_args, save_args=save_args
    )


class TestAppendableExcelDataSet:
    def test_save_and_load(self, dummy_dataframe, filepath):
        """Test saving and reloading the data set."""
        excel_dataset, excel_df = setup_excel_dataset(filepath)
        appendable_excel_dataset = AppendableExcelDataSet(
            filepath=filepath,
            load_args={"sheet_name": "test"},
            save_args={"sheet_name": "test"},
        )
        appendable_excel_dataset.save(dummy_dataframe)
        reloaded = appendable_excel_dataset.load()
        assert_frame_equal(dummy_dataframe, reloaded)

        reloaded_first_sheet = excel_dataset.load()
        assert_frame_equal(reloaded_first_sheet, excel_df)

        assert appendable_excel_dataset._save_args == {
            "index": False,
            "sheet_name": "test",
        }
        assert appendable_excel_dataset._load_args == {
            "engine": "openpyxl",
            "sheet_name": "test",
        }
        assert appendable_excel_dataset._writer_args == {
            "engine": "openpyxl",
            "mode": "a",
        }

    def test_exists(self, filepath):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        appendable_excel_dataset = AppendableExcelDataSet(filepath)
        assert not appendable_excel_dataset.exists()
        setup_excel_dataset(filepath)
        assert appendable_excel_dataset.exists()

    @pytest.mark.parametrize(
        "load_args", [{"k1": "v1", "engine": "value"}], indirect=True
    )
    def test_load_extra_params(self, appendable_excel_dataset, load_args):
        """Test overriding the default load arguments."""
        for key, value in load_args.items():
            assert appendable_excel_dataset._load_args[key] == value

    @pytest.mark.parametrize(
        "save_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_save_extra_params(self, appendable_excel_dataset, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert appendable_excel_dataset._save_args[key] == value

    @pytest.mark.parametrize(
        "save_args", [{"writer": {"mode": "write", "engine": "test"}}], indirect=True
    )
    def test_writer_args(
        self, appendable_excel_dataset, save_args
    ):  # pylint: disable=unused-argument
        """Test overriding the default writer arguments except mode."""
        assert appendable_excel_dataset._writer_args == {"engine": "test", "mode": "a"}

    def test_load_missing_file(self, appendable_excel_dataset):
        """Check the error when trying to load missing file."""
        pattern = (
            r"Failed while loading data from data set AppendableExcelDataSet\(.*\)"
        )
        with pytest.raises(DataSetError, match=pattern):
            appendable_excel_dataset.load()

    def test_appending_to_non_existing_file(
        self, appendable_excel_dataset, dummy_dataframe
    ):
        pattern = (
            rf"`{appendable_excel_dataset._filepath}` Excel file not found\. "
            rf"The file cannot be opened in append mode\."
        )
        with pytest.raises(DataSetError, match=pattern):
            appendable_excel_dataset.save(dummy_dataframe)

    def test_str_repr(self, appendable_excel_dataset):
        """Test that meta data is in string representation of the class instance."""

        assert str(appendable_excel_dataset._filepath) in str(appendable_excel_dataset)
        assert "version" not in str(appendable_excel_dataset)
        assert "writer_args" in str(appendable_excel_dataset)
        assert "save_args={" in str(appendable_excel_dataset)
        assert "load_args={" in str(appendable_excel_dataset)

    def test_load_args_passed_in_read_excel(self, appendable_excel_dataset, mocker):
        read_excel_mock = mocker.patch("pandas.read_excel")
        appendable_excel_dataset.load()
        assert appendable_excel_dataset._load_args
        read_excel_mock.assert_called_once_with(
            str(appendable_excel_dataset._filepath),
            **appendable_excel_dataset._load_args,
        )

    def test_save_args_passed_in_to_excel_and_writer(
        self, appendable_excel_dataset, dummy_dataframe, mocker
    ):
        to_excel_mock = mocker.patch.object(dummy_dataframe, "to_excel")
        writer_mock = mocker.patch("pandas.ExcelWriter")

        appendable_excel_dataset.save(dummy_dataframe)
        assert appendable_excel_dataset._writer_args
        writer_mock.assert_called_once_with(
            str(appendable_excel_dataset._filepath),
            **appendable_excel_dataset._writer_args,
        )

        assert appendable_excel_dataset._save_args
        to_excel_mock.assert_called_once_with(
            writer_mock.return_value.__enter__.return_value,
            **appendable_excel_dataset._save_args,
        )
