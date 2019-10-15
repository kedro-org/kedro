import pytest
from moto import mock_s3
import matplotlib.pyplot as plt

from kedro.contrib.io.matplotlib.matplotlib_s3_writer import MatplotlibWriterS3

BUCKET_NAME = "test_bucket"
AWS_CREDENTIALS = dict(
    aws_access_key_id="FAKE_ACCESS_KEY", aws_secret_access_key="FAKE_SECRET_KEY"
)

import boto3


import io


class MockMatplotlibWriterS3(MatplotlibWriterS3):
    """Exact copy of _save_to_s3 method with decorator"""

    @mock_s3
    def _save_to_s3(self, key_name, plot):

        conn = boto3.resource("s3", region_name="us-east-1")
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
        yield boto3.client("s3", region_name="us-east-1")


def test_single_save(s3, tmp_path):

    single_plot_writer = MockMatplotlibWriterS3(
        bucket="test_bucket", filepath="matplotlib_single_plot.png"
    )

    plt.plot([1, 2, 3], [4, 5, 6])
    single_plot_writer.save(plt)

    expected_path = tmp_path / "test.png"
    actual_filepath = tmp_path / "whatever.png"

    plt.savefig(actual_filepath)
    s3.download_file("test_bucket", "matplotlib_single_plot.png", str(expected_path))

    assert actual_filepath.read_bytes() == expected_path.read_bytes()
