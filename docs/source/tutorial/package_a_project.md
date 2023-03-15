# Package an entire Kedro project

This section explains how to build your project documentation, and how to bundle your entire project into a Python package.

Kedro also has an advanced feature which supports packaging on a pipeline level allowing you share and reuse pipelines across projects! To read more about this please look at the [section on micro-packaging](../nodes_and_pipelines/micro_packaging.md).

## Add documentation to your project

There are several documentation frameworks for Python projects. This section describes how to use [Sphinx](https://www.sphinx-doc.org) to build the documentation of your Kedro project.

To install Sphinx, run the following:

```bash
pip install sphinx
```

### Set up the Sphinx project files

```{warning}
Currently, Kedro projects are created with a `docs/source` subdirectory, which gets pre-populated with two Sphinx configuration files (`conf.py`, and `index.rst`), needed by the `kedro build-docs` command. This command is deprecated; it will be removed in Kedro version 0.19, along with those dummy files.

Before proceeding with these instructions, back up the contents of `docs/source/index.rst` and remove both `docs/source/conf.py` and `docs/source/index.rst`.
```

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

Your project documentation will be written to the `docs/build/html` directory.

You may want to add project-specific Markdown documentation within the `docs/source` folder of your Kedro project. To be able to build it, follow the [introduction instructions of MyST-Parser](https://myst-parser.readthedocs.io/en/stable/intro.html) and update your `docs/source/index.rst` file to add the markdown files to the table of contents.

### Documentation from docstrings
If you wish to add documentation built from [`docstrings`](https://datacamp.com/community/tutorials/docstrings-python) within your project, you need to make some changes to the Sphinx configuration files found in the `docs/source` directory to use [automatic documentation generation from code](https://www.sphinx-doc.org/en/master/tutorial/automatic-doc-generation.html).

In `conf.py`, add the following to ensure that the `sphinx.ext.autodoc` and `sphinx.ext.autosummary` extensions are specified, and `autosummary_generate` is enabled:

```python
extensions = ["sphinx.ext.autodoc", "sphinx.ext.autosummary"]
autosummary_generate = True
```

Finally, to ensure that you include the autodoc modules in your build, run the following command once **from the `docs` folder**:

```bash
sphinx-apidoc --module-first -o source ../src/<project_name>

```

This will generate a `docs/src/modules.rst` file, as well as other files containing references to your docstrings. To include those in your documentation, make sure your `docs/src/index.rst` has a `modules` entry in the table of contents:

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

## Package your project

To package your project, run the following in your project root directory:

```bash
kedro package
```

Kedro builds the package into the `dist` folder of your project, and creates one `.egg` file and one `.whl` file, which are [Python packaging formats for binary distribution](https://packaging.python.org/).

The resulting `.egg` and `.whl` packages only contain the Python source code of your Kedro pipeline, not any of the `conf`, `data` and `logs` subfolders. This means that you can distribute the project to run elsewhere, such as on a separate computer with different configuration information, dataset and logging locations.

The project configuration is provided separately in a `tar.gz` file, also inside the `dist` folder. This compressed version of the config files excludes any files inside your `local` directory.

### Package recipients

Recipients of the `.egg` and `.whl` files need to have Python and `pip` on their machines, but do not need to have Kedro installed.

A recipient can install the project by calling:

```bash
pip install <path-to-wheel-file>
```

An executable, `kedro-tutorial`, is placed in the `bin` subfolder of the Python install folder, so the project can be run as follows:

```bash
python -m kedro_tutorial
```

```{note}
The recipient will need to add a `conf` subfolder. They also need to add `data` and `logs` if the pipeline loads/saves local data or uses logging.
Alternatively, they can make use of the ``OmegaConfigLoader`` to run the configuration directly from the compressed .tar.gz configuration file by running
kedro run --conf-source <path-to-compressed-config>.tar.gz
```

Once your project is installed, to run your pipelines from any Python code, simply import it:

```python
from kedro_tutorial.__main__ import main

main(
    ["--pipeline", "__default__"]
)  # or simply main() if you don't want to provide any arguments
```

This is equivalent to running `kedro run`, and you can provide all the parameters described by `kedro run --help`.

### Docker, Airflow and other deployment targets

There are various methods to deploy packaged pipelines via Kedro plugins:

* [Kedro-Docker](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-docker) plugin for packaging and shipping Kedro projects within [Docker](https://www.docker.com/) containers.
* [Kedro-Airflow](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-airflow) to convert your Kedro project into an [Airflow](https://airflow.apache.org/) project.
* The [Deployment guide](../deployment/deployment_guide) touches on other deployment targets such as AWS Batch and Prefect, and there is a [range of third-party plugins for deployment](extend_kedro/plugins.md#community-developed-plugins).
