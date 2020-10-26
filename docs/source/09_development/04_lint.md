# Linting your Kedro project

To follow these instructions, you will need to install the  `pylint` package, subject to GPL licence.

> *Note:* This documentation is based on `Kedro 0.16.6`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

You can lint your project code to ensure code quality using the `kedro lint` command, your project is linted with [`black`](https://github.com/psf/black) (projects created with Python 3.6 and above), [`flake8`](https://gitlab.com/pycqa/flake8) and [`isort`](https://github.com/timothycrosley/isort). If you prefer to use [pylint](https://www.pylint.org/), a popular linting tool, then the sample commands you can use to help with this are included in the script below:

```bash
isort
pylint -j 0 src/<your_project>
pylint -j 0 --disable=missing-docstring,redefined-outer-name src/tests
```

Alternatively, you can opt to use it as a plugin to your Kedro project. To do this, add the following code snippet to `cli.py` in your project package directory:

```python
@cli.command()
def lint():
    """Check the Python code quality."""
    python_call("isort", ["-rc", "src/<your_project>", "src/tests"])
    python_call("pylint", ["-j", "0", "src/<your_project>"])
    python_call(
        "pylint",
        ["-j", "0", "--disable=missing-docstring,redefined-outer-name", "src/tests"],
    )
```

To trigger the behaviour, simply run the following command in your terminal window:
```bash
kedro lint
```

Make sure you also include the dependency in your `requirements.txt`, i.e:
```text
pylint>=2.3.1,<3.0
```
