# Automated Testing

An important step towards achieving high code quality and maintainability in your Kedro project is the use of automated tests. Let's take a look at how you can set this up.

## Motivation

Software testing is the process of checking that the code you have written fulfils its requirements. Software testing can either be **manual** or **automated**. In the context of Kedro:
- **Manual testing** is when you run part or all of your project and check that the results are what you expect.
- **Automated testing** is writing new code (using code libraries called _testing frameworks_) that runs part or all of your project and automatically checks the results against what you expect.

As a project grows larger, new code will increasingly rely on existing code. Making changes in one part of the code base can unexpectedly break the intended functionality in another part.

The major disadvantage of manual testing is that it is time-consuming. Manual tests are usually run once for new functionality, directly after it has been added. Manual testing is a bad solution to the problem of breaking dependencies.

The solution to this problem is automated testing, which allows many tests across the codebase to be run in seconds, every time a new feature is added or an old one is changed. In this way, breaking changes can be discovered early, before any time is lost in production.

## Set up automated testing with pytest

There are many testing frameworks available for Python. One of the most popular is a [pytest](https://docs.pytest.org/). Pytest is often used in Python projects for its short, readable tests and powerful set of features.

Let's look at how you can start working with pytest in your Kedro project.

### Install pytest

Install pytest as you would install other packages with pip, making sure your project's virtual environment is active.

```bash
pip install pytest
```

### Create a /tests directory

Now that pytest is installed, you will need a place to put your tests. Create a `/tests` folder in the `/src' directory of your project.

```bash
mkdir <project_root>/src/tests
```

### Test directory structure

The subdirectories in your project's `/tests` directory should mirror the directory structure of your project's `<project_root>/src/<project_name>` directory. All files in the `/tests` folder should be named `test_<file_being_tested>.py`. For instance:

```
src
│   ...
└───<project_name>
│   └───pipelines
│       └───dataprocessing
│           │   ...
│           │   nodes.py
│           │   ...
│   
└───tests
│   └───pipelines
│       └───dataprocessing
│           │   ...
│           │   test_nodes.py
│           │   ...
```

### Create an example test

Now that you have a place to put your tests, you can create an example 

```
import pytest
from kedro.config import ConfigLoader
from kedro.framework.context import KedroContext
from kedro.framework.hooks import _create_hook_manager


@pytest.fixture
def config_loader():
    return ConfigLoader(conf_source=str(Path.cwd()))


@pytest.fixture
def project_context(config_loader):
    return KedroContext(
        package_name="kedro_re_run",
        project_path=Path.cwd(),
        config_loader=config_loader,
        hook_manager=_create_hook_manager(),
    )

class TestProjectContext:
    def test_project_path(self, project_context):
        assert project_context.project_path == Path.cwd()
```

### Run your tests

To run your tests, run `pytest` from within your project's root directory or from the `/src` directory.

```bash
cd <project_root>
pytest
```

If you wrote the example test above, you should then see the following output in your shell:

```
============================= test session starts ==============================
...
collected 1 item

src/tests/test_run.py .                                                  [100%]

============================== 1 passed in 0.38s ===============================
```

This output indicates that one test ran successfully in the file `src/tests/test_run.py`. For help writing your own tests and using all of the features of pytest, see the [docs](https://docs.pytest.org/).

## Add test coverage reports with pytest-cov

It can be useful to see how much of your project is covered by tests. For this, you can install and configure the [pytest-cov](https://pypi.org/project/pytest-cov/) plugin for pytest, which is based on the popular [coverage.py](https://coverage.readthedocs.io/) library.

### Install pytest-cov

Install pytest as you would install other packages with pip, making sure your project's virtual environment is active.

```bash
pip install pytest-cov
```

### Configure pytest to use pytest-cov

To configure pytest to generate a coverage report using pytest-cov, you can add the following lines to your `<project_root>/pyproject.toml` file (creating it if it does not exist).

```
[tool.pytest.ini_options]
addopts = """
--cov-report term-missing \
--cov src/<project_name> -ra"""
```

### Run pytest with pytest-cov

Now when you run `pytest` you will receive a test coverage report. Running `pytest` in the spaceflights starter with pytest-cov installed results in the following additional report.

```
Name                                                     Stmts   Miss  Cover   Missing
--------------------------------------------------------------------------------------
src/spaceflights/__init__.py                                 1      1     0%   4
src/spaceflights/__main__.py                                30     30     0%   4-47
src/spaceflights/pipeline_registry.py                        7      7     0%   2-16
src/spaceflights/pipelines/__init__.py                       0      0   100%
src/spaceflights/pipelines/data_processing/__init__.py       1      1     0%   3
src/spaceflights/pipelines/data_processing/nodes.py         25     25     0%   1-67
src/spaceflights/pipelines/data_processing/pipeline.py       5      5     0%   1-8
src/spaceflights/pipelines/data_science/__init__.py          1      1     0%   3
src/spaceflights/pipelines/data_science/nodes.py            20     20     0%   1-55
src/spaceflights/pipelines/data_science/pipeline.py          8      8     0%   1-40
src/spaceflights/settings.py                                 0      0   100%
--------------------------------------------------------------------------------------
TOTAL                                                       98     98     0%
```

This is the simplest report that coverage.py (via pytest-cov) will produce, it gives an overview of how many of the executable statements in each project file are covered by tests. For a full set of features offered by coverage.py, see the [docs](https://coverage.readthedocs.io/).
