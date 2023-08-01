import numpy as np
from utils import TEST_HEIGHT, TEST_WIDTH


class TestSlicedVideo:
    def test_slice_sequence_video_first(self, color_video):
        """Test slicing and then indexing a SequenceVideo"""
        slice_red_green = color_video[:2]
        red = np.array(slice_red_green[0])
        assert red.shape == (TEST_HEIGHT, TEST_WIDTH, 3)
        assert np.all(red[:, :, 0] == 255)
        assert np.all(red[:, :, 1] == 0)
        assert np.all(red[:, :, 2] == 0)

    def test_slice_sequence_video_last_as_index(self, color_video):
        """Test slicing and then indexing a SequenceVideo"""
        slice_blue_yellow_purple = color_video[2:5]
        purple = np.array(slice_blue_yellow_purple[2])
        assert purple.shape == (TEST_HEIGHT, TEST_WIDTH, 3)
        assert np.all(purple[:, :, 0] == 255)
        assert np.all(purple[:, :, 1] == 0)
        assert np.all(purple[:, :, 2] == 255)

    def test_slice_sequence_video_last_as_end(self, color_video):
        """Test slicing and then indexing a SequenceVideo"""
        slice_blue_yellow_purple = color_video[2:]
        purple = np.array(slice_blue_yellow_purple[-1])
        assert purple.shape == (TEST_HEIGHT, TEST_WIDTH, 3)
        assert np.all(purple[:, :, 0] == 255)
        assert np.all(purple[:, :, 1] == 0)
        assert np.all(purple[:, :, 2] == 255)

    def test_slice_sequence_attribute(self, color_video):
        """Test that attributes from the base class are reachable from sliced views"""
        slice_red_green = color_video[:2]
        assert slice_red_green.fps == color_video.fps

    def test_slice_sliced_video(self, color_video):
        """Test slicing and then indexing a SlicedVideo"""
        slice_green_blue_yellow = color_video[1:4]
        slice_green_blue = slice_green_blue_yellow[:-1]
        blue = np.array(slice_green_blue[1])
        assert blue.shape == (TEST_HEIGHT, TEST_WIDTH, 3)
        assert np.all(blue[:, :, 0] == 0)
        assert np.all(blue[:, :, 1] == 0)
        assert np.all(blue[:, :, 2] == 255)

    def test_slice_file_video_first(self, mp4_object):
        """Test slicing and then indexing a FileVideo"""
        sliced_video = mp4_object[:2]
        assert np.all(np.array(sliced_video[0]) == np.array(mp4_object[0]))

    def test_slice_file_video_last(self, mp4_object):
        """Test slicing and then indexing a FileVideo"""
        sliced_video = mp4_object[-2:]
        assert np.all(np.array(sliced_video[-1]) == np.array(mp4_object[-1]))
