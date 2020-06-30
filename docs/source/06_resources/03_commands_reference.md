# Guide to CLI commands

> *Note:* This documentation is based on `Kedro 0.16.2`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

The `kedro` command line interface (CLI) helps with reproducibility in projects by allowing you to associate a set of commands and dependencies with a target and then execute them from the command line when inside a Kedro project directory. All project related CLI commands should be run from the project’s root directory.

The supported commands are specified in the `kedro_cli.py` file. It is easy to extend `kedro_cli.py` by either modifying the file or injecting commands into it by using the [`plugin` framework](../04_user_guide/10_developing_plugins.md).

### Autocomplete

To allow your shell to autocomplete `kedro` commands, you can add the following to your `.bashrc` (or just run it on the command line)

```
eval "$(_KEDRO_COMPLETE=source kedro)"
```

## Global Kedro commands

Show version and exit:

```bash
kedro -V
kedro --version
```

See extensive logging and error stack traces:

```bash
kedro -v
kedro --verbose
```

Get help on Kedro commands:

```bash
kedro -h
kedro --help
```

Create a new kedro project:

```bash
kedro new
```

See the Kedro API documentation (including the tutorial):

```bash
kedro docs
```

## Project-specific Kedro commands

### `kedro run`
Calls the `run()` method of the `ProjectContext` defined in `run.py` (`src/project-name/run.py`)

To make sure the project is shareable and reproducible, you should maintain the `kedro run` program definitions in the `kedro_cli.py` to point to the entry point in your project.

### `kedro build-reqs`
Build the project dependency requirements. This command will run [`pip-compile`](https://github.com/jazzband/pip-tools#example-usage-for-pip-compile) on `src/requirements.in` file. If the file doesn't exist, Kedro will create it by copying the contents from `src/requirements.txt`. `kedro build-reqs` also accepts and passes through CLI options accepted by `pip-compile`. For example, `kedro build-reqs --generate-hashes` will call `pip-compile --generate-hashes src/requirements.in`.

### `kedro install`
Install all package dependencies specified in `src/requirements.txt`. `kedro install` will also compile your project dependencies (by running [`kedro build-reqs`](#kedro-build-reqs) behind the scenes) the first time you run `kedro install`. If you don't want Kedro to compile the requirements (for performance reasons, for example), run `kedro install --no-build-reqs`. To recompile the requirements, run `kedro install --build-reqs`. We recommend recompiling your requirements every time you update `src/requirements.in` file.

> *Note:* As project dependencies may evolve very quickly, we strongly recommend working with compiled requirements, which is the default behaviour of `kedro install`, as mentioned above. This helps to keep your development environment reproducible, ensures compatibility between the dependencies and prevents version conflicts, which are often hard to debug.

### `kedro test`
Run all `pytest` unit tests found in `src/tests`, including coverage (see the file `.coveragerc`).

### `kedro package`
Package your application as one `.egg` file  and one `.whl` file within the `src/dist/` folder of your project. For further information about packaging for Python, documentation is provided [here](https://packaging.python.org/overview/).

### `kedro build-docs`
Build the project documentation using the [Sphinx](https://www.sphinx-doc.org) framework. To further customise it, please refer to `docs/source/conf.py` and the [corresponding section](http://www.sphinx-doc.org/en/master/usage/configuration.html) of the Sphinx documentation.

### `kedro jupyter notebook`, `kedro jupyter lab`, `kedro ipython`
Start a Jupyter Notebook, Lab or REPL session respectively.

Every time you start or restart a notebook kernel, a startup script (`<project-root>/.ipython/profile_default/startup/00-kedro-init.py`) will add the following variables in scope:
- `context` (Instance of `ProjectContext` class defined in `src/project-name/run.py`) (The details of how to use `context` can be found [here](../04_user_guide/11_ipython.md))
- `startup_error` (`Exception`)

To reload these at any point in your notebook (e.g. if you updated `catalog.yml`) use the line magic `%reload_kedro`.

This [line magic](https://ipython.readthedocs.io/en/stable/interactive/magics.html#line-magics) can be also used to see the error message if any of the variables above are undefined.

> *Note:* If you get an error message `Module ``<module_name>`` not found. Make sure to install required project dependencies by running ``kedro install`` command first.` when running any of those commands, it indicates that some Jupyter or IPython dependencies are not installed in your environment. To resolve this you will need to a) make sure the corresponding dependency is present in `src/requirements.in` (`src/requirements.txt` if not compiled), b) run [`kedro install`](#kedro-install) command from your terminal.

### `kedro jupyter convert`
Copy the code from cells [tagged](https://jupyter-notebook.readthedocs.io/en/stable/changelog.html#cell-tags) with `node` tag into Python files under `src/<package_name>/nodes/` in a Kedro project.

### `kedro lint`
Lint your project code using the `kedro lint` command. Your project is linted with [`black`](https://github.com/psf/black), [`flake8`](https://gitlab.com/pycqa/flake8) and [`isort`](https://github.com/timothycrosley/isort).

### `kedro activate-nbstripout`
Typically output cells of Jupyter Notebook should not be tracked by git, especially if they contain sensitive information.

This command adds a `git hook` which clears all notebook output cells before committing anything to `git`.  This needs to run only once per local repository.

### `kedro catalog list`
This command shows datasets per pipeline per type. The result includes datasets that are/aren't used by a specific pipeline. It also accept optional `--pipeline` argument that allows specifying pipeline name(s) (comma-separated value) for which the datasets should be shown, e.g. `kedro catalog list --pipeline "ds,de"`.

### `kedro pipeline list`
This command shows a list of all pipelines in your project.

### `kedro pipeline create`

This command creates a new modular pipeline in your project. More details in [this section](../04_user_guide/06_pipelines.md#how-do-i-create-modular-pipelines).

### `kedro pipeline package <pipeline_name>`
This command packages a modular pipeline into a [wheel file](https://pythonwheels.com/). More details in [this section](../04_user_guide/06_pipelines.md#how-do-i-package-a-modular-pipeline).

## Using Python
You can also invoke the Kedro CLI as a Python module:

```console
python -m kedro
```
