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

"""``kedro.io`` provides functionality to read and write to a
number of data sets. At core of the library is ``AbstractDataSet``
which allows implementation of various ``AbstractDataSet``s.
"""

from .cached_dataset import CachedDataSet  # NOQA
from .core import AbstractDataSet  # NOQA
from .core import AbstractVersionedDataSet  # NOQA
from .core import DataSetAlreadyExistsError  # NOQA
from .core import DataSetError  # NOQA
from .core import DataSetNotFoundError  # NOQA
from .core import Version  # NOQA
from .csv_http import CSVHTTPDataSet  # NOQA
from .csv_local import CSVLocalDataSet  # NOQA
from .csv_s3 import CSVS3DataSet  # NOQA
from .data_catalog import DataCatalog  # NOQA
from .data_catalog_with_default import DataCatalogWithDefault  # NOQA
from .excel_local import ExcelLocalDataSet  # NOQA
from .hdf_local import HDFLocalDataSet  # NOQA
from .hdf_s3 import HDFS3DataSet  # NOQA
from .json_dataset import JSONDataSet  # NOQA
from .json_local import JSONLocalDataSet  # NOQA
from .lambda_data_set import LambdaDataSet  # NOQA
from .memory_data_set import MemoryDataSet  # NOQA
from .parquet_local import ParquetLocalDataSet  # NOQA
from .partitioned_data_set import IncrementalDataSet  # NOQA
from .partitioned_data_set import PartitionedDataSet  # NOQA
from .pickle_local import PickleLocalDataSet  # NOQA
from .pickle_s3 import PickleS3DataSet  # NOQA
from .sql import SQLQueryDataSet  # NOQA
from .sql import SQLTableDataSet  # NOQA
from .text_local import TextLocalDataSet  # NOQA
from .transformers import AbstractTransformer  # NOQA
