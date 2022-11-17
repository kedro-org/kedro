from pathlib import Path

import pytest
from PIL import Image
from utils import TEST_FPS, TEST_HEIGHT, TEST_WIDTH

from kedro.extras.datasets.video.video_dataset import (
    FileVideo,
    GeneratorVideo,
    SequenceVideo,
)


@pytest.fixture(scope="module")
def red_frame():
    return Image.new("RGB", (TEST_WIDTH, TEST_HEIGHT), (255, 0, 0))


@pytest.fixture(scope="module")
def green_frame():
    return Image.new("RGB", (TEST_WIDTH, TEST_HEIGHT), (0, 255, 0))


@pytest.fixture(scope="module")
def blue_frame():
    return Image.new("RGB", (TEST_WIDTH, TEST_HEIGHT), (0, 0, 255))


@pytest.fixture(scope="module")
def yellow_frame():
    return Image.new("RGB", (TEST_WIDTH, TEST_HEIGHT), (255, 255, 0))


@pytest.fixture(scope="module")
def purple_frame():
    return Image.new("RGB", (TEST_WIDTH, TEST_HEIGHT), (255, 0, 255))


@pytest.fixture
def color_video(red_frame, green_frame, blue_frame, yellow_frame, purple_frame):
    return SequenceVideo(
        [red_frame, green_frame, blue_frame, yellow_frame, purple_frame],
        fps=TEST_FPS,
    )


@pytest.fixture
def color_video_generator(
    red_frame, green_frame, blue_frame, yellow_frame, purple_frame
):
    sequence = [red_frame, green_frame, blue_frame, yellow_frame, purple_frame]

    def generator():
        yield from sequence

    return GeneratorVideo(
        generator(),
        length=len(sequence),
        fps=TEST_FPS,
    )


@pytest.fixture
def filepath_mp4():
    """This is a real video converted to mp4/h264 with ffmpeg command"""
    return str(Path(__file__).parent / "data/video.mp4")


@pytest.fixture
def filepath_mkv():
    """This a a real video recoreded with an Axis network camera"""
    return str(Path(__file__).parent / "data/video.mkv")


@pytest.fixture
def filepath_mjpeg():
    """This is a real video recorded with an Axis network camera"""
    return str(Path(__file__).parent / "data/video.mjpeg")


@pytest.fixture
def filepath_color_mp4():
    """This is a video created with the OpenCV VideoWriter

    it contains 5 frames which each is a single color: red, green, blue, yellow, purple
    """
    return str(Path(__file__).parent / "data/color_video.mp4")


@pytest.fixture
def mp4_object(filepath_mp4):
    return FileVideo(filepath_mp4)


@pytest.fixture
def mkv_object(filepath_mkv):
    return FileVideo(filepath_mkv)


@pytest.fixture
def mjpeg_object(filepath_mjpeg):
    return FileVideo(filepath_mjpeg)


@pytest.fixture
def color_video_object(filepath_color_mp4):
    return FileVideo(filepath_color_mp4)
