"""``VideoDataSet`` loads/saves video data from an underlying
filesystem (e.g.: local, S3, GCS). It uses OpenCV VideoCapture to read
and decode videos and OpenCV VideoWriter to encode and write video.
"""
import itertools
import tempfile
from collections import abc
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Generator, Optional, Sequence, Tuple, Union

import cv2
import fsspec
import numpy as np
import PIL.Image

from kedro.io.core import AbstractDataset, get_protocol_and_path


class SlicedVideo:
    """A representation of slices of other video types"""

    def __init__(self, video, slice_indexes):
        self.video = video
        self.indexes = range(*slice_indexes.indices(len(video)))

    def __getitem__(self, index: Union[int, slice]) -> PIL.Image.Image:
        if isinstance(index, slice):
            return SlicedVideo(self, index)
        return self.video[self.indexes[index]]

    def __len__(self) -> int:
        return len(self.indexes)

    def __getattr__(self, item):
        return getattr(self.video, item)


class AbstractVideo(abc.Sequence):
    """Base class for the underlying video data"""

    _n_frames = 0
    _index = 0  # Next available frame

    @property
    def fourcc(self) -> str:
        """Get the codec fourcc specification"""
        raise NotImplementedError()

    @property
    def fps(self) -> float:
        """Get the video frame rate"""
        raise NotImplementedError()

    @property
    def size(self) -> Tuple[int, int]:
        """Get the resolution of the video"""
        raise NotImplementedError()

    def __len__(self) -> int:
        return self._n_frames

    def __getitem__(self, index: Union[int, slice]):
        """Get a frame from the video"""
        raise NotImplementedError()


class FileVideo(AbstractVideo):
    """A video object read from a file"""

    def __init__(self, filepath: str) -> None:
        self._filepath = filepath
        self._cap = cv2.VideoCapture(filepath)
        self._n_frames = self._get_length()

    @property
    def fourcc(self) -> str:
        fourcc = self._cap.get(cv2.CAP_PROP_FOURCC)
        return int(fourcc).to_bytes(4, "little").decode("ascii")

    @property
    def fps(self) -> float:
        return self._cap.get(cv2.CAP_PROP_FPS)

    @property
    def size(self) -> Tuple[int, int]:
        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return width, height

    def __getitem__(self, index: Union[int, slice]):
        if isinstance(index, slice):
            return SlicedVideo(self, index)

        if index < 0:
            index += len(self)
        if index >= len(self):
            raise IndexError()

        if index != self._index:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        self._index = index + 1  # Next frame to decode after this
        ret, frame_bgr = self._cap.read()
        if not ret:
            raise IndexError()

        height, width = frame_bgr.shape[:2]
        return PIL.Image.frombuffer(  # Convert to PIL image with RGB instead of BGR
            "RGB", (width, height), frame_bgr, "raw", "BGR", 0, 0
        )

    def _get_length(self) -> int:
        # OpenCV's frame count might be an approximation depending on what
        # headers are available in the video file
        length = int(round(self._cap.get(cv2.CAP_PROP_FRAME_COUNT)))
        if length >= 0:
            return length

        # Getting the frame count with OpenCV can fail on some video files,
        # counting the frames would be too slow so it is better to raise an exception.
        raise ValueError(
            "Failed to load video since number of frames can't be inferred"
        )


class SequenceVideo(AbstractVideo):
    """A video object read from an indexable sequence of frames"""

    def __init__(
        self, frames: Sequence[PIL.Image.Image], fps: float, fourcc: str = "mp4v"
    ) -> None:
        self._n_frames = len(frames)
        self._frames = frames
        self._fourcc = fourcc
        self._size = frames[0].size
        self._fps = fps

    @property
    def fourcc(self) -> str:
        return self._fourcc

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def size(self) -> Tuple[int, int]:
        return self._size

    def __getitem__(self, index: Union[int, slice]):
        if isinstance(index, slice):
            return SlicedVideo(self, index)
        return self._frames[index]


class GeneratorVideo(AbstractVideo):
    """A video object with frames yielded by a generator"""

    def __init__(
        self,
        frames: Generator[PIL.Image.Image, None, None],
        length,
        fps: float,
        fourcc: str = "mp4v",
    ) -> None:
        self._n_frames = length
        first = next(frames)
        self._gen = itertools.chain([first], frames)
        self._fourcc = fourcc
        self._size = first.size
        self._fps = fps

    @property
    def fourcc(self) -> str:
        return self._fourcc

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def size(self) -> Tuple[int, int]:
        return self._size

    def __getitem__(self, index: Union[int, slice]):
        raise NotImplementedError("Underlying video is a generator")

    def __next__(self):
        return next(self._gen)

    def __iter__(self):
        return self


class VideoDataSet(AbstractDataset[AbstractVideo, AbstractVideo]):
    """``VideoDataSet`` loads / save video data from a given filepath as sequence
    of PIL.Image.Image using OpenCV.

    Example usage for the
    `YAML API <https://kedro.readthedocs.io/en/stable/data/\
    data_catalog_yaml_examples.html>`_:


    .. code-block:: yaml

        cars:
          type: video.VideoDataSet
          filepath: data/01_raw/cars.mp4

        motorbikes:
          type: video.VideoDataSet
          filepath: s3://your_bucket/data/02_intermediate/company/motorbikes.mp4
          credentials: dev_s3

    Example usage for the
    `Python API <https://kedro.readthedocs.io/en/stable/data/\
    advanced_data_catalog_usage.html>`_:
    ::

        >>> from kedro.extras.datasets.video import VideoDataSet
        >>> import numpy as np
        >>>
        >>> video = VideoDataSet(filepath='/video/file/path.mp4').load()
        >>> frame = video[0]
        >>> np.sum(np.asarray(frame))


    Example creating a video from numpy frames using Python API:
    ::

        >>> from kedro.extras.datasets.video.video_dataset import VideoDataSet, SequenceVideo
        >>> import numpy as np
        >>> from PIL import Image
        >>>
        >>> frame = np.ones((640,480,3), dtype=np.uint8) * 255
        >>> imgs = []
        >>> for i in range(255):
        >>>   imgs.append(Image.fromarray(frame))
        >>>   frame -= 1
        >>>
        >>> video = VideoDataSet("my_video.mp4")
        >>> video.save(SequenceVideo(imgs, fps=25))


    Example creating a video from numpy frames using a generator and the Python API:
    ::

        >>> from kedro.extras.datasets.video.video_dataset import VideoDataSet, GeneratorVideo
        >>> import numpy as np
        >>> from PIL import Image
        >>>
        >>> def gen():
        >>>   frame = np.ones((640,480,3), dtype=np.uint8) * 255
        >>>   for i in range(255):
        >>>     yield Image.fromarray(frame)
        >>>     frame -= 1
        >>>
        >>> video = VideoDataSet("my_video.mp4")
        >>> video.save(GeneratorVideo(gen(), fps=25, length=None))

    """

    def __init__(
        self,
        filepath: str,
        fourcc: Optional[str] = "mp4v",
        credentials: Dict[str, Any] = None,
        fs_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of VideoDataSet to load / save video data for given filepath.

        Args:
            filepath: The location of the video file to load / save data.
            fourcc: The codec to use when writing video, note that depending on how opencv is
                installed there might be more or less codecs avaiable. If set to None, the
                fourcc from the video object will be used.
            credentials: Credentials required to get access to the underlying filesystem.
                E.g. for ``GCSFileSystem`` it should look like `{"token": None}`.
            fs_args: Extra arguments to pass into underlying filesystem class constructor
                (e.g. `{"project": "my-project"}` for ``GCSFileSystem``).
        """
        # parse the path and protocol (e.g. file, http, s3, etc.)
        protocol, path = get_protocol_and_path(filepath)
        self._protocol = protocol
        self._filepath = PurePosixPath(path)
        self._fourcc = fourcc
        _fs_args = deepcopy(fs_args) or {}
        _credentials = deepcopy(credentials) or {}
        self._storage_options = {**_credentials, **_fs_args}
        self._fs = fsspec.filesystem(self._protocol, **self._storage_options)

    def _load(self) -> AbstractVideo:
        """Loads data from the video file.

        Returns:
            Data from the video file as a AbstractVideo object
        """
        with fsspec.open(
            f"filecache::{self._protocol}://{self._filepath}",
            mode="rb",
            **{self._protocol: self._storage_options},
        ) as fs_file:
            return FileVideo(fs_file.name)

    def _save(self, data: AbstractVideo) -> None:
        """Saves video data to the specified filepath."""
        if self._protocol == "file":
            # Write directly to the local file destination
            self._write_to_filepath(data, str(self._filepath))
        else:
            # VideoWriter can't write to an open file object, instead write to a
            # local tmpfile and then copy that to the destination with fsspec.
            # Note that the VideoWriter fails to write to the file on Windows if
            # the file is already open, thus we can't use NamedTemporaryFile.
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_file = Path(tmp_dir) / self._filepath.name
                self._write_to_filepath(data, str(tmp_file))
                with fsspec.open(
                    f"{self._protocol}://{self._filepath}",
                    "wb",
                    **self._storage_options,
                ) as f_target:
                    with tmp_file.open("r+b") as f_tmp:
                        f_target.write(f_tmp.read())

    def _write_to_filepath(self, video: AbstractVideo, filepath: str) -> None:
        # TODO: This uses the codec specified in the VideoDataSet if it is not None, this is due
        # to compatibility issues since e.g. h264 coded is licensed and is thus not included in
        # opencv if installed from a binary distribution. Since a h264 video can be read, but not
        # written, it would be error prone to use the videos fourcc code. Further, an issue is
        # that the video object does not know what container format will be used since that is
        # selected by the suffix in the file name of the VideoDataSet. Some combinations of codec
        # and container format might not work or will have bad support.
        fourcc = self._fourcc or video.fourcc

        writer = cv2.VideoWriter(
            filepath, cv2.VideoWriter_fourcc(*fourcc), video.fps, video.size
        )
        if not writer.isOpened():
            raise ValueError(
                "Failed to open video writer with params: "
                + f"fourcc={fourcc} fps={video.fps} size={video.size[0]}x{video.size[1]} "
                + f"path={filepath}"
            )
        try:
            for frame in iter(video):
                writer.write(  # PIL images are RGB, opencv expects BGR
                    np.asarray(frame)[:, :, ::-1]
                )
        finally:
            writer.release()

    def _describe(self) -> Dict[str, Any]:
        return {"filepath": self._filepath, "protocol": self._protocol}

    def _exists(self) -> bool:
        return self._fs.exists(self._filepath)
