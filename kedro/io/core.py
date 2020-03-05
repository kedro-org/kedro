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

"""This module provides a set of classes which underpin the data loading and
saving functionality provided by ``kedro.io``.
"""

import abc
import copy
import logging
import os
import warnings
from collections import namedtuple
from datetime import datetime, timezone
from glob import iglob
from pathlib import Path, PurePath
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from urllib.parse import urlparse

from fsspec.utils import infer_storage_options

from kedro.utils import load_obj

warnings.simplefilter("default", DeprecationWarning)

VERSIONED_FLAG_KEY = "versioned"
VERSION_KEY = "version"
HTTP_PROTOCOLS = ("http", "https")
PROTOCOL_DELIMITER = "://"


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


class VersionNotFoundError(DataSetError):
    """``VersionNotFoundError`` raised by ``AbstractVersionedDataSet`` implementations
    in case of no load versions available for the data set.
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
        try:
            class_obj, config = parse_dataset_definition(
                config, load_version, save_version
            )
        except Exception as ex:
            raise DataSetError(
                "An exception occurred when parsing config "
                "for DataSet `{}`:\n{}".format(name, str(ex))
            )

        try:
            data_set = class_obj(**config)  # type: ignore
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

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(__name__)

    def get_last_load_version(self) -> Optional[str]:
        """Versioned datasets should override this property to return last loaded
        version"""
        # pylint: disable=no-self-use
        return None  # pragma: no cover

    def load(self) -> Any:
        """Loads data by delegation to the provided load method.

        Returns:
            Data returned by the provided load method.

        Raises:
            DataSetError: When underlying load method raises error.

        """

        self._logger.debug("Loading %s", str(self))

        try:
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

    def get_last_save_version(self) -> Optional[str]:
        """Versioned datasets should override this property to return last saved
        version."""
        # pylint: disable=no-self-use
        return None  # pragma: no cover

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
            self._logger.debug("Saving %s", str(self))
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
            return str(obj)

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

    def exists(self) -> bool:
        """Checks whether a data set's output already exists by calling
        the provided _exists() method.

        Returns:
            Flag indicating whether the output already exists.

        Raises:
            DataSetError: when underlying exists method raises error.

        """
        try:
            self._logger.debug("Checking whether target of %s exists", str(self))
            return self._exists()
        except Exception as exc:
            message = "Failed during exists check for data set {}.\n{}".format(
                str(self), str(exc)
            )
            raise DataSetError(message) from exc

    def _exists(self) -> bool:
        self._logger.warning(
            "`exists()` not implemented for `%s`. Assuming output does not exist.",
            self.__class__.__name__,
        )
        return False

    def release(self) -> None:
        """Release any cached data.

        Raises:
            DataSetError: when underlying exists method raises error.

        """
        try:
            self._logger.debug("Releasing %s", str(self))
            self._release()
        except Exception as exc:
            message = "Failed during release for data set {}.\n{}".format(
                str(self), str(exc)
            )
            raise DataSetError(message) from exc

    def _release(self) -> None:
        pass

    def _copy(self, **overwrite_params) -> "AbstractDataSet":
        dataset_copy = copy.deepcopy(self)
        for name, value in overwrite_params.items():
            setattr(dataset_copy, name, value)
        return dataset_copy


def generate_timestamp() -> str:
    """Generate the timestamp to be used by versioning.

    Returns:
        String representation of the current timestamp.

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


_CONSISTENCY_WARNING = (
    "Save version `{}` did not match load version `{}` for {}. This is strongly "
    "discouraged due to inconsistencies it may cause between `save` and "
    "`load` operations. Please refrain from setting exact load version for "
    "intermediate data sets where possible to avoid this warning."
)

_DEFAULT_PACKAGES = ["kedro.io.", "kedro.extras.datasets.", ""]


def parse_dataset_definition(
    config: Dict[str, Any], load_version: str = None, save_version: str = None
) -> Tuple[Type[AbstractDataSet], Dict[str, Any]]:
    """Parse and instantiate a dataset class using the configuration provided.

    Args:
        config: Data set config dictionary. It *must* contain the `type` key
            with fully qualified class name.
        load_version: Version string to be used for ``load`` operation if
                the data set is versioned. Has no effect on the data set
                if versioning was not enabled.
        save_version: Version string to be used for ``save`` operation if
            the data set is versioned. Has no effect on the data set
            if versioning was not enabled.

    Raises:
        DataSetError: If the function fails to parse the configuration provided.

    Returns:
        2-tuple: (Dataset class object, configuration dictionary)
    """
    save_version = save_version or generate_timestamp()
    config = copy.deepcopy(config)

    if "type" not in config:
        raise DataSetError("`type` is missing from DataSet catalog configuration")

    class_obj = config.pop("type")
    if isinstance(class_obj, str):
        if len(class_obj.strip(".")) != len(class_obj):
            raise DataSetError(
                "`type` class path does not support relative "
                "paths or paths ending with a dot."
            )

        class_paths = (prefix + class_obj for prefix in _DEFAULT_PACKAGES)

        trials = (_load_obj(class_path) for class_path in class_paths)
        try:
            class_obj = next(obj for obj in trials if obj is not None)
        except StopIteration:
            raise DataSetError("Class `{}` not found.".format(class_obj))

    if not issubclass(class_obj, AbstractDataSet):
        raise DataSetError(
            "DataSet type `{}.{}` is invalid: all data set types must extend "
            "`AbstractDataSet`.".format(class_obj.__module__, class_obj.__qualname__)
        )

    if VERSION_KEY in config:
        # remove "version" key so that it's not passed
        # to the "unversioned" data set constructor
        message = (
            "`%s` attribute removed from data set configuration since it is a "
            "reserved word and cannot be directly specified"
        )
        logging.getLogger(__name__).warning(message, VERSION_KEY)
        del config[VERSION_KEY]
    if config.pop(VERSIONED_FLAG_KEY, False):  # data set is versioned
        config[VERSION_KEY] = Version(load_version, save_version)

    return class_obj, config


def _load_obj(class_path: str) -> Optional[object]:
    try:
        class_obj = load_obj(class_path)
    except ImportError as error:
        if error.name in class_path:
            return None
        # class_obj was successfully loaded, but some dependencies are missing.
        raise DataSetError("{} for {}".format(error, class_path))
    except (AttributeError, ValueError):
        return None

    return class_obj


def _local_exists(filepath: str) -> bool:
    filepath = Path(filepath)
    return filepath.exists() or any(par.is_file() for par in filepath.parents)


def is_remote_path(filepath: str) -> bool:
    """Check if the given path looks like a remote URL (has scheme)."""
    # Get rid of Windows-specific "C:\" start,
    # which is treated as a URL scheme.
    _, filepath = os.path.splitdrive(filepath)
    return bool(urlparse(filepath).scheme)


class AbstractVersionedDataSet(AbstractDataSet, abc.ABC):
    """
    ``AbstractVersionedDataSet`` is the base class for all versioned data set
    implementations. All data sets that implement versioning should extend this
    abstract class and implement the methods marked as abstract.

    Example:
    ::

        >>> from kedro.io import AbstractVersionedDataSet
        >>> import pandas as pd
        >>>
        >>>
        >>> class MyOwnDataSet(AbstractVersionedDataSet):
        >>>     def __init__(self, param1, param2, filepath, version):
        >>>         super().__init__(filepath, version)
        >>>         self._param1 = param1
        >>>         self._param2 = param2
        >>>
        >>>     def _load(self) -> pd.DataFrame:
        >>>         load_path = self._get_load_path()
        >>>         return pd.read_csv(load_path)
        >>>
        >>>     def _save(self, df: pd.DataFrame) -> None:
        >>>         save_path = self._get_save_path()
        >>>         df.to_csv(str(save_path))
        >>>
        >>>     def _exists(self) -> bool:
        >>>         path = self._get_load_path()
        >>>         return path.is_file()
        >>>
        >>>     def _describe(self):
        >>>         return dict(version=self._version, param1=self._param1, param2=self._param2)
    """

    # pylint: disable=abstract-method

    def __init__(
        self,
        filepath: PurePath,
        version: Optional[Version],
        exists_function: Callable[[str], bool] = None,
        glob_function: Callable[[str], List[str]] = None,
    ):
        """Creates a new instance of ``AbstractVersionedDataSet``.

        Args:
            filepath: Path to file.
            version: If specified, should be an instance of
                ``kedro.io.core.Version``. If its ``load`` attribute is
                None, the latest version will be loaded. If its ``save``
                attribute is None, save version will be autogenerated.
            exists_function: Function that is used for determining whether
                a path exists in a filesystem.
            glob_function: Function that is used for finding all paths
                in a filesystem, which match a given pattern.
        """
        self._filepath = filepath
        self._version = version
        self._exists_function = exists_function or _local_exists
        self._glob_function = glob_function or iglob
        self._last_load_version = None  # type: Optional[str]
        self._last_save_version = None  # type: Optional[str]

    def get_last_load_version(self) -> Optional[str]:
        return self._last_load_version

    def _lookup_load_version(self) -> Optional[str]:
        if not self._version:
            return None
        if self._version.load:
            return self._version.load

        # When load version is unpinned, fetch the most recent existing
        # version from the given path
        pattern = str(self._get_versioned_path("*"))
        version_paths = sorted(self._glob_function(pattern), reverse=True)
        most_recent = next(
            (path for path in version_paths if self._exists_function(path)), None
        )

        if not most_recent:
            raise VersionNotFoundError(
                "Did not find any versions for {}".format(str(self))
            )

        return PurePath(most_recent).parent.name

    def _get_load_path(self) -> PurePath:
        if not self._version:
            # When versioning is disabled, load from original filepath
            return self._filepath

        load_version = self._last_load_version or self._lookup_load_version()
        return self._get_versioned_path(load_version)  # type: ignore

    def get_last_save_version(self) -> Optional[str]:
        return self._last_save_version

    def _lookup_save_version(self) -> Optional[str]:
        if not self._version:
            return None
        return self._version.save or generate_timestamp()

    def _get_save_path(self) -> PurePath:
        if not self._version:
            # When versioning is disabled, return original filepath
            return self._filepath

        save_version = self._last_save_version or self._lookup_save_version()
        versioned_path = self._get_versioned_path(save_version)  # type: ignore
        if self._exists_function(str(versioned_path)):
            raise DataSetError(
                "Save path `{}` for {} must not exist if versioning "
                "is enabled.".format(versioned_path, str(self))
            )

        return versioned_path

    def _get_versioned_path(self, version: str) -> PurePath:
        return self._filepath / version / self._filepath.name

    def load(self) -> Any:
        self._last_load_version = self._lookup_load_version()
        return super().load()

    def save(self, data: Any) -> None:
        self._last_save_version = self._lookup_save_version()
        super().save(data)

        load_version = self._lookup_load_version()
        if load_version != self._last_save_version:
            warnings.warn(
                _CONSISTENCY_WARNING.format(
                    self._last_save_version, load_version, str(self)
                )
            )

    def exists(self) -> bool:
        """Checks whether a data set's output already exists by calling
        the provided _exists() method.

        Returns:
            Flag indicating whether the output already exists.

        Raises:
            DataSetError: when underlying exists method raises error.

        """
        self._logger.debug("Checking whether target of %s exists", str(self))
        try:
            return self._exists()
        except VersionNotFoundError:
            return False
        except Exception as exc:
            message = "Failed during exists check for data set {}.\n{}".format(
                str(self), str(exc)
            )
            raise DataSetError(message) from exc


def get_protocol_and_path(filepath: str, version: Version = None) -> Tuple[str, str]:
    """Parses filepath on protocol and path.

    Args:
        filepath: raw filepath e.g.: `gcs://bucket/test.json`.
        version: instance of ``kedro.io.core.Version`` or None.

    Returns:
            Protocol and path.

    Raises:
            DataSetError: when protocol is http(s) and version is not None.
            Note: HTTP(s) dataset doesn't support versioning.
    """
    options_dict = infer_storage_options(filepath)
    path = options_dict["path"]
    protocol = options_dict["protocol"]

    if protocol in HTTP_PROTOCOLS:
        if version:
            raise DataSetError(
                "HTTP(s) DataSet doesn't support versioning. "
                "Please remove version flag from the dataset configuration."
            )
        path = path.split(PROTOCOL_DELIMITER, 1)[-1]

    return protocol, path


def get_filepath_str(path: PurePath, protocol: str) -> str:
    """Returns filepath. Returns full filepath (with protocol) if protocol is HTTP(s).

    Args:
        path: filepath without protocol.
        protocol: protocol.

    Returns:
        Filepath string.
    """
    path = str(path)
    if protocol in HTTP_PROTOCOLS:
        path = "".join((protocol, PROTOCOL_DELIMITER, path))
    return path


def validate_on_forbidden_chars(**kwargs):
    """Validate that string values do not include white-spaces or ;"""
    for key, value in kwargs.items():
        if " " in value or ";" in value:
            raise DataSetError(
                "Neither white-space nor semicolon are allowed in `{}`.".format(key)
            )


def deprecation_warning(class_name):
    """Log deprecation warning."""
    warnings.warn(
        "{} will be deprecated in future releases. Please refer "
        "to replacement datasets in kedro.extras.datasets.".format(class_name),
        DeprecationWarning,
    )
