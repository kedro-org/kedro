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

# pylint: disable=unused-argument

import subprocess
import sys

import pytest

from kedro.cli.utils import KedroCliError


@pytest.fixture(autouse=True)
def call_mock(mocker, fake_project):
    return mocker.patch.object(fake_project.kedro_cli, 'call')


@pytest.fixture()
def fake_nbstripout():
    """
    ``nbstripout`` tries to access ``sys.stdin.buffer.readable``
    on import, but it's patches by pytest.
    Let's replace it by the fake!
    """
    sys.modules['nbstripout'] = 'fake'
    yield
    del sys.modules['nbstripout']


@pytest.fixture
def missing_nbstripout(mocker):
    """
    Pretend ``nbstripout`` module doesn't exist.
    In fact, no new imports are possible after that.
    """
    sys.modules.pop('nbstripout', None)
    mocker.patch.object(sys, 'path', [])


@pytest.fixture
def fake_git_repo(mocker):
    return mocker.patch('subprocess.run', return_value=mocker.Mock(returncode=0))


@pytest.fixture
def without_git_repo(mocker):
    return mocker.patch('subprocess.run', return_value=mocker.Mock(returncode=1))


def test_install_successfully(fake_project, call_mock, fake_nbstripout, fake_git_repo):
    fake_project.kedro_cli.activate_nbstripout.callback()
    call_mock.assert_called_once_with(['nbstripout', '--install'])

    fake_git_repo.assert_called_once_with(
        ["git", "rev-parse", "--git-dir"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_nbstripout_not_found(fake_project, missing_nbstripout, fake_git_repo):
    """
    Run activate-nbstripout target without nbstripout installed
    There should be a clear message about it.
    """
    with pytest.raises(KedroCliError, match='nbstripout is not installed'):
        fake_project.kedro_cli.activate_nbstripout.callback()


def test_no_git_repo(fake_project, fake_nbstripout, without_git_repo):
    """
    Run activate-nbstripout target with no git repo available.
    There should be a clear message about it.
    """
    with pytest.raises(KedroCliError, match='Not a git repository'):
        fake_project.kedro_cli.activate_nbstripout.callback()
