# Package a Kedro project

This section explains how to build your project documentation, and how to bundle your project into a Python package.


## Add documentation to your project

Kedro uses the [Sphinx framework](https://www.sphinx-doc.org) and creates a `docs` directory that builds a basic template for project-specific documentation. We recommend that you add your project-specific documentation as markdown in `docs/source` 

If you want to customise your documentation beyond the basic template, refer to the [Sphinx documentation](https://www.sphinx-doc.org/en/master/usage/configuration.html) for details of how to extend `docs/source/conf.py`.

Once you have added any documentation you need, run the following from the project's root directory: 

```bash
kedro build-docs --open
``` 

The HTML documention is built to `docs/build/html/` and opens automatically in a browser tab. 

```{note} 
The `build-docs` command creates documentation based on the code structure of your project. Documentation includes any [`docstrings`](https://datacamp.com/community/tutorials/docstrings-python) defined in your code.
```


## Package your project

To package your project, run the following in your project's root directory:

```bash
kedro package
```

Kedro builds the package into the `dist/` folder of your project, and creates one `.egg` file and one `.whl` file, which are [Python packaging formats for binary distribution](https://packaging.python.org/).

The resulting package only contains the Python source code of your Kedro pipeline, not any of the `conf/`, `data/` and `logs/` subfolders. This means that you can distribute the project to run elsewhere, such as on a separate computer with different configuration, dataset location and logging as. 

### Package recipients

Recipients of the `.egg` and `.whl` files need to have Python and `pip` on their machines, but do not need to have Kedro installed. 

A recipient can install the project into a folder by calling:

```bash
pip install <path-to-wheel-file>
```

An executable, `kedro-tutorial`, is placed in the `bin/` subfolder of the Python installation location, so the project can be run as follows from the installation directory:

```bash
python -m kedro_tutorial
```

```{note}
The recipient will need to add a `conf/` subfolder. They also need to add `data/` and `logs/` if the pipeline loads/saves local data or uses logging.
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

There are several methods to deploy packaged pipelines via 1st party plugins and associated documentation:

* [Kedro-Docker](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-docker) plugin for packaging and shipping Kedro projects within [Docker](https://www.docker.com/) containers.
* [Kedro-Airflow](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-airflow) to convert your Kedro project into an [Airflow](https://airflow.apache.org/) project.
* The [Deployment guide](../deployment/deployment_guide) touches on other deployment targets such as AWS Batch and Prefect.
