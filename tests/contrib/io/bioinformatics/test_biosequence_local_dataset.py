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

from kedro.contrib.io.bioinformatics import BioSequenceLocalDataSet


def test_save_load_sequence_file():
    ifile = "tests/contrib/io/bioinformatics/ls_orchid.fasta"
    data_set = BioSequenceLocalDataSet(
        filepath=ifile, load_args={"format": "fasta"}, save_args={"format": "fasta"}
    )
    fasta_sequences = data_set.load()
    data_set.save(fasta_sequences)
    reloaded_list = data_set.load()
    assert fasta_sequences[0].id == reloaded_list[0].id
    assert len(fasta_sequences) == len(reloaded_list)
    assert data_set.exists()


def test_save_sequence_file_to_missing_directory(tmp_path):
    """Ensure directories are created if missing at write time"""
    directory = tmp_path / "missing" / "dir"
    ifile = directory / "file"
    data_set = BioSequenceLocalDataSet(
        filepath=str(ifile),
        load_args={"format": "fasta"},
        save_args={"format": "fasta"},
    )
    data_set.save([])
    reloaded = data_set.load()
    assert reloaded == []
    assert directory.is_dir()
