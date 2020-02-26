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


"""``MatplotlibLocalWriter `` saves matplotlib objects to a local image file."""

from pathlib import Path
from typing import Any, Dict, List, Union

from matplotlib.pyplot import figure

from kedro.io import AbstractDataSet, DataSetError
from kedro.io.core import deprecation_warning


class MatplotlibLocalWriter(AbstractDataSet):
    """``MatplotlibLocalWriter`` saves matplotlib objects to a local image file.

        Example:
        ::

            >>> import matplotlib.pyplot as plt
            >>> from kedro.contrib.io.matplotlib import MatplotlibLocalWriter
            >>>
            >>> plt.plot([1,2,3],[4,5,6])
            >>>
            >>> single_plot_writer = MatplotlibLocalWriter(filepath="data/new_plot.png")
            >>> single_plot_writer.save(plt)
            >>>
            >>> plt.close()
            >>>
            >>> plots_dict = dict()
            >>>
            >>> for colour in ['blue', 'green', 'red']:
            >>>     plots_dict[colour] = plt.figure()
            >>>     plt.plot([1,2,3],[4,5,6], color=colour)
            >>>     plt.close()
            >>>
            >>> dict_plot_writer = MatplotlibLocalWriter(filepath="data/")
            >>> dict_plot_writer.save(plots_dict)
            >>>
            >>> plots_list = []
            >>> for index in range(5):
            >>>    plots_list.append(plt.figure())
            >>>    plt.plot([1,2,3],[4,5,6], color=colour)
            >>> list_plot_writer = MatplotlibLocalWriter(filepath="data/")
            >>> list_plot_writer.save(plots_list)

    """

    def __init__(
        self,
        filepath: str,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of ``MatplotlibLocalWriter``.

        Args:
            filepath: Path to a matplot object file.
            load_args: Currently ignored as loading is not supported.
            save_args: Save args passed to `plt.savefig`. See
                https://matplotlib.org/api/_as_gen/matplotlib.pyplot.savefig.html
        """
        deprecation_warning(self.__class__.__name__)
        self._filepath = Path(filepath)
        self._load_args = load_args if load_args else dict()
        self._save_args = save_args if save_args else dict()

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            load_args=self._load_args,
            save_args=self._save_args,
        )

    def _load(self) -> None:
        raise DataSetError(
            "Loading not supported for `{}`".format(self.__class__.__name__)
        )

    def _save(self, data: Union[figure, List[figure], Dict[str, figure]]) -> None:
        if isinstance(data, list):
            self._filepath.mkdir(exist_ok=True)
            for index, plot in enumerate(data):
                plot.savefig(str(self._filepath / str(index)), **self._save_args)

        elif isinstance(data, dict):
            self._filepath.mkdir(exist_ok=True)
            for plot_name, plot in data.items():
                plot.savefig(str(self._filepath / plot_name), **self._save_args)
        else:
            data.savefig(str(self._filepath), **self._save_args)

    def _exists(self) -> bool:
        return self._filepath.is_file() or (
            self._filepath.is_dir() and bool(list(self._filepath.iterdir()))
        )
