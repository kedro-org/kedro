# Code formatting and linting

## Introduction

Code formatting guidelines set a standard for the layout of your code, for stylistic elements such as use of line breaks and whitespace. Format doesn't have any impact on how the code works, but using a consistent style makes your code more readable, and makes it more likely to be reused.

Linting tools check your code for errors such as a missing bracket or line indent. This can save time and frustration because you can catch errors in advance of running the code.

As a project grows and goes through various stages of development it becomes important to maintain code quality. Using a consistent format and linting your code ensures that it is consistent, readable, and easy to debug and maintain.

## Set up Python tools
There are a variety of Python tools available to use with your Kedro projects. This guide shows you how to use [`black`](https://github.com/psf/black) and [`ruff`](https://beta.ruff.rs).
- **`black`** is a [PEP 8](https://peps.python.org/pep-0008/) compliant opinionated Python code formatter. `black` can
check for styling inconsistencies and reformat your files in place.
[You can read more in the `black` documentation](https://black.readthedocs.io/en/stable/).
- **`ruff`** is a fast linter that replaces `flake8`, `pylint`, `pyupgrade`, `isort` and [more](https://beta.ruff.rs/docs/rules/).
  - It helps to make your code compliant to [`pep8`](https://pypi.org/project/pep8/).
  - It reformats code by sorting imports alphabetically and automatically separating them into sections by
type. [You can read more in the `isort` documentation](https://pycqa.github.io/isort/).


### Install the tools
Install `black` and `ruff` by adding the following lines to your project's `requirements.txt`
file:
```text
black # Used for formatting code
ruff # Used for linting, formatting and sorting module imports

```
To install all the project-specific dependencies, including the linting tools, navigate to the root directory of the
project and run:
```bash
pip install -r requirements.txt
```
Alternatively, you can individually install the linting tools using the following shell commands:
```bash
pip install black ruff
```
#### Configure `ruff`
`ruff` read configurations from `pyproject.toml` within your project root. You can enable different rule sets within the `[tool.ruff]` section. For example, the rule set `F` is equivalent to `Pyflakes`.

To start with `ruff`, we recommend adding this section to enable a few basic rules sets.
```toml
[tool.ruff]
select = [
    "F",  # Pyflakes
    "E",  # Pycodestyle
    "W",  # Pycodestyle
    "UP",  # pyupgrade
    "I",  # isort
    "PL", # Pylint
]
ignore = ["E501"]  # Black take care off line-too-long
```

```{note}
It is a good practice to [split your line when it is too long](https://beta.ruff.rs/docs/rules/line-too-long/), so it can be read easily even in a small screen. `ruff` treats this slightly different from `black`, when using together we recommend to disable this rule, i.e. `E501` to avoid conflicts.
```

### Run the tools
Use the following commands to run lint checks:
```bash
black --check <project_root>
ruff check <project_root>
```
You can also have `black` automatically format your code by omitting the `--check` flag.

## Automated formatting and linting with `pre-commit` hooks

You can automate the process of formatting and linting with [`pre-commit`](https://github.com/pre-commit/pre-commit) hooks.
These hooks are run before committing your code to your repositories to automatically point out formatting issues,
making code reviews easier and less time-consuming.

### Install `pre-commit`
You can install `pre-commit` along with other dependencies by including it in the `requirements.txt` file of your
Kedro project by adding the following line:
```text
pre-commit
```
You can also install `pre-commit` using the following command:
```bash
pip install pre-commit
```
### Add `pre-commit` configuration file
Create a file named `.pre-commit-config.yaml` in your Kedro project root directory. You can add entries for the hooks
you want to run before each `commit`.
Below is a sample `YAML` file with entries for `ruff` and black`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    # Ruff version.
    rev: v0.0.270
    hooks:
      - id: ruff

  - repo: https://github.com/psf/black
    rev: 22.8.0
    hooks:
      - id: black
        language_version: python3.9
```
### Install git hook scripts
Run the following command to complete installation:
```bash
pre-commit install
```
This enables `pre-commit` hooks to run automatically every time you execute `git commit`.
