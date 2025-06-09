"""Behave step definitions for the cli_scenarios feature."""

import json
import shutil
from pathlib import Path
from time import sleep, time

import behave
import requests
import toml
import yaml
from behave import given, then, when
from packaging.requirements import Requirement

import kedro
from features.steps import util
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


@given("I have prepared a run_config file with config options")
def create_run_config_file(context):
    curr_dir = Path(__file__).parent
    run_config_file = context.root_project_dir / "run_config.yml"
    shutil.copyfile(str(curr_dir / "e2e_test_cli_config.yml"), str(run_config_file))


@given("I have prepared a config file")
# We will use that config with starters, so tools and example_options removed
def create_config_file(context):
    """Behave step to create a temporary config file
    (given the existing temp directory) and store it in the context.
    """
    context.config_file = context.temp_dir / "config.yml"
    context.project_name = "project-dummy"
    context.root_project_dir = context.temp_dir / context.project_name
    context.package_name = context.project_name.replace("-", "_")
    config = {
        "project_name": context.project_name,
        "repo_name": context.project_name,
        "output_dir": str(context.temp_dir),
        "python_package": context.package_name,
    }
    with context.config_file.open("w") as config_file:
        yaml.dump(config, config_file, default_flow_style=False)


@given("I have prepared a config file without starter")
def create_config_file_without_starter(context):
    """Behave step to create a temporary config file
    (given the existing temp directory) and store it in the context.
    """
    context.config_file = context.temp_dir / "config.yml"
    context.project_name = "project-dummy"
    context.root_project_dir = context.temp_dir / context.project_name
    context.package_name = context.project_name.replace("-", "_")
    config = {
        "tools": "lint, test, log, docs, data",
        "project_name": context.project_name,
        "example_pipeline": "no",
        "repo_name": context.project_name,
        "output_dir": str(context.temp_dir),
        "python_package": context.package_name,
    }
    with context.config_file.open("w") as config_file:
        yaml.dump(config, config_file, default_flow_style=False)


@given('I have prepared a config file with tools "{tools}"')
def create_config_file_with_tools(context, tools):
    """Behave step to create a temporary config file
    (given the existing temp directory) and store it in the context.
    It takes a custom tools list and sets example prompt to `n`.
    """

    context.config_file = context.temp_dir / "config.yml"
    context.project_name = "project-dummy"
    context.root_project_dir = context.temp_dir / context.project_name
    context.package_name = context.project_name.replace("-", "_")
    config = {
        "tools": tools,
        "example_pipeline": "n",
        "project_name": context.project_name,
        "repo_name": context.project_name,
        "output_dir": str(context.temp_dir),
        "python_package": context.package_name,
    }
    with context.config_file.open("w") as config_file:
        yaml.dump(config, config_file, default_flow_style=False)


@given("I have installed the project dependencies")
def pip_install_dependencies(context):
    """Install project dependencies using pip."""
    reqs_path = "requirements.txt"
    res = run(
        [context.pip, "install", "-r", reqs_path],
        env=context.env,
        cwd=str(context.root_project_dir),
    )

    if res.returncode != OK_EXIT_CODE:
        print(res.stdout)
        print(res.stderr)
        assert False


@when("I install the project's python package")
def install_project_package_via_pip(context):
    """Install a python package using pip."""
    dist_dir = context.root_project_dir / "dist"
    (whl_file,) = dist_dir.glob("*.whl")
    run([context.pip, "install", str(whl_file)], env=context.env)


@given("I have installed the test plugin")
def install_test_plugin(context):
    """Install a python package using pip."""
    plugin_dir = Path(__file__).parent / "test_plugin"
    res = run([context.pip, "install", "-e", str(plugin_dir)], env=context.env)
    assert res.returncode == OK_EXIT_CODE, res


@given('I have disabled hooks for "{plugin}" plugin via config')
def disable_plugin_hooks(context, plugin):
    """Set `disable_hooks_for_plugins` in `settings.py`."""
    settings_path = (
        context.root_project_dir / "src" / context.package_name / "settings.py"
    )
    to_add = f"""\nDISABLE_HOOKS_FOR_PLUGINS = ("{plugin}",)"""
    with settings_path.open("a") as settings_file:
        settings_file.write(to_add)


@given("I have set the OmegaConfigLoader in settings")
def use_omegaconfigloader(context):
    """Set `config_loader_class` in `settings.py`."""
    settings_path = (
        context.root_project_dir / "src" / context.package_name / "settings.py"
    )
    to_add = """\nfrom kedro.config import OmegaConfigLoader
            \nCONFIG_LOADER_CLASS = OmegaConfigLoader"""
    with settings_path.open("a") as settings_file:
        settings_file.write(to_add)


@given("I have initialized a git repository")
def init_git_repo(context):
    """Init git repo"""
    with util.chdir(context.root_project_dir):
        check_run("git init")
        check_run("git config user.name 'Tester'")
        check_run("git config user.email 'tester.kedro@kedro.com'")


@given("I have added a test jupyter notebook")
def add_test_jupyter_nb(context):
    """Create a test jupyter notebook using TEST_JUPYTER_ORG."""
    with open(
        str(context.root_project_dir / "notebooks" / "hello_world.ipynb"),
        "w",
        encoding="utf-8",
    ) as test_nb_fh:
        test_nb_fh.write(TEST_JUPYTER_ORG)


@given('I have run a non-interactive kedro new with starter "{starter}"')
@when('I run a non-interactive kedro new with starter "{starter}"')
def create_project_with_starter(context, starter):
    """Behave step to run kedro new given the config I previously created."""

    if starter == "default":
        starter = Path(__file__).parent / "test_starter"

    args = [
        context.kedro,
        "new",
        "-c",
        str(context.config_file),
        "--starter",
        str(starter),
    ]

    res = run(
        args,
        env=context.env,
        cwd=context.temp_dir,
    )

    assert res.returncode == OK_EXIT_CODE, res


@given("I have run a non-interactive kedro new without starter")
@when("I run a non-interactive kedro new without starter")
def create_project_without_starter(context):
    """Behave step to run kedro new given the config I previously created."""
    res = run(
        [context.kedro, "new", "-c", str(context.config_file)],
        env=context.env,
        cwd=context.temp_dir,
    )
    assert res.returncode == OK_EXIT_CODE, res
    # prevent telemetry from prompting for input during e2e tests
    telemetry_file = context.root_project_dir / ".telemetry"
    telemetry_file.write_text("consent: false", encoding="utf-8")


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
        check_run(f"git commit -m 'Change {time()}'")


@given('I have executed the kedro command "{command}"')
@when('I execute the kedro command "{command}"')
def exec_kedro_target(context, command):
    """Execute Kedro target."""
    split_command = command.split()
    cmd = [context.kedro, *split_command]
    context.result = run(cmd, env=context.env, cwd=str(context.root_project_dir))


@when("I execute the installed project package")
def exec_project(context):
    """Execute installed Kedro project target."""
    cmd = [str(context.bin_dir / context.project_name)]
    # N.B.: prior to the introduction of load_package_context, this test was passing
    # accidentally because it was executing the installed project package at the
    # same directory as project root, so a lot of things were available on Path.cwd().
    # We take care to delete with `delete_unnecessary_assets` to simulate the behaviour
    # of a installed package in a fresh environment.
    context.result = run(cmd, env=context.env, cwd=str(context.root_project_dir))


@when("I ask the CLI for a version")
def get_kedro_version(context):
    """Behave step to run `kedro -V`."""
    res = run([context.kedro, "-V"], env=context.env, cwd=context.temp_dir)
    context.version_str = res.stdout
    assert context.version_str, res  # check non-empty


@when("I ask the CLI for a version using python -m")
def get_kedro_version_python(context):
    """Behave step to run `python -m kedro -V`."""
    cmd = [context.python, "-m", "kedro", "-V"]
    context.version_str = run(cmd, env=context.env, cwd=context.temp_dir).stdout
    assert context.version_str  # check non-empty


@when('I execute the kedro jupyter command "{command}"')
def exec_notebook(context, command):
    """Execute Kedro Jupyter target."""
    split_command = command.split()
    cmd = [context.kedro, "jupyter", *split_command]

    # Jupyter notebook forks a child process from a parent process, and
    # only kills the parent process when it is terminated
    context.result = ChildTerminatingPopen(
        cmd, env=context.env, cwd=str(context.root_project_dir), universal_newlines=True
    )


@then('I wait for the jupyter webserver to run for up to "{timeout:d}" seconds')
def wait_for_notebook_to_run(context, timeout):
    timeout_start = time()
    # FIXME: Will continue iterating after the process has returned
    while time() < timeout_start + timeout:
        stdout = context.result.stdout.readline()
        if "http://127.0.0.1:" in stdout:
            # Take a breath, and declare success
            sleep(1)
            break

    if time() >= timeout_start + timeout:
        raise TimeoutError("Failed to run Jupyter server in time")


@when('Wait until the process is finished for up to "{timeout:d}" seconds')
def wait(context, timeout):
    """Wait for child process to terminate."""
    context.result.wait(timeout)


@when("I execute the test jupyter notebook and save changes")
def simulate_nb_execution(context):
    """Change test jupyter notebook to TEST_JUPYTER_AFTER_EXEC
    simulate that it was executed and output was saved.
    """
    with open(
        str(context.root_project_dir / "notebooks" / "hello_world.ipynb"),
        "w",
        encoding="utf-8",
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


@when('I move the package to "{new_source_dir}"')
def move_package(context: behave.runner.Context, new_source_dir):
    """Move the project package to a new directory."""
    current_src_path = (context.root_project_dir / "src").resolve()
    new_src_path = (context.root_project_dir / new_source_dir).resolve()

    new_src_path.mkdir(exist_ok=True)
    shutil.move(str(current_src_path / context.package_name), str(new_src_path))


@when('Source directory is updated to "{new_source_dir}" in pyproject.toml')
def update_pyproject_toml(context: behave.runner.Context, new_source_dir):
    """Update `source_dir` in pyproject.toml file."""
    pyproject_toml_path = context.root_project_dir / "pyproject.toml"
    content = toml.load(pyproject_toml_path)
    content["tool"]["kedro"]["source_dir"] = new_source_dir
    content_str = toml.dumps(content)
    pyproject_toml_path.write_text(content_str)


@given("I have updated kedro requirements")
def update_kedro_req(context: behave.runner.Context):
    """Remove kedro as a standalone requirement."""
    reqs_path = context.root_project_dir / "requirements.txt"

    if reqs_path.is_file():
        old_reqs = reqs_path.read_text().splitlines()
        new_reqs = []
        for req in old_reqs:
            if req.startswith("kedro") and Requirement(req).name.lower() == "kedro":
                # Do not include kedro as it's preinstalled in the environment
                pass
            else:
                new_reqs.append(req)
        new_reqs = "\n".join(new_reqs)
        assert old_reqs != new_reqs
        reqs_path.write_text(new_reqs)


@when("I add {dependency} to the requirements")
def add_req(context: behave.runner.Context, dependency: str):
    reqs_path = context.root_project_dir / "requirements.txt"
    if reqs_path.is_file():
        reqs_path.write_text(reqs_path.read_text() + "\n" + str(dependency) + "\n")


@then("CLI should print the version in an expected format")
def check_kedro_version(context):
    """Behave step to check validity of the kedro version."""
    CLI_flat_list = context.version_str.split()
    CLI_dictionary = {
        CLI_flat_list[i]: CLI_flat_list[i + 1]
        for i in range(0, len(CLI_flat_list) - 1, 2)
    }
    version_no = CLI_dictionary.get("version")
    assert version_no == kedro.__version__


@then("the expected project directories and files should be created")
def check_created_project_structure(context):
    """Behave step to check the subdirectories created by kedro new."""

    def is_created(name):
        """Check if path exists."""
        return (context.root_project_dir / name).exists()

    for path in ("README.md", "src", "data"):
        assert is_created(path)


@then('the expected tool directories and files should be created with "{tools}"')
def check_created_project_structure_from_tools(context, tools):
    """Behave step to check the subdirectories created by kedro new with tools."""

    def is_created(name):
        """Check if path exists."""
        return (context.root_project_dir / name).exists()

    # Base checks for any project
    for path in ["README.md", "src", "pyproject.toml", "requirements.txt"]:
        assert is_created(path), f"{path} does not exist"

    tools_list = (
        tools.split(",")
        if tools != "all"
        else ["lint", "test", "log", "docs", "data", "pyspark", "viz"]
    )

    if "lint" in tools_list:  # lint tool
        pass  # No files are added

    if "test" in tools_list:  # test tool
        assert is_created("tests"), "tests directory does not exist"

    if "log" in tools_list:  # log tool
        assert is_created("conf/logging.yml"), "logging configuration does not exist"

    if "docs" in tools_list:  # docs tool
        assert is_created("docs"), "docs directory does not exist"

    if "data" in tools_list:  # data tool
        assert is_created("data"), "data directory does not exist"

    if "pyspark" in tools_list:  # PySpark tool
        assert is_created("conf/base/spark.yml"), "spark.yml does not exist"

    if "viz" in tools_list:  # viz tool
        expected_reporting_path = Path(
            f"src/{context.package_name}/pipelines/reporting"
        )
        assert is_created(
            expected_reporting_path
        ), "reporting pipeline directory does not exist"


@then("the logs should show that {number} nodes were run")
def check_one_node_run(context, number):
    expected_log_line = f"Completed {number} out of {number} tasks"
    assert expected_log_line in context.result.stdout


@then('the logs should show that "{node}" was run')
def check_correct_nodes_run(context, node):
    expected_log_line = f"Running node: {node}"
    stdout = context.result.stdout
    clean_logs = util.clean_up_log(stdout)
    assert expected_log_line in clean_logs, (
        "Expected the following message segment to be printed on stdout: "
        f"{expected_log_line},\nbut got {stdout}"
    )


@then("the logs should show that load_node executed successfully")
def check_load_node_run(context):
    expected_log_line = "load_node executed successfully"
    stdout = context.result.stdout
    clean_logs = util.clean_up_log(stdout)
    assert expected_log_line in clean_logs, (
        "Expected the following message segment to be printed on stdout: "
        f"{expected_log_line},\nbut got {stdout}"
    )


@then("I should get a successful exit code")
def check_status_code(context):
    if context.result.returncode != OK_EXIT_CODE:
        print(context.result.stdout)
        print(context.result.stderr)

        error_msg = (
            f"Expected exit code {OK_EXIT_CODE} but got {context.result.returncode}"
        )
        assert False, error_msg


@then("I should get an error exit code")
def check_failed_status_code(context):
    if context.result.returncode == OK_EXIT_CODE:
        print(context.result.stdout)
        print(context.result.stderr)

        error_msg = (
            f"Expected exit code other than {OK_EXIT_CODE} "
            f"but got {context.result.returncode}"
        )
        assert False, error_msg


@then('I should get a message including "{msg}"')
def check_message_printed(context, msg):
    """Check that specified message is printed to stdout (can be a segment)."""

    if isinstance(context.result, ChildTerminatingPopen):
        stdout = context.result.stdout.read().decode()
        context.result.terminate()
    else:
        stdout = context.result.stdout

    clean_logs = util.clean_up_log(stdout)
    assert msg in clean_logs, (
        "Expected the following message segment to be printed on stdout: "
        f"{msg},\nbut got {stdout}"
    )


@then('I should not get a message including "{msg}"')
def check_message_not_printed(context, msg):
    """Check that specified message is not printed to stdout."""

    if isinstance(context.result, ChildTerminatingPopen):
        stdout = context.result.stdout.read().decode()
        context.result.terminate()
    else:
        stdout = context.result.stdout

    assert msg not in stdout, (
        "Expected the following message segment not to be printed on stdout: "
        f"{msg},\nbut got {stdout}"
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
        f"{msg},\nbut got {stderr}"
    )


@then("there should be an additional cell in the jupyter notebook")
def check_additional_cell_added(context):
    """Check that an additional cell has been added compared to notebook
    coded by TEST_JUPYTER_ORG.
    """
    with open(
        str(context.root_project_dir / "notebooks" / "hello_world.ipynb"),
        encoding="utf-8",
    ) as test_nb_fh:
        context.nb_data = json.load(test_nb_fh)
        assert len(context.nb_data["cells"]) == 2  # noqa: PLR2004


@then("the output should be empty in all the cells in the jupyter notebook")
def check_output_cells_empty(context):
    """Check that all cells contain empty output array."""
    for cell in context.nb_data["cells"]:
        assert cell["outputs"] == []


@then("jupyter notebook should run on port {port:d}")
def check_jupyter_nb_proc_on_port(context: behave.runner.Context, port: int):
    """Check that jupyter notebook service is running on specified port.

    Args:
        context: Test context
        port: Port to check

    """
    url = f"http://localhost:{port}"
    try:
        _check_service_up(context, url, "Jupyter Server")
    finally:
        context.result.terminate()


@then("Jupyter Lab should run on port {port:d}")
def check_jupyter_lab_proc_on_port(context: behave.runner.Context, port: int):
    """Check that jupyter lab service is running on specified port.

    Args:
        context: Test context
        port: Port to check

    """
    url = f"http://localhost:{port}"
    try:
        _check_service_up(context, url, '<a href="/lab"')
    finally:
        context.result.terminate()


@then("docs should be generated")
def check_docs_generated(context: behave.runner.Context):
    """Check that new project docs are generated."""
    index_html = (
        context.root_project_dir / "docs" / "build" / "html" / "index.html"
    ).read_text("utf-8")
    project_repo = context.project_name.replace("-", "_")
    assert f"Welcome to project {project_repo}'s API docs!" in index_html, index_html


@then("requirements should be generated")
def check_reqs_generated(context: behave.runner.Context):
    """Check that new project requirements are generated."""
    reqs_path = context.root_project_dir / "requirements.lock"
    assert reqs_path.is_file()
    assert "This file is autogenerated by pip-compile" in reqs_path.read_text()


@then("{dependency} should be in the requirements")
def check_dependency_in_reqs(context: behave.runner.Context, dependency: str):
    reqs_path = context.root_project_dir / "requirements.txt"
    assert dependency in reqs_path.read_text()


@given("I have executed the load_node magic command")
@when("I execute the load_node magic command")
def exec_magic_command(context):
    """Execute Kedro target."""
    cmd = [context.python, "ipython_script.py"]
    context.result = run(
        cmd, env=context.env, cwd=str(context.root_project_dir), print_output=True
    )


@given('I have changed the current working directory to "{dir}"')
def change_dir(context, dir):
    """Execute Kedro target."""
    util.chdir(dir)


@when("I install project and its dev dependencies")
def pip_install_project_and_dev_dependencies(context):
    """Install project and its development dependencies using pip."""
    _ = run(
        [context.pip, "install", ".[dev]"],
        env=context.env,
        cwd=str(context.root_project_dir),
    )
