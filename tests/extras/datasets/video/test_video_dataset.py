import boto3
import pytest
from moto import mock_s3
from utils import TEST_FPS, assert_videos_equal

from kedro.extras.datasets.video import VideoDataSet
from kedro.extras.datasets.video.video_dataset import FileVideo, SequenceVideo
from kedro.io import DataSetError

S3_BUCKET_NAME = "test_bucket"
S3_KEY_PATH = "video"
S3_FULL_PATH = f"s3://{S3_BUCKET_NAME}/{S3_KEY_PATH}/"
AWS_CREDENTIALS = {"key": "FAKE_ACCESS_KEY", "secret": "FAKE_SECRET_KEY"}


@pytest.fixture
def tmp_filepath_mp4(tmp_path):
    return (tmp_path / "test.mp4").as_posix()


@pytest.fixture
def tmp_filepath_avi(tmp_path):
    return (tmp_path / "test.mjpeg").as_posix()


@pytest.fixture
def empty_dataset_mp4(tmp_filepath_mp4):
    return VideoDataSet(filepath=tmp_filepath_mp4)


@pytest.fixture
def empty_dataset_avi(tmp_filepath_avi):
    return VideoDataSet(filepath=tmp_filepath_avi)


@pytest.fixture
def mocked_s3_bucket():
    """Create a bucket for testing using moto."""
    with mock_s3():
        conn = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id=AWS_CREDENTIALS["key"],
            aws_secret_access_key=AWS_CREDENTIALS["secret"],
        )
        conn.create_bucket(Bucket=S3_BUCKET_NAME)
        yield conn


class TestVideoDataSet:
    def test_load_mp4(self, filepath_mp4, mp4_object):
        """Loading a mp4 dataset should create a FileVideo"""
        ds = VideoDataSet(filepath_mp4)
        loaded_video = ds.load()
        assert_videos_equal(loaded_video, mp4_object)

    def test_save_and_load_mp4(self, empty_dataset_mp4, mp4_object):
        """Test saving and reloading the data set."""
        empty_dataset_mp4.save(mp4_object)
        reloaded_video = empty_dataset_mp4.load()
        assert_videos_equal(mp4_object, reloaded_video)
        assert reloaded_video.fourcc == empty_dataset_mp4._fourcc

    @pytest.mark.skip(
        reason="Only one available codec that is typically installed when testing"
    )
    def test_save_with_other_codec(self, tmp_filepath_mp4, mp4_object):
        """Test saving the video with another codec than default."""
        save_fourcc = "xvid"
        ds = VideoDataSet(filepath=tmp_filepath_mp4, fourcc=save_fourcc)
        ds.save(mp4_object)
        reloaded_video = ds.load()
        assert reloaded_video.fourcc == save_fourcc

    def test_save_with_derived_codec(self, tmp_filepath_mp4, color_video):
        """Test saving video by the codec specified in the video object"""
        ds = VideoDataSet(filepath=tmp_filepath_mp4, fourcc=None)
        ds.save(color_video)
        reloaded_video = ds.load()
        assert reloaded_video.fourcc == color_video.fourcc

    def test_saved_fps(self, empty_dataset_mp4, color_video):
        """Verify that a saved video has the same framerate as specified in the video object"""
        empty_dataset_mp4.save(color_video)
        reloaded_video = empty_dataset_mp4.load()
        assert reloaded_video.fps == TEST_FPS

    def test_save_sequence_video(self, color_video, empty_dataset_mp4):
        """Test save (and load) a SequenceVideo object"""
        empty_dataset_mp4.save(color_video)
        reloaded_video = empty_dataset_mp4.load()
        assert_videos_equal(color_video, reloaded_video)

    def test_save_generator_video(
        self, color_video_generator, empty_dataset_mp4, color_video
    ):
        """Test save (and load) a GeneratorVideo object

        Since the GeneratorVideo is exhaused after saving the video to file we use
        the SequenceVideo (color_video) which has the same frames to compare the
        loaded video to.
        """
        empty_dataset_mp4.save(color_video_generator)
        reloaded_video = empty_dataset_mp4.load()
        assert_videos_equal(color_video, reloaded_video)

    def test_exists(self, empty_dataset_mp4, mp4_object):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not empty_dataset_mp4.exists()
        empty_dataset_mp4.save(mp4_object)
        assert empty_dataset_mp4.exists()

    @pytest.mark.skip(reason="Can't deal with videos with missing time info")
    def test_convert_video(self, empty_dataset_mp4, mjpeg_object):
        """Load a file video in mjpeg format and save in mp4v"""
        empty_dataset_mp4.save(mjpeg_object)
        reloaded_video = empty_dataset_mp4.load()
        assert_videos_equal(mjpeg_object, reloaded_video)

    def test_load_missing_file(self, empty_dataset_mp4):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set VideoDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            empty_dataset_mp4.load()

    def test_save_s3(self, mp4_object, mocked_s3_bucket, tmp_path):
        """Test to save a VideoDataSet to S3 storage"""
        video_name = "video.mp4"

        dataset = VideoDataSet(
            filepath=S3_FULL_PATH + video_name, credentials=AWS_CREDENTIALS
        )
        dataset.save(mp4_object)

        tmp_file = tmp_path / video_name
        mocked_s3_bucket.download_file(
            Bucket=S3_BUCKET_NAME,
            Key=S3_KEY_PATH + "/" + video_name,
            Filename=str(tmp_file),
        )
        reloaded_video = FileVideo(str(tmp_file))
        assert_videos_equal(reloaded_video, mp4_object)

    @pytest.mark.xfail
    @pytest.mark.parametrize(
        "fourcc, suffix",
        [
            ("mp4v", "mp4"),
            ("mp4v", "mjpeg"),
            ("mp4v", "avi"),
            ("avc1", "mp4"),
            ("avc1", "mjpeg"),
            ("avc1", "avi"),
            ("mjpg", "mp4"),
            ("mjpg", "mjpeg"),
            ("mjpg", "avi"),
            ("xvid", "mp4"),
            ("xvid", "mjpeg"),
            ("xvid", "avi"),
            ("x264", "mp4"),
            ("x264", "mjpeg"),
            ("x264", "avi"),
            ("divx", "mp4"),
            ("divx", "mjpeg"),
            ("divx", "avi"),
            ("fmp4", "mp4"),
            ("fmp4", "mjpeg"),
            ("fmp4", "avi"),
        ],
    )
    def test_video_codecs(self, fourcc, suffix, color_video):
        """Test different codec and container combinations

        Some of these are expected to fail depending on what
        codecs are installed on the machine.
        """
        video_name = f"video.{suffix}"
        video = SequenceVideo(color_video._frames, 25, fourcc)
        ds = VideoDataSet(video_name, fourcc=None)
        ds.save(video)
        # We also need to verify that the correct codec was used
        # since OpenCV silently (with a warning in the log) fall backs to
        # another codec if one specified is not compatible with the container
        reloaded_video = ds.load()
        assert reloaded_video.fourcc == fourcc
