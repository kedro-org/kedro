# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
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
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.


"""``MatplotlibS3Writer`` saves matplotlib objects as image files to S3."""

import copy
import io
from pathlib import Path
from typing import Any, Dict, List, Union

from matplotlib.pyplot import figure
from s3fs import S3FileSystem

from kedro.io import AbstractDataSet, DataSetError
from kedro.io.core import deprecation_warning


class MatplotlibS3Writer(AbstractDataSet):
    """``MatplotlibS3Writer`` saves matplotlib objects to an image file in S3.

    Example:
    ::

        >>> import matplotlib.pyplot as plt
        >>> from kedro.contrib.io.matplotlib import MatplotlibS3Writer
        >>>
        >>> # Saving single plot
        >>> plt.plot([1, 2, 3], [4, 5, 6])
        >>> single_plot_writer = MatplotlibS3Writer(
        >>>     bucket="my-super-great-bucket", filepath="matplot_lib_single_plot.png"
        >>> )
        >>> single_plot_writer.save(plt)
        >>> plt.close()
        >>>
        >>> # Saving dictionary of plots
        >>> plots_dict = dict()
        >>> for colour in ["blue", "green", "red"]:
        >>>     plots_dict[colour] = plt.figure()
        >>>     plt.plot([1, 2, 3], [4, 5, 6], color=colour)
        >>>     plt.close()
        >>> dict_plot_writer = MatplotlibS3Writer(
        >>>     bucket="my-super-great-bucket", filepath="matplotlib_dict",
        >>> )
        >>> dict_plot_writer.save(plots_dict)
        >>>
        >>> # Saving list of plots
        >>> plots_list = []
        >>> for index in range(5):
        >>>     plots_list.append(plt.figure())
        >>>     plt.plot([1,2,3],[4,5,6], color=colour)
        >>> list_plot_writer = MatplotlibS3Writer(
        >>>     bucket="my-super-great-bucket", filepath="matplotlib_list"
        >>> )
        >>> list_plot_writer.save(plots_list)

    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        filepath: str,
        bucket_name: str,
        s3fs_args: Dict[str, Any] = None,
        credentials: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of ``MatplotlibS3Writer``.

        Args:
            bucket_name: Name of the bucket without "s3://" prefix.
            filepath: Key path to matplot object file(s).
            s3fs_args: Arguments for ``S3FileSystem``. See
                https://s3fs.readthedocs.io/en/latest/api.html#s3fs.core.S3FileSystem
            credentials: Arguments for ``client_kwargs``. If needed ``aws_access_key_id``
                and ``aws_secret_access_key`` are provided here.
            save_args: Save args passed to `plt.savefig`. See
                https://matplotlib.org/api/_as_gen/matplotlib.pyplot.savefig.html
        """
        deprecation_warning(self.__class__.__name__)
        _credentials = copy.deepcopy(credentials) or {}

        self._s3fs_args = copy.deepcopy(s3fs_args) or {}
        self._filepath = Path(filepath)
        self._save_args = save_args if save_args else dict()
        self._bucket_name = Path(bucket_name)

        self._s3 = S3FileSystem(client_kwargs=_credentials, **self._s3fs_args)

    def _describe(self) -> Dict[str, Any]:
        return dict(
            bucket_name=self._bucket_name,
            filepath=self._filepath,
            s3fs_args=self._s3fs_args,
            save_args=self._save_args,
        )

    def _load(self) -> None:
        raise DataSetError(
            "Loading not supported for `{}`".format(self.__class__.__name__)
        )

    def _save(self, data: Union[figure, List[figure], Dict[str, figure]]) -> None:
        if isinstance(data, list):
            for index, plot in enumerate(data):
                full_key_path = (
                    self._bucket_name / self._filepath / (str(index) + ".png")
                )
                self._save_to_s3(full_key_path=str(full_key_path), plot=plot)

        elif isinstance(data, dict):
            for plot_name, plot in data.items():
                full_key_path = self._bucket_name / self._filepath / plot_name
                self._save_to_s3(full_key_path=str(full_key_path), plot=plot)

        else:
            full_key_path = self._bucket_name / self._filepath
            self._save_to_s3(full_key_path=str(full_key_path), plot=data)

    def _save_to_s3(self, full_key_path: str, plot: figure):
        bytes_buffer = io.BytesIO()
        plot.savefig(bytes_buffer, **self._save_args)

        with self._s3.open(full_key_path, mode="wb") as s3_file:
            s3_file.write(bytes_buffer.getvalue())

    def _exists(self) -> bool:
        load_path = str(self._bucket_name / self._filepath)
        return self._s3.isfile(load_path) or (
            self._s3.isdir(load_path) and bool(list(self._s3.walk(load_path)))
        )
