import numpy as np
import pytest
from utils import (
    DEFAULT_FOURCC,
    MJPEG_FOURCC,
    MJPEG_FPS,
    MJPEG_LEN,
    MJPEG_SIZE,
    MKV_FOURCC,
    MKV_FPS,
    MKV_LEN,
    MKV_SIZE,
    MP4_FOURCC,
    MP4_FPS,
    MP4_LEN,
    MP4_SIZE,
    TEST_FPS,
    TEST_HEIGHT,
    TEST_NUM_COLOR_FRAMES,
    TEST_WIDTH,
    assert_images_equal,
)

from kedro.extras.datasets.video.video_dataset import (
    FileVideo,
    GeneratorVideo,
    SequenceVideo,
)


class TestSequenceVideo:
    def test_sequence_video_indexing_first(self, color_video, red_frame):
        """Test indexing a SequenceVideo"""
        red = np.array(color_video[0])
        assert red.shape == (TEST_HEIGHT, TEST_WIDTH, 3)
        assert np.all(red == red_frame)

    def test_sequence_video_indexing_last(self, color_video, purple_frame):
        """Test indexing a SequenceVideo"""
        purple = np.array(color_video[-1])
        assert purple.shape == (TEST_HEIGHT, TEST_WIDTH, 3)
        assert np.all(purple == purple_frame)

    def test_sequence_video_iterable(self, color_video):
        """Test iterating a SequenceVideo"""
        for i, img in enumerate(map(np.array, color_video)):
            assert np.all(img == np.array(color_video[i]))
        assert i == TEST_NUM_COLOR_FRAMES - 1

    def test_sequence_video_fps(self, color_video):
        # Test the one set by the fixture
        assert color_video.fps == TEST_FPS

        # Test creating with another fps
        test_fps_new = 123
        color_video_new = SequenceVideo(color_video._frames, fps=test_fps_new)
        assert color_video_new.fps == test_fps_new

    def test_sequence_video_len(self, color_video):
        assert len(color_video) == TEST_NUM_COLOR_FRAMES

    def test_sequence_video_size(self, color_video):
        assert color_video.size == (TEST_WIDTH, TEST_HEIGHT)

    def test_sequence_video_fourcc_default_value(self, color_video):
        assert color_video.fourcc == DEFAULT_FOURCC

    def test_sequence_video_fourcc(self, color_video):
        fourcc_new = "mjpg"
        assert (
            DEFAULT_FOURCC != fourcc_new
        ), "Test does not work if new test value is same as default"
        color_video_new = SequenceVideo(
            color_video._frames, fps=TEST_FPS, fourcc=fourcc_new
        )
        assert color_video_new.fourcc == fourcc_new


class TestGeneratorVideo:
    def test_generator_video_iterable(self, color_video_generator, color_video):
        """Test iterating a GeneratorVideo

        The content of the mock GeneratorVideo should be the same as the SequenceVideo,
        the content in the later is tested in other unit tests and can thus be trusted
        """
        for i, img in enumerate(map(np.array, color_video_generator)):
            assert np.all(img == np.array(color_video[i]))
        assert i == TEST_NUM_COLOR_FRAMES - 1

    def test_generator_video_fps(self, color_video_generator):
        # Test the one set by the fixture
        assert color_video_generator.fps == TEST_FPS

        # Test creating with another fps
        test_fps_new = 123
        color_video_new = GeneratorVideo(
            color_video_generator._gen, length=TEST_NUM_COLOR_FRAMES, fps=test_fps_new
        )
        assert color_video_new.fps == test_fps_new

    def test_generator_video_len(self, color_video_generator):
        assert len(color_video_generator) == TEST_NUM_COLOR_FRAMES

    def test_generator_video_size(self, color_video_generator):
        assert color_video_generator.size == (TEST_WIDTH, TEST_HEIGHT)

    def test_generator_video_fourcc_default_value(self, color_video_generator):
        assert color_video_generator.fourcc == DEFAULT_FOURCC

    def test_generator_video_fourcc(self, color_video_generator):
        fourcc_new = "mjpg"
        assert (
            DEFAULT_FOURCC != fourcc_new
        ), "Test does not work if new test value is same as default"
        color_video_new = GeneratorVideo(
            color_video_generator._gen,
            length=TEST_NUM_COLOR_FRAMES,
            fps=TEST_FPS,
            fourcc=fourcc_new,
        )
        assert color_video_new.fourcc == fourcc_new


class TestFileVideo:
    @pytest.mark.skip(reason="Can't deal with videos with missing time info")
    def test_file_props_mjpeg(self, mjpeg_object):
        assert mjpeg_object.fourcc == MJPEG_FOURCC
        assert mjpeg_object.fps == MJPEG_FPS
        assert mjpeg_object.size == MJPEG_SIZE
        assert len(mjpeg_object) == MJPEG_LEN

    def test_file_props_mkv(self, mkv_object):
        assert mkv_object.fourcc == MKV_FOURCC
        assert mkv_object.fps == MKV_FPS
        assert mkv_object.size == MKV_SIZE
        assert len(mkv_object) == MKV_LEN

    def test_file_props_mp4(self, mp4_object):
        assert mp4_object.fourcc == MP4_FOURCC
        assert mp4_object.fps == MP4_FPS
        assert mp4_object.size == MP4_SIZE
        assert len(mp4_object) == MP4_LEN

    def test_file_index_first(self, color_video_object, red_frame):
        assert_images_equal(color_video_object[0], red_frame)

    def test_file_index_last_by_index(self, color_video_object, purple_frame):
        assert_images_equal(color_video_object[TEST_NUM_COLOR_FRAMES - 1], purple_frame)

    def test_file_index_last(self, color_video_object, purple_frame):
        assert_images_equal(color_video_object[-1], purple_frame)

    def test_file_video_failed_capture(self, mocker):
        """Validate good behavior on failed decode

        The best behavior in this case is not obvious, the len property of the
        video object specifies more frames than is actually possible to decode. We
        cannot know this in advance without spending loads of time to decode all frames
        in order to count them."""
        mock_cv2 = mocker.patch("kedro.extras.datasets.video.video_dataset.cv2")
        mock_cap = mock_cv2.VideoCapture.return_value = mocker.Mock()
        mock_cap.get.return_value = 2  # Set the length of the video
        ds = FileVideo("/a/b/c")

        mock_cap.read.return_value = True, np.zeros((1, 1))
        assert ds[0]

        mock_cap.read.return_value = False, None
        with pytest.raises(IndexError):
            ds[1]
