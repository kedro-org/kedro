# Package a project

This section explains how to build your project documentation, and how to bundle your project into a Python package.

## Add documentation to your project

To generate project-specific documentation, run `kedro build-docs` in the project's root directory. Kedro builds the resulting HTML files in `docs/build/html/`. To browse the documentation generated, open `docs/build/html/index.html` in your browser, or run `kedro build-docs --open` to open the documentation automatically after it builds.

The `build-docs` command creates documentation based on the code structure of your project. Documentation includes any [`docstrings`](https://datacamp.com/community/tutorials/docstrings-python) defined in your code.

Kedro uses the [Sphinx](https://www.sphinx-doc.org) framework, so if you want to customise your documentation, please refer to `docs/source/conf.py` and the [corresponding section of the Sphinx documentation](https://www.sphinx-doc.org/en/master/usage/configuration.html).


## Package your project

To package your project, run the following in your project's root directory:

```bash
kedro package
```

Kedro builds the package into the `dist/` folder of your project, and creates one `.egg` file and one `.whl` file, which are [Python packaging formats for binary distribution](https://packaging.python.org/).

The resulting package only contains the Python source code of your Kedro pipeline, not any of the `conf/`, `data/` and `logs/` subfolders. This means that you can distribute the project to run elsewhere, such as on a separate computer with different configuration, data and logging. When distributed, the packaged project must be run from within a directory that contains the `conf/` subfolder (and `data/` and `logs/` if your pipeline loads/saves local data or uses logging).

Recipients of the `.egg` and `.whl` files need to have Python and `pip` on their machines, but do not need to have Kedro installed. The project is installed to the root of a folder with the relevant `conf/`, `data/` and `logs/` subfolders, by navigating to the root and calling:

```bash
pip install <path-to-wheel-file>
```

For example, having installed project `kedro-spaceflights` and package `kedro_spaceflights`, a recipient can run the Kedro project as follows from the root of the project:

```bash
python -m kedro_spaceflights
```

An executable, `kedro-spaceflights`, is also placed in the `bin/` subfolder of the Python installation location.

Once your project is installed, to run your pipelines from any Python code, simply import it:

```python
from kedro_spaceflights.__main__ import main

main(
    ["--pipeline", "__default__"]
)  # or simply main() if you don't want to provide any arguments
```

This is equivalent to running `kedro run`, and you can provide all the parameters described by `kedro run --help`.

### Docker, Airflow and Deployment

There are several methods to deploy packaged pipelines via 1st party plugins and associated documentation:

* [Kedro-Docker](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-docker) plugin for packaging and shipping Kedro projects within [Docker](https://www.docker.com/) containers.
* [Kedro-Airflow](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-airflow) to convert your Kedro project into an [Airflow](https://airflow.apache.org/) project.
* The [Deployment guide](../deployment/deployment_guide) touches on other deployment targets such as AWS Batch and Prefect.
