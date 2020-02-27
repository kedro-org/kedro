![Kedro Logo Banner](https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/img/kedro_banner.png)

-----------------

| Theme | Status |
|------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Latest Release | [![PyPI version](https://badge.fury.io/py/kedro.svg)](https://pypi.org/project/kedro/) |
| Python Version | [![Python Version](https://img.shields.io/badge/python-3.5%20%7C%203.6%20%7C%203.7-blue.svg)](https://pypi.org/project/kedro/) |
| `master` Branch Build | [![CircleCI](https://circleci.com/gh/quantumblacklabs/kedro/tree/master.svg?style=shield)](https://circleci.com/gh/quantumblacklabs/kedro/tree/master) |
| `develop` Branch Build | [![CircleCI](https://circleci.com/gh/quantumblacklabs/kedro/tree/develop.svg?style=shield)](https://circleci.com/gh/quantumblacklabs/kedro/tree/develop) |
| Documentation Build | [![Documentation](https://readthedocs.org/projects/kedro/badge/?version=latest)](https://kedro.readthedocs.io/) |
| License | [![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) |
| Code Style | [![Code Style: Black](https://img.shields.io/badge/code%20style-black-black.svg)](https://github.com/ambv/black) |
| Questions | [![Questions: Stackoverflow "kedro"](https://img.shields.io/badge/stackoverflow%20tag-kedro-yellow)](https://stackoverflow.com/questions/tagged/kedro) |


## What is Kedro?

> "The centre of your data pipeline."

Kedro is a development workflow framework that implements software engineering best-practice for data pipelines with an eye towards productionising machine learning models. We provide a standard approach so that you can:
 - Worry less about how to write production-ready code,
 - Spend more time building data pipelines that are robust, scalable, deployable, reproducible and versioned,
 - And, standardise the way that your team collaborates across your project.


## How do I install Kedro?

`kedro` is a Python package. To install it, simply run:

```
pip install kedro
```

See more detailed installation instructions, including how to setup Python virtual environments, in our [installation guide](https://kedro.readthedocs.io/en/stable/02_getting_started/02_install.html) and get started with our ["Hello Word"](https://kedro.readthedocs.io/en/stable/02_getting_started/04_hello_world.html) example.


## Why does Kedro exist?

Kedro is built upon our collective best-practice (and mistakes) trying to deliver real-world ML applications that have vast amounts of dirty data. We developed Kedro to achieve the following:

 - **Collaboration** on an analytics codebase when different team members have varied exposure to software engineering best-practice
 - Focussing on **maintainable data and ML pipelines** as the standard, instead of a singular activity of deploying models in production
 - A way to inspire the creation of **reusable analytics code** so that we never start from scratch when working on a new project
 - **Efficient use of time** because we're able to quickly move from experimentation into production

Kedro was originally designed by [Aris Valtazanos](https://github.com/arisvqb) and [Nikolaos Tsaousis](https://github.com/tsanikgr) to solve challenges they faced in their project work. This work was later turned into a product thanks to the following contributors:
[Ivan Danov](https://github.com/idanov), [Dmitrii Deriabin](https://github.com/DmitryDeryabin), [Gordon Wrigley](https://github.com/tolomea), [Yetunde Dada](https://github.com/yetudada), [Nasef Khan](https://github.com/nakhan98), [Kiyohito Kunii](https://github.com/921kiyo), [Nikolaos Kaltsas](https://github.com/nikos-kal), [Meisam Emamjome](https://github.com/misamae), [Peteris Erins](https://github.com/Pet3ris), [Lorena Balan](https://github.com/lorenabalan), [Richard Westenra](https://github.com/richardwestenra) and [Anton Kirilenko](https://github.com/Flid).


## What are the main features of Kedro?

![Kedro-Viz Pipeline Visualisation](https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/img/pipeline_visualisation.png)
*A pipeline visualisation generated using [Kedro-Viz](https://github.com/quantumblacklabs/kedro-viz)*


| Feature | What is this? |
|----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Project Template | A standard, modifiable and easy-to-use project template based on [Cookiecutter Data Science](https://github.com/drivendata/cookiecutter-data-science/). |
| Data Catalog | A series of lightweight data connectors used for saving and loading data across many different file formats and file systems including local and network file systems, cloud object stores, and HDFS. The Data Catalog also includes data and model versioning for file-based systems. Used with a Python or YAML API. |
| Pipeline Abstraction | Automatic resolution of dependencies between pure Python functions and data pipeline visualisation using [Kedro-Viz](https://github.com/quantumblacklabs/kedro-viz). |
| The Journal | An ability to reproduce pipeline runs with saved pipeline run results. |
| Coding Standards | Test-driven development using [`pytest`](https://github.com/pytest-dev/pytest), produce well-documented code using [Sphinx](http://www.sphinx-doc.org/en/master/), create linted code with support for [`flake8`](https://github.com/PyCQA/flake8), [`isort`](https://github.com/timothycrosley/isort) and [`black`](https://github.com/psf/black) and make use of the standard Python logging library. |
| Flexible Deployment | Deployment strategies that include the use of Docker with [Kedro-Docker](https://github.com/quantumblacklabs/kedro-docker), conversion of Kedro pipelines into Airflow DAGs with [Kedro-Airflow](https://github.com/quantumblacklabs/kedro-airflow), leveraging a REST API endpoint with Kedro-Server _(coming soon)_ and serving Kedro pipelines as a Python package. Kedro can be deployed locally, on-premise and cloud (AWS, Azure and Google Cloud Platform) servers, or clusters (EMR, EC2, Azure HDinsight and Databricks). |


## How do I use Kedro?

Our [documentation](https://kedro.readthedocs.io/en/stable/) explains:

- Best-practice on how to [get started using Kedro](https://kedro.readthedocs.io/en/stable/02_getting_started/01_prerequisites.html)
- A ["Hello World" data and ML pipeline example](https://kedro.readthedocs.io/en/stable/02_getting_started/04_hello_world.html) based on the **Iris dataset**
- A two-hour [Spaceflights tutorial](https://kedro.readthedocs.io/en/stable/03_tutorial/01_workflow.html) that teaches you beginner to intermediate functionality
- How to [use the CLI](https://kedro.readthedocs.io/en/stable/06_resources/03_commands_reference.html) offered by `kedro_cli.py` (`kedro new`, `kedro run`, ...)
- An overview of [Kedro architecture](https://kedro.readthedocs.io/en/stable/06_resources/02_architecture_overview.html)
- [Frequently asked questions (FAQs)](https://kedro.readthedocs.io/en/stable/06_resources/01_faq.html)

Documentation for the latest stable release can be found [here](https://kedro.readthedocs.io/en/stable/). You can also run `kedro docs` from your CLI and open the documentation for your current version of Kedro in a browser.

> *Note:* The CLI is a convenient tool for being able to run `kedro` commands but you can also invoke the Kedro CLI as a Python module with `python -m kedro`

*Note:* Read our [FAQs](https://kedro.readthedocs.io/en/stable/06_resources/01_faq.html#how-does-kedro-compare-to-other-projects) to learn how we differ from workflow managers like Airflow and Luigi.


## Can I contribute?

Yes! Want to help build Kedro? Check out our guide to [contributing](https://github.com/quantumblacklabs/kedro/blob/master/CONTRIBUTING.md).


## Where can I learn more?

There is a growing community around Kedro. Have a look at our [FAQs](https://kedro.readthedocs.io/en/stable/06_resources/01_faq.html#where-can-i-learn-more) to find projects using Kedro and links to articles, podcasts and talks.


## What licence do you use?

Kedro is licensed under the [Apache 2.0](https://github.com/quantumblacklabs/kedro/blob/master/LICENSE.md) License.


## We're hiring!

Do you want to be part of the team that builds Kedro and [other great products](https://quantumblack.com/labs) at QuantumBlack? If so, you're in luck! QuantumBlack is currently hiring Software Engineers who love using data to drive their decisions. Take a look at [our open positions](https://www.quantumblack.com/careers/current-openings#content) and see if you're a fit.
