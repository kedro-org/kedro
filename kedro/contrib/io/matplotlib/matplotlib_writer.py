# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
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
# The QuantumBlack Visual Analytics Limited (“QuantumBlack”) name and logo
# (either separately or in combination, “QuantumBlack Trademarks”) are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.


"""
``AbstractDataSet`` implementation to save matplotlib objects as image files.
"""

from pathlib import Path, PurePath
from typing import Any, Dict, Optional

from kedro.io import AbstractDataSet, DataSetError


class MatplotlibWriter(AbstractDataSet):
    """
        ``MatplotlibWriter`` saves matplotlib objects as image files.

        Example:
        ::

            >>> import matplotlib.pyplot as plt
            >>> from kedro.contrib.io.matplotlib import MatplotlibWriter
            >>>
            >>> plt.plot([1,2,3],[4,5,6])
            >>>
            >>> single_plot_writer = MatplotlibWriter(filepath="docs/new_plot.png")
            >>> single_plot_writer.save(plt)
            >>>
            >>> plt.close()
            >>>
            >>> plots = dict()
            >>>
            >>> for colour in ['blue', 'green', 'red']:
            >>>     plots[colour] = plt.figure()
            >>>     plt.plot([1,2,3],[4,5,6], color=colour)
            >>>     plt.close()
            >>>
            >>> multi_plot_writer = MatplotlibWriter(filepath="docs/",
            >>>                                      save_args={'multiFile': True})
            >>> multi_plot_writer.save(plots)

    """

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            load_args=self._load_args,
            save_args=self._save_args,
        )

    def __init__(
        self,
        filepath: str,
        load_args: Optional[Dict[str, Any]] = None,
        save_args: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Creates a new instance of ``MatplotlibWriter``.

        Args:
            filepath: path to a text file.
            load_args: Currently ignored as loading is not supported.
            save_args: multiFile: allows for multiple plot objects
                to be saved. Additional load arguments can be found at
                https://matplotlib.org/api/_as_gen/matplotlib.pyplot.savefig.html
        """
        default_save_args = {"multiFile": False}
        default_load_args = {}

        self._filepath = filepath
        self._load_args = self._handle_default_args(load_args, default_load_args)
        self._save_args = self._handle_default_args(save_args, default_save_args)
        self._mutlifile_mode = self._save_args.pop("multiFile")

    @staticmethod
    def _handle_default_args(user_args: dict, default_args: dict) -> dict:
        return {**default_args, **user_args} if user_args else default_args

    def _load(self) -> str:
        raise DataSetError("Loading not supported for MatplotlibWriter")

    def _save(self, data) -> None:

        if self._mutlifile_mode:

            if not Path(self._filepath).is_dir():
                Path(self._filepath).mkdir()

            if isinstance(data, list):
                for index, plot in enumerate(data):
                    plot.savefig(
                        PurePath(self._filepath, str(index)), **self._save_args
                    )

            elif isinstance(data, dict):
                for plot_name, plot in data.items():
                    plot.savefig(
                        PurePath(self._filepath, plot_name), **self._save_args
                    )

            else:
                plot_type = type(data)
                raise DataSetError(
                    (
                        "multiFile is True but data type "
                        "not dict or list. Rather, {}".format(plot_type)
                    )
                )

        else:
            data.savefig(self._filepath, **self._save_args)

    def _exists(self) -> bool:
        return Path(self._filepath).is_file()
