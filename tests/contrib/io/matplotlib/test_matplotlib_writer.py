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

matplotlib.use("TkAgg")  # used to facilitate simple inclusion into kedro CI/CD


class TestMatplotlibWriter:
    def test_simgle_image(self, tmp_path):
        # generate plot
        plt.plot(np.random.rand(1, 5)[0], np.random.rand(1, 5)[0])

        # write and compare
        trusted_filepath = tmp_path / "image_we_expect.png"
        plt.savefig(str(trusted_filepath))

        experimental_filepath = tmp_path / "image_we_write.png"
        plot_writer = MatplotlibWriter(filepath=str(experimental_filepath))
        plot_writer.save(plt)
        plt.close()

        assert trusted_filepath.read_bytes() == experimental_filepath.read_bytes()

    def test_list_images(self, tmp_path):
        # generate plots
        plots = list()
        for index in range(5):
            plots.append(plt.figure())
            plt.plot(np.random.rand(1, 5)[0], np.random.rand(1, 5)[0])
        plt.close()

        experimental_filepath = tmp_path / "list_images"
        plot_writer = MatplotlibWriter(filepath=str(experimental_filepath))
        plot_writer.save(plots)

        # write and compare
        for index, plot in enumerate(plots):
            trusted_filepath = tmp_path / "image_we_expect_{}.png".format(str(index))

            plot.savefig(trusted_filepath)

            full_experimental_filepath = experimental_filepath / "{}.png".format(
                str(index)
            )
            assert (
                trusted_filepath.read_bytes() == full_experimental_filepath.read_bytes()
            )

    def test_dict_images(self, tmp_path):
        plots = dict()
        # generate plots
        for index in ["boo", "far"]:
            filename = "{}.png".format(index)

            plots[filename] = plt.figure()
            plt.plot(np.random.rand(1, 5)[0], np.random.rand(1, 5)[0])
        plt.close()

        plot_writer = MatplotlibWriter(filepath=str(tmp_path / "dict_images"))

        plot_writer.save(plots)

        # write and compare
        for filename, plot in plots.items():
            trusted_filepath = (
                tmp_path / "dict_images" / filename.replace(".png", "_trusted.png")
            )
            plot.savefig(str(trusted_filepath))
            experimental_filepath = tmp_path / "dict_images" / filename

            assert trusted_filepath.read_bytes() == experimental_filepath.read_bytes()

    def test_load_fail(self, tmp_path):
        plot_writer = MatplotlibWriter(filepath=str(tmp_path / "some_path"))

        expected_load_error = "Loading not supported for MatplotlibWriter"

        with pytest.raises(DataSetError, match=expected_load_error):
            plot_writer.load()

    def test_exists(self, tmp_path):
        plot_object = plt.figure()
        plt.plot(np.random.rand(1, 5)[0], np.random.rand(1, 5)[0])
        plt.close()

        plot_writer = MatplotlibWriter(filepath=str(tmp_path / "some_image.png"))

        assert not plot_writer.exists()

        plot_writer.save(plot_object)

        assert plot_writer.exists()
