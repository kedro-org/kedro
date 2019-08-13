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

import glob

PATHS_REQUIRING_HEADER = ["kedro", "tests"]
LEGAL_HEADER_FILE = "legal_header.txt"
LICENSE_MD = "LICENSE.md"

RED_COLOR = "\033[0;31m"
NO_COLOR = "\033[0m"

LICENSE = """Copyright 2018-2019 QuantumBlack Visual Analytics Limited

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
(either separately or in combination, "QuantumBlack Trademarks") are
trademarks of QuantumBlack. The License does not grant you any right or
license to the QuantumBlack Trademarks. You may not use the QuantumBlack
Trademarks or any confusingly similar mark as a trademark for your product,
or use the QuantumBlack Trademarks in any other manner that might cause
confusion in the marketplace, including but not limited to in advertising,
on websites, or on software.

See the License for the specific language governing permissions and
limitations under the License.
"""


def files_at_path(path: str):
    return glob.glob(path + "/**/*.py", recursive=True)


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
    exit_code = 0

    with open(LEGAL_HEADER_FILE) as header_f:
        header = header_f.read()

    # find all .py files recursively
    files = [
        new_file for path in PATHS_REQUIRING_HEADER for new_file in files_at_path(path)
    ]

    # find all files which do not contain the header and are non-empty
    files_with_missing_header = list(files_missing_substring(files, header))

    # exit with an error and print all files without header in read, if any
    if files_with_missing_header:
        print(
            RED_COLOR
            + "The legal header is missing from the following files:\n- "
            + "\n- ".join(files_with_missing_header)
            + NO_COLOR
            + "\nPlease add it by copy-pasting the below:\n\n"
            + header
            + "\n"
        )
        exit_code = 1

    # check the LICENSE.md exists and has the right contents
    try:
        files = list(files_missing_substring([LICENSE_MD], LICENSE))
        if files:
            print(
                RED_COLOR
                + "Please make sure the LICENSE.md file "
                + "at the root of the project "
                + "has the right contents."
                + NO_COLOR
            )
            exit(1)
    except IOError:
        print(
            RED_COLOR + "Please add the LICENSE.md file at the root of the project "
            "with the appropriate contents." + NO_COLOR
        )
        exit(1)

    # if it doesn't exist, send a notice
    exit(exit_code)


if __name__ == "__main__":
    main()
