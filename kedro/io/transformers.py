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
"""``Transformers`` modify the loading and saving of ``DataSets`` in a
``DataCatalog``.
"""
import abc
from typing import Any, Callable


class AbstractTransformer(abc.ABC):
    """ Transformers will be deprecated in Kedro 0.18.0 in favour of the Dataset Hooks.

    ``AbstractTransformer`` is the base class for all transformer implementations.
    All transformer implementations should extend this abstract class
    and customise the `load` and `save` methods where appropriate."""

    def load(self, data_set_name: str, load: Callable[[], Any]) -> Any:
        """
        This method will be deprecated in Kedro 0.18.0 in favour of the Dataset Hooks
        `before_dataset_loaded` and `after_dataset_loaded`.

        Wrap the loading of a dataset.
        Call ``load`` to get the data from the data set / next transformer.

        Args:
            data_set_name: The name of the data set being loaded.
            load: A callback to retrieve the data being loaded from the
                data set / next transformer.

        Returns:
            The loaded data.
        """
        # pylint: disable=unused-argument, no-self-use
        return load()

    def save(self, data_set_name: str, save: Callable[[Any], None], data: Any) -> None:
        """
        This method will be deprecated in Kedro 0.18.0 in favour of the Dataset Hooks
        `before_dataset_saved` and `after_dataset_saved`.

        Wrap the saving of a dataset.
        Call ``save`` to pass the data to the  data set / next transformer.

        Args:
            data_set_name: The name of the data set being saved.
            save: A callback to pass the data being saved on to the
                data set / next transformer.
            data: The data being saved
        """
        # pylint: disable=unused-argument, no-self-use
        save(data)
