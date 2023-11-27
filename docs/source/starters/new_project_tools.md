# Using tools to configure your Kedro project

## Configuring your tool selection

There are several ways to configure your project tool when creating a new Kedro project.

### Through the `kedro new` prompt

Navigate to the directory in which you would like to create your new Kedro project, and run the following command:

```bash
kedro new
```

This will start the new project creation wizard<!--wording-->, promptng you to input a project name, any tools you would like to include, and whether or not you would like to populate the project with example code. The creation wizard will provide you with a list of available tools and a brief description of each:

| ![cli-prompt.jpg](IMAGE RESOURCE PLACEHOLDER) |
|:--:|
| *Prompt for tools selection* |

When selecting your desired tools, you may provide them as comma separated values `(1,2,4)`, a range of values `(3-5)`, or using the key words `all` or `none`.

Skipping the prompt by entering no value will result in the default selection of `none`.

### Through the use of the flag `kedro new --tools/-t=...`

You may also specify your tools selection directly from the command line by using the flag `--tools`:

```bash
kedro new --tools=<your tool selection>
```

To specify your desired tools you must provide them by name as a comma separated list, for example `--tools=lint,test,viz`. Currently the following tools are availavle for selection: lint, test, log, docs, data, pyspark, and viz.

A list of available tools can also be accessed by running `kedro new --help`

![cli-output.jpg](IMAGE RESOURCE PLACEHOLDER)

Providing your tool configuration in the command line will skip the tool selection prompt as part of the project creation wizard. The other prompts, for projet name and example code, can be skipped by the flags `--name` and `--example` respectively.

### Using a configuration file `kedro new --config/-c=`

You can also supply your selected tools by providing a config file to your `kedro new` command. Consider the following config:

```yaml
"project_name":
    "My Project"

"repo_name":
    "my-project"

"python_package":
    "my project"

"tools":
    "2-6"
```

Then, after navigating to the directory in which you would like to create your new project, run the following command:

```bash
kedro new --config=<path/to/config.yml>
```

Note: When using a config file to create a new project, you must provide values for the project, repository and package names. Specifying your tools selection is optional, omitting them results in the default selection of `none`.

## Kedro tools
<!--TO DO: FILL PLACEHOLDERS-->

Tools are [modular functionalities that can be added to a basic Kedro project] . They allow for [...]. When creating a new project, you may select one or more of the available tools, or none at all.

The available tools include: linting, testing, custom logging, documentation, data structure, Pyspark, and Kedro-Viz.

### Linting

The Kedro linting tool introduces [`black`](https://black.readthedocs.io/en/stable/index.html) and [`ruff`](https://docs.astral.sh/ruff/) as dependencies in your new project's requirements. After project creation, make sure these are installed by running the following command:

```bash
pip install -r path/to/project/root/requirements.txt
```

The linting tool will configure `ruff` with the following settings by default:
```toml
#pyproject.toml

[tool.ruff]
line-length = 88
show-fixes = true
select = [
    "F",   # Pyflakes
    "W",   # pycodestyle
    "E",   # pycodestyle
    "I",   # isort
    "UP",  # pyupgrade
    "PL",  # Pylint
    "T201", # Print Statement
]
ignore = ["E501"]  # Black takes care of line-too-long
```

With these installed, you can then make use of the following commands to format and lint your code:

```bash
ruff format path/to/project/root
black path/to/project/root --check
```

Though it has no impact on how your code works, linting is important for code quality because improves consistency, readabity, debugging, and maintainability. To learn more about linting your Kedro projects, check our [linting documentation](../development/linting.md).

### Testing

This tool introduces the `tests` directory to the new project's structure, containing the file `test_run.py` with an example unit test.

| ![cli-output.jpg](IMAGE RESOURCE PLACEHOLDER) |
|:--:|
| *Prompt for tools selection* |

The tool leverages [`pytest`](https://docs.pytest.org/en/7.4.x/) with the following configuration:

```toml
[tool.pytest.ini_options]
addopts = """
--cov-report term-missing \
--cov src/{{ cookiecutter.python_package }} -ra"""

[tool.coverage.report]
fail_under = 0
show_missing = true
exclude_lines = ["pragma: no cover", "raise NotImplementedError"]
```

To run your tests, use the following command:
```bash
pytest path/to/your/project/root/tests
```

Kedro promotes the use of unit tests to achieve high code quality and maintainability in your projects. To read more about unit testing with Kedro, check our [testing documentation](../development/automated_testing.md#set-up-automated-testing-with-pytest)

### Custom logging

Selecting the custom logging tool introduces the file `logging.yml` to your project's `conf` directory.

| ![cli-output.jpg](IMAGE RESOURCE PLACEHOLDER) |
|:--:|
| *Prompt for tools selection* |

This tool allows you to customise your logging configuration instead of using [Kedro's default logging configuration](https://github.com/kedro-org/kedro/blob/main/kedro/framework/project/default_logging.yml). The populated `conf/logging.yml` provides two additional logging handlers: `console` and `info_file_handler`, as well as `rich` that is available in the default configuration. However, only `info_file_handler` and `rich` are used.

To learn more about using logging in your project, or modifying the logging configuration, take a look at out [logging documentation](../logging/index.md).
