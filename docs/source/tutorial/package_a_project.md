# Package an entire Kedro project

This section explains how to build your project documentation, and how to bundle your entire project into a Python package.

Kedro also has an advanced feature which supports packaging on a pipeline level allowing you share and reuse pipelines across projects! To read more about this please look at the [section on micro-packaging](../nodes_and_pipelines/micro_packaging.md).

## Add documentation to your project

Kedro uses the [Sphinx framework](https://www.sphinx-doc.org) to build any documentation that you create about your project.

To install a compatible version of Sphinx, run the following from the project root directory:

```bash
pip install sphinx
```

### Set up the Sphinx project files
Navigate to the `docs` directory of your Kedro project. Before Kedro version 0.19, the `docs/source` subdirectory was pre-populated with two Sphinx configuration files (`conf.py`, and `index.rst`) which the `kedro build-docs` command needed.

From Kedro version 0.19 that command is deprecated, and those files will no longer exist. If you have used an earlier version of Kedro to create your project, and want to follow the following instructions to build the documentation without using `kedro build-docs`, you should delete the two files and the `source` subdirectory so that your project's `docs` directory is empty.

Navigate to the empty `docs` directory in the terminal, and run the following command:

```bash
sphinx-quickstart
```

Sphinx will ask a series of configuration questions. The first is as follows:

```text
You have two options for placing the build directory for Sphinx output.
Either, you use a directory "_build" within the root path,
or you separate "source" and "build" directories within the root path.

> Separate source and build directories (y/n)? [n]:
```

In the following instructions, we assume that you select `y` to separate the built files from the source files, but you can choose either option safely and continue to follow the process.

Enter any additional information that Sphinx requests such as the project name and the documentation language (which defaults to English).


### Build HTML documentation
When the quickstart process is complete, you may add project-specific markdown documentation within the `docs/source` folder of your Kedro project and update `docs/source/index.rst` to add it to the table of contents.

To build the documentation, run the following **from the `docs` directory**:

```bash
make html
```

Your project documentation is built to the `docs/build/html` directory.

### Documentation from docstrings
If you wish to add documentation built from [`docstrings`](https://datacamp.com/community/tutorials/docstrings-python) within your project, you need to make the following changes to the Sphinx configuration files found in the `docs/source` directory to use [automatic documentation generation from code](https://www.sphinx-doc.org/en/master/tutorial/automatic-doc-generation.html).

Add the following to the beginning of the `docs/source/conf.py` file:

```python
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join("..", "..", "src")))
```

Also in `conf.py`, add the following to ensure that the `sphinx.ext.autodoc` and `sphinx.ext.autosummary` extensions are specified, and `autosummary_generate` is enabled:

```python
extensions = ["sphinx.ext.autodoc", "sphinx.ext.autosummary"]
autosummary_generate = True
```

Finally, to ensure that you include the autodoc modules in your build, create a separate file called `api.rst` in `docs/source`. You must replace `project_name` with the name of your project:

```text

.. autosummary::
   :toctree: generated

   <project_name>
```

Add the new file to `docs/src/index.rst` to include the automatically built documentation in the table of contents:

```text
.. toctree::

   api
```

**Run `make html` from the `docs` folder** to build a full set of documentation that automatically includes docstrings.


```{note}
Consult the Sphinx project documentation for [additional options to pass to `sphinx-build`](https://www.sphinx-doc.org/en/master/man/sphinx-build.html). To customise your documentation beyond the basic template, you'll need to adjust the [Sphinx configuration settings](https://www.sphinx-doc.org/en/master/usage/configuration.html) which are stored in `docs/source/conf.py` file.
```

## Package your project

To package your project, run the following in your project root directory:

```bash
kedro package
```

Kedro builds the package into the `dist` folder of your project, and creates one `.egg` file and one `.whl` file, which are [Python packaging formats for binary distribution](https://packaging.python.org/).

The resulting package only contains the Python source code of your Kedro pipeline, not any of the `conf`, `data` and `logs` subfolders. This means that you can distribute the project to run elsewhere, such as on a separate computer with different configuration information, dataset and logging locations.

We recommend that you document the configuration required (parameters and catalog) in the local `README.md` file for any project recipients.

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
