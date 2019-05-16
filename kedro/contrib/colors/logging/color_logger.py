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
"""A logging handler class which produces coloured logs."""


import logging

import click


class ColorHandler(logging.StreamHandler):
    """A color log handler.

    You can use this handler by incorporating the example below into your
    logging configuration:

    ``conf/project/logging.yml``:
    ::

        formatters:
          simple:
            format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        handlers:
          console:
            class: kedro.contrib.colors.logging.ColorHandler
            level: INFO
            formatter: simple
            stream: ext://sys.stdout
            # defining colors is optional
            colors:
              debug: white
              info: magenta
              warning: yellow

        root:
          level: INFO
          handlers: [console]

    The ``colors`` parameter is optional, and you can use any ANSI color.

      * Black
      * Red
      * Green
      * Yellow
      * Blue
      * Magenta
      * Cyan
      * White

    The default colors are:

      * debug: magenta
      * info: cyan
      * warning: yellow
      * error: red
      * critical: red
    """

    def __init__(self, stream=None, colors=None):
        logging.StreamHandler.__init__(self, stream)
        colors = colors or {}
        self.colors = {
            "critical": colors.get("critical", "red"),
            "error": colors.get("error", "red"),
            "warning": colors.get("warning", "yellow"),
            "info": colors.get("info", "cyan"),
            "debug": colors.get("debug", "magenta"),
        }

    def _get_color(self, level):
        if level >= logging.CRITICAL:
            return self.colors["critical"]  # pragma: no cover
        if level >= logging.ERROR:
            return self.colors["error"]  # pragma: no cover
        if level >= logging.WARNING:
            return self.colors["warning"]  # pragma: no cover
        if level >= logging.INFO:
            return self.colors["info"]
        if level >= logging.DEBUG:  # pragma: no cover
            return self.colors["debug"]  # pragma: no cover

        return None  # pragma: no cover

    def format(self, record: str) -> str:
        """The handler formatter.

        Args:
            record: The record to format.

        Returns:
            The record formatted as a string.

        """
        text = logging.StreamHandler.format(self, record)
        color = self._get_color(record.levelno)
        return click.style(text, color)
