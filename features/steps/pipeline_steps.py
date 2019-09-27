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

"""Behave step definitions for running pipelines end to end."""

import logging
import shutil
import sys
from io import StringIO
from pathlib import Path
from shutil import copyfile

import behave
import pandas as pd
import yaml
from behave import given, then, when
from pandas.util.testing import assert_frame_equal

import features.steps.util as util
from features.steps.sh_run import run
from kedro.io import DataCatalog, MemoryDataSet

LOG_EVIDENCE_PHRASE = "Running a risky operation"
INTENTIONAL_FAILURE = "Something intentionally went wrong."
INDENT4 = " " * 4
INDENTED_NEWLINE = "\n" + INDENT4


behave.register_type(CSV=util.parse_csv)


def identity(item):
    """Function intended for identity node."""
    return item


def concatenate(item1, item2):
    """Function intended for concatinating two items."""
    return item1 + item2


def sum_dfs(dataframe1, dataframe2):
    """pd.DataFrame Sum method that outputs a warning in the logs."""
    logging.getLogger("kedro.runner").warning(LOG_EVIDENCE_PHRASE)
    return dataframe1 + dataframe2.values


def failing_function(item):
    """Fail with an exception."""
    raise RuntimeError(INTENTIONAL_FAILURE)


def _set_up_temp_logging(context):
    context.log_data = StringIO()
    handler = logging.StreamHandler(context.log_data)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger = logging.getLogger("kedro.runner")
    logger.setLevel(logging.INFO)
    logger.handlers = []
    logger.addHandler(handler)


def _setup_template_files(context):
    curr_dir = Path(__file__).parent
    pipeline_file = (
        context.root_project_dir
        / "src"
        / context.project_name.replace("-", "_")
        / "pipeline.py"
    )

    catalog_file = context.root_project_dir / "conf" / "base" / "catalog.yml"

    if pipeline_file.exists():
        pipeline_file.unlink()
    copyfile(str(curr_dir / "pipeline_template.py"), str(pipeline_file))

    if catalog_file.exists():
        catalog_file.unlink()
    copyfile(str(curr_dir / "e2e_test_catalog.yml"), str(catalog_file))

    with catalog_file.open("r") as cat_file:
        catalog = yaml.safe_load(cat_file)

    context.output_file1 = context.root_project_dir / catalog["E"]["filepath"]
    context.output_file2 = context.root_project_dir / catalog["F"]["filepath"]

    df_a = pd.DataFrame({"col1": [1, 2], "col2": [3, 4], "col3": [5, 6]})
    df_c = pd.DataFrame({"col1": [9, 8], "col2": [7, 6], "col3": [5, 4]})

    df_a.to_csv(context.root_project_dir / catalog["A"]["filepath"], index=False)
    df_c.to_csv(context.root_project_dir / catalog["C"]["filepath"], index=False)

    _add_external_packages(context)


def _add_external_packages(context):
    external_packages = getattr(context, "external_packages", [])

    if not external_packages:
        return

    pipeline_file = (
        context.root_project_dir
        / "src"
        / context.project_name.replace("-", "_")
        / "pipeline.py"
    )
    with pipeline_file.open("at", encoding="utf-8") as _pf:
        _imports = "\n".join("import {}".format(p) for p in external_packages)
        _pf.write("\n{0}\n".format(_imports))

    requirements_file = context.root_project_dir / "src" / "requirements.txt"
    with requirements_file.open("at", encoding="utf-8") as _reqs:
        _reqs.write("\n".join(external_packages) + "\n")


def _create_template_project(context):
    # Sets the following fields on the context:
    # - project_name      (the simple project name == project-pipeline)
    # - temp_dir          (the directory containing the created project)
    # - root_project_dir  (the full path to the created project)
    # - include_example   (the project contains code example)

    context.project_name = "project-pipeline"
    context.config_file = context.temp_dir / "config"

    root_project_dir = context.temp_dir / context.project_name
    context.root_project_dir = root_project_dir

    context.include_example = True

    config = {
        "project_name": context.project_name,
        "repo_name": context.project_name,
        "output_dir": str(context.temp_dir),
        "python_package": context.project_name.replace("-", "_"),
        "include_example": context.include_example,
    }

    with context.config_file.open("w") as config_file:
        yaml.dump(config, config_file, default_flow_style=False)

    res = run([context.kedro, "new", "-c", str(context.config_file)], env=context.env)
    assert res.returncode == 0

    _setup_template_files(context)


def resolve_free_inputs(context):
    catalog = context.catalog if hasattr(context, "catalog") else None
    feed_dict = context.feed_dict if hasattr(context, "feed_dict") else None
    return catalog, feed_dict


@given(
    "I have defined an io catalog containing "
    '["{key1}", "{key2}", "{key3}", "{key4}"]'
)
def set_catalog(context, key1, key2, key3, key4):
    ds1 = pd.DataFrame({"col1": [1, 2], "col2": [3, 4], "col3": [5, 6]})
    ds2 = pd.DataFrame({"col1": [9, 8], "col2": [7, 6], "col3": [5, 4]})
    context.catalog = DataCatalog(
        {
            key1: MemoryDataSet(ds1),
            key2: MemoryDataSet(),
            key3: MemoryDataSet(ds2),
            key4: MemoryDataSet(),
        }
    )


@given('I have added external packages "{external_packages}" to project requirements')
def add_external_packages(context, external_packages):
    context.external_packages = [p.strip() for p in external_packages.split(",")]


@given("I have included a pipeline definition in a project template")
def create_template_with_pipeline(context):
    _create_template_project(context)


@given('I have defined a node "{node_name}" tagged with {tags:CSV}')
def node_tagged_with(context, node_name, tags):
    """
    Check tagging in `pipeline_template.py` is consistent with tagging
    descriptions in background steps
    """
    sys.path.append(
        str(context.root_project_dir / "src" / context.project_name.replace("-", "_"))
    )
    import pipeline  # pylint: disable=import-error,useless-suppression

    # pylint: disable=no-member
    context.project_pipeline = pipeline.create_pipelines()["__default__"]
    node_objs = [n for n in context.project_pipeline.nodes if n.name == node_name]
    assert node_objs
    assert set(tags) == node_objs[0].tags


@given('I have set the project log level to "{log_level}"')
def change_log_level_proj(context, log_level):
    logging_yml = context.root_project_dir / "conf" / "base" / "logging.yml"
    with logging_yml.open() as file_handle:
        logging_conf = yaml.safe_load(file_handle)

    logging_conf["handlers"]["console"]["level"] = log_level
    logging_conf["loggers"]["kedro.pipeline"]["level"] = log_level
    logging_conf["root"]["level"] = log_level

    with logging_yml.open("w") as file_handle:
        yaml.dump(logging_conf, file_handle)


@when("the template pipeline is run")
def run_template_pipeline(context):
    run_cmd = [context.kedro, "run"]
    context.run_result = run(
        run_cmd, env=context.env, cwd=str(context.root_project_dir)
    )
    if context.run_result.returncode == 0:
        context.df_e = pd.read_csv(context.output_file1)
        context.df_f = pd.read_csv(context.output_file2)
    shutil.rmtree(str(context.root_project_dir))


@then("it should successfully produce the results")
def check_template_run_success(context):
    if context.run_result.returncode:
        print(context.run_result.stdout)
        print(context.run_result.stderr)
        assert False
    assert_frame_equal(context.df_e, context.df_f)
    assert context.df_e.values.tolist() == [[10, 10, 10], [10, 10, 10]]
    assert context.df_f.values.tolist() == [[10, 10, 10], [10, 10, 10]]


@then('it should fail with an error message including "{msg}"')
def check_template_run_fail(context, msg):
    assert context.run_result.returncode > 0
    try:
        assert msg in context.run_result.stderr
    except AssertionError:
        print(context.run_result.stderr)
        raise
