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

"""This module provides a set of classes which underpin the data loading and
saving functionality provided by ``kedro.io``.
"""

import abc
import copy
import logging
from collections import namedtuple
from datetime import datetime, timezone
from glob import iglob
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Type
from warnings import warn

from kedro.utils import load_obj

MAX_DESCRIPTION_LENGTH = 70
VERSIONED_FLAG_KEY = "versioned"
VERSION_KEY = "version"


class DataSetError(Exception):
    """``DataSetError`` raised by ``AbstractDataSet`` implementations
    in case of failure of input/output methods.

    ``AbstractDataSet`` implementations should provide instructive
    information in case of failure.
    """

    pass


class DataSetNotFoundError(DataSetError):
    """``DataSetNotFoundError`` raised by ``DataCatalog`` class in case of
    trying to use a non-existing data set.
    """

    pass


class DataSetAlreadyExistsError(DataSetError):
    """``DataSetAlreadyExistsError`` raised by ``DataCatalog`` class in case
    of trying to add a data set which already exists in the ``DataCatalog``.
    """

    pass


class AbstractDataSet(abc.ABC):
    """``AbstractDataSet`` is the base class for all data set implementations.
    All data set implementations should extend this abstract class
    and implement the methods marked as abstract.

    Example:
    ::

        >>> from kedro.io import AbstractDataSet
        >>> import pandas as pd
        >>>
        >>> class MyOwnDataSet(AbstractDataSet):
        >>>     def __init__(self, param1, param2):
        >>>         self._param1 = param1
        >>>         self._param2 = param2
        >>>
        >>>     def _load(self) -> pd.DataFrame:
        >>>         print("Dummy load: {}".format(self._param1))
        >>>         return pd.DataFrame()
        >>>
        >>>     def _save(self, df: pd.DataFrame) -> None:
        >>>         print("Dummy save: {}".format(self._param2))
        >>>
        >>>     def _describe(self):
        >>>         return dict(param1=self._param1, param2=self._param2)
    """

    @classmethod
    def from_config(
        cls: Type,
        name: str,
        config: Dict[str, Any],
        load_version: str = None,
        save_version: str = None,
    ) -> "AbstractDataSet":
        """Create a data set instance using the configuration provided.

        Args:
            name: Data set name.
            config: Data set config dictionary.
            load_version: Version string to be used for ``load`` operation if
                the data set is versioned. Has no effect on the data set
                if versioning was not enabled.
            save_version: Version string to be used for ``save`` operation if
                the data set is versioned. Has no effect on the data set
                if versioning was not enabled.

        Returns:
            An instance of an ``AbstractDataSet`` subclass.

        Raises:
            DataSetError: When the function fails to create the data set
                from its config.

        """
        config = copy.deepcopy(config)
        save_version = save_version or generate_current_version()

        if VERSION_KEY in config:
            # remove "version" key so that it's not passed
            # to the 'unversioned' data set constructor
            message = (
                "`%s` attribute removed from `%s` data set "
                "configuration since it is a reserved word and cannot "
                "be directly specified",
                VERSION_KEY,
                name,
            )
            logging.getLogger(__name__).warning(*message)
            del config[VERSION_KEY]
        if config.pop(VERSIONED_FLAG_KEY, False):  # data set is versioned
            config[VERSION_KEY] = Version(load_version, save_version)

        dataset_class_path = config.pop("type")
        try:
            class_obj = load_obj(dataset_class_path, "kedro.io")
        except ImportError:
            raise DataSetError(
                "Cannot import module when trying to load type "
                "`{}` for DataSet `{}`.".format(dataset_class_path, name)
            )
        except AttributeError:
            raise DataSetError(
                "Class `{}` for DataSet `{}` not found.".format(
                    dataset_class_path, name
                )
            )

        if not issubclass(class_obj, AbstractDataSet):
            raise DataSetError(
                "DataSet '{}' type `{}.{}` is invalid: "
                "all data set types must extend "
                "`AbstractDataSet`.".format(
                    name, class_obj.__module__, class_obj.__qualname__
                )
            )
        try:
            data_set = class_obj(**config)
        except TypeError as err:
            raise DataSetError(
                "\n{}.\nDataSet '{}' must only contain "
                "arguments valid for the constructor "
                "of `{}.{}`.".format(
                    str(err), name, class_obj.__module__, class_obj.__qualname__
                )
            )
        except Exception as err:
            raise DataSetError(
                "\n{}.\nFailed to instantiate DataSet "
                "'{}' of type `{}.{}`.".format(
                    str(err), name, class_obj.__module__, class_obj.__qualname__
                )
            )
        return data_set

    def load(self) -> Any:
        """Loads data by delegation to the provided load method.

        Returns:
            Data returned by the provided load method.

        Raises:
            DataSetError: When underlying load method raises error.

        """

        try:
            logging.getLogger(__name__).debug("Loading %s", str(self))
            return self._load()
        except DataSetError:
            raise
        except Exception as exc:
            # This exception handling is by design as the composed data sets
            # can throw any type of exception.
            message = "Failed while loading data from data set {}.\n{}".format(
                str(self), str(exc)
            )
            raise DataSetError(message) from exc

    def save(self, data: Any) -> None:
        """Saves data by delegation to the provided save method.

        Args:
            data: the value to be saved by provided save method.

        Raises:
            DataSetError: when underlying save method raises error.

        """

        if data is None:
            raise DataSetError("Saving `None` to a `DataSet` is not allowed")

        try:
            logging.getLogger(__name__).debug("Saving %s", str(self))
            self._save(data)
        except DataSetError:
            raise
        except Exception as exc:
            message = "Failed while saving data to data set {}.\n{}".format(
                str(self), str(exc)
            )
            raise DataSetError(message) from exc

    def __str__(self):
        def _to_str(obj, is_root=False):
            """Returns a string representation where
            1. The root level (i.e. the DataSet.__init__ arguments) are
            formatted like DataSet(key=value).
            2. Dictionaries have the keys alphabetically sorted recursively.
            3. Empty dictionaries and None values are not shown.
            4. String representations of dictionary values are
            capped to MAX_DESCRIPTION_LENGTH.
            """

            fmt = "{}={}" if is_root else "'{}': {}"  # 1

            if isinstance(obj, dict):
                sorted_dict = sorted(obj.items(), key=lambda pair: str(pair[0]))  # 2

                text = ", ".join(
                    fmt.format(key, _to_str(value))  # 2
                    for key, value in sorted_dict
                    if value or isinstance(value, bool)
                )  # 3

                return text if is_root else "{" + text + "}"  # 1

            # not a dictionary
            value = str(obj)
            suffix = "" if len(value) <= MAX_DESCRIPTION_LENGTH else "..."
            return value[:MAX_DESCRIPTION_LENGTH] + suffix  # 4

        return "{}({})".format(type(self).__name__, _to_str(self._describe(), True))

    @abc.abstractmethod
    def _load(self) -> Any:
        raise NotImplementedError(
            "`{}` is a subclass of AbstractDataSet and"
            "it must implement the `_load` method".format(self.__class__.__name__)
        )

    @abc.abstractmethod
    def _save(self, data: Any) -> None:
        raise NotImplementedError(
            "`{}` is a subclass of AbstractDataSet and"
            "it must implement the `_save` method".format(self.__class__.__name__)
        )

    @abc.abstractmethod
    def _describe(self) -> Dict[str, Any]:
        raise NotImplementedError(
            "`{}` is a subclass of AbstractDataSet and"
            "it must implement the `_describe` method".format(self.__class__.__name__)
        )


class ExistsMixin(abc.ABC):
    """Mixin class which provides an exists() method."""

    def exists(self) -> bool:
        """Checks whether a data set's output already exists by calling
        the provided _exists() method.

        Returns:
            Flag indicating whether the output already exists.

        Raises:
            DataSetError: when underlying exists method raises error.

        """
        try:
            logging.getLogger(__name__).debug(
                "Checking whether target of %s exists", str(self)
            )
            return self._exists()
        except Exception as exc:
            message = "Failed during exists check for data set {}.\n{}".format(
                str(self), str(exc)
            )
            raise DataSetError(message) from exc

    @abc.abstractmethod
    def _exists(self) -> bool:
        raise NotImplementedError(
            "`{}` inherits from ExistsMixin and "
            "it must implement the `_exists` method".format(self.__class__.__name__)
        )


def generate_current_version() -> str:
    """Generate the current version to be used by versioned data sets.

    Returns:
        String representation of the current version.

    """
    current_ts = datetime.now(tz=timezone.utc)
    fmt = (
        "{d.year:04d}-{d.month:02d}-{d.day:02d}T{d.hour:02d}"
        ".{d.minute:02d}.{d.second:02d}.{ms:03d}Z"
    )
    return fmt.format(d=current_ts, ms=current_ts.microsecond // 1000)


class Version(namedtuple("Version", ["load", "save"])):
    """This namedtuple is used to provide load and save versions for versioned
    data sets. If ``Version.load`` is None, then the latest available version
    is loaded. If ``Version.save`` is None, then save version is formatted as
    YYYY-MM-DDThh.mm.ss.sssZ of the current timestamp.
    """

    __slots__ = ()


_PATH_CONSISTENCY_WARNING = (
    "Save path `{}` did not match load path `{}` for {}. This is strongly "
    "discouraged due to inconsistencies it may cause between `save` and "
    "`load` operations. Please refrain from setting exact load version for "
    "intermediate data sets where possible to avoid this warning."
)


# pylint: disable=too-few-public-methods
class FilepathVersionMixIn:
    """Mixin class which helps to version filepath-like data sets."""

    def _get_load_path(self, filepath: str, version: Version = None) -> str:
        if not version:
            return filepath
        if version.load:
            return self._get_versioned_path(filepath, version.load)
        pattern = self._get_versioned_path(filepath, "*")
        paths = [f for f in iglob(pattern) if Path(f).exists()]
        if not paths:
            message = "Did not find any versions for {}".format(str(self))
            raise DataSetError(message)
        return sorted(paths, reverse=True)[0]

    def _get_save_path(self, filepath: str, version: Version = None) -> str:
        if not version:
            return filepath
        save_version = version.save or generate_current_version()
        versioned_path = self._get_versioned_path(filepath, save_version)
        if Path(versioned_path).exists():
            message = (
                "Save path `{}` for {} must not exist if versioning "
                "is enabled.".format(versioned_path, str(self))
            )
            raise DataSetError(message)
        return versioned_path

    @staticmethod
    def _get_versioned_path(filepath: str, version: str) -> str:
        filepath = Path(filepath)
        return str(filepath / version / filepath.name)

    def _check_paths_consistency(self, load_path: str, save_path: str):
        if load_path != save_path:
            warn(_PATH_CONSISTENCY_WARNING.format(save_path, load_path, str(self)))


# pylint: disable=too-few-public-methods
class S3PathVersionMixIn:
    """Mixin class which helps to version S3 data sets."""

    def _get_load_path(
        self, client: Any, bucket: str, filepath: str, version: Version = None
    ) -> str:
        if not version:
            return filepath
        if version.load:
            return self._get_versioned_path(filepath, version.load)
        prefix = filepath if filepath.endswith("/") else filepath + "/"
        keys = list(self._list_objects(client, bucket, prefix))
        if not keys:
            message = "Did not find any versions for {}".format(str(self))
            raise DataSetError(message)
        return sorted(keys, reverse=True)[0]

    def _get_save_path(
        self, client: Any, bucket: str, filepath: str, version: Version = None
    ) -> str:
        if not version:
            return filepath
        save_version = version.save or generate_current_version()
        versioned_path = self._get_versioned_path(filepath, save_version)
        if versioned_path in self._list_objects(client, bucket, versioned_path):
            message = (
                "Save path `{}` for {} must not exist if versioning "
                "is enabled.".format(versioned_path, str(self))
            )
            raise DataSetError(message)
        return versioned_path

    def _check_paths_consistency(self, load_path: str, save_path: str):
        if load_path != save_path:
            warn(_PATH_CONSISTENCY_WARNING.format(save_path, load_path, str(self)))

    @staticmethod
    def _get_versioned_path(filepath: str, version: str) -> str:
        filepath = PurePosixPath(filepath)
        return str(filepath / version / filepath.name)

    @staticmethod
    def _list_objects(client: Any, bucket: str, prefix: str):
        paginator = client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
        for page in page_iterator:
            yield from (
                obj["Key"]
                for obj in page.get("Contents", [])
                if not obj["Key"].endswith("/")
            )
