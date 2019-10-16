import pytest
import s3fs
from moto import mock_s3
import matplotlib.pyplot as plt

from kedro.contrib.io.matplotlib.matplotlib_s3_writer import MatplotlibWriterS3
from kedro.io import DataSetError

BUCKET_NAME = "test_bucket"
AWS_CREDENTIALS = dict(aws_access_key_id="testing", aws_secret_access_key="testing")
KEY_PATH = "matplotlib"
COLOUR_LIST = ["blue", "green", "red"]


@pytest.fixture
def mock_single_plot():
    plt.plot([1, 2, 3], [4, 5, 6])
    return plt


@pytest.fixture
def mock_list_plot():
    plots_list = []
    colour = "red"
    for index in range(5):
        plots_list.append(plt.figure())
        plt.plot([1, 2, 3], [4, 5, 6], color=colour)
    return plots_list


@pytest.fixture
def mock_dict_plot():
    plots_dict = {}
    for colour in COLOUR_LIST:
        plots_dict[colour] = plt.figure()
        plt.plot([1, 2, 3], [4, 5, 6], color=colour)
        plt.close()
    return plots_dict


@pytest.fixture
def mocked_s3_bucket():
    """Create a bucket for testing using moto."""
    with mock_s3():
        conn = s3fs.core.boto3.client("s3", **AWS_CREDENTIALS)
        conn.create_bucket(Bucket=BUCKET_NAME)
        yield conn


@pytest.fixture
def single_plot_writer():
    return MatplotlibWriterS3(bucket=BUCKET_NAME, filepath=KEY_PATH)


@pytest.fixture
def iterable_plot_writer():
    return MatplotlibWriterS3(bucket=BUCKET_NAME, filepath=KEY_PATH)


def test_save_data(tmp_path, mock_single_plot, single_plot_writer, mocked_s3_bucket):
    """Test saving single matplotlib plot to S3."""
    single_plot_writer.save(mock_single_plot)

    expected_path = tmp_path / "downloaded_image.png"
    actual_filepath = tmp_path / "locally_saved.png"

    plt.savefig(actual_filepath)

    mocked_s3_bucket.download_file(BUCKET_NAME, KEY_PATH, str(expected_path))

    assert actual_filepath.read_bytes() == expected_path.read_bytes()


def test_list_save(tmp_path, mock_list_plot, iterable_plot_writer, mocked_s3_bucket):
    """Test saving list of plots to S3."""

    iterable_plot_writer.save(mock_list_plot)

    for index in range(5):

        expected_path = tmp_path / "downloaded_image.png"
        actual_filepath = tmp_path / "locally_saved.png"

        mock_list_plot[index].savefig(actual_filepath)

        _key_path = KEY_PATH + "/" + str(index) + ".png"

        mocked_s3_bucket.download_file(BUCKET_NAME, _key_path, str(expected_path))

        assert actual_filepath.read_bytes() == expected_path.read_bytes()


def test_dict_save(tmp_path, mock_dict_plot, iterable_plot_writer, mocked_s3_bucket):
    """Test saving dictionary of plots to S3."""

    iterable_plot_writer.save(mock_dict_plot)

    for colour in COLOUR_LIST:

        expected_path = tmp_path / "downloaded_image.png"
        actual_filepath = tmp_path / "locally_saved.png"

        mock_dict_plot[colour].savefig(actual_filepath)

        _key_path = KEY_PATH + "/" + colour

        mocked_s3_bucket.download_file(BUCKET_NAME, _key_path, str(expected_path))

        assert actual_filepath.read_bytes() == expected_path.read_bytes()
