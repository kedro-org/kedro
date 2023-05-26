# Code formatting and linting

## Introduction

Code formatting guidelines set a standard for the layout of your code, for stylistic elements such as use of line breaks and whitespace. Format doesn't have any impact on how the code works, but using a consistent style makes your code more readable, and makes it more likely to be reused.

Linting tools check your code for errors such as a missing bracket or line indent. This can save time and frustration because you can catch errors in advance of running the code.

As a project grows and goes through various stages of development it becomes important to maintain code quality. Using a consistent format and linting your code ensures that it is consistent, readable, and easy to debug and maintain.

## Set up Python tools
There are a variety of Python tools available to use with your Kedro projects. This guide shows you how to use
[`black`](https://github.com/psf/black), [`flake8`](https://github.com/PyCQA/flake8), and
[`isort`](https://github.com/PyCQA/isort) to format and lint your Kedro projects.
- **`black`** is a [PEP 8](https://peps.python.org/pep-0008/) compliant opinionated Python code formatter. `black` can
check for styling inconsistencies and reformat your files in place.
[You can read more in the `black` documentation](https://black.readthedocs.io/en/stable/).
- **`flake8`** is a wrapper around [`pep8`](https://pypi.org/project/pep8/),
[`pyflakes`](https://pypi.org/project/pyflakes/), and [`mccabe`](https://pypi.org/project/mccabe/) which can lint code and format it with respect to [PEP 8](https://peps.python.org/pep-0008/),
and check the [cyclomatic complexity](https://www.ibm.com/docs/en/raa/6.1?topic=metrics-cyclomatic-complexity) of your code base.
[You can read more in the `flake8` documentation](https://flake8.pycqa.org/en/latest/).
- **`isort`** is a Python library used to reformat code by sorting imports alphabetically and automatically separating them into sections by
type. [You can read more in the `isort` documentation](https://pycqa.github.io/isort/).

### Install the tools
Install `black`, `flake8`, and `isort` by adding the following lines to your project's `requirements.txt`
file:
```text
black # Used for formatting code
flake8 # Used for linting and formatting
isort # Used for formatting code (sorting module imports)
```
To install all the project-specific dependencies, including the linting tools, navigate to the root directory of the
project and run:
```bash
pip install -r requirements.txt
```
Alternatively, you can individually install the linting tools using the following shell commands:
```bash
pip install black
pip install flake8
pip install isort
```
#### Configure `flake8`

Store your `flake8` configuration in a file named `setup.cfg` within your project root. The Kedro starters use the [following configuration](https://github.com/kedro-org/kedro-starters/blob/main/pandas-iris/%7B%7B%20cookiecutter.repo_name%20%7D%7D/setup.cfg):

```text
[flake8]
max-line-length=88
extend-ignore=E203
```

### Run the tools
Use the following commands to run lint checks:
```bash
black --check <project_root>
isort --profile black --check <project_root>
```
You can also have `black` and `isort` automatically format your code by omitting the `--check` flag. Since `isort` and
`black` both format your imports, adding `--profile black` to the `isort` run helps avoid potential conflicts.

Use the following to invoke `flake8`:
```bash
flake8 <project_root>
```

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
Below is a sample `YAML` file with entries for `black`,`flake8`, and `isort`:
```yaml
repos:
  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort
        name: isort (python)
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: ''  # pick a git hash / tag to point to
    hooks:
      - id: flake8

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
