# Linting

## Introduction
Lint, or a linter, is a static code analysis tool used to flag programming errors, bugs, stylistic errors and suspicious constructs.
As a project grows and goes through various stages of development, it becomes important to maintain the code quality. Linting makes
your code more readable, easy to debug and maintain, and stylistically consistent.
## Set up linting tools
There are a variety of linting tools available to use
with your Kedro projects. This guide shows you how to use [`black`](https://github.com/psf/black), [`flake8`](https://gitlab.com/pycqa/flake8), and [`isort`](https://github.com/PyCQA/isort) to lint your Kedro projects.
- **`black`** is a [PEP 8](https://peps.python.org/pep-0008/) compliant opinionated Python code formatter. Read the full documentation [here](https://black.readthedocs.io/en/stable/).
- **`flake8`** is a wrapper around [`pep8`](https://pypi.org/project/pep8/), [`pyflakes`](https://pypi.org/project/pyflakes/), and [`mccabe`](https://pypi.org/project/mccabe/). Read the full documentation [here](https://flake8.pycqa.org/en/latest/).
- **`isort`** is a Python library used to sort imports alphabetically. Read the full documentation [here](https://pycqa.github.io/isort/).

### Install linting tools
You can install `black`, `flake8`, and `isort` by adding the following lines to your project's `src/requirements.txt` file:
```text
black==22.1.0 # Used for formatting code
flake8>=3.7.9, <5.0 # Used for linting code
isort~=5.0 # Used for linting code
```
To install all the project-specific dependencies, including the linting tools, navigate to the root directory of the project and run:
```bash
pip install -r src/requirements.txt
```
Alternatively, you can individually install the linting tools using the following shell commands:
```bash
pip install black
pip install flake8
pip install isort
```

### Run linting tools
Use the following commands to run lint checks:
```bash
black --check <project_root>
flake8 <project_root>
isort --check <project_root>
```
You can also have `black` and `isort` automatically format your code by omitting the `--check` flag.

## Automating linting with `pre-commit` hooks

You can also automate linting by using [`pre-commit`](https://github.com/pre-commit/pre-commit) hooks.
These hooks are run before committing your code to your repositories to automatically point out formatting issues,
making code reviews easier and less time-consuming.

### Install `pre-commit`
You can install `pre-commit` along with other dependencies by including it in the `src\requirements.txt` file of your
Kedro project by adding the following line:
```text
pre-commit
```
You can also install is using the following command:
```bash
pip install pre-commit
```
### Add pre-commit configuration file
Create a file named `.pre-commit-config.yaml`. You can add entries for the hooks you want to run before each `commit`.
Below is a sample `YAML` file with entries for `black`,`flake8`, and `isort`:
```yaml
repos:
  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort
        name: isort (python)

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
This enables `pre-commit` hooks to run automatically every time you  `git commit`.
