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


"""
``MatplotlibWriterS3`` saves matplotlib objects as image files to s3.
"""

import copy
import io
from typing import Any, Dict, List, Optional, Union

import boto3
from matplotlib.pyplot import figure

from kedro.io import AbstractDataSet, DataSetError


class MatplotlibWriterS3(AbstractDataSet):
    # pylint: disable=too-many-instance-attributes
    """``MatplotlibWriter`` saves matplotlib objects as image files.

        Example:
        ::

            import matplotlib.pyplot as plt
            from kedro.contrib.io.matplotlib_s3_writer import MatplotlibWriterS3

            plt.plot([1, 2, 3], [4, 5, 6])

            # Saving single plot
            single_plot_writer = MatplotlibWriterS3(
                bucket="my-super-great-bucket", filepath="matplot_lib_single_plot.png"
            )
            single_plot_writer.save(plt)

            # Saving dictionary of plots (with SSE)
            plots_dict = {}
            for colour in ["blue", "green", "red"]:
                plots_dict[colour] = plt.figure()
                plt.plot([1, 2, 3], [4, 5, 6], color=colour)
                plt.close()

            dict_plot_writer = MatplotlibWriterS3(
                bucket="my-super-great-bucket",
                s3_put_object_args={"ServerSideEncryption": "AES256"},
                filepath="matplotlib_dict",
            )
            dict_plot_writer.save(plots_dict)

            # Saving list of plots
            plots_list = []
            for index in range(5):
                plots_list.append(plt.figure())
                plt.plot([1,2,3],[4,5,6], color=colour)
            list_plot_writer = MatplotlibWriterS3(
                bucket="my-super-great-bucket", filepath="matplotlib_list"
            )
            list_plot_writer.save(plots_list)

    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        bucket: str,
        filepath: str,
        boto_session_args: Optional[Dict[str, Any]] = None,
        s3_client_args: Optional[Dict[str, Any]] = None,
        s3_put_object_args: Optional[Dict[str, Any]] = None,
        credentials: Optional[Dict[str, Any]] = None,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of ``MatplotlibWriter``.

        Args:
            bucket_name: Name of the bucket without "s3://" prefix
            filepath: Path to a matplot object file.
            boto_session_args: See
                https://boto3.amazonaws.com/v1/documentation/api/latest/reference/core/session.html
            s3_client_args: See
                https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#client
            s3_put_object_args: See
                https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.put_object
            credentials: A dictionary of s3 access and secret keys.
                Must contain ``aws_access_key_id`` and ``aws_secret_access_key``.
                Updates ``s3_client_args`` if provided.
            load_args: Currently ignored as loading is not supported.
            save_args: Save args passed to `plt.savefig`. See
                https://matplotlib.org/api/_as_gen/matplotlib.pyplot.savefig.html
        """

        self._boto_session_args = boto_session_args or {}
        self._s3_client_args = s3_client_args or {}
       _credentials = copy.deepcopy(credentials) or {}
        self._s3_put_object_args = s3_put_object_args or {}

        if self._credentials:
            self._s3_client_args["aws_access_key_id"] = self._credentials[
                "aws_access_key_id"
            ]
            self._s3_client_args["aws_secret_access_key"] = self._credentials[
                "aws_secret_access_key"
            ]

        self._filepath = filepath
        self._load_args = load_args if load_args else dict()
        self._save_args = save_args if save_args else dict()
        self._bucket = bucket

    def _describe(self) -> Dict[str, Any]:
        return dict(
            bucket=self._bucket, load_args=self._load_args, save_args=self._save_args
        )

    def _load(self) -> None:
        raise DataSetError(
            "Loading not supported for `{}`".format(self.__class__.__name__)
        )

    def _save(self, data: Union[figure, List[figure], Dict[str, figure]]) -> None:
        if isinstance(data, list):
            for index, plot in enumerate(data):
                key_path = self._filepath + "/" + str(index) + ".png"
                self._save_to_s3(key_name=key_path, plot=plot)

        elif isinstance(data, dict):
            for plot_name, plot in data.items():
                key_path = self._filepath + "/" + plot_name
                self._save_to_s3(key_name=key_path, plot=plot)

        else:
            self._save_to_s3(key_name=self._filepath, plot=data)

    def _save_to_s3(self, key_name, plot):

        bytes_object = io.BytesIO()
        plot.savefig(bytes_object, **self._save_args)

        session = boto3.Session(**self._boto_session_args)

        session.client("s3", **self._s3_client_args).put_object(
            Bucket=self._bucket,
            Key=key_name,
            **self._s3_put_object_args,
            Body=bytes_object.getvalue(),
        )
