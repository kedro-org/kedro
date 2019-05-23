![Kedro Logo Banner](https://raw.githubusercontent.com/quantumblacklabs/kedro/master/img/kedro_banner.jpg)

`develop` | `master`  
----------|---------  
[![CircleCI](https://circleci.com/gh/quantumblacklabs/kedro/tree/develop.svg?style=shield)](https://circleci.com/gh/quantumblacklabs/kedro/tree/develop) | [![CircleCI](https://circleci.com/gh/quantumblacklabs/kedro/tree/master.svg?style=shield)](https://circleci.com/gh/quantumblacklabs/kedro/tree/master)

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Version](https://img.shields.io/badge/python-3.5%20%7C%203.6%20%7C%203.7-blue.svg)](https://pypi.org/project/kedro/)
[![PyPI version](https://badge.fury.io/py/kedro.svg)](https://pypi.org/project/kedro/)
[![Documentation](https://readthedocs.org/projects/kedro/badge/?version=latest)](https://kedro.readthedocs.io/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-black.svg)](https://github.com/ambv/black)

# What is Kedro?

> “The centre of your data pipeline.”

Kedro is a workflow development tool that helps you build data pipelines that are robust, scalable, deployable, reproducible and versioned. We provide a standard approach so that you can:
-   spend more time building your data pipeline,
-   worry less about how to write production-ready code,
-   standardise the way that your team collaborates across your project,
-   work more efficiently.

Kedro was originally designed by [Aris Valtazanos](https://github.com/arisvqb) and [Nikolaos Tsaousis](https://github.com/tsanikgr) to solve challenges they faced in their project work.

## How do I install Kedro?

`kedro` is a Python package. To install it, simply run:

```
pip install kedro
```

For more detailed installation instructions, including how to setup Python virtual environments, please visit our [installation guide](https://kedro.readthedocs.io/en/latest/02_getting_started/02_install.html).

## What are the main features of Kedro?

### 1. Project template and coding standards

- A standard and easy-to-use project template
- Configuration for credentials, logging, data loading and Jupyter Notebooks / Lab
- Test-driven development using `pytest`
- [Sphinx](http://www.sphinx-doc.org/en/master/) integration to produce well-documented code

### 2. Data abstraction and versioning

- Separation of the _compute_ layer from the _data handling_ layer, including support for different data formats and storage options
- Versioning for your data sets and machine learning models

### 3. Modularity and pipeline abstraction

- Support for pure Python functions, `nodes`, to break large chunks of code into small independent sections
- Automatic resolution of dependencies between `nodes`
- (_coming soon_) Visualise your data pipeline with Kedro-Viz, a tool that shows the pipeline structure of Kedro projects

*Note:* Read our [FAQs](https://kedro.readthedocs.io/en/latest/06_resources/01_faq.html#how-does-kedro-compare-to-other-projects) to learn how we differ from workflow managers like Airflow and Luigi.

### 4. Feature extensibility

- A plugin system that injects commands into the Kedro command line interface (CLI)
- (_coming soon_) List of officially supported plugins:
  - Kedro-Airflow, making it easy to prototype your data pipeline in Kedro before deploying to [Airflow](https://github.com/apache/airflow), a workflow scheduler
  - Kedro-Docker, a tool for packing and shipping Kedro projects within containers
- Kedro can be deployed locally, on-premise and cloud (AWS, Azure and GCP) servers, or clusters (EMR, Azure HDinsight, GCP and Databricks)

![Kedro-Viz Pipeline Visualisation](https://raw.githubusercontent.com/quantumblacklabs/kedro/master/img/pipeline_visualisation.png)
*Random pipeline visualisation using Kedro-Viz (coming soon)*

## How do I use Kedro?

Our [documentation](https://kedro.readthedocs.io/en/latest/) explains:

- A typical Kedro workflow
- How to set up the project configuration
- Building your first pipeline
- How to use the CLI offered by `kedro_cli.py` (`kedro new`, `kedro run`, ...)

> *Note:* The CLI is a convenient tool for being able to run `kedro` commands but you can also invoke the Kedro CLI as a Python module with `python -m kedro`

## How do I find Kedro documentation?

This CLI command will open the documentation for your current version of Kedro in a browser:

```
kedro docs
```

Documentation for the latest stable release can be found [here](https://kedro.readthedocs.io/en/latest/). Check these out first:

- [Getting started](https://kedro.readthedocs.io/en/latest/02_getting_started/01_prerequisites.html)
- [Tutorial](https://kedro.readthedocs.io/en/latest/03_tutorial/01_workflow.html)
- [FAQ](https://kedro.readthedocs.io/en/latest/06_resources/01_faq.html)

## Can I contribute?

Yes! Want to help build Kedro? Check out our guide to [contributing](https://github.com/quantumblacklabs/kedro/blob/master/CONTRIBUTING.md).

## How do I upgrade Kedro?

We use [Semantic Versioning](http://semver.org/). The best way to safely upgrade is to check our [release notes](https://github.com/quantumblacklabs/kedro/blob/master/RELEASE.md) for any notable breaking changes.

Once Kedro is installed, you can check your version as follows:

```
kedro --version
```

To later upgrade Kedro to a different version, simply run:

```
pip install kedro -U
```

## What licence do you use?

Kedro is licensed under the [Apache 2.0](https://github.com/quantumblacklabs/kedro/blob/master/LICENSE.md) License.
