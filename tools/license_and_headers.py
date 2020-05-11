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

import glob
import sys
from itertools import chain
from textwrap import indent

PATHS_REQUIRING_HEADER = ["kedro", "tests"]
LICENSE_MD = "LICENSE.md"

RED_COLOR = "\033[0;31m"
NO_COLOR = "\033[0m"


def files_at_path(path: str):
    return glob.iglob(path + "/**/*.py", recursive=True)


def files_missing_substring(file_names, substring):
    for file_name in file_names:
        with open(file_name, "r", encoding="utf-8") as current_file:
            content = current_file.read()

            if content.strip() and substring not in content:
                yield file_name

            # In some locales Python 3.5 on Windows can't deal with non ascii chars in source files
            try:
                content.encode("ascii")
            except UnicodeError as e:
                print(
                    "Non ascii characters in {} after '{}'".format(
                        file_name, content[e.start - 30 : e.start]
                    )
                )
                yield file_name


def main():
    with open(LICENSE_MD) as header_f:
        header = indent(header_f.read(), " ")
        header = indent(header, "#", lambda line: True)

    # find all .py files recursively
    files = chain.from_iterable(files_at_path(path) for path in PATHS_REQUIRING_HEADER)

    # find all files which do not contain the header and are non-empty
    files_with_missing_header = list(files_missing_substring(files, header))

    # exit with an error and print all files without header in read, if any
    if files_with_missing_header:
        sys.exit(
            RED_COLOR
            + "The legal header is missing from the following files:\n- "
            + "\n- ".join(files_with_missing_header)
            + NO_COLOR
            + "\nPlease add it by copy-pasting the below:\n\n"
            + header
            + "\n"
        )


if __name__ == "__main__":
    main()
