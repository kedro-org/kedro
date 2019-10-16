import pytest
import s3fs
from moto import mock_s3
import matplotlib.pyplot as plt

from kedro.contrib.io.matplotlib.matplotlib_s3_writer import MatplotlibWriterS3
from kedro.io import DataSetError

BUCKET_NAME = "test_bucket"
AWS_CREDENTIALS = dict(
    aws_access_key_id="testing", aws_secret_access_key="testing"
)
import boto3


import io


class MockMatplotlibWriterS3(MatplotlibWriterS3):
    """Exact copy of _save_to_s3 method with decorator"""

    @mock_s3
    def _save_to_s3(self, key_name, plot):

        conn = boto3.resource("s3")
        conn.create_bucket(Bucket=self._bucket)

        bytes_object = io.BytesIO()
        plot.savefig(bytes_object, **self._save_args)

        session = boto3.Session(**self._boto_session_args)

        session.client("s3", **self._s3_client_args).put_object(
            Bucket=self._bucket,
            Key=key_name,
            **self._s3_put_object_args,
            Body=bytes_object.getvalue(),
        )


import os




@pytest.fixture(scope="function")
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"



@pytest.fixture(scope="function")
def s3(aws_credentials):
    with mock_s3():
        yield boto3.client("s3")

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
def mocked_s3_bucket():
    """Create a bucket for testing using moto."""
    with mock_s3():
        conn = s3fs.core.boto3.client("s3", **AWS_CREDENTIALS)
        conn.create_bucket(Bucket=BUCKET_NAME)
        yield conn


@pytest.fixture
def mocked_s3_object(mocked_s3_bucket, mock_single_plot):
    """Create versioned test data and add it to mocked S3 bucket."""

    bytes_object = io.BytesIO()
    mock_single_plot.savefig(bytes_object)

    mocked_s3_bucket.put_object(
        Bucket=BUCKET_NAME,
        Key="matplotlib_single_plot.png",
        Body=bytes_object.getvalue(),
    )
    return mocked_s3_bucket


@pytest.fixture
def single_plot_writer():
    return MatplotlibWriterS3(
        bucket=BUCKET_NAME,
        filepath="matplotlib_single_plot.png",

    )


@pytest.mark.usefixtures("mocked_s3_object")
def test_save_data(s3, tmp_path, mock_single_plot, single_plot_writer):
    """Test saving the data to S3."""
    # single_plot_writer = MatplotlibWriterS3(
    #     bucket=BUCKET_NAME, filepath="matplotlib_single_plot.png"
    # )

    single_plot_writer.save(mock_single_plot)

    expected_path = tmp_path / "downloaded_image.png"
    actual_filepath = tmp_path / "locally_saved.png"

    plt.savefig(actual_filepath)
    s3.download_file(BUCKET_NAME, "matplotlib_single_plot.png", str(expected_path))

    assert actual_filepath.read_bytes() == expected_path.read_bytes()



# pytest tests/contrib/io/matplotlib/test_matplotlib_s3_writer.py
def test_single_save(s3, tmp_path, mock_single_plot):

    single_plot_writer = MockMatplotlibWriterS3(
        bucket=BUCKET_NAME, filepath="matplotlib_single_plot.png"
    )

    single_plot_writer.save(mock_single_plot)

    expected_path = tmp_path / "downloaded_image.png"
    actual_filepath = tmp_path / "locally_saved.png"

    plt.savefig(actual_filepath)
    s3.download_file(BUCKET_NAME, "matplotlib_single_plot.png", str(expected_path))

    assert actual_filepath.read_bytes() == expected_path.read_bytes()
#
#
# def test_list_save(s3, tmp_path, mock_list_plot):
#
#     plots_list = []
#     colour = "red"
#     for index in range(5):
#         plots_list.append(plt.figure())
#         plt.plot([1, 2, 3], [4, 5, 6], color=colour)
#
#     _filepath = "matplotlib_list"
#
#
#
#     for index in range(5):
#
#         list_plot_writer = MockMatplotlibWriterS3(
#             bucket=BUCKET_NAME, filepath=_filepath
#         )
#
#         list_plot_writer.save([plots_list[index]])
#
#         expected_path = tmp_path / "downloaded_image.png"
#         actual_filepath = tmp_path / "locally_saved.png"
#
#
#         _key_path = _filepath + "/" + str(index) + ".png"
#
#         # test = [my_bucket_object for my_bucket_object in s3.objects.all()]
#
#         test = [key['Key'] for key in s3.list_objects(Bucket=BUCKET_NAME)['Contents']]
#
#
#
#         # assert index == 1
#         assert str(test[0]) == _key_path
#
#
#         mock_list_plot[index].savefig(actual_filepath)
#         s3.download_file(BUCKET_NAME, _key_path, str(expected_path))
#
#         assert actual_filepath.read_bytes() == expected_path.read_bytes()

