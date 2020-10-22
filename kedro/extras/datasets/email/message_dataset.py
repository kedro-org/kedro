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

"""``EmailMessageDataSet`` loads/saves an email message from/to a file
using an underlying filesystem (e.g.: local, S3, GCS). It uses the
``email`` package in the standard library to manage email messages.
"""
from copy import deepcopy
from email.generator import Generator
from email.message import Message
from email.parser import Parser
from email.policy import default
from pathlib import PurePosixPath
from typing import Any, Dict

import fsspec

from kedro.io.core import (
    AbstractVersionedDataSet,
    DataSetError,
    Version,
    get_filepath_str,
    get_protocol_and_path,
)


class EmailMessageDataSet(
    AbstractVersionedDataSet
):  # pylint: disable=too-many-instance-attributes
    """``EmailMessageDataSet`` loads/saves an email message from/to a file
    using an underlying filesystem (e.g.: local, S3, GCS). It uses the
    ``email`` package in the standard library to manage email messages.

    Note that ``EmailMessageDataSet`` doesn't handle sending email messages.

    Example:
    ::

        >>> from email.message import EmailMessage
        >>>
        >>> from kedro.extras.datasets.email import EmailMessageDataSet
        >>>
        >>> string_to_write = "what would you do if you were invisable for one day????"
        >>>
        >>> # Create a text/plain message
        >>> msg = EmailMessage()
        >>> msg.set_content(string_to_write)
        >>> msg["Subject"] = "invisibility"
        >>> msg["From"] = '"sin studly17"'
        >>> msg["To"] = '"strong bad"'
        >>>
        >>> # data_set = EmailMessageDataSet(filepath="gcs://bucket/test")
        >>> data_set = EmailMessageDataSet(filepath="test")
        >>> data_set.save(msg)
        >>> reloaded = data_set.load()
        >>> assert msg.__dict__ == reloaded.__dict__

    """

    DEFAULT_LOAD_ARGS = {}  # type: Dict[str, Any]
    DEFAULT_SAVE_ARGS = {}  # type: Dict[str, Any]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        filepath: str,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
        version: Version = None,
        credentials: Dict[str, Any] = None,
        fs_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of ``EmailMessageDataSet`` pointing to a concrete text file
        on a specific filesystem.

        Args:
            filepath: Filepath in POSIX format to a text file prefixed with a protocol like `s3://`.
                If prefix is not provided, `file` protocol (local filesystem) will be used.
                The prefix should be any protocol supported by ``fsspec``.
                Note: `http(s)` doesn't support versioning.
            load_args: ``email`` options for parsing email messages (arguments passed
                into ``email.parser.Parser.parse``). Here you can find all available arguments:
                https://docs.python.org/3/library/email.parser.html#email.parser.Parser.parse
                If you would like to specify options for the `Parser`,
                you can include them under the "parser" key. Here you can
                find all available arguments:
                https://docs.python.org/3/library/email.parser.html#email.parser.Parser
                All defaults are preserved, but "policy", which is set to ``email.policy.default``.
            save_args: ``email`` options for generating MIME documents (arguments passed into
                ``email.generator.Generator.flatten``). Here you can find all available arguments:
                https://docs.python.org/3/library/email.generator.html#email.generator.Generator.flatten
                If you would like to specify options for the `Generator`,
                you can include them under the "generator" key. Here you can
                find all available arguments:
                https://docs.python.org/3/library/email.generator.html#email.generator.Generator
                All defaults are preserved.
            version: If specified, should be an instance of
                ``kedro.io.core.Version``. If its ``load`` attribute is
                None, the latest version will be loaded. If its ``save``
                attribute is None, save version will be autogenerated.
            credentials: Credentials required to get access to the underlying filesystem.
                E.g. for ``GCSFileSystem`` it should look like `{"token": None}`.
            fs_args: Extra arguments to pass into underlying filesystem class constructor
                (e.g. `{"project": "my-project"}` for ``GCSFileSystem``), as well as
                to pass to the filesystem's `open` method through nested keys
                `open_args_load` and `open_args_save`.
                Here you can find all available arguments for `open`:
                https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.spec.AbstractFileSystem.open
                All defaults are preserved, except `mode`, which is set to `r` when loading
                and to `w` when saving.
        """
        _fs_args = deepcopy(fs_args) or {}
        _fs_open_args_load = _fs_args.pop("open_args_load", {})
        _fs_open_args_save = _fs_args.pop("open_args_save", {})
        _credentials = deepcopy(credentials) or {}

        protocol, path = get_protocol_and_path(filepath, version)

        self._protocol = protocol
        if protocol == "file":
            _fs_args.setdefault("auto_mkdir", True)
        self._fs = fsspec.filesystem(self._protocol, **_credentials, **_fs_args)

        super().__init__(
            filepath=PurePosixPath(path),
            version=version,
            exists_function=self._fs.exists,
            glob_function=self._fs.glob,
        )

        # Handle default load arguments
        self._load_args = deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args is not None:
            self._load_args.update(load_args)
        self._parser_args = self._load_args.pop("parser", {"policy": default})

        # Handle default save arguments
        self._save_args = deepcopy(self.DEFAULT_SAVE_ARGS)
        if save_args is not None:
            self._save_args.update(save_args)
        self._generator_args = self._save_args.pop("generator", {})

        _fs_open_args_load.setdefault("mode", "r")
        _fs_open_args_save.setdefault("mode", "w")
        self._fs_open_args_load = _fs_open_args_load
        self._fs_open_args_save = _fs_open_args_save

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            protocol=self._protocol,
            load_args=self._load_args,
            parser_args=self._parser_args,
            save_args=self._save_args,
            generator_args=self._generator_args,
            version=self._version,
        )

    def _load(self) -> Message:
        load_path = get_filepath_str(self._get_load_path(), self._protocol)

        with self._fs.open(load_path, **self._fs_open_args_load) as fs_file:
            return Parser(**self._parser_args).parse(fs_file, **self._load_args)

    def _save(self, data: Message) -> None:
        save_path = get_filepath_str(self._get_save_path(), self._protocol)

        with self._fs.open(save_path, **self._fs_open_args_save) as fs_file:
            Generator(fs_file, **self._generator_args).flatten(data, **self._save_args)

        self._invalidate_cache()

    def _exists(self) -> bool:
        try:
            load_path = get_filepath_str(self._get_load_path(), self._protocol)
        except DataSetError:
            return False

        return self._fs.exists(load_path)

    def _release(self) -> None:
        super()._release()
        self._invalidate_cache()

    def _invalidate_cache(self) -> None:
        """Invalidate underlying filesystem caches."""
        filepath = get_filepath_str(self._filepath, self._protocol)
        self._fs.invalidate_cache(filepath)
