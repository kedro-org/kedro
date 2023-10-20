# Package an entire Kedro project

This section explains how to build project documentation, and how to bundle a Kedro project into a Python package.

Kedro also has an advanced feature which supports packaging on a pipeline level allowing you share and reuse pipelines across projects! To read more about this please look at the [section on micro-packaging](../nodes_and_pipelines/micro_packaging.md).

## Add documentation to a Kedro project

There are several documentation frameworks for Python projects. This section describes how to use [Sphinx](https://www.sphinx-doc.org).

To install Sphinx, run the following:

```bash
pip install sphinx
```

### Set up the Sphinx project files
First, run the following command:

```bash
sphinx-quickstart docs
```

Sphinx will ask a series of configuration questions. The first is as follows:

```text
You have two options for placing the build directory for Sphinx output.
Either, you use a directory "_build" within the root path,
or you separate "source" and "build" directories within the root path.

> Separate source and build directories (y/n)? [n]:
```

Select `y` to separate the build files from the source files, and enter any additional information that Sphinx requests such as the project name and the documentation language, which defaults to English.

### Build HTML documentation

```{warning}
If you previously backed up the contents of `index.rst`, restore them before proceeding.
```

After the quickstart process is complete, you can build the documentation by **navigating to the `docs` directory** and running the following:

```bash
make html
```

Project documentation will be written to the `docs/build/html` directory.

You may want to add project-specific Markdown documentation within the `docs/source` folder of your Kedro project. To be able to build it, follow the [introduction instructions of MyST-Parser](https://myst-parser.readthedocs.io/en/stable/intro.html) and update the `docs/source/index.rst` file to add the markdown files to the table of contents.

### Documentation from docstrings
If you wish to add documentation built from [`docstrings`](https://datacamp.com/community/tutorials/docstrings-python) within your project, you need to make some changes to the Sphinx configuration files found in the `docs/source` directory to use [automatic documentation generation from code](https://www.sphinx-doc.org/en/master/tutorial/automatic-doc-generation.html).

In `conf.py`, add the following to ensure that the `sphinx.ext.autodoc` and `sphinx.ext.autosummary` extensions are specified, and `autosummary_generate` is enabled:

```python
extensions = ["sphinx.ext.autodoc", "sphinx.ext.autosummary"]
autosummary_generate = True
```

Finally, to ensure that you include the autodoc modules in the build, run the following command once **from the `docs` folder**:

```bash
sphinx-apidoc --module-first -o source ../src/<package_name>

```

This will generate a `docs/src/modules.rst` file, as well as other files containing references to any docstrings. To include those in your documentation, make sure `docs/src/index.rst` has a `modules` entry in the table of contents:

```text
.. toctree::

   modules
```

**From the `docs` folder** run the following:

```text
pip install -e ../src
```

Finally, **from the `docs folder`**, run this command to build a full set of documentation that automatically includes docstrings:

```text
make html
```

```{note}
Consult the Sphinx project documentation for [additional options to pass to `sphinx-build`](https://www.sphinx-doc.org/en/master/man/sphinx-build.html). To customise your documentation beyond the basic template, you'll need to adjust the [Sphinx configuration settings](https://www.sphinx-doc.org/en/master/usage/configuration.html) which are stored in `docs/source/conf.py` file.
```

## Package a Kedro project

To package a project, run the following in your project root directory:

```bash
kedro package
```

Kedro builds the package into the `dist` folder of the project as a `.whl` file, which is a [Python packaging format for binary distribution](https://packaging.python.org/en/latest/overview/#python-binary-distributions).

The resulting `.whl` packages only contain the Python source code of the Kedro pipeline, not any of the `conf` and `data` subfolders. This means that you can distribute the project to run elsewhere, such as on a separate computer with different configuration information, dataset and logging locations.

The project configuration is provided separately in a `tar.gz` file, also inside the `dist` folder. This compressed version of the config files excludes any files inside the `local` directory.

### Run a packaged project

To run a packaged project it must first be installed. To install the package from a `.whl` file, you need to have Python and `pip` installed on your machine, but you do not need to have Kedro installed.

To install the project, run the following command:

```bash
pip install <path-to-wheel-file>
```

```{note}
Once the packaged project is installed, you will need to add:

* a `conf` folder
* a `data` folder if the pipeline loads/saves local data

Alternatively, you can make use of the ``OmegaConfigLoader`` to run the configuration directly from the compressed .tar.gz configuration file by running
kedro run --conf-source <path-to-compressed-config>.tar.gz
```

Once your project is installed, it can be run either from the command line or interactively using Python code.

To do a basic run of your installed project from the command line, run `python -m <package_name>`. The packaged project also exposes a command line interface which you can use to modify how your project will be run. To see a list of options, use `python -m <package_name> --help` at the command line.

To run your packaged project interactively using code, you can import `main` from the project:

```python
from <package_name>.__main__ import main

main(
    ["--pipeline", "__default__"]
)  # or simply main() if you don't want to provide any arguments
```

This is equivalent to `python -m <package_name>` at the command line, and you can pass in all the arguments that correspond to the options described by `python -m <package_name> --help`.

### Docker, Airflow and other deployment targets

There are various methods to deploy packaged pipelines via Kedro plugins:

* [Kedro-Docker](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-docker) plugin for packaging and shipping Kedro projects within [Docker](https://www.docker.com/) containers.
* [Kedro-Airflow](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-airflow) to convert your Kedro project into an [Airflow](https://airflow.apache.org/) project.
* The [Deployment guide](../deployment/index) touches on other deployment targets such as AWS Batch and Prefect, and there is a [range of third-party plugins for deployment](../extend_kedro/plugins.md#community-developed-plugins).
