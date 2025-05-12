# Package an entire Kedro project

This section explains how to build project documentation, and how to bundle a Kedro project into a Python package.

Kedro also has an advanced feature which supports packaging on a pipeline level allowing you share and reuse pipelines across projects!

## Add documentation to a Kedro project if you have not selected `docs` tool

!!! note
    These steps are for projects without the `docs` tool option. You can verify this by looking to see if you don't have a `docs` directory in your project.


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

!!! note
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

!!! note
    If you run the packaged project in the interactive environment like IPython or Databricks you can also consume the output of the `main()`
    which returns the `session.run()` output.

```python
from spaceflights.__main__ import main

def run_kedro_pipeline():
   result = main(pipeline_name=<pipeline>)
   do_something_with(<result>)
```

### Docker, Airflow and other deployment targets

There are various methods to deploy packaged pipelines via Kedro plugins:

* [Kedro-Docker](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-docker) plugin for packaging and shipping Kedro projects within [Docker](https://www.docker.com/) containers.
* [Kedro-Airflow](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-airflow) to convert your Kedro project into an [Airflow](https://airflow.apache.org/) project.
* The [Deployment guide](../deploy/index.md) touches on other deployment targets such as AWS Batch and Prefect, and there is a [range of third-party plugins for deployment](../extend/plugins.md#community-developed-plugins).
