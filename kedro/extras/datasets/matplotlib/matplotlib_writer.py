# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.


"""``MatplotlibWriter`` saves matplotlib objects as image file(s) to an underlying
filesystem (e.g. local, S3, GCS)."""

import io
from copy import deepcopy
from pathlib import PurePosixPath
from typing import Any, Dict, List, Union

import fsspec
import matplotlib.pyplot as plt

from kedro.io.core import (
    AbstractVersionedDataSet,
    DataSetError,
    Version,
    get_filepath_str,
    get_protocol_and_path,
)


class MatplotlibWriter(AbstractVersionedDataSet):
    """``MatplotlibWriter`` saves matplotlib objects to image file(s) in an underlying
    filesystem (e.g. local, S3, GCS).

    Example:
    ::

        >>> import matplotlib.pyplot as plt
        >>> from kedro.extras.datasets.matplotlib import MatplotlibWriter
        >>>
        >>> # Saving single plot
        >>> plt.plot([1, 2, 3], [4, 5, 6])
        >>> single_plot_writer = MatplotlibWriter(
        >>>     filepath="matplot_lib_single_plot.png"
        >>> )
        >>> plt.close()
        >>> single_plot_writer.save(plt)
        >>>
        >>> # Saving dictionary of plots
        >>> plots_dict = dict()
        >>> for colour in ["blue", "green", "red"]:
        >>>     plots_dict[colour] = plt.figure()
        >>>     plt.plot([1, 2, 3], [4, 5, 6], color=colour)
        >>> plt.close("all")
        >>> dict_plot_writer = MatplotlibWriter(
        >>>     filepath="matplotlib_dict"
        >>> )
        >>> dict_plot_writer.save(plots_dict)
        >>>
        >>> # Saving list of plots
        >>> plots_list = []
        >>> for index in range(5):
        >>>     plots_list.append(plt.figure())
        >>>     plt.plot([1,2,3],[4,5,6])
        >>> plt.close("all")
        >>> list_plot_writer = MatplotlibWriter(
        >>>     filepath="matplotlib_list"
        >>> )
        >>> list_plot_writer.save(plots_list)

    """

    DEFAULT_SAVE_ARGS = {}  # type: Dict[str, Any]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        filepath: str,
        fs_args: Dict[str, Any] = None,
        credentials: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
        version: Version = None,
    ) -> None:
        """Creates a new instance of ``MatplotlibWriter``.

        Args:
            filepath: Filepath in POSIX format to a matplot object file(s) prefixed with a protocol
                like `s3://`. If prefix is not provided, `file` protocol (local filesystem) will be
                used. The prefix should be any protocol supported by ``fsspec``.
            fs_args: Extra arguments to pass into underlying filesystem class constructor
                (e.g. `{"project": "my-project"}` for ``GCSFileSystem``), as well as
                to pass to the filesystem's `open` method through nested key `open_args_save`.
                Here you can find all available arguments for `open`:
                https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem.open
                All defaults are preserved, except `mode`, which is set to `wb` when saving.
            credentials: Credentials required to get access to the underlying filesystem.
                E.g. for ``S3FileSystem`` it should look like:
                `{'client_kwargs': {'aws_access_key_id': '<id>', 'aws_secret_access_key': '<key>'}}`
            save_args: Save args passed to `plt.savefig`. See
                https://matplotlib.org/api/_as_gen/matplotlib.pyplot.savefig.html
            version: If specified, should be an instance of
                ``kedro.io.core.Version``. If its ``load`` attribute is
                None, the latest version will be loaded. If its ``save``
                attribute is None, save version will be autogenerated.
        """
        _credentials = deepcopy(credentials) or {}
        _fs_args = deepcopy(fs_args) or {}
        _fs_open_args_save = _fs_args.pop("open_args_save", {})
        _fs_open_args_save.setdefault("mode", "wb")

        protocol, path = get_protocol_and_path(filepath, version)
        self._fs_args = _fs_args
        self._protocol = protocol
        self._fs = fsspec.filesystem(self._protocol, **_credentials, **self._fs_args)

        super().__init__(
            filepath=PurePosixPath(path),
            version=version,
            exists_function=self._fs.exists,
            glob_function=self._fs.glob,
        )

        self._fs_open_args_save = _fs_open_args_save

        # Handle default save arguments
        self._save_args = deepcopy(self.DEFAULT_SAVE_ARGS)
        if save_args is not None:
            self._save_args.update(save_args)

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            protocol=self._protocol,
            fs_args=self._fs_args,
            save_args=self._save_args,
            version=self._version,
        )

    def _load(self) -> None:
        raise DataSetError(
            "Loading not supported for `{}`".format(self.__class__.__name__)
        )

    def _save(
        self, data: Union[plt.figure, List[plt.figure], Dict[str, plt.figure]]
    ) -> None:
        save_path = self._get_save_path()

        if isinstance(data, list):
            for index, plot in enumerate(data):
                full_key_path = get_filepath_str(
                    save_path / f"{index}.png", self._protocol
                )
                self._save_to_fs(full_key_path=full_key_path, plot=plot)
        elif isinstance(data, dict):
            for plot_name, plot in data.items():
                full_key_path = get_filepath_str(save_path / plot_name, self._protocol)
                self._save_to_fs(full_key_path=full_key_path, plot=plot)
        else:
            full_key_path = get_filepath_str(save_path, self._protocol)
            self._save_to_fs(full_key_path=full_key_path, plot=data)

        plt.close("all")

        self._invalidate_cache()

    def _save_to_fs(self, full_key_path: str, plot: plt.figure):
        bytes_buffer = io.BytesIO()
        plot.savefig(bytes_buffer, **self._save_args)

        with self._fs.open(full_key_path, **self._fs_open_args_save) as fs_file:
            fs_file.write(bytes_buffer.getvalue())

    def _exists(self) -> bool:
        load_path = get_filepath_str(self._get_load_path(), self._protocol)
        return self._fs.exists(load_path)

    def _release(self) -> None:
        super()._release()
        self._invalidate_cache()

    def _invalidate_cache(self) -> None:
        """Invalidate underlying filesystem caches."""
        filepath = get_filepath_str(self._filepath, self._protocol)
        self._fs.invalidate_cache(filepath)
