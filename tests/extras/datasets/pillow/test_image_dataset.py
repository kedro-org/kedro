from pathlib import Path, PurePosixPath
from time import sleep

import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from PIL import Image, ImageChops
from s3fs.core import S3FileSystem

from kedro.extras.datasets.pillow import ImageDataSet
from kedro.io import DataSetError
from kedro.io.core import PROTOCOL_DELIMITER, Version, generate_timestamp


@pytest.fixture
def filepath_png(tmp_path):
    return (tmp_path / "test.png").as_posix()


@pytest.fixture
def image_dataset(filepath_png, save_args, fs_args):
    return ImageDataSet(filepath=filepath_png, save_args=save_args, fs_args=fs_args)


@pytest.fixture
def versioned_image_dataset(filepath_png, load_version, save_version):
    return ImageDataSet(
        filepath=filepath_png, version=Version(load_version, save_version)
    )


@pytest.fixture(scope="module")
def image_object():
    filepath = str(Path(__file__).parent / "data/image.png")
    return Image.open(filepath).copy()


def images_equal(image_1, image_2):
    diff = ImageChops.difference(image_1, image_2)
    return not diff.getbbox()


class TestImageDataSet:
    def test_save_and_load(self, image_dataset, image_object):
        """Test saving and reloading the data set."""
        image_dataset.save(image_object)
        reloaded_image = image_dataset.load()
        assert images_equal(image_object, reloaded_image)
        assert image_dataset._fs_open_args_save == {"mode": "wb"}

    def test_exists(self, image_dataset, image_object):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not image_dataset.exists()
        image_dataset.save(image_object)
        assert image_dataset.exists()

    @pytest.mark.parametrize(
        "save_args", [{"format": "png", "index": "value"}], indirect=True
    )
    def test_load_extra_params(self, image_dataset, save_args):
        """Test overriding the default load arguments."""
        for key, value in save_args.items():
            assert image_dataset._save_args[key] == value

    @pytest.mark.parametrize(
        "fs_args",
        [
            {
                "open_args_load": {"mode": "r", "compression": "gzip"},
                "open_args_save": {"fs_save": "fs_save"},
            }
        ],
        indirect=True,
    )
    def test_open_extra_args(self, image_dataset, fs_args):
        assert image_dataset._fs_open_args_load == fs_args["open_args_load"]
        expected_save_fs_args = {"mode": "wb"}  # default
        expected_save_fs_args.update(fs_args["open_args_save"])
        assert image_dataset._fs_open_args_save == expected_save_fs_args

    def test_load_missing_file(self, image_dataset):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set ImageDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            image_dataset.load()

    @pytest.mark.parametrize(
        "filepath,instance_type",
        [
            ("s3://bucket/file.png", S3FileSystem),
            ("file:///tmp/test.png", LocalFileSystem),
            ("/tmp/test.png", LocalFileSystem),
            ("https://example.com/file.png", HTTPFileSystem),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type):
        data_set = ImageDataSet(filepath=filepath)
        assert isinstance(data_set._fs, instance_type)

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)

    def test_catalog_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.png"
        data_set = ImageDataSet(filepath=filepath)
        data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)


class TestImageDataSetVersioned:
    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "/tmp/test.png"
        ds = ImageDataSet(filepath=filepath)
        ds_versioned = ImageDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert filepath in str(ds_versioned)

        assert "version" not in str(ds)
        ver_str = f"version=Version(load={load_version}, save='{save_version}')"
        assert ver_str in str(ds_versioned)
        assert "ImageDataSet" in str(ds_versioned)
        assert "ImageDataSet" in str(ds)
        assert "protocol" in str(ds_versioned)
        assert "protocol" in str(ds)

    def test_save_and_load(self, versioned_image_dataset, image_object):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_image_dataset.save(image_object)
        reloaded_image = versioned_image_dataset.load()
        assert images_equal(image_object, reloaded_image)

    def test_multiple_loads(self, versioned_image_dataset, image_object, filepath_png):
        """Test that if a new version is created mid-run, by an
        external system, it won't be loaded in the current run."""
        versioned_image_dataset.save(image_object)
        v1 = versioned_image_dataset.resolve_load_version()

        # Sometimes for some reason `v1 == v_new` on Windows.
        # `sleep()` was added to fix this.
        sleep(0.5)
        # force-drop a newer version into the same location
        v_new = generate_timestamp()
        ImageDataSet(filepath=filepath_png, version=Version(v_new, v_new)).save(
            image_object
        )

        v2 = versioned_image_dataset.resolve_load_version()

        assert v2 == v1  # v2 should not be v_new!
        ds_new = ImageDataSet(filepath=filepath_png, version=Version(None, None))
        assert (
            ds_new.resolve_load_version() == v_new
        )  # new version is discoverable by a new instance

    def test_no_versions(self, versioned_image_dataset):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for ImageDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_image_dataset.load()

    def test_exists(self, versioned_image_dataset, image_object):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_image_dataset.exists()
        versioned_image_dataset.save(image_object)
        assert versioned_image_dataset.exists()

    def test_prevent_overwrite(self, versioned_image_dataset, image_object):
        """Check the error when attempting to override the data set if the
        corresponding image file for a given save version already exists."""
        versioned_image_dataset.save(image_object)
        pattern = (
            r"Save path \`.+\` for ImageDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_image_dataset.save(image_object)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_image_dataset, load_version, save_version, image_object
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            fr"Save version `{save_version}` did not match load version "
            fr"`{load_version}` for ImageDataSet\(.+\)"
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_image_dataset.save(image_object)

    def test_http_filesystem_no_versioning(self):
        pattern = r"HTTP\(s\) DataSet doesn't support versioning\."

        with pytest.raises(DataSetError, match=pattern):
            ImageDataSet(
                filepath="https://example.com/file.png", version=Version(None, None)
            )

    def test_versioning_existing_dataset(
        self, image_dataset, versioned_image_dataset, image_object
    ):
        """Check the error when attempting to save a versioned dataset on top of an
        already existing (non-versioned) dataset."""
        image_dataset.save(image_object)
        assert image_dataset.exists()
        assert image_dataset._filepath == versioned_image_dataset._filepath
        pattern = (
            f"(?=.*file with the same name already exists in the directory)"
            f"(?=.*{versioned_image_dataset._filepath.parent.as_posix()})"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_image_dataset.save(image_object)

        # Remove non-versioned dataset and try again
        Path(image_dataset._filepath.as_posix()).unlink()
        versioned_image_dataset.save(image_object)
        assert versioned_image_dataset.exists()
