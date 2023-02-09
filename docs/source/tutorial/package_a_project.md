# Package an entire Kedro project

This section explains how to build your project documentation, and how to bundle your entire project into a Python package.

Kedro also has an advanced feature which supports packaging on a pipeline level allowing you share and reuse pipelines across projects! To read more about this please look at the [section on micro-packaging](../nodes_and_pipelines/micro_packaging.md).


## Add documentation to your project

Kedro uses the [Sphinx framework](https://www.sphinx-doc.org) to build markdown documentation that you create about your project, in combination with any [`docstrings`](https://datacamp.com/community/tutorials/docstrings-python) that are defined in your code.

Within the Kedro project structure there is a `docs` directory for Sphinx configuration files and to store project-specific markdown documentation.

Add the documentation you need, and update `docs/source/index.rst` to define a table of contents

Next, run the following from the project root directory:

```bash
sphinx-build -M html docs/source docs/build -a
```

The command is configured to build the documentation as HTML, taking `docs/source` as the `sourcedir` and `/docs/build` as the `outputdir`.

Consult the Sphinx project documentation for [additional options to pass to `sphinx-build`](https://www.sphinx-doc.org/en/master/man/sphinx-build.html). To customise your documentation beyond the basic template, you'll need to adjust the [Sphinx configuration settings](https://www.sphinx-doc.org/en/master/usage/configuration.html) which are stored in `docs/source/conf.py` file.

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
