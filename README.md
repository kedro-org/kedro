![Kedro Logo Banner](https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/static/img/kedro_banner.png)

-----------------

| Theme | Status |
|------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Python Version | [![Python Version](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8-blue.svg)](https://pypi.org/project/kedro/) |
| Latest PyPI Release | [![PyPI version](https://badge.fury.io/py/kedro.svg)](https://pypi.org/project/kedro/) |
| Latest Conda Release | [![Conda Version](https://img.shields.io/conda/vn/conda-forge/kedro.svg)](https://anaconda.org/conda-forge/kedro) |
| `master` Branch Build | [![CircleCI](https://circleci.com/gh/quantumblacklabs/kedro/tree/master.svg?style=shield)](https://circleci.com/gh/quantumblacklabs/kedro/tree/master) |
| `develop` Branch Build | [![CircleCI](https://circleci.com/gh/quantumblacklabs/kedro/tree/develop.svg?style=shield)](https://circleci.com/gh/quantumblacklabs/kedro/tree/develop) |
| Documentation Build | [![Documentation](https://readthedocs.org/projects/kedro/badge/?version=latest)](https://kedro.readthedocs.io/) |
| License | [![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) |
| Code Style | [![Code Style: Black](https://img.shields.io/badge/code%20style-black-black.svg)](https://github.com/ambv/black) |
| Questions | [![Questions: Stackoverflow "kedro"](https://img.shields.io/badge/stackoverflow%20tag-kedro-yellow)](https://stackoverflow.com/questions/tagged/kedro) |


## What is Kedro?

> "The centre of your data pipeline."

Kedro is an open-source Python framework that applies software engineering best-practice to data and machine-learning pipelines.  You can use it, for example, to optimise the process of taking a machine learning model into a production environment. You can use Kedro to organise a single user project running on a local environment, or collaborate within a team on an enterprise-level project.

We provide a standard approach so that you can:

 - Worry less about how to write production-ready code,
 - Spend more time building data pipelines that are robust, scalable, deployable, reproducible and versioned,
 - Standardise the way that your team collaborates across your project.


## How do I install Kedro?

`kedro` is a Python package built for Python 3.6, 3.7 and 3.8.

To install Kedro from the Python Package Index (PyPI) simply run:

```
pip install kedro
```

You can also install `kedro` using `conda`, a package and environment manager program bundled with Anaconda. With [`conda`](https://kedro.readthedocs.io/en/stable/02_get_started/01_prerequisites.html#virtual-environments) already installed, simply run:

```
conda install -c conda-forge kedro
```

Our [Get Started guide](https://kedro.readthedocs.io/en/stable/02_get_started/01_prerequisites.html) contains full installation instructions, and includes how to set up Python virtual environments.

We also recommend the [frequently asked questions](https://kedro.readthedocs.io/en/stable/11_faq/01_faq.html) and the [API reference documentation](https://kedro.readthedocs.io/en/stable/kedro.html) for additional information.


## What are the main features of Kedro?

![Kedro-Viz Pipeline Visualisation](https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/static/img/pipeline_visualisation.png)
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

The [Kedro documentation](https://kedro.readthedocs.io/en/stable/) includes three examples to help get you started:

-   A typical "Hello World" example, for an [entry-level description of the main Kedro concepts](https://kedro.readthedocs.io/en/stable/02_get_started/03_hello_kedro.html)
-   The more detailed ["spaceflights" tutorial](https://kedro.readthedocs.io/en/stable/03_tutorial/02_tutorial_template.html) to give you hands-on experience as you learn about Kedro

Additional documentation includes:

- An overview of [Kedro architecture](https://kedro.readthedocs.io/en/stable/11_faq/02_architecture_overview.html)
- How to [use the CLI](https://kedro.readthedocs.io/en/stable/09_development/03_commands_reference.html) offered by `kedro_cli.py` (`kedro new`, `kedro run`, ...)

> *Note:* The CLI is a convenient tool for being able to run `kedro` commands but you can also invoke the Kedro CLI as a Python module with `python -m kedro`

Every Kedro function or class has extensive help, which you can call from a Python session as follows if the item is in local scope:

```
from kedro.io import MemoryDataSet
help(MemoryDataSet)
```


## Why does Kedro exist?

Kedro is built upon our collective best-practice (and mistakes) trying to deliver real-world ML applications that have vast amounts of raw unvetted data. We developed Kedro to achieve the following:

 - **Collaboration** on an analytics codebase when different team members have varied exposure to software engineering best-practice
 - A focus on **maintainable data and ML pipelines** as the standard, instead of a singular activity of deploying models in production
 - A way to inspire the creation of **reusable analytics code** so that we never start from scratch when working on a new project
 - **Efficient use of time** because we're able to quickly move from experimentation into production


## The humans behind Kedro

Kedro was originally designed by [Aris Valtazanos](https://github.com/arisvqb) and [Nikolaos Tsaousis](https://github.com/tsanikgr) to solve challenges they faced in their project work.
Their work was later turned into an internal product by [Peteris Erins](https://github.com/Pet3ris), [Ivan Danov](https://github.com/idanov), [Nikolaos Kaltsas](https://github.com/nikos-kal), [Meisam Emamjome](https://github.com/misamae) and [Nikolaos Tsaousis](https://github.com/tsanikgr).

Currently the core Kedro team consists of:

* [Yetunde Dada](https://github.com/yetudada)
* [Ivan Danov](https://github.com/idanov)
* [Richard Westenra](https://github.com/richardwestenra)
* [Dmitrii Deriabin](https://github.com/DmitriiDeriabinQB)
* [Lorena Balan](https://github.com/lorenabalan)
* [Kiyohito Kunii](https://github.com/921kiyo)
* [Zain Patel](https://github.com/mzjp2)
* [Lim Hoang](https://github.com/limdauto)
* [Andrii Ivaniuk](https://github.com/andrii-ivaniuk)
* [Jo Stichbury](https://github.com/stichbury)
* [Laís Carvalho](https://github.com/laisbsc)
* [Merel Theisen](https://github.com/MerelTheisenQB)

Former core team members with significant contributions include: [Gordon Wrigley](https://github.com/tolomea), [Nasef Khan](https://github.com/nakhan98) and [Anton Kirilenko](https://github.com/Flid).

And last but not least, all the open-source contributors whose work went into all Kedro [releases](https://github.com/quantumblacklabs/kedro/blob/master/RELEASE.md).


## Can I contribute?

Yes! Want to help build Kedro? Check out our [guide to contributing to Kedro](https://github.com/quantumblacklabs/kedro/blob/master/CONTRIBUTING.md).


## Where can I learn more?

There is a growing community around Kedro. Have a look at the [Kedro FAQs](https://kedro.readthedocs.io/en/stable/11_faq/01_faq.html#how-can-i-find-out-more-about-kedro) to find projects using Kedro and links to articles, podcasts and talks.


## Who is using Kedro?
- [AI Singapore](https://makerspace.aisingapore.org/2020/08/leveraging-kedro-in-100e/)
- [Caterpillar](https://www.caterpillar.com/)
- [ElementAI](https://www.elementai.com/)
- [Jungle Scout](https://www.junglescout.com/)
- [MercadoLibre Argentina](https://www.mercadolibre.com.ar)
- [Mosaic Data Science](https://www.youtube.com/watch?v=fCWGevB366g)
- [NaranjaX](https://www.youtube.com/watch?v=_0kMmRfltEQ)
- [Open Data Science LatAm](https://www.odsla.org/)
- [Retrieva](https://tech.retrieva.jp/entry/2020/07/28/181414)
- [Roche](https://www.roche.com/)
- [UrbanLogiq](https://urbanlogiq.com/)
- [XP](https://youtu.be/wgnGOVNkXqU?t=2210)

## What licence do you use?

Kedro is licensed under the [Apache 2.0](https://github.com/quantumblacklabs/kedro/blob/master/LICENSE.md) License.


## We're hiring!

Do you want to be part of the team that builds Kedro and [other great products](https://quantumblack.com/labs) at QuantumBlack? If so, you're in luck! QuantumBlack is currently hiring Software Engineers who love using data to drive their decisions. Take a look at [our open positions](https://www.quantumblack.com/careers/current-openings#content) and see if you're a fit.
