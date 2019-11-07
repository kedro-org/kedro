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

"""Behave step definitions for the cli_scenarios feature."""

import itertools
import json
import shlex
import shutil
from time import time

import behave
import requests
import yaml
from behave import given, then, when

import features.steps.util as util
import kedro
from features.steps.sh_run import ChildTerminatingPopen, check_run, run

OK_EXIT_CODE = 0


TEST_JUPYTER_ORG = r"""
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "print(\"Hello World!\")"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.5.6"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}
"""

# The difference
TEST_JUPYTER_AFTER_EXEC = r"""
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 1,
   "metadata": {
    "tags": [
     "node"
    ]
   },
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "Hello World!\n"
     ]
    }
   ],
   "source": [
    "print(\"Hello World!\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": []
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.5.6"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}
"""


behave.register_type(CSV=util.parse_csv)


def _check_service_up(context: behave.runner.Context, url: str, string: str):
    """Check that a service is running and responding appropriately.

    Args:
        context: Test context.
        url: Url that is to be read.
        string: The string to be checked.

    """
    response = requests.get(url, timeout=1.0)
    response.raise_for_status()

    data = response.text
    assert string in data
    assert context.result.poll() is None


def _create_config_file(context, include_example):
    context.config_file = context.temp_dir / "config.yml"
    context.project_name = "project-dummy"
    root_project_dir = context.temp_dir / context.project_name
    context.root_project_dir = root_project_dir
    context.package_name = context.project_name.replace("-", "_")
    config = {
        "project_name": context.project_name,
        "repo_name": context.project_name,
        "output_dir": str(context.temp_dir),
        "python_package": context.package_name,
        "include_example": include_example,
    }
    with context.config_file.open("w") as config_file:
        yaml.dump(config, config_file, default_flow_style=False)


@given("I have prepared a config file without example code")
def create_config_file_no_example(context):
    """Behave step to create a temporary config file
    (given the existing temp directory) and store it in the context.
    """
    _create_config_file(context, include_example=False)


@given("I have prepared a config file with example code")
def create_config_file_with_example(context):
    """Behave step to create a temporary config file
    (given the existing temp directory) and store it in the context.
    """
    _create_config_file(context, include_example=True)


@given('I have executed the kedro command "{command}"')
def exec_kedro_target_checked(context, command):
    """Execute Kedro command and check the status."""
    cmd = [context.kedro] + command.split()

    res = run(cmd, env=context.env, cwd=str(context.root_project_dir))

    if res.returncode != OK_EXIT_CODE:
        print(res.stdout)
        print(res.stderr)
        assert False


@given('I have created new environment "{}"')
def create_new_env(context, env_name):
    env_path = context.root_project_dir / "conf" / env_name
    env_path.mkdir()

    for config_name in ("catalog", "parameters", "credentials"):
        path = env_path / "{}.yml".format(config_name)
        with path.open("w") as config_file:
            yaml.dump({}, config_file, default_flow_style=False)

    # overwrite the log level for anyconfig from WARNING to INFO
    logging_path = env_path / "logging.yml"
    logging_json = {
        "loggers": {
            "anyconfig": {
                "level": "INFO",
                "handlers": ["console", "info_file_handler", "error_file_handler"],
                "propagate": "no",
            },
            "kedro.io": {
                "level": "INFO",
                "handlers": ["console", "info_file_handler", "error_file_handler"],
                "propagate": "no",
            },
            "kedro.pipeline": {
                "level": "INFO",
                "handlers": ["console", "info_file_handler", "error_file_handler"],
                "propagate": "no",
            },
        }
    }
    with logging_path.open("w") as config_file:
        yaml.dump(logging_json, config_file, default_flow_style=False)


@given('the python package "{package}" has been uninstalled')
def uninstall_package_via_pip(context, package):
    """Uninstall a python package using pip."""
    run([context.pip, "uninstall", "-y", package], env=context.env)


@given("I have installed the project's python package")
@when("I install the project's python package")
def install_project_package_via_pip(context):
    """Install a python package using pip."""
    dist_dir = context.root_project_dir / "src" / "dist"
    (whl_file,) = dist_dir.glob("*.whl")
    run([context.pip, "install", str(whl_file)], env=context.env)


@given("I have initialized a git repository")
def init_git_repo(context):
    """Init git repo"""
    with util.chdir(context.root_project_dir):
        check_run("git init")
        check_run("git config user.name 'Tester'")
        check_run("git config user.email 'tester.kedro@quantumblack.com'")


@given("I have added a test jupyter notebook")
def add_test_jupyter_nb(context):
    """Create a test jupyter notebook using TEST_JUPYTER_ORG."""
    with open(
        str(context.root_project_dir / "notebooks" / "hello_world.ipynb"), "wt"
    ) as test_nb_fh:
        test_nb_fh.write(TEST_JUPYTER_ORG)


@given("I have run a non-interactive kedro new")
@when("I run a non-interactive kedro new")
def create_project_from_config_file(context):
    """Behave step to run kedro new given the config I previously created.
    """
    res = run([context.kedro, "new", "-c", str(context.config_file)], env=context.env)
    assert res.returncode == OK_EXIT_CODE


@given("I have deleted the credentials file")
def delete_credentials_file(context):
    """Delete configuration file from project"""
    path_to_config_file = context.root_project_dir / "conf" / "base" / "credentials.yml"
    path_to_config_file.unlink()


@given("I have added the project directory to staging")
@when("I add the project directory to staging")
def add_proj_dir_to_staging(context):
    """Add root project dir to staging"""
    with util.chdir(context.root_project_dir):
        check_run("git add .")


@given("I have committed changes to git")
@when("I commit changes to git")
def commit_changes_to_git(context):
    """Commit changes to git"""
    with util.chdir(context.root_project_dir):
        check_run("git commit -m 'Change {time}'".format(time=time()))


@given("I have removed kedro from the requirements")
def remove_req(context: behave.runner.Context):
    reqs_path = context.root_project_dir / "src" / "requirements.txt"
    if reqs_path.is_file():
        old_reqs = reqs_path.read_text()
        new_reqs = old_reqs.replace("kedro==", "#kedro==")
        assert not old_reqs == new_reqs
        reqs_path.write_text(new_reqs)


@when('I execute the kedro command "{command}"')
def exec_kedro_target(context, command):
    """Execute Kedro target."""
    split_command = command.split()
    cmd = [context.kedro] + split_command
    context.result = run(cmd, env=context.env, cwd=str(context.root_project_dir))


@when("I execute the project")
def exec_project(context):
    """Execute installed Kedro project target."""
    cmd = [str(context.bin_dir / context.project_name)]
    context.result = run(cmd, env=context.env, cwd=str(context.root_project_dir))


@when('with tags {tags:CSV}, I execute the kedro command "{cmd}"')
def exec_kedro_run_with_tag(context, cmd, tags):
    """Execute `kedro run` with tags"""
    kedro_args = shlex.split(cmd)
    context.logfile_count = util.get_logline_count(
        util.get_logfile_path(context.root_project_dir)
    )

    tag_list = [["--tag", t] for t in tags]
    tag_args = list(itertools.chain.from_iterable(tag_list))
    run_cmd = [context.kedro] + kedro_args + tag_args

    context.result = run(run_cmd, env=context.env, cwd=str(context.root_project_dir))


@when("I ask the CLI for a version")
def get_kedro_version(context):
    """Behave step to run `kedro -V`."""
    context.version_str = run([context.kedro, "-V"], env=context.env).stdout
    assert context.version_str  # check non-empty


@when("I ask the CLI for a version using python -m")
def get_kedro_version_python(context):
    """Behave step to run `python -m kedro -V`."""
    cmd = [context.python, "-m", "kedro", "-V"]
    context.version_str = run(cmd, env=context.env).stdout
    assert context.version_str  # check non-empty


@when('I execute the kedro jupyter command "{command}"')
def exec_notebook(context, command):
    """Execute Kedro Jupyter target."""
    split_command = command.split()
    cmd = [context.kedro, "jupyter"] + split_command

    # Jupyter notebook forks a child process from a parent process, and
    # only kills the parent process when it is terminated
    context.result = ChildTerminatingPopen(
        cmd, env=context.env, cwd=str(context.root_project_dir)
    )


@when("Wait until the process is finished")
def wait(context):
    """Wait for child process to terminate."""
    context.result.wait()


@when("I execute the test jupyter notebook and save changes")
def simulate_nb_execution(context):
    """Change test jupyter notebook to TEST_JUPYTER_AFTER_EXEC
    simulate that it was executed and output was saved.
    """
    with open(
        str(context.root_project_dir / "notebooks" / "hello_world.ipynb"), "wt"
    ) as test_nb_fh:
        test_nb_fh.write(TEST_JUPYTER_AFTER_EXEC)


@when("I remove the notebooks directory")
def delete_notebooks_dir(context):
    """Delete notebooks directory in project"""
    with util.chdir(context.root_project_dir):
        shutil.rmtree("notebooks/")


@when("I perform a hard git reset to restore the project to last commit")
def do_git_reset_hard(context):
    """Perform a hard git reset"""
    with util.chdir(context.root_project_dir):
        check_run("git reset --hard HEAD")


@when("I add {dependency} to the requirements")
def add_req(context: behave.runner.Context, dependency: str):
    reqs_path = context.root_project_dir / "src" / "requirements.in"
    if reqs_path.is_file():
        reqs_path.write_text(reqs_path.read_text() + "\n" + str(dependency) + "\n")


@then("CLI should print the version in an expected format")
def check_kedro_version(context):
    """Behave step to check validity of the kedro version."""
    version_no = context.version_str.split()[-1]
    assert version_no == kedro.__version__


@then("the expected project directories and files should be created")
def check_created_project_structure(context):
    """Behave step to check the subdirectories created by kedro new."""

    def is_created(name):
        """Check if path exists."""
        return (context.root_project_dir / name).exists()

    for path in ("README.md", "src", "data"):
        assert is_created(path)


@then("the pipeline should contain no nodes")
def check_empty_pipeline_exists(context):
    """Check if the created `pipeline.py` contains no nodes"""
    pipeline_file = (
        context.root_project_dir
        / "src"
        / context.project_name.replace("-", "_")
        / "pipeline.py"
    )
    assert '"__default__": Pipeline([])' in pipeline_file.read_text("utf-8")


@then("the pipeline should contain nodes")
def check_pipeline_not_empty(context):
    """Check if the created `pipeline.py` contains nodes"""
    pipeline_file = (
        context.root_project_dir
        / "src"
        / context.project_name.replace("-", "_")
        / "pipeline.py"
    )
    assert "pipeline = Pipeline([])" not in pipeline_file.read_text("utf-8")


@then("the console log should show that {number} nodes were run")
def check_one_node_run(context, number):
    expected_log_line = "Completed {number} out of {number} tasks".format(number=number)
    assert expected_log_line in context.result.stdout


@then('the console log should show that "{node}" was run')
def check_correct_nodes_run(context, node):
    expected_log_line = "Running node: {node}".format(node=node)
    assert expected_log_line in context.result.stdout


@then("I should get a successful exit code")
def check_status_code(context):
    if context.result.returncode != OK_EXIT_CODE:
        print(context.result.stdout)
        print(context.result.stderr)
        assert False, "Expected exit code {} but got {}".format(
            OK_EXIT_CODE, context.result.returncode
        )


@then("I should get an error exit code")
def check_failed_status_code(context):
    if context.result.returncode == OK_EXIT_CODE:
        print(context.result.stdout)
        print(context.result.stderr)
        assert False, "Expected exit code other than {} but got {}".format(
            OK_EXIT_CODE, context.result.returncode
        )


@then("the relevant packages should be created")
def check_python_packages_created(context):
    """Check that egg and whl files exist in dist dir."""
    dist_dir = context.root_project_dir / "src" / "dist"
    egg_file = dist_dir.glob("*.egg")
    whl_file = dist_dir.glob("*.whl")
    assert any(egg_file)
    assert any(whl_file)


@then('"{env}" environment was used')
def check_environment_used(context, env):
    env_path = context.root_project_dir / "conf" / env
    assert env_path.exists(), 'Environment "{}" does not exist'.format(env)

    if isinstance(context.result, ChildTerminatingPopen):
        stdout = context.result.stdout.read().decode()
        context.result.terminate()
    else:
        stdout = context.result.stdout

    for config_name in ("catalog", "parameters", "credentials"):
        path = env_path.joinpath("{}.yml".format(config_name))
        if path.exists():
            msg = "Loading: {}".format(str(path.resolve()))
            assert msg in stdout, (
                "Expected the following message segment to be printed on stdout: "
                "{0}, but got:\n{1}".format(msg, stdout)
            )


@then('I should get a message including "{msg}"')
def check_message_printed(context, msg):
    """Check that specified message is printed to stdout (can be a segment)."""

    if isinstance(context.result, ChildTerminatingPopen):
        stdout = context.result.stdout.read().decode()
        context.result.terminate()
    else:
        stdout = context.result.stdout

    assert msg in stdout, (
        "Expected the following message segment to be printed on stdout: "
        "{exp_msg},\nbut got {actual_msg}".format(exp_msg=msg, actual_msg=stdout)
    )


@then('I should get an error message including "{msg}"')
def check_error_message_printed(context, msg):
    """Check that specified message is printed to stderr (can be a segment)."""

    if isinstance(context.result, ChildTerminatingPopen):
        stderr = context.result.stderr.read().decode()
        context.result.terminate()
    else:
        stderr = context.result.stderr

    assert msg in stderr, (
        "Expected the following message segment to be printed on stderr: "
        "{exp_msg},\nbut got {actual_msg}".format(exp_msg=msg, actual_msg=stderr)
    )


@then("there should be an additional cell in the jupyter notebook")
def check_additional_cell_added(context):
    """Check that an addiitonal cell has been added compared to notebook
    coded by TEST_JUPYTER_ORG.
    """
    with open(
        str(context.root_project_dir / "notebooks" / "hello_world.ipynb")
    ) as test_nb_fh:
        context.nb_data = json.load(test_nb_fh)
        assert len(context.nb_data["cells"]) == 2


@then("the output should be empty in all the cells in the jupyter notebook")
def check_output_cells_empty(context):
    """Check that all cells contain empty output array."""
    for cell in context.nb_data["cells"]:
        assert cell["outputs"] == []


@then("jupyter notebook should run on port {port}")
def check_jupyter_nb_proc_on_port(context: behave.runner.Context, port: int):
    """Check that jupyter notebook service is running on specified port.

    Args:
        context: Test context
        port: Port to check

    """
    url = "http://localhost:%d" % int(port)
    try:
        util.wait_for(
            func=_check_service_up,
            context=context,
            url=url,
            string="Jupyter Notebook",
            timeout_=15,
            print_error=True,
        )
    finally:
        context.result.terminate()


@then("Jupyter Lab should run on port {port}")
def check_jupyter_lab_proc_on_port(context: behave.runner.Context, port: int):
    """Check that jupyter lab service is running on specified port.

    Args:
        context: Test context
        port: Port to check

    """
    url = "http://localhost:%d" % int(port)
    try:
        util.wait_for(
            func=_check_service_up,
            context=context,
            url=url,
            string='<a href="/lab"',
            print_error=True,
        )
    finally:
        context.result.terminate()


@then("docs should be generated")
def check_docs_generated(context: behave.runner.Context):
    """Check that new project docs are generated."""
    index_html = (
        context.root_project_dir / "docs" / "build" / "html" / "index.html"
    ).read_text("utf-8")
    project_repo = context.project_name.replace("-", "_")
    assert "Welcome to project’s %s API docs!" % project_repo in index_html


@then("requirements should be generated")
def check_reqs_generated(context: behave.runner.Context):
    """Check that new project docs are generated."""
    reqs_path = context.root_project_dir / "src" / "requirements.in"
    assert reqs_path.is_file()
    assert (
        "This file is autogenerated by pip-compile"
        in (context.root_project_dir / "src" / "requirements.txt").read_text()
    )


@then("{dependency} should be in the requirements")
def check_dependency_in_reqs(context: behave.runner.Context, dependency: str):
    reqs_path = context.root_project_dir / "src" / "requirements.txt"
    assert dependency in reqs_path.read_text()


@then("Code cell with node tag should be converted into kedro node")
def check_cell_conversion(context: behave.runner.Context):
    converted_file = (
        context.root_project_dir
        / "src"
        / context.package_name
        / "nodes"
        / "hello_world.py"
    )
    assert "Hello World!" in converted_file.read_text()
