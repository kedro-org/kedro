import pytest
import s3fs
from moto import mock_s3
import matplotlib.pyplot as plt

# FILENAME = "test.csv"
from kedro.contrib.io.matplotlib.matplotlib_s3_writer import MatplotlibWriterS3

BUCKET_NAME = "test_bucket"
AWS_CREDENTIALS = dict(
    aws_access_key_id="FAKE_ACCESS_KEY", aws_secret_access_key="FAKE_SECRET_KEY"
)

# @pytest.fixture
# def mocked_s3_bucket():
#     """Create a bucket for testing using moto."""
#     with mock_s3():
#         conn = s3fs.core.boto3.client("s3", **AWS_CREDENTIALS)
#         conn.create_bucket(Bucket=BUCKET_NAME)
#         return conn
#
#
@pytest.fixture
def mocked_single_plot():
    return plt.plot([1, 2, 3], [4, 5, 6])

@pytest.fixture
def mocked_list_plot():
    plots_list = []
    colour="red"
    for index in range(5):
        plots_list.append(plt.figure())
        plt.plot([1, 2, 3], [4, 5, 6], color=colour)
    return plots_list

@pytest.fixture
def mocked_dict_plot():
    plots_dict = {}
    for colour in ["blue", "green", "red"]:
        plots_dict[colour] = plt.figure()
        plt.plot([1, 2, 3], [4, 5, 6], color=colour)
        plt.close()

    return plots_dict
#
#
# @mock_s3
# def test_single_save():

#
#     raise NotImplementedError()
#
# def test_list_save():
#     raise NotImplementedError()
#
# def test_dict_save():
#     raise NotImplementedError()
#


import boto3

class MyModel(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def save(self):
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.put_object(Bucket='mybucket', Key=self.name, Body=self.value)



import io

class MockMatplotlibWriterS3(MatplotlibWriterS3):



    @mock_s3
    def _save_to_s3(self, key_name, plot):

        conn = boto3.resource('s3', region_name='us-east-1')
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


@mock_s3
def test_my_model_save():
    conn = boto3.resource('s3', region_name='us-east-1')
    # We need to create the bucket since this is all in Moto's 'virtual' AWS account
    conn.create_bucket(Bucket='mybucket')

    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    body = conn.Object('mybucket', 'steve').get()['Body'].read().decode("utf-8")

    assert body == 'is awesome'


def test_raw():
    mock = mock_s3()
    mock.start()

    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='mybucket')

    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    assert conn.Object('mybucket', 'steve').get()['Body'].read().decode() == 'is awesome'

    mock.stop()

import os

@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'

@pytest.fixture(scope='function')
def s3(aws_credentials):
    with mock_s3():
        yield boto3.client('s3', region_name='us-east-1')




def test_create_bucket(s3):
    # s3 is a fixture defined above that yields a boto3 s3 client.
    # Feel free to instantiate another boto3 S3 client -- Keep note of the region though.
    s3.create_bucket(Bucket="somebucket")

    result = s3.list_buckets()
    assert len(result['Buckets']) == 1
    assert result['Buckets'][0]['Name'] == 'somebucket'


# def test_something(s3):
#    from some.package.that.does.something.with.s3 import some_func # <-- Local import for unit test
#    # ^^ Importing here ensures that the mock has been established.
#
#    sume_func()  # The mock has been established from the "s3" pytest fixture, so this function that uses
#                 # a package-level S3 client will properly use the mock and not reach out to AWS.


def test_single_save(s3, tmp_path):



    single_plot_writer = MockMatplotlibWriterS3(
            bucket="test_bucket",
            filepath="matplotlib_single_plot.png",

        )

    plt.plot([1, 2, 3], [4, 5, 6])

    single_plot_writer.save(plt)


    expected_path = tmp_path / "test.png"
    actual_filepath = tmp_path  / "whatever.png"


    plt.savefig(actual_filepath)

    s3.download_file("test_bucket", "matplotlib_single_plot.png", str(expected_path))



    assert actual_filepath.read_bytes() == expected_path.read_bytes()





