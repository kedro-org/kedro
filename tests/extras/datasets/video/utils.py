import itertools

import numpy as np
from PIL import ImageChops

TEST_WIDTH = 640  # Arbitrary value for testing
TEST_HEIGHT = 480  # Arbitrary value for testing
TEST_FPS = 1  # Arbitrary value for testing

TEST_NUM_COLOR_FRAMES = (
    5  # This should be the same as number of frames in conftest videos
)
DEFAULT_FOURCC = "mp4v"  # The expected default fourcc value

# This is video data extracted from the video files with ffmpeg command
MKV_SIZE = (640, 360)
MKV_FPS = 50
MKV_FOURCC = "h264"
MKV_LEN = 109  # from ffprobe

MP4_SIZE = (640, 360)
MP4_FPS = 50
MP4_FOURCC = "avc1"
MP4_LEN = 109  # from ffprobe

MJPEG_SIZE = (640, 360)
MJPEG_FPS = 25  # From ffprobe, not reported by ffmpeg command
# I'm not sure that MJPE is the correct fourcc code for
# mjpeg video since I cannot find any official reference to
# that code. This is however what the openCV VideoCapture
# reports for the video, so we leave it like this for now..
MJPEG_FOURCC = "mjpe"
MJPEG_LEN = 24  # from ffprobe


def assert_images_equal(image_1, image_2):
    """Assert that two images are approximately equal, allow for some
    compression artifacts"""
    assert image_1.size == image_2.size
    diff = np.asarray(ImageChops.difference(image_1, image_2))
    assert np.mean(diff) < 5
    assert np.mean(diff > 50) < 0.01  # Max 1% of pixels


def assert_videos_equal(video_1, video_2):
    assert len(video_1) == len(video_2)

    for image_1, image_2 in itertools.zip_longest(video_1, video_2):
        assert_images_equal(image_1, image_2)
