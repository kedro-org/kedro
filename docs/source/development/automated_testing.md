# Automated testing

An important step towards achieving high code quality and maintainability in your Kedro project is the use of automated tests. Let's look at how you can set this up.
## Introduction

Software testing is the process of checking that the code you have written fulfills its requirements. Software testing can either be **manual** or **automated**. In the context of Kedro:
- **Manual testing** is when you run part or all of your project and check that the results are what you expect.
- **Automated testing** is writing new code (using libraries called _testing frameworks_) that runs part or all of your project and automatically checks the results against what you expect.

As a project grows larger, new code will increasingly rely on existing code. As these interdependencies grow, making changes in one part of the code base can unexpectedly break the intended functionality in another part.

The major disadvantage of manual testing is that it is time-consuming. Manual tests are usually run once, directly after new functionality has been added. It is impractical to repeat manual tests for the entire code base each time a change is made, which means this strategy often misses breaking changes.

The solution to this problem is automated testing. Automated testing allows many tests across the whole code base to be run in seconds, every time a new feature is added or an old one is changed. In this way, breaking changes can be discovered during development rather than in production.

## Set up automated testing with `pytest`

There are many testing frameworks available for Python. One of the most popular is `pytest` (see the [project's home page](https://docs.pytest.org/en/7.1.x/) for a quick overview). `pytest` is often used in Python projects for its short, readable tests and powerful set of features.

Let's look at how you can start working with `pytest` in your Kedro project.

### Install test requirements
Before getting started with test requirements, it is important to ensure you have installed your project locally. This allows you to test different parts of your project by importing them into your test files.


To install your project including all the project-specific dependencies and test requirements:
1. Add the following section to the `pyproject.toml` file located in the project root:
```toml
[project.optional-dependencies]
dev = [
    "pytest-cov",
    "pytest-mock",
    "pytest",
]
```

2. Navigate to the root directory of the project and run:
```bash
pip install ."[dev]"
```

Alternatively, you can individually install test requirements as you would install other packages with `pip`, making sure you have installed your project locally and your [project's virtual environment is active](../get_started/install.md#create-a-virtual-environment-for-your-kedro-project).

1. To install your project, navigate to your project root and run the following command:

```bash
pip install -e .
```
>**NOTE**: The option `-e` installs an editable version of your project, allowing you to make changes to the project files without needing to re-install them each time.

2. Install test requirements one by one:
```bash
pip install pytest
```

### Create a `/tests` directory

Now that `pytest` is installed, you will need a place to put your tests. Create a `/tests` folder in the root directory of your project.

```bash
mkdir <project_root>/tests
```

### Test directory structure

The subdirectories in your project's `/tests` directory should mirror the directory structure of your project's `/src/<package_name>` directory. All files in the `/tests` folder should be named `test_<file_being_tested>.py`. See an example `/tests` folder below.

```
src
│   ...
└───<package_name>
│   └───pipelines
│       └───dataprocessing
│           │   ...
│           │   nodes.py
│           │   ...
│
tests
└───pipelines
│   └───dataprocessing
│       │   ...
│       │   test_nodes.py
│       │   ...
```

### Create an example test

Now that you have a place to put your tests, you can create an example test in the new file `/src/tests/test_run.py`.
This example test demonstrates how to programmatically execute a `kedro run` using the `KedroSession` class.

```
from pathlib import Path
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project

class TestKedroRun:
    def test_kedro_run(self):
        bootstrap_project(Path.cwd())

        with KedroSession.create(project_path=Path.cwd()) as session:
            assert session.run() is not None
```

This test is redundant, but it introduces a few of `pytest`'s core features and demonstrates the layout of a test file:
- Tests are implemented in methods or functions beginning with `test_` and classes beginning with `Test`.
- The `assert` statement is used to compare the result of the test with an expected value.

Although this specific example does not utilise fixtures, they are an essential part of pytest for defining reusable resources across tests. See [Fixtures](https://docs.pytest.org/en/7.1.x/explanation/fixtures.html#about-fixtures)

Tests should be named as descriptively as possible, especially if you are working with other people. For example, it is easier to understand the purpose of a test with the name `test_node_passes_with_valid_input` than a test with the name `test_passes`.

You can read more about the [basics of using `pytest` on the getting started page](https://docs.pytest.org/en/7.1.x/getting-started.html). For help writing your own tests and using all of the features of `pytest`, see the [project documentation](https://docs.pytest.org/).


### Run your tests

To run your tests, run `pytest` from within your project's root directory.

```bash
cd <project_root>
pytest
```

If you created the example test in the previous section, you should see the following output in your shell.

```
============================= test session starts ==============================
...
collected 1 item

tests/test_run.py .                                                  [100%]

============================== 1 passed in 0.38s ===============================
```

This output indicates that one test ran successfully in the file `src/tests/test_run.py`.

## Add test coverage reports with `pytest-cov`

It can be useful to see how much of your project is covered by tests. For this, you can install and configure the [`pytest-cov`](https://pypi.org/project/pytest-cov/) plugin for `pytest`, which is based on the popular [`coverage.py` library](https://coverage.readthedocs.io/).

### Install `pytest-cov`

Install `pytest` as you would install other packages with pip, making sure your [project's virtual environment is active](../get_started/install.md#create-a-virtual-environment-for-your-kedro-project).

```bash
pip install pytest-cov
```

### Configure `pytest` to use `pytest-cov`

To configure `pytest` to generate a coverage report using `pytest-cov`, you can add the following lines to your `<project_root>/pyproject.toml` file (creating it if it does not exist).

```
[tool.pytest.ini_options]
addopts = """
--cov-report term-missing \
--cov src/<package_name> -ra"""
```

### Run `pytest` with `pytest-cov`

Running `pytest` in the spaceflights starter with `pytest-cov` installed results in the following additional report.

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

This is the simplest report that `coverage.py` (via `pytest-cov`) will produce. It gives an overview of how many of the executable statements in each project file are covered by tests. For detail on the full set of features offered, see the [`coverage.py` docs](https://coverage.readthedocs.io/).
