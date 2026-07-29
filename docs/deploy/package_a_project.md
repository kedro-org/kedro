# Package an entire Kedro project

This section explains how to build project documentation, and how to bundle a Kedro project into a Python package.

Kedro also has an advanced feature which supports packaging on a pipeline level allowing you share and reuse pipelines across projects!

## Add documentation to a Kedro project if you have not selected `docs` tool

!!! note
    These steps are for projects without the `docs` tool option. You can verify this by looking to see if you don't have a `docs` directory in your project.

If you selected the `docs` tool when running `kedro new`, your project already contains a Sphinx-based documentation setup in the `docs` directory. The steps below use [MkDocs](https://www.mkdocs.org/) instead, which is the documentation tool used for Kedro's own documentation site.

### Install dependencies

Run the following from your project root:

```bash
pip install mkdocs mkdocs-material mkdocstrings[python] mkdocs-autorefs
```

### Configure MkDocs

Create an `mkdocs.yml` file in your project root:

```yaml
site_name: My Project
site_url: https://example.com/
repo_name: my-project
repo_url: https://github.com/my-org/my-project

theme:
  name: material

plugins:
  - search
  - autorefs
  - mkdocstrings:
      handlers:
        python:
          paths: [src]
          options:
            docstring_style: google

nav:
  - Home: index.md
  - API reference: api.md
```

### Add documentation pages

Create a `docs` directory and add two files. Replace `my_project` with the name of your Python package (the value of `python_package` in `pyproject.toml`).

`docs/index.md`:

```markdown
# My Project

Welcome to the documentation for My Project.
```

`docs/api.md`:

```markdown
# API reference

::: my_project
```

### Build and preview

Run the following from your project root to preview the site:

```bash
mkdocs serve
```

Then open `http://127.0.0.1:8000/` in your browser. To build the static site, run:

```bash
mkdocs build
```

The built site is written to the `site/` directory.

## Package a Kedro project

To package a project, run the following in your project root directory:

```bash
kedro package
```

Kedro builds the package into the `dist` folder of the project as a `.whl` file, which is a [Python packaging format for binary distribution](https://packaging.python.org/en/latest/overview/#python-binary-distributions).

The resulting `.whl` packages include the Python source code of the Kedro pipeline, not any of the `conf` and `data` subdirectories. This means that you can distribute the project to run elsewhere, such as on a separate computer with different configuration information, dataset, and logging locations.

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
    * a `data` folder if the pipeline loads or saves local data

You can also use the `OmegaConfigLoader` to run the configuration directly from the compressed `.tar.gz` configuration file by running:

```bash
kedro run --conf-source <path-to-compressed-config>.tar.gz
```

Once your project is installed, it can be run either from the command line or interactively using Python code.

To do a basic run of your installed project from the command line, run `python -m <package_name>`. The packaged project also exposes a command line interface that lets you adjust how your project runs. To see a list of options, use `python -m <package_name> --help` at the command line.

To run your packaged project interactively using code, you can import `main` from the project:

```python
from <package_name>.__main__ import main

main(
    ["--pipelines", "__default__"]
)  # or simply main() if you don't want to provide any arguments
```

This mirrors running `python -m <package_name>` at the command line, and you can pass in all the arguments that correspond to the options described by `python -m <package_name> --help`.

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

There are various methods to deploy packaged pipelines through Kedro plugins:

* [Kedro-Docker](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-docker) plugin for packaging and shipping Kedro projects within [Docker](https://www.docker.com/) containers.
* [Kedro-Airflow](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-airflow) to convert your Kedro project into an [Airflow](https://airflow.apache.org/) project.
* The [Deployment guide](../deploy/index.md) touches on other deployment targets such as AWS Batch and Prefect, and there is a [range of third-party plugins for deployment](../extend/plugins.md#community-developed-plugins).
