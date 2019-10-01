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


import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

from kedro.contrib.io.matplotlib import MatplotlibWriter
from kedro.io import DataSetError

matplotlib.use("Agg")  # Disable interactive mode


class TestMatplotlibWriter:
    def test_save_simgle_image(self, tmp_path):
        # generate a plot
        # pylint: disable=unsubscriptable-object,useless-suppression
        plt.plot(np.random.rand(1, 5)[0], np.random.rand(1, 5)[0])

        # write and compare
        actual_filepath = tmp_path / "image_we_expect.png"
        plt.savefig(str(actual_filepath))

        expected_filepath = tmp_path / "image_we_write.png"
        plot_writer = MatplotlibWriter(filepath=str(expected_filepath))
        plot_writer.save(plt)
        plt.close()

        assert actual_filepath.read_bytes() == expected_filepath.read_bytes()

    def test_save_list_images(self, tmp_path):
        # generate plots
        plots = []
        for index in range(5):
            plots.append(plt.figure())
            # pylint: disable=unsubscriptable-object,useless-suppression
            plt.plot(np.random.rand(1, 5)[0], np.random.rand(1, 5)[0])

        expected_filepath = tmp_path / "list_images"
        plot_writer = MatplotlibWriter(filepath=str(expected_filepath))
        assert not plot_writer.exists()
        plot_writer.save(plots)
        assert plot_writer.exists()

        # write and compare
        for index, plot in enumerate(plots):
            actual_filepath = tmp_path / "image_we_expect_{}.png".format(str(index))
            plot.savefig(str(actual_filepath))

            full_expected_filepath = expected_filepath / "{}.png".format(str(index))
            assert actual_filepath.read_bytes() == full_expected_filepath.read_bytes()

    def test_save_dict_images(self, tmp_path):
        plots = dict()
        # generate plots
        for filename in ["boo.png", "far.png"]:
            plots[filename] = plt.figure()
            # pylint: disable=unsubscriptable-object,useless-suppression
            plt.plot(np.random.rand(1, 5)[0], np.random.rand(1, 5)[0])

        plot_writer = MatplotlibWriter(filepath=str(tmp_path / "dict_images"))
        assert not plot_writer.exists()
        plot_writer.save(plots)
        assert plot_writer.exists()

        # write and compare
        for filename, plot in plots.items():
            actual_filepath = (
                tmp_path / "dict_images" / filename.replace(".png", "_actual.png")
            )
            plot.savefig(str(actual_filepath))
            expected_filepath = tmp_path / "dict_images" / filename

            assert actual_filepath.read_bytes() == expected_filepath.read_bytes()

    def test_load_fail(self, tmp_path):
        plot_writer = MatplotlibWriter(filepath=str(tmp_path / "some_path"))

        pattern = r"Loading not supported for `MatplotlibWriter`"
        with pytest.raises(DataSetError, match=pattern):
            plot_writer.load()

    def test_exists(self, tmp_path):
        plot_object = plt.figure()
        # pylint: disable=unsubscriptable-object,useless-suppression
        plt.plot(np.random.rand(1, 5)[0], np.random.rand(1, 5)[0])
        plt.close()

        plot_writer = MatplotlibWriter(filepath=str(tmp_path / "some_image.png"))
        assert not plot_writer.exists()
        plot_writer.save(plot_object)
        assert plot_writer.exists()
