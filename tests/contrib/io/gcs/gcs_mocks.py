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

from contextlib import contextmanager
from fnmatch import fnmatch
from io import StringIO


class BasicGCSFileSystemMock:
    protocol = ("gcs", "gs")
    root_marker = ""

    def __init__(self):
        self._files = {}

    @contextmanager
    def open(self, filepath, *args, **kwargs):
        raise NotImplementedError

    def exists(self, filepath):
        return str(filepath) in self._files

    def glob(self, pattern, **kwargs):  # pylint: disable=unused-argument
        all_filepaths = set(self._files.keys())
        return [f for f in all_filepaths if fnmatch(f, pattern)]

    def invalidate_cache(self, *args, **kwargs):
        pass

    @classmethod
    def _strip_protocol(cls, path):
        """ Turn path from fully-qualified to file-system-specific
        May require FS-specific handling, e.g., for relative paths or links.
        """
        protos = (cls.protocol,) if isinstance(cls.protocol, str) else cls.protocol
        for protocol in protos:
            path = path.rstrip("/")
            if path.startswith(protocol + "://"):
                path = path[(len(protocol) + 3) :]  # pragma: no cover
            elif path.startswith(protocol + ":"):
                path = path[(len(protocol) + 1) :]  # pragma: no cover
        # use of root_marker to make minimum required path, e.g., "/"
        return path or cls.root_marker


class MockGCSFile(StringIO):
    def write(self, data):
        super().write(data)
        self.seek(0)
